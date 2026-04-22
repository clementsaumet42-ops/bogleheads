"""Tests unitaires — calculs fiscaux"""
import pytest
from pathlib import Path
import yaml
from src.fiscalite import (
    charger_params_fiscaux,
    calculer_pfu,
    calculer_is,
    calculer_base_taxable_contrat_cap_is,
    avantage_fiscal_pea,
)


@pytest.fixture
def params():
    return charger_params_fiscaux()


def test_charger_params_fiscaux(params):
    assert params["annee"] == 2026
    assert params["prelevements_sociaux"]["taux_global"] == pytest.approx(0.186)


def test_pfu_taux_correct(params):
    result = calculer_pfu(10000, params)
    assert result["ir"] == pytest.approx(10000 * 0.128)
    assert result["ps"] == pytest.approx(10000 * 0.186)
    assert result["net"] == pytest.approx(10000 * (1 - 0.128 - 0.186))


def test_pfu_taux_effectif(params):
    result = calculer_pfu(10000, params)
    assert result["taux_effectif"] == pytest.approx(0.314)


def test_pfu_zero(params):
    result = calculer_pfu(0, params)
    assert result["taux_effectif"] == 0.0
    assert result["net"] == 0.0


def test_is_taux_reduit(params):
    result = calculer_is(30000, params)
    assert result["is_du"] == pytest.approx(30000 * 0.15)
    assert result["taux_effectif"] == pytest.approx(0.15)


def test_is_taux_normal_partiel(params):
    """Test sur un bénéfice qui dépasse le seuil du taux réduit."""
    result = calculer_is(100000, params)
    is_attendu = 42500 * 0.15 + 57500 * 0.25
    assert result["is_du"] == pytest.approx(is_attendu)
    assert result["taux_effectif"] == pytest.approx(is_attendu / 100000)


def test_is_seuil_exact(params):
    """Test exactement au seuil du taux réduit."""
    seuil = params["is"]["seuil_taux_reduit"]
    result = calculer_is(seuil, params)
    assert result["is_du"] == pytest.approx(seuil * 0.15)
    assert result["taux_effectif"] == pytest.approx(0.15)


def test_base_contrat_cap_is(params):
    prime = 1_000_000
    tme = 0.030
    base = calculer_base_taxable_contrat_cap_is(prime, tme, params)
    assert base == pytest.approx(1.05 * 0.030 * 1_000_000)


def test_base_contrat_cap_is_tme_faible(params):
    """Base faible si TME bas — avantage du contrat cap IS."""
    prime = 1_000_000
    tme = 0.010
    base = calculer_base_taxable_contrat_cap_is(prime, tme, params)
    assert base == pytest.approx(1.05 * 0.010 * 1_000_000)
    assert base < prime * 0.02  # base < 2% de la prime


def test_avantage_pea_apres_5_ans(params):
    result = avantage_fiscal_pea(100000, params, apres_5_ans=True)
    assert result["impots_pea"] == pytest.approx(100000 * 0.186)
    assert result["economie"] > 0
    assert result["economie"] == pytest.approx(100000 * 0.128)


def test_avantage_pea_avant_5_ans(params):
    """Avant 5 ans : PFU complet — pas d'avantage vs CTO."""
    result = avantage_fiscal_pea(100000, params, apres_5_ans=False)
    assert result["economie"] == pytest.approx(0.0)


def test_pfu_total_egale_314(params):
    """Vérifie que PFU total = 31,4%."""
    assert params["pfu"]["taux_total_avec_ps"] == pytest.approx(0.314)
    # Et que 12.8 + 18.6 = 31.4
    assert params["pfu"]["taux_ir"] + params["prelevements_sociaux"]["taux_global"] == pytest.approx(0.314)
