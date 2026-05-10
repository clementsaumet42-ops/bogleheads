"""Tests cascade trimestrielle 12 mois — Bloc C de la roadmap.

3 scenarios golden : faible ecart / ecart moyen / forte derive.
"""

from __future__ import annotations

import pytest

from src.plan_action.calendrier_trimestriel import (
    CalendrierTrimestriel,
    Trimestre,
    generer_calendrier,
)
from src.rebalancement_flux import EtatPortefeuille

# ── Fixtures de portefeuille ──────────────────────────────────────────────


def _portefeuille_quasi_aligne() -> EtatPortefeuille:
    """Faible ecart : 100 k€, 68% actions vs 70% cible."""
    return EtatPortefeuille(actions_monde=68_000, obligations=32_000)


def _portefeuille_ecart_moyen() -> EtatPortefeuille:
    """Ecart moyen : 100 k€, 60% actions vs 70% cible (10pts)."""
    return EtatPortefeuille(actions_monde=60_000, obligations=40_000)


def _portefeuille_forte_derive() -> EtatPortefeuille:
    """Forte derive : 100 k€, 40% actions vs 70% cible (30pts)."""
    return EtatPortefeuille(actions_monde=40_000, obligations=60_000)


CIBLE_70_30 = {"actions_monde": 0.70, "obligations": 0.30}


# ── Tests structurels ─────────────────────────────────────────────────────


def test_genere_4_trimestres():
    plan = generer_calendrier(
        portefeuille_actuel=_portefeuille_ecart_moyen(),
        allocation_cible=CIBLE_70_30,
        flux_entrants_12m=20_000,
    )
    assert isinstance(plan, CalendrierTrimestriel)
    assert len(plan.trimestres) == 4
    for i, t in enumerate(plan.trimestres):
        assert isinstance(t, Trimestre)
        assert t.numero == i + 1
        assert t.mois_debut == i * 3
        assert t.versement_total == pytest.approx(5_000)


def test_versements_priorisent_classe_sous_ponderee():
    """Le flux doit aller en priorite sur actions sous-ponderee."""
    plan = generer_calendrier(
        portefeuille_actuel=_portefeuille_ecart_moyen(),
        allocation_cible=CIBLE_70_30,
        flux_entrants_12m=40_000,
    )
    montant_actions = sum(
        v.montant for t in plan.trimestres for v in t.versements if v.classe == "actions_monde"
    )
    montant_obligs = sum(
        v.montant for t in plan.trimestres for v in t.versements if v.classe == "obligations"
    )
    assert montant_actions > montant_obligs


def test_aucun_arbitrage_si_flux_suffisant():
    """Faible ecart + flux suffisant : pas de vente requise."""
    plan = generer_calendrier(
        portefeuille_actuel=_portefeuille_quasi_aligne(),
        allocation_cible=CIBLE_70_30,
        flux_entrants_12m=20_000,
    )
    nb_arbitrages = sum(len(t.arbitrages) for t in plan.trimestres)
    assert nb_arbitrages == 0
    assert plan.cout_fiscal_optimise == 0.0


def test_arbitrage_propose_si_forte_derive_et_flux_insuffisant():
    """Forte derive + flux faible : doit declencher des arbitrages."""
    plan = generer_calendrier(
        portefeuille_actuel=_portefeuille_forte_derive(),
        allocation_cible=CIBLE_70_30,
        flux_entrants_12m=2_000,  # tres faible
    )
    nb_arbitrages = sum(len(t.arbitrages) for t in plan.trimestres)
    assert nb_arbitrages > 0


def test_economie_fiscale_positive_quand_flux_suffit():
    """Si on evite les ventes, l'economie vs naif doit etre positive."""
    plan = generer_calendrier(
        portefeuille_actuel=_portefeuille_ecart_moyen(),
        allocation_cible=CIBLE_70_30,
        flux_entrants_12m=20_000,
    )
    assert plan.cout_fiscal_naif > 0
    assert plan.economie_realisee > 0
    # L'economie doit etre proche du cout naif si pas d'arbitrage
    if not any(t.arbitrages for t in plan.trimestres):
        assert plan.economie_realisee == pytest.approx(plan.cout_fiscal_naif)


