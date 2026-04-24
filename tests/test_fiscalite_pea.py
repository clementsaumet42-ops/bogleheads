"""Tests pour le PEA et PEA-PME"""

import pytest

from src.fiscalite.pea import (
    avantage_pea_vs_cto,
    calculer_fiscalite_retrait_pea,
    verifier_plafond_pea,
)


def test_plafond_pea_respecte():
    """Test plafond PEA respecté"""
    result = verifier_plafond_pea(100000, 0)
    assert result["respect_plafond"] is True
    assert result["depassement_pea"] == 0


def test_plafond_pea_depasse():
    """Test plafond PEA dépassé"""
    result = verifier_plafond_pea(160000, 0)
    assert result["respect_plafond"] is False
    assert result["depassement_pea"] == 10000


def test_plafond_cumul_pea_pea_pme():
    """Test plafond cumul PEA + PEA-PME"""
    result = verifier_plafond_pea(150000, 100000)
    assert result["respect_plafond"] is False
    assert result["depassement_cumul"] == 25000


def test_pea_plus_5_ans_exoneration_ir():
    """Test PEA > 5 ans : exonération IR"""
    profil = {"tmi": 0.30, "situation": "celibataire", "rfr": 50000}
    operation = {
        "montant_brut": 20000,
        "gains": 10000,
        "duree_detention": 6.0,
        "type_pea": "pea",
    }
    result = calculer_fiscalite_retrait_pea(operation, profil)

    assert result.impot_ir == pytest.approx(0.0)
    assert result.prelevements_sociaux == pytest.approx(10000 * 0.186)
    assert result.total_impots == pytest.approx(10000 * 0.186)


def test_pea_entre_2_5_ans():
    """Test PEA entre 2 et 5 ans : IR 12.8% + PS"""
    profil = {"tmi": 0.30, "situation": "celibataire", "rfr": 50000}
    operation = {
        "montant_brut": 20000,
        "gains": 10000,
        "duree_detention": 3.0,
        "type_pea": "pea",
    }
    result = calculer_fiscalite_retrait_pea(operation, profil)

    assert result.impot_ir == pytest.approx(10000 * 0.128)
    assert result.prelevements_sociaux == pytest.approx(10000 * 0.186)
    assert result.total_impots == pytest.approx(10000 * 0.314)


def test_pea_moins_2_ans_tmi():
    """Test PEA < 2 ans : IR au TMI + PS"""
    profil = {"tmi": 0.30, "situation": "celibataire", "rfr": 50000}
    operation = {
        "montant_brut": 20000,
        "gains": 10000,
        "duree_detention": 1.0,
        "type_pea": "pea",
    }
    result = calculer_fiscalite_retrait_pea(operation, profil)

    assert result.impot_ir == pytest.approx(10000 * 0.30)
    assert result.prelevements_sociaux == pytest.approx(10000 * 0.186)
    assert result.total_impots == pytest.approx(10000 * 0.486)


def test_pea_cas_force_majeure():
    """Test PEA cas force majeure : exonération totale"""
    profil = {"tmi": 0.30, "situation": "celibataire", "rfr": 50000}
    operation = {
        "montant_brut": 20000,
        "gains": 10000,
        "duree_detention": 1.0,
        "type_pea": "pea",
        "cas_force_majeure": True,
    }
    result = calculer_fiscalite_retrait_pea(operation, profil)

    assert result.impot_ir == pytest.approx(0.0)
    assert result.prelevements_sociaux == pytest.approx(0.0)
    assert result.total_impots == pytest.approx(0.0)
    assert result.montant_net == pytest.approx(20000)


def test_avantage_pea_apres_5_ans():
    """Test avantage PEA vs CTO après 5 ans"""
    result = avantage_pea_vs_cto(100000, 6.0, 0.30)
    assert result["impots_pea"] == pytest.approx(100000 * 0.186)
    assert result["impots_cto"] == pytest.approx(100000 * 0.314)
    assert result["economie"] == pytest.approx(100000 * 0.128)


def test_avantage_pea_avant_2_ans():
    """Test avantage PEA vs CTO avant 2 ans (pas d'avantage)"""
    result = avantage_pea_vs_cto(100000, 1.0, 0.30)
    # PEA < 2 ans : TMI 30% + PS 18.6% = 48.6%
    # CTO : PFU 31.4%
    # PEA moins avantageux
    assert result["impots_pea"] > result["impots_cto"]
