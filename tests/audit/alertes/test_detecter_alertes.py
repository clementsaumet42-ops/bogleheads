"""Tests for S12 alert engine — detecter_alertes orchestrator."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from src.audit.alertes import detecter_alertes, Alerte, Severite


def _make_profil(**kwargs):
    """Create a simple namespace object simulating a Profil."""
    defaults = {
        "age": 35,
        "tmi": 0.30,
        "patrimoine_financier_total": 100000.0,
        "composition_actuelle": [],
        "positions_detaillees": [],
        "frais_courtier_par_transaction": 0.0,
        "allocation_cible_bogleheads": MagicMock(
            actions=0.6, obligations=0.3, immobilier_cote=0.05, or_=0.0, liquidites=0.05
        ),
        "enveloppes_disponibles": None,
        "revenu_fiscal_reference": None,
        "regime_fiscal_detenteur": "IR",
        "abattements_utilises": MagicMock(),
        "contraintes_personnalisees": MagicMock(),
    }
    defaults.update(kwargs)
    return MagicMock(**defaults)


def test_detecter_alertes_returns_list():
    profil = _make_profil()
    result = detecter_alertes(profil)
    assert isinstance(result, list)


def test_alertes_sorted_by_severity():
    """Alertes should be ordered ROUGE < JAUNE < VERT."""
    profil = _make_profil(
        age=35,
        tmi=0.30,
        patrimoine_financier_total=100000.0,
        plafond_per_non_utilise=10000.0,  # triggers R16 ROUGE
        epargne_precaution=500.0,
        charges_mensuelles=3000.0,  # triggers R21 ROUGE
    )
    alertes = detecter_alertes(profil)
    sev_order = {"ROUGE": 0, "JAUNE": 1, "VERT": 2}
    for i in range(len(alertes) - 1):
        assert sev_order[alertes[i].severite.value] <= sev_order[alertes[i + 1].severite.value]


def test_detecter_alertes_handles_exception_gracefully():
    """Even if a profil causes rule errors, should not crash."""
    broken_profil = object()  # no attributes at all
    result = detecter_alertes(broken_profil)
    assert isinstance(result, list)


def test_no_alertes_for_clean_profil():
    """A well-configured profil should produce fewer critical alerts."""
    profil = _make_profil(
        age=35,
        tmi=0.11,  # low TMI — many fiscal rules won't trigger
        patrimoine_financier_total=50000.0,
        plafond_per_non_utilise=0.0,
        epargne_precaution=10000.0,
        charges_mensuelles=2000.0,
        a_livret_a=True,
        assurances_vie=None,
        fond_de_fonds=False,
        frais_courtier_par_transaction=0.5,
    )
    alertes = detecter_alertes(profil)
    rouges = [a for a in alertes if a.severite == Severite.ROUGE]
    # Clean profil with low TMI should not have fiscal red alerts
    fiscal_rouges = [a for a in rouges if a.famille == "Fiscalité gâchée"]
    assert len(fiscal_rouges) == 0
