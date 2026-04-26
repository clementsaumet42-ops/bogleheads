"""Tests for S12 alert rules R12-R40 (fiscalité, config, liquidité, épargne, crédit, transmission, hygiène, bonus)."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.audit.alertes.base import Severite
from src.audit.alertes.bonus import (
    detecter_R36,
    detecter_R37,
    detecter_R38,
    detecter_R39,
    detecter_R40,
)
from src.audit.alertes.configuration import detecter_R19, detecter_R20
from src.audit.alertes.credit import detecter_R29, detecter_R30, detecter_R31
from src.audit.alertes.epargne_salariale import (
    detecter_R25,
    detecter_R26,
    detecter_R27,
    detecter_R28,
)
from src.audit.alertes.fiscalite import (
    detecter_R12,
    detecter_R13,
    detecter_R14,
    detecter_R15,
    detecter_R16,
    detecter_R17,
    detecter_R18,
)
from src.audit.alertes.hygiene import detecter_R35
from src.audit.alertes.liquidite import detecter_R21, detecter_R22, detecter_R23, detecter_R24
from src.audit.alertes.transmission import detecter_R32, detecter_R33, detecter_R34


def _ligne(
    enveloppe="CTO",
    classe_actif="actions",
    montant_eur=10000.0,
    libelle_libre="ETF World",
    etf_ticker="IWDA",
    date_acquisition=None,
):
    return MagicMock(
        enveloppe=enveloppe,
        classe_actif=classe_actif,
        montant_eur=montant_eur,
        libelle_libre=libelle_libre,
        etf_ticker=etf_ticker,
        date_acquisition=date_acquisition,
    )


# ── R12: ETF DIST en CTO ─────────────────────────────────────────────────────


def test_R12_triggers_dist_cto_high_tmi():
    ligne = _ligne(enveloppe="CTO", etf_ticker="IWDA DIST", montant_eur=50000.0)
    profil = MagicMock(tmi=0.30, composition_actuelle=[ligne], patrimoine_financier_total=50000.0)
    alerte = detecter_R12(profil)
    assert alerte is not None
    assert alerte.code == "R12"
    assert alerte.severite == Severite.ROUGE


def test_R12_no_trigger_low_tmi():
    ligne = _ligne(enveloppe="CTO", etf_ticker="IWDA DIST", montant_eur=50000.0)
    profil = MagicMock(tmi=0.11, composition_actuelle=[ligne])
    assert detecter_R12(profil) is None


def test_R12_no_trigger_acc_etf():
    ligne = _ligne(enveloppe="CTO", etf_ticker="IWDA ACC", montant_eur=50000.0)
    profil = MagicMock(tmi=0.30, composition_actuelle=[ligne])
    assert detecter_R12(profil) is None


# ── R13: PEA fonds actifs ────────────────────────────────────────────────────


def test_R13_triggers_pea_fonds_actifs():
    ligne = _ligne(enveloppe="PEA", classe_actif="OPCVM", montant_eur=20000.0)
    profil = MagicMock(composition_actuelle=[ligne])
    alerte = detecter_R13(profil)
    assert alerte is not None
    assert alerte.code == "R13"


def test_R13_no_trigger_pea_etf():
    ligne = _ligne(enveloppe="PEA", classe_actif="actions", montant_eur=20000.0)
    profil = MagicMock(composition_actuelle=[ligne])
    assert detecter_R13(profil) is None


# ── R14: AV < 8 ans ──────────────────────────────────────────────────────────


def test_R14_triggers_young_av():
    ligne = _ligne(enveloppe="AV", date_acquisition="2023-01-01")
    profil = MagicMock(composition_actuelle=[ligne])
    alerte = detecter_R14(profil)
    assert alerte is not None
    assert alerte.code == "R14"


def test_R14_no_trigger_old_av():
    ligne = _ligne(enveloppe="AV", date_acquisition="2010-01-01")
    profil = MagicMock(composition_actuelle=[ligne])
    assert detecter_R14(profil) is None


# ── R15: AV < 8 ans non alimentée ───────────────────────────────────────────


def test_R15_triggers():
    ligne = _ligne(enveloppe="AV", date_acquisition="2022-01-01")
    profil = MagicMock(composition_actuelle=[ligne], est_en_couple=False, tmi=0.30)
    alerte = detecter_R15(profil)
    assert alerte is not None
    assert alerte.code == "R15"


# ── R16: PER non alimenté ────────────────────────────────────────────────────


def test_R16_triggers():
    profil = MagicMock(plafond_per_non_utilise=5000.0, tmi=0.41)
    alerte = detecter_R16(profil)
    assert alerte is not None
    assert alerte.code == "R16"
    assert alerte.gain_eur_annuel == round(5000.0 * 0.41, 0)


def test_R16_no_trigger_low_tmi():
    profil = MagicMock(plafond_per_non_utilise=5000.0, tmi=0.11)
    assert detecter_R16(profil) is None


def test_R16_no_trigger_no_plafond():
    profil = MagicMock(plafond_per_non_utilise=0.0, tmi=0.41)
    assert detecter_R16(profil) is None


# ── R17: Plafond PEA non utilisé ─────────────────────────────────────────────


def test_R17_triggers_underused_pea():
    ligne = _ligne(enveloppe="PEA", montant_eur=50000.0)
    profil = MagicMock(age=35, composition_actuelle=[ligne])
    alerte = detecter_R17(profil)
    assert alerte is not None
    assert alerte.code == "R17"


def test_R17_no_trigger_full_pea():
    ligne = _ligne(enveloppe="PEA", montant_eur=148000.0)
    profil = MagicMock(age=35, composition_actuelle=[ligne])
    assert detecter_R17(profil) is None


# ── R18: Donation ────────────────────────────────────────────────────────────


def test_R18_triggers():
    profil = MagicMock(age=55, a_utilise_donation=False, patrimoine_financier_total=200000.0)
    alerte = detecter_R18(profil)
    assert alerte is not None
    assert alerte.severite == Severite.VERT


def test_R18_no_trigger_already_used():
    profil = MagicMock(age=55, a_utilise_donation=True, patrimoine_financier_total=200000.0)
    assert detecter_R18(profil) is None


# ── R19: PEA non ouvert ──────────────────────────────────────────────────────


def test_R19_triggers_no_pea():
    profil = MagicMock(age=30, composition_actuelle=[], enveloppes_disponibles={})
    alerte = detecter_R19(profil)
    assert alerte is not None
    assert alerte.code == "R19"
    assert alerte.severite == Severite.ROUGE


def test_R19_no_trigger_has_pea():
    ligne = _ligne(enveloppe="PEA")
    profil = MagicMock(age=30, composition_actuelle=[ligne], enveloppes_disponibles={})
    assert detecter_R19(profil) is None


def test_R19_no_trigger_age_40():
    profil = MagicMock(age=45, composition_actuelle=[], enveloppes_disponibles={})
    assert detecter_R19(profil) is None


# ── R20: Clause bénéficiaire ─────────────────────────────────────────────────


def test_R20_triggers_no_clause():
    ligne = _ligne(enveloppe="AV")
    profil = MagicMock(composition_actuelle=[ligne], clause_beneficiaire_renseignee=False)
    alerte = detecter_R20(profil)
    assert alerte is not None
    assert alerte.code == "R20"


def test_R20_no_trigger_clause_set():
    ligne = _ligne(enveloppe="AV")
    profil = MagicMock(composition_actuelle=[ligne], clause_beneficiaire_renseignee=True)
    assert detecter_R20(profil) is None


# ── R21: Épargne précaution insuffisante ─────────────────────────────────────


def test_R21_triggers():
    profil = MagicMock(charges_mensuelles=3000.0, epargne_precaution=5000.0)
    alerte = detecter_R21(profil)
    assert alerte is not None
    assert alerte.code == "R21"
    assert alerte.severite == Severite.ROUGE


def test_R21_no_trigger_adequate():
    profil = MagicMock(charges_mensuelles=2000.0, epargne_precaution=10000.0)
    assert detecter_R21(profil) is None


def test_R21_no_trigger_no_data():
    profil = MagicMock(charges_mensuelles=None, epargne_precaution=None)
    assert detecter_R21(profil) is None


# ── R22: Livret A ────────────────────────────────────────────────────────────


def test_R22_triggers_no_livret():
    profil = MagicMock(a_livret_a=False, composition_actuelle=[])
    alerte = detecter_R22(profil)
    assert alerte is not None
    assert alerte.code == "R22"


def test_R22_no_trigger_has_livret():
    profil = MagicMock(a_livret_a=True, composition_actuelle=[])
    assert detecter_R22(profil) is None


# ── R23: Excès de liquidités ─────────────────────────────────────────────────


def test_R23_triggers_excess_cash():
    profil = MagicMock(charges_mensuelles=2000.0, epargne_precaution=30000.0)
    alerte = detecter_R23(profil)
    assert alerte is not None
    assert alerte.code == "R23"
    assert alerte.gain_eur_annuel > 0


def test_R23_no_trigger_normal_cash():
    profil = MagicMock(charges_mensuelles=2000.0, epargne_precaution=10000.0)
    assert detecter_R23(profil) is None


# ── R24: Livret A non plein avant fonds euros ────────────────────────────────


def test_R24_triggers():
    ligne_fe = _ligne(classe_actif="FONDS_EURO", montant_eur=10000.0)
    profil = MagicMock(composition_actuelle=[ligne_fe])
    alerte = detecter_R24(profil)
    assert alerte is not None
    assert alerte.code == "R24"


# ── R25: PEE/PERCO non alimenté ──────────────────────────────────────────────


def test_R25_triggers():
    profil = MagicMock(a_pee=True, a_perco=False, composition_actuelle=[])
    alerte = detecter_R25(profil)
    assert alerte is not None
    assert alerte.code == "R25"


def test_R25_no_trigger_invested():
    ligne = _ligne(enveloppe="PEE")
    profil = MagicMock(a_pee=True, a_perco=False, composition_actuelle=[ligne])
    assert detecter_R25(profil) is None


# ── R26: PEE concentration employer ─────────────────────────────────────────


def test_R26_triggers():
    profil = MagicMock(pee_actions_entreprise_pct=0.5)
    alerte = detecter_R26(profil)
    assert alerte is not None
    assert alerte.code == "R26"


def test_R26_no_trigger_diversified():
    profil = MagicMock(pee_actions_entreprise_pct=0.2)
    assert detecter_R26(profil) is None


# ── R27: Abondement non maxé ─────────────────────────────────────────────────


def test_R27_triggers():
    profil = MagicMock(abondement_employeur_max=2000.0, abondement_employeur_actuel=500.0)
    alerte = detecter_R27(profil)
    assert alerte is not None
    assert alerte.code == "R27"
    assert alerte.gain_eur_annuel == 1500.0


def test_R27_no_trigger_maxed():
    profil = MagicMock(abondement_employeur_max=2000.0, abondement_employeur_actuel=1980.0)
    assert detecter_R27(profil) is None


# ── R28: Participation non versée PEE ────────────────────────────────────────


def test_R28_triggers():
    profil = MagicMock(participation_versee_pee=False, tmi=0.30)
    alerte = detecter_R28(profil)
    assert alerte is not None
    assert alerte.code == "R28"


def test_R28_no_trigger_versee():
    profil = MagicMock(participation_versee_pee=True, tmi=0.30)
    assert detecter_R28(profil) is None


# ── R29: Crédit conso avec cash ──────────────────────────────────────────────


def test_R29_triggers():
    profil = MagicMock(
        taeg_credits_conso=0.08,
        solde_credit_conso=5000.0,
        epargne_precaution=50000.0,
    )
    alerte = detecter_R29(profil)
    assert alerte is not None
    assert alerte.code == "R29"


def test_R29_no_trigger_no_cash():
    profil = MagicMock(
        taeg_credits_conso=0.08,
        solde_credit_conso=5000.0,
        epargne_precaution=1000.0,
    )
    assert detecter_R29(profil) is None


# ── R30: Crédit immo renégociable ────────────────────────────────────────────


def test_R30_triggers():
    profil = MagicMock(taeg_credit_immo=0.06, capital_restant_immo=200000.0)
    alerte = detecter_R30(profil)
    assert alerte is not None
    assert alerte.code == "R30"


def test_R30_no_trigger_low_rate():
    profil = MagicMock(taeg_credit_immo=0.038, capital_restant_immo=200000.0)
    assert detecter_R30(profil) is None


# ── R31: Rachat crédits ──────────────────────────────────────────────────────


def test_R31_triggers():
    profil = MagicMock(nb_credits_conso=3)
    alerte = detecter_R31(profil)
    assert alerte is not None
    assert alerte.code == "R31"


def test_R31_no_trigger_single():
    profil = MagicMock(nb_credits_conso=1)
    assert detecter_R31(profil) is None


# ── R32: Clause bénéficiaire démembrée ──────────────────────────────────────


def test_R32_triggers():
    ligne = _ligne(enveloppe="AV")
    profil = MagicMock(
        est_en_couple=True, clause_beneficiaire_demembree=False, composition_actuelle=[ligne]
    )
    alerte = detecter_R32(profil)
    assert alerte is not None
    assert alerte.code == "R32"


def test_R32_no_trigger_not_couple():
    ligne = _ligne(enveloppe="AV")
    profil = MagicMock(
        est_en_couple=False, clause_beneficiaire_demembree=False, composition_actuelle=[ligne]
    )
    assert detecter_R32(profil) is None


# ── R33: Testament ──────────────────────────────────────────────────────────


def test_R33_triggers():
    profil = MagicMock(patrimoine_financier_total=600000.0, a_testament=False)
    alerte = detecter_R33(profil)
    assert alerte is not None
    assert alerte.code == "R33"


def test_R33_no_trigger_small_patrimoine():
    profil = MagicMock(patrimoine_financier_total=100000.0, a_testament=False)
    assert detecter_R33(profil) is None


# ── R34: Quotient familial ──────────────────────────────────────────────────


def test_R34_triggers():
    profil = MagicMock(
        est_en_couple=True, tmi=0.41, revenu_fiscal_reference=80000.0, regime_fiscal_detenteur="IR"
    )
    alerte = detecter_R34(profil)
    assert alerte is not None
    assert alerte.code == "R34"
    assert alerte.severite == Severite.VERT


def test_R34_no_trigger_low_tmi():
    profil = MagicMock(est_en_couple=True, tmi=0.11, revenu_fiscal_reference=30000.0)
    assert detecter_R34(profil) is None


# ── R35: Revue patrimoniale ──────────────────────────────────────────────────


def test_R35_triggers_no_date():
    profil = MagicMock(date_revue_patrimoine=None)
    alerte = detecter_R35(profil)
    assert alerte is not None
    assert alerte.code == "R35"


def test_R35_triggers_old_date():
    profil = MagicMock(date_revue_patrimoine="2021-01-01")
    alerte = detecter_R35(profil)
    assert alerte is not None
    assert alerte.code == "R35"


def test_R35_no_trigger_recent():
    from datetime import date, timedelta

    recent = (date.today() - timedelta(days=30)).isoformat()
    profil = MagicMock(date_revue_patrimoine=recent)
    assert detecter_R35(profil) is None


# ── R36-R40: Bonus ──────────────────────────────────────────────────────────


def test_R36_triggers():
    profil = MagicMock(plafond_per_non_utilise=3000.0, tmi=0.30)
    alerte = detecter_R36(profil)
    assert alerte is not None
    assert alerte.code == "R36"
    assert alerte.severite == Severite.VERT


def test_R37_triggers():
    profil = MagicMock(a_utilise_ir_pme=False, tmi=0.41)
    alerte = detecter_R37(profil)
    assert alerte is not None
    assert alerte.code == "R37"


def test_R37_no_trigger_already_used():
    profil = MagicMock(a_utilise_ir_pme=True, tmi=0.41)
    assert detecter_R37(profil) is None


def test_R38_triggers():
    profil = MagicMock(age=55, a_utilise_donation=False, patrimoine_financier_total=200000.0)
    alerte = detecter_R38(profil)
    assert alerte is not None
    assert alerte.code == "R38"


def test_R39_triggers_before_70():
    ligne = _ligne(enveloppe="AV")
    profil = MagicMock(age=67, composition_actuelle=[ligne])
    alerte = detecter_R39(profil)
    assert alerte is not None
    assert alerte.code == "R39"


def test_R39_no_trigger_wrong_age():
    ligne = _ligne(enveloppe="AV")
    profil = MagicMock(age=45, composition_actuelle=[ligne])
    assert detecter_R39(profil) is None


def test_R40_triggers():
    profil = MagicMock(a_utilise_ir_pme=False, tmi=0.41, est_en_couple=False)
    alerte = detecter_R40(profil)
    assert alerte is not None
    assert alerte.code == "R40"
    assert alerte.severite == Severite.VERT
