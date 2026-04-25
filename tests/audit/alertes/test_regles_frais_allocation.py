"""Tests for S12 alert rules R1-R11 (frais + allocation)."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from src.audit.alertes.frais import (
    detecter_R1, detecter_R2, detecter_R3, detecter_R4, detecter_R5, detecter_R6,
)
from src.audit.alertes.allocation import (
    detecter_R7, detecter_R8, detecter_R9, detecter_R10, detecter_R11,
)
from src.audit.alertes.base import Severite


def _ligne(enveloppe="CTO", classe_actif="actions", montant_eur=10000.0,
           libelle_libre="ETF World", etf_ticker="IWDA", date_acquisition=None):
    return MagicMock(
        enveloppe=enveloppe, classe_actif=classe_actif, montant_eur=montant_eur,
        libelle_libre=libelle_libre, etf_ticker=etf_ticker, date_acquisition=date_acquisition,
        prix_revient_eur=montant_eur, quantite=10.0,
    )


# ── R1: AV frais UC ──────────────────────────────────────────────────────────

def test_R1_triggers_on_high_frais_uc():
    profil = MagicMock(
        assurances_vie=[{"frais_uc": 0.015, "encours": 50000}],
        composition_actuelle=[],
    )
    alerte = detecter_R1(profil)
    assert alerte is not None
    assert alerte.code == "R1"
    assert alerte.severite == Severite.ROUGE
    assert alerte.gain_eur_annuel > 0


def test_R1_no_trigger_low_frais():
    profil = MagicMock(
        assurances_vie=[{"frais_uc": 0.005, "encours": 50000}],
        composition_actuelle=[],
    )
    assert detecter_R1(profil) is None


def test_R1_no_trigger_low_encours():
    profil = MagicMock(
        assurances_vie=[{"frais_uc": 0.015, "encours": 10000}],
        composition_actuelle=[],
    )
    assert detecter_R1(profil) is None


def test_R1_no_av():
    profil = MagicMock(assurances_vie=None, composition_actuelle=[])
    assert detecter_R1(profil) is None


# ── R2: ETF en AV ────────────────────────────────────────────────────────────

def test_R2_triggers_on_av_etf():
    pos = MagicMock(enveloppe="AV", montant_actuel=50000.0)
    profil = MagicMock(positions_detaillees=[pos], composition_actuelle=[])
    alerte = detecter_R2(profil)
    assert alerte is not None
    assert alerte.code == "R2"


def test_R2_no_trigger_low_amount():
    pos = MagicMock(enveloppe="AV", montant_actuel=5000.0)
    profil = MagicMock(positions_detaillees=[pos], composition_actuelle=[])
    assert detecter_R2(profil) is None


# ── R3: SCPI frais ───────────────────────────────────────────────────────────

def test_R3_triggers_on_scpi():
    ligne = _ligne(classe_actif="SCPI", montant_eur=30000.0)
    profil = MagicMock(composition_actuelle=[ligne], frais_entree_scpi=None)
    alerte = detecter_R3(profil)
    assert alerte is not None
    assert alerte.code == "R3"


def test_R3_no_trigger_low_frais():
    ligne = _ligne(classe_actif="SCPI", montant_eur=30000.0)
    profil = MagicMock(composition_actuelle=[ligne], frais_entree_scpi=0.05)
    assert detecter_R3(profil) is None


def test_R3_no_scpi():
    profil = MagicMock(composition_actuelle=[], frais_entree_scpi=None)
    assert detecter_R3(profil) is None


# ── R4: Fonds actifs TER ─────────────────────────────────────────────────────

def test_R4_triggers_on_fonds_actifs():
    ligne = _ligne(classe_actif="OPCVM", montant_eur=20000.0)
    profil = MagicMock(composition_actuelle=[ligne], ter_fonds_actifs=0.025)
    alerte = detecter_R4(profil)
    assert alerte is not None
    assert alerte.code == "R4"


def test_R4_no_trigger_no_ter_field():
    ligne = _ligne(classe_actif="OPCVM", montant_eur=20000.0)
    profil = MagicMock(composition_actuelle=[ligne], ter_fonds_actifs=None)
    assert detecter_R4(profil) is None


# ── R5: Frais courtage ───────────────────────────────────────────────────────

def test_R5_triggers_on_high_courtage():
    profil = MagicMock(
        frais_courtier_par_transaction=5.0,
        volume_ordres_annuel=None,
    )
    alerte = detecter_R5(profil)
    assert alerte is not None
    assert alerte.code == "R5"
    assert alerte.gain_eur_annuel > 0


def test_R5_no_trigger_low_courtage():
    profil = MagicMock(frais_courtier_par_transaction=0.5, volume_ordres_annuel=None)
    assert detecter_R5(profil) is None


# ── R6: Fond de fonds ────────────────────────────────────────────────────────

def test_R6_triggers_fond_de_fonds():
    profil = MagicMock(fond_de_fonds=True, patrimoine_financier_total=100000.0)
    alerte = detecter_R6(profil)
    assert alerte is not None
    assert alerte.code == "R6"
    assert alerte.severite == Severite.ROUGE


def test_R6_no_trigger():
    profil = MagicMock(fond_de_fonds=False, patrimoine_financier_total=100000.0)
    assert detecter_R6(profil) is None


# ── R7: Cash >50% ────────────────────────────────────────────────────────────

def test_R7_triggers_on_excess_cash():
    ligne_cash = _ligne(classe_actif="LIQUIDITES", montant_eur=60000.0)
    profil = MagicMock(
        age=35,
        patrimoine_financier_total=100000.0,
        composition_actuelle=[ligne_cash],
        allocation_cible_bogleheads=MagicMock(liquidites=0.6),
    )
    alerte = detecter_R7(profil)
    assert alerte is not None
    assert alerte.code == "R7"


def test_R7_no_trigger_age_55():
    profil = MagicMock(age=55, patrimoine_financier_total=100000.0, composition_actuelle=[])
    assert detecter_R7(profil) is None


def test_R7_no_trigger_low_cash():
    ligne_actions = _ligne(classe_actif="actions", montant_eur=80000.0)
    profil = MagicMock(
        age=35,
        patrimoine_financier_total=100000.0,
        composition_actuelle=[ligne_actions],
    )
    assert detecter_R7(profil) is None


# ── R8: Sous-exposition actions ──────────────────────────────────────────────

def test_R8_triggers_young_low_actions():
    alloc = MagicMock(actions=0.10)
    profil = MagicMock(
        age=35,
        allocation_cible_bogleheads=alloc,
        patrimoine_financier_total=100000.0,
    )
    alerte = detecter_R8(profil)
    assert alerte is not None
    assert alerte.code == "R8"


def test_R8_no_trigger_adequate_actions():
    alloc = MagicMock(actions=0.60)
    profil = MagicMock(
        age=35,
        allocation_cible_bogleheads=alloc,
        patrimoine_financier_total=100000.0,
    )
    assert detecter_R8(profil) is None


def test_R8_no_trigger_age_45():
    alloc = MagicMock(actions=0.05)
    profil = MagicMock(
        age=50,
        allocation_cible_bogleheads=alloc,
        patrimoine_financier_total=100000.0,
    )
    assert detecter_R8(profil) is None


# ── R9: 100% fonds euros ─────────────────────────────────────────────────────

def test_R9_triggers_100pct_fonds_euros():
    ligne_fe = _ligne(enveloppe="AV", classe_actif="FONDS_EURO", montant_eur=50000.0)
    profil = MagicMock(
        age=35,
        composition_actuelle=[ligne_fe],
    )
    alerte = detecter_R9(profil)
    assert alerte is not None
    assert alerte.code == "R9"


def test_R9_no_trigger_mixed_av():
    ligne_fe = _ligne(enveloppe="AV", classe_actif="FONDS_EURO", montant_eur=30000.0)
    ligne_uc = _ligne(enveloppe="AV", classe_actif="actions", montant_eur=20000.0)
    profil = MagicMock(age=35, composition_actuelle=[ligne_fe, ligne_uc])
    assert detecter_R9(profil) is None


def test_R9_no_trigger_age_50():
    ligne_fe = _ligne(enveloppe="AV", classe_actif="FONDS_EURO", montant_eur=50000.0)
    profil = MagicMock(age=55, composition_actuelle=[ligne_fe])
    assert detecter_R9(profil) is None


# ── R10: Diversification ─────────────────────────────────────────────────────

def test_R10_triggers_single_class():
    ligne1 = _ligne(classe_actif="actions", montant_eur=50000.0)
    ligne2 = _ligne(classe_actif="actions", montant_eur=30000.0)
    profil = MagicMock(composition_actuelle=[ligne1, ligne2])
    alerte = detecter_R10(profil)
    assert alerte is not None
    assert alerte.code == "R10"


def test_R10_no_trigger_3_classes():
    lignes = [
        _ligne(classe_actif="actions"),
        _ligne(classe_actif="obligations"),
        _ligne(classe_actif="immobilier"),
    ]
    profil = MagicMock(composition_actuelle=lignes)
    assert detecter_R10(profil) is None


def test_R10_no_trigger_empty():
    profil = MagicMock(composition_actuelle=[])
    assert detecter_R10(profil) is None


# ── R11: Sur-concentration ───────────────────────────────────────────────────

def test_R11_triggers_concentration():
    ligne = _ligne(etf_ticker="IWDA", montant_eur=40000.0)
    profil = MagicMock(
        composition_actuelle=[ligne],
        patrimoine_financier_total=100000.0,
    )
    alerte = detecter_R11(profil)
    assert alerte is not None
    assert alerte.code == "R11"
    assert alerte.ligne_concernee == "IWDA"


def test_R11_no_trigger_balanced():
    lignes = [_ligne(etf_ticker=f"ETF{i}", montant_eur=5000.0) for i in range(10)]
    profil = MagicMock(
        composition_actuelle=lignes,
        patrimoine_financier_total=100000.0,
    )
    assert detecter_R11(profil) is None


def test_R11_no_trigger_zero_patrimoine():
    ligne = _ligne(etf_ticker="VWCE", montant_eur=40000.0)
    profil = MagicMock(composition_actuelle=[ligne], patrimoine_financier_total=0.0)
    assert detecter_R11(profil) is None
