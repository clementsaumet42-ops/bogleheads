"""Tests pour contrat de capitalisation IS"""

import pytest

from src.fiscalite.contrat_cap_is import (
    calculer_base_taxable_contrat_cap_is,
    calculer_is_contrat_cap,
    comparer_contrat_cap_vs_mtm,
)


def test_base_taxable_contrat_cap():
    """Test calcul base taxable 105% × TME × prime"""
    prime = 1000000
    tme = 0.030
    base = calculer_base_taxable_contrat_cap_is(prime, tme, {})

    assert base == pytest.approx(1.05 * 0.030 * 1000000)
    assert base == pytest.approx(31500)


def test_base_taxable_tme_faible():
    """Test base taxable très faible si TME bas"""
    prime = 1000000
    tme = 0.010  # TME très bas
    base = calculer_base_taxable_contrat_cap_is(prime, tme, {})

    assert base == pytest.approx(1.05 * 0.010 * 1000000)
    assert base == pytest.approx(10500)
    # Base < 2% du capital
    assert base / prime < 0.02


def test_is_contrat_cap_taux_reduit():
    """Test IS contrat cap avec taux réduit"""
    result = calculer_is_contrat_cap(1000000, 0.030, annees=1)

    base = 1.05 * 0.030 * 1000000  # 31 500€
    is_attendu = base * 0.15  # < seuil 42 500€
    assert result.total_impots == pytest.approx(is_attendu)


def test_is_contrat_cap_plusieurs_annees():
    """Test IS contrat cap cumulé sur plusieurs années"""
    result = calculer_is_contrat_cap(1000000, 0.030, annees=5)

    base_annuelle = 1.05 * 0.030 * 1000000
    is_annuel = base_annuelle * 0.15
    is_cumule = is_annuel * 5
    assert result.total_impots == pytest.approx(is_cumule)


def test_comparatif_contrat_cap_vs_mtm():
    """Test comparatif contrat cap vs MTM"""
    result = comparer_contrat_cap_vs_mtm(
        capital=1000000,
        rendement_reel=0.06,
        tme=0.03,
        horizon_ans=10,
    )

    # Contrat cap avantageux si rendement > TME
    assert result["economie_is"] > 0
    assert result["avantage_capital"] > 0
    assert "avantageux" in result["conclusion"]


def test_comparatif_rendement_egal_tme():
    """Test comparatif quand rendement ≈ TME"""
    result = comparer_contrat_cap_vs_mtm(
        capital=1000000,
        rendement_reel=0.03,
        tme=0.03,
        horizon_ans=10,
    )

    # Contrat cap reste avantageux même si rendement = TME
    # car la base est forfaitaire et fixe chaque année
    assert result["economie_is"] > 0
    assert result["avantage_capital"] > 0
