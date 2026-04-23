"""Tests for src/rebalancement.py"""

import pytest

from src.rebalancement import calculer_cout_fiscal_arbitrage, calculer_derive_allocation

PARAMS_FISCAUX = {
    "prelevements_sociaux": {"taux_global": 0.186},
    "pfu": {"taux_ir": 0.128},
    "is": {"taux_reduit": 0.15},
}


class TestCalculerDeriveAllocation:
    def test_pas_de_derive(self):
        cible = {"actions": 0.60, "obligations": 0.40}
        actuelle = {"actions": 0.60, "obligations": 0.40}
        result = calculer_derive_allocation(actuelle, cible)
        assert not result["rebalancement_necessaire"]
        assert result["details"]["actions"]["action"] == "OK"

    def test_derive_action_necessaire(self):
        cible = {"actions": 0.60, "obligations": 0.40}
        actuelle = {"actions": 0.80, "obligations": 0.20}
        result = calculer_derive_allocation(actuelle, cible)
        assert result["rebalancement_necessaire"]
        assert result["details"]["actions"]["action"] == "VENDRE"
        assert result["details"]["obligations"]["action"] == "ACHETER"

    def test_derive_abs_correcte(self):
        cible = {"actions": 0.60}
        actuelle = {"actions": 0.70}
        result = calculer_derive_allocation(actuelle, cible)
        assert result["details"]["actions"]["derive_abs"] == pytest.approx(0.10, abs=0.001)

    def test_ignore_commentaire(self):
        cible = {"actions": 1.0, "commentaire": "Profil test"}
        actuelle = {"actions": 1.0}
        result = calculer_derive_allocation(actuelle, cible)
        assert "commentaire" not in result["details"]


class TestCalculerCoutFiscalArbitrage:
    def test_intra_pea_gratuit(self):
        result = calculer_cout_fiscal_arbitrage(
            montant_cede=10000,
            prix_revient=6000,
            enveloppe_id="PEA",
            params_fiscaux=PARAMS_FISCAUX,
        )
        assert result["cout_fiscal"] == 0.0

    def test_moins_value_gratuite(self):
        result = calculer_cout_fiscal_arbitrage(
            montant_cede=5000,
            prix_revient=8000,
            enveloppe_id="CTO_perso",
            params_fiscaux=PARAMS_FISCAUX,
        )
        assert result["cout_fiscal"] == 0.0

    def test_cto_pfu_correct(self):
        result = calculer_cout_fiscal_arbitrage(
            montant_cede=10000,
            prix_revient=6000,
            enveloppe_id="CTO_perso",
            params_fiscaux=PARAMS_FISCAUX,
        )
        pv = 4000
        expected = pv * (0.128 + 0.186)
        assert result["cout_fiscal"] == pytest.approx(expected, rel=0.001)

    def test_per_arbitrage_gratuit(self):
        result = calculer_cout_fiscal_arbitrage(
            montant_cede=20000,
            prix_revient=10000,
            enveloppe_id="PER",
            params_fiscaux=PARAMS_FISCAUX,
        )
        assert result["cout_fiscal"] == 0.0

    def test_structure_resultat(self):
        result = calculer_cout_fiscal_arbitrage(
            montant_cede=10000,
            prix_revient=7000,
            enveloppe_id="CTO_perso",
            params_fiscaux=PARAMS_FISCAUX,
        )
        for key in ["plus_value", "cout_fiscal", "net_apres_impots", "taux_effectif"]:
            assert key in result
