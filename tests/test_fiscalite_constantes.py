"""Tests pour les constantes fiscales"""

import pytest

from src.fiscalite.constantes import (
    AV_ABATTEMENT_CELIBATAIRE,
    AV_SEUIL_150K,
    IS_SEUIL,
    IS_TAUX_NORMAL,
    IS_TAUX_REDUIT,
    PEA_PLAFOND_VERSEMENTS,
    TAUX_PFU_IR,
    TAUX_PFU_TOTAL,
    TAUX_PS,
)


def test_taux_ps():
    """Test que le taux PS est bien 18.6%"""
    assert pytest.approx(0.186) == TAUX_PS


def test_taux_pfu_ir():
    """Test que le taux PFU IR est bien 12.8%"""
    assert pytest.approx(0.128) == TAUX_PFU_IR


def test_taux_pfu_total():
    """Test que le taux PFU total est bien 31.4%"""
    assert pytest.approx(0.314) == TAUX_PFU_TOTAL
    assert pytest.approx(0.314) == TAUX_PFU_IR + TAUX_PS


def test_is_seuil():
    """Test que le seuil IS taux réduit est bien 42 500€"""
    assert IS_SEUIL == 42500


def test_is_taux_reduit():
    """Test que le taux IS réduit est bien 15%"""
    assert pytest.approx(0.15) == IS_TAUX_REDUIT


def test_is_taux_normal():
    """Test que le taux IS normal est bien 25%"""
    assert pytest.approx(0.25) == IS_TAUX_NORMAL


def test_av_seuil_150k():
    """Test que le seuil AV célibataire est bien 150 000€"""
    assert AV_SEUIL_150K == 150000


def test_av_abattement_celibataire():
    """Test que l'abattement AV célibataire est bien 4 600€"""
    assert AV_ABATTEMENT_CELIBATAIRE == 4600


def test_pea_plafond():
    """Test que le plafond PEA est bien 150 000€"""
    assert PEA_PLAFOND_VERSEMENTS == 150000


def test_constantes_coherentes():
    """Test que les constantes sont cohérentes entre elles"""
    # PFU total = IR + PS
    assert pytest.approx(TAUX_PFU_IR + TAUX_PS) == TAUX_PFU_TOTAL

    # IS taux normal > IS taux réduit
    assert IS_TAUX_NORMAL > IS_TAUX_REDUIT

    # Seuil IS positif
    assert IS_SEUIL > 0
