"""Tests pour src.audit.analyse_existant."""

from __future__ import annotations

import pytest

from src.audit.analyse_existant import analyser_existant


def _make_profil(composition: list[dict]) -> dict:
    return {
        "id": 1,
        "code": "TEST",
        "nom": "Test",
        "age": 45,
        "tmi": 0.30,
        "allocation_cible_bogleheads": {"actions_usa": 0.6, "obligations_euro": 0.4},
        "composition_actuelle": composition,
    }


def test_retourne_diagnostic_vide_sans_composition():
    profil = _make_profil([])
    diag = analyser_existant(profil, {})
    assert diag.montant_total_eur == 0.0
    assert diag.repartition_par_classe == {}


def test_montant_total_correct():
    profil = _make_profil(
        [
            {"enveloppe": "CTO", "classe_actif": "actions_usa", "montant_eur": 10000.0},
            {"enveloppe": "PEA", "classe_actif": "obligations_euro", "montant_eur": 5000.0},
        ]
    )
    diag = analyser_existant(profil, {})
    assert diag.montant_total_eur == 15000.0


def test_repartition_par_classe():
    profil = _make_profil(
        [
            {"enveloppe": "CTO", "classe_actif": "actions_usa", "montant_eur": 8000.0},
            {"enveloppe": "PEA", "classe_actif": "actions_usa", "montant_eur": 2000.0},
        ]
    )
    diag = analyser_existant(profil, {})
    assert diag.repartition_par_classe["actions_usa"] == pytest.approx(10000.0)


def test_repartition_par_enveloppe():
    profil = _make_profil(
        [
            {"enveloppe": "PEA", "classe_actif": "actions_usa", "montant_eur": 30000.0},
            {"enveloppe": "CTO", "classe_actif": "obligations_euro", "montant_eur": 10000.0},
        ]
    )
    diag = analyser_existant(profil, {})
    assert diag.repartition_par_enveloppe["PEA"] == pytest.approx(30000.0)
    assert diag.repartition_par_enveloppe["CTO"] == pytest.approx(10000.0)


def test_pourcentage_par_classe():
    profil = _make_profil(
        [
            {"enveloppe": "CTO", "classe_actif": "actions_usa", "montant_eur": 60.0},
            {"enveloppe": "CTO", "classe_actif": "obligations_euro", "montant_eur": 40.0},
        ]
    )
    diag = analyser_existant(profil, {})
    assert diag.pourcentage_par_classe["actions_usa"] == pytest.approx(0.60)
    assert diag.pourcentage_par_classe["obligations_euro"] == pytest.approx(0.40)


def test_drift_vs_allocation_cible():
    allocation_cible = {"actions_usa": 0.50, "obligations_euro": 0.50}
    profil = _make_profil(
        [
            {"enveloppe": "CTO", "classe_actif": "actions_usa", "montant_eur": 70.0},
            {"enveloppe": "CTO", "classe_actif": "obligations_euro", "montant_eur": 30.0},
        ]
    )
    diag = analyser_existant(profil, allocation_cible)
    assert diag.drift_par_classe["actions_usa"] == pytest.approx(0.20, abs=0.001)
    assert diag.drift_par_classe["obligations_euro"] == pytest.approx(-0.20, abs=0.001)


def test_classes_sur_et_sous_ponderees():
    allocation_cible = {"actions_usa": 0.50, "obligations_euro": 0.50}
    profil = _make_profil(
        [
            {"enveloppe": "CTO", "classe_actif": "actions_usa", "montant_eur": 80.0},
            {"enveloppe": "CTO", "classe_actif": "obligations_euro", "montant_eur": 20.0},
        ]
    )
    diag = analyser_existant(profil, allocation_cible)
    assert "actions_usa" in diag.classes_sur_ponderees
    assert "obligations_euro" in diag.classes_sous_ponderees


def test_risque_concentration_detecte():
    profil = _make_profil(
        [
            {"enveloppe": "PEA", "classe_actif": "actions_usa", "montant_eur": 90000.0},
            {"enveloppe": "CTO", "classe_actif": "obligations_euro", "montant_eur": 10000.0},
        ]
    )
    diag = analyser_existant(profil, {})
    assert diag.risque_concentration is True
    assert diag.concentration_max_enveloppe_pct == pytest.approx(0.9, abs=0.001)


def test_cout_fiscal_cto():
    profil = _make_profil(
        [
            {"enveloppe": "CTO", "classe_actif": "actions_usa", "montant_eur": 100000.0},
        ]
    )
    diag = analyser_existant(profil, {})
    # actions_usa: taux_dist=1.8%, CTO: taux_imp=30%
    expected = 100000.0 * 0.018 * 0.30
    assert diag.cout_fiscal_annuel_estime_eur == pytest.approx(expected, rel=0.01)


def test_cout_fiscal_pea_nul():
    profil = _make_profil(
        [
            {"enveloppe": "PEA", "classe_actif": "actions_usa", "montant_eur": 100000.0},
        ]
    )
    diag = analyser_existant(profil, {})
    assert diag.cout_fiscal_annuel_estime_eur == pytest.approx(0.0)


def test_plus_values_latentes():
    profil = _make_profil(
        [
            {
                "enveloppe": "CTO",
                "classe_actif": "actions_usa",
                "montant_eur": 15000.0,
                "prix_revient_eur": 10000.0,
            },
        ]
    )
    diag = analyser_existant(profil, {})
    assert diag.plus_values_latentes_eur == pytest.approx(5000.0)
