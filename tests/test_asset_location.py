"""Tests for src/asset_location.py"""

import pytest

from src.asset_location import calculer_gain_fiscal_enveloppe, suggerer_asset_location

PARAMS_FISCAUX = {
    "prelevements_sociaux": {"taux_global": 0.186},
    "pfu": {"taux_ir": 0.128},
    "is": {"taux_reduit": 0.15},
}


class TestCalculerGainFiscal:
    def test_pea_moins_impots_que_cto(self):
        result_pea = calculer_gain_fiscal_enveloppe(
            etf={},
            enveloppe_id="PEA",
            montant=10000,
            horizon_ans=10,
            rendement_annuel=0.07,
            params_fiscaux=PARAMS_FISCAUX,
        )
        result_cto = calculer_gain_fiscal_enveloppe(
            etf={},
            enveloppe_id="CTO_perso",
            montant=10000,
            horizon_ans=10,
            rendement_annuel=0.07,
            params_fiscaux=PARAMS_FISCAUX,
        )
        assert result_pea["capital_net"] > result_cto["capital_net"]

    def test_avantage_pea_positif(self):
        result = calculer_gain_fiscal_enveloppe(
            etf={},
            enveloppe_id="PEA",
            montant=10000,
            horizon_ans=10,
            rendement_annuel=0.07,
            params_fiscaux=PARAMS_FISCAUX,
        )
        assert result["avantage_vs_cto"] > 0

    def test_cto_avantage_zero(self):
        result = calculer_gain_fiscal_enveloppe(
            etf={},
            enveloppe_id="CTO_perso",
            montant=10000,
            horizon_ans=10,
            rendement_annuel=0.07,
            params_fiscaux=PARAMS_FISCAUX,
        )
        assert result["avantage_vs_cto"] == pytest.approx(0.0)

    def test_structure_resultat(self):
        result = calculer_gain_fiscal_enveloppe(
            etf={},
            enveloppe_id="PEA",
            montant=10000,
            horizon_ans=5,
            rendement_annuel=0.05,
            params_fiscaux=PARAMS_FISCAUX,
        )
        for key in ["enveloppe", "montant_initial", "capital_brut", "impots", "capital_net"]:
            assert key in result


class TestSuggererAssetLocation:
    def test_suggestions_non_vides(self):
        etfs = [
            {"isin": "IE0031442068", "nom": "CW8", "eligibilite": {"PEA": True, "CTO_perso": True}},
        ]
        suggestions = suggerer_asset_location(
            etfs=etfs,
            enveloppes_dispo=["PEA", "CTO_perso"],
            allocation_cible={"actions": 1.0},
            patrimoine_total=100000,
        )
        assert len(suggestions) == 1
        assert suggestions[0]["enveloppe_suggeree"] == "PEA"

    def test_pea_prioritaire(self):
        etfs = [
            {"isin": "TEST", "nom": "ETF PEA", "eligibilite": {"PEA": True, "CTO_perso": True}},
        ]
        suggestions = suggerer_asset_location(
            etfs=etfs,
            enveloppes_dispo=["PEA", "CTO_perso"],
            allocation_cible={"actions": 1.0},
            patrimoine_total=50000,
        )
        assert suggestions[0]["enveloppe_suggeree"] == "PEA"

    def test_etf_non_eligible_exclue(self):
        etfs = [
            {
                "isin": "TEST",
                "nom": "ETF non-eligible",
                "eligibilite": {"PEA": False, "CTO_perso": False},
            },
        ]
        suggestions = suggerer_asset_location(
            etfs=etfs,
            enveloppes_dispo=["PEA"],
            allocation_cible={"actions": 1.0},
            patrimoine_total=50000,
        )
        assert len(suggestions) == 0