def test_priorite_enveloppe_sans_friction():
    """Si PEA dispo dans enveloppes_disponibles, vente arbitrage va sur PEA d'abord."""
    plan = generer_calendrier(
        portefeuille_actuel=_portefeuille_forte_derive(),
        allocation_cible=CIBLE_70_30,
        flux_entrants_12m=1_000,
        enveloppes_disponibles=["PEA", "PEA_5ans", "CTO_perso"],
    )
    arbitrages = [a for t in plan.trimestres for a in t.arbitrages]
    if arbitrages:
        assert arbitrages[0].enveloppe_source == "PEA_5ans"
        assert arbitrages[0].cout_fiscal_estime < arbitrages[0].montant * 0.20


def test_derive_finale_diminue():
    """La derive doit baisser entre debut et fin de cascade."""
    plan = generer_calendrier(
        portefeuille_actuel=_portefeuille_forte_derive(),
        allocation_cible=CIBLE_70_30,
        flux_entrants_12m=20_000,
    )
    assert plan.derive_finale_pct < plan.derive_initiale_pct


def test_dump_dict_serialisable():
    plan = generer_calendrier(
        portefeuille_actuel=_portefeuille_ecart_moyen(),
        allocation_cible=CIBLE_70_30,
        flux_entrants_12m=20_000,
    )
    import json

    dump = plan.vers_dict()
    # Doit etre JSON-serialisable sans erreur
    json.dumps(dump)
    assert "trimestres" in dump
    assert len(dump["trimestres"]) == 4


# ── Validations d'entree ──────────────────────────────────────────────────


def test_flux_negatif_leve_erreur():
    with pytest.raises(ValueError, match="flux_entrants_12m"):
        generer_calendrier(
            portefeuille_actuel=_portefeuille_ecart_moyen(),
            allocation_cible=CIBLE_70_30,
            flux_entrants_12m=-1_000,
        )


def test_allocation_vide_leve_erreur():
    with pytest.raises(ValueError, match="allocation_cible"):
        generer_calendrier(
            portefeuille_actuel=_portefeuille_ecart_moyen(),
            allocation_cible={},
            flux_entrants_12m=10_000,
        )


def test_versement_zero_ne_casse_pas():
    """Cas degenere : aucun flux. On obtient juste les arbitrages eventuels."""
    plan = generer_calendrier(
        portefeuille_actuel=_portefeuille_ecart_moyen(),
        allocation_cible=CIBLE_70_30,
        flux_entrants_12m=0,
    )
    assert plan.flux_total_12m == 0
    for t in plan.trimestres:
        assert t.versement_total == 0
        assert len(t.versements) == 0


# ── Golden : 3 scenarios cles ─────────────────────────────────────────────


def test_golden_faible_ecart():
    """Scenario faible ecart : versements suffisants, zero arbitrage, economie complete."""
    plan = generer_calendrier(
        portefeuille_actuel=_portefeuille_quasi_aligne(),
        allocation_cible=CIBLE_70_30,
        flux_entrants_12m=12_000,
    )
    assert plan.cout_fiscal_optimise == 0.0
    assert all(len(t.arbitrages) == 0 for t in plan.trimestres)


def test_golden_ecart_moyen():
    """Scenario ecart moyen : versements bien orientes, derive reduite."""
    plan = generer_calendrier(
        portefeuille_actuel=_portefeuille_ecart_moyen(),
        allocation_cible=CIBLE_70_30,
        flux_entrants_12m=20_000,
    )
    assert plan.derive_initiale_pct == pytest.approx(0.10, abs=0.001)
    assert plan.derive_finale_pct < plan.derive_initiale_pct


def test_golden_forte_derive():
    """Scenario forte derive : meme avec arbitrage, on ramene la derive."""
    plan = generer_calendrier(
        portefeuille_actuel=_portefeuille_forte_derive(),
        allocation_cible=CIBLE_70_30,
        flux_entrants_12m=10_000,
        enveloppes_disponibles=["PEA_5ans", "CTO_perso"],
    )
    assert plan.derive_initiale_pct == pytest.approx(0.30, abs=0.001)
    # Apres flux + arbitrages, derive nettement reduite
    assert plan.derive_finale_pct < 0.10
