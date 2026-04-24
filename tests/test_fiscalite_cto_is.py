"""Tests pour CTO IS et Mark-to-Market"""

import pytest

from src.fiscalite.cto_is import (
    calculer_mtm_annuel,
    comparer_cto_is_vs_contrat_cap_is,
    detecter_piege_mtm,
)


def test_detection_mtm_opcvm_is():
    """Test détection MTM sur OPCVM détenu à > 90% par société IS"""
    position = {
        "type_actif": "etf",
        "valeur_marche": 110000,
        "prix_acquisition": 100000,
        "pourcent_detention_is": 0.95,  # 95% > 90%
    }
    alerte = detecter_piege_mtm(position, "is")

    assert alerte is not None
    assert alerte["alerte"] == "PIÈGE MTM DÉTECTÉ"
    assert alerte["pv_latente"] == pytest.approx(10000)
    assert alerte["is_du_annuel"] > 0


def test_pas_mtm_si_ir():
    """Test pas de MTM si détenu par particulier (IR)"""
    position = {
        "type_actif": "etf",
        "valeur_marche": 110000,
        "prix_acquisition": 100000,
        "pourcent_detention_is": 0.95,
    }
    alerte = detecter_piege_mtm(position, "ir")

    assert alerte is None


def test_pas_mtm_si_detention_inferieure_90():
    """Test pas de MTM si détention IS < 90%"""
    position = {
        "type_actif": "etf",
        "valeur_marche": 110000,
        "prix_acquisition": 100000,
        "pourcent_detention_is": 0.85,  # 85% < 90%
    }
    alerte = detecter_piege_mtm(position, "is")

    assert alerte is None


def test_pas_mtm_si_action_directe():
    """Test pas de MTM sur actions directes"""
    position = {
        "type_actif": "action",
        "valeur_marche": 110000,
        "prix_acquisition": 100000,
        "pourcent_detention_is": 0.95,
    }
    alerte = detecter_piege_mtm(position, "is")

    assert alerte is None


def test_calcul_mtm_annuel():
    """Test calcul MTM annuel sur un portefeuille"""
    positions = [
        {
            "nom": "ETF World",
            "type_actif": "etf",
            "valeur_marche": 110000,
            "prix_acquisition": 100000,
            "pourcent_detention_is": 0.95,
        },
        {
            "nom": "ETF Emerging",
            "type_actif": "etf",
            "valeur_marche": 55000,
            "prix_acquisition": 50000,
            "pourcent_detention_is": 0.92,
        },
    ]
    result = calculer_mtm_annuel(positions, 2026)

    # PV latentes : 10 000 + 5 000 = 15 000
    assert result.montant_brut == pytest.approx(15000)
    # IS sur 15 000 à 15% = 2 250
    assert result.total_impots == pytest.approx(15000 * 0.15)


def test_comparatif_cto_is_vs_contrat_cap():
    """Test comparatif CTO IS (MTM) vs contrat cap IS"""
    result = comparer_cto_is_vs_contrat_cap_is(
        capital_initial=100000,
        rendement_annuel=0.06,
        horizon_ans=10,
        tme=0.03,
    )

    # Contrat cap doit être avantageux si rendement > TME
    assert result["avantage_contrat_cap"] > 0
    assert result["economie_is"] > 0
    assert result["capital_final_contrat_cap_is"] > result["capital_final_cto_is"]
