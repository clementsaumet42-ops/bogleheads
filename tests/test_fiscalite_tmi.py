"""Tests pour le barème IR et le TMI"""

import pytest

from src.fiscalite.tmi import (
    calculer_decote,
    calculer_ir_brut_bareme,
    calculer_ir_complet,
    calculer_parts_fiscales,
    calculer_taux_moyen,
    calculer_tmi,
)


def test_parts_celibataire_sans_enfant():
    """Test parts fiscales célibataire sans enfant"""
    parts = calculer_parts_fiscales("celibataire", 0)
    assert parts == 1.0


def test_parts_couple_sans_enfant():
    """Test parts fiscales couple sans enfant"""
    parts = calculer_parts_fiscales("couple", 0)
    assert parts == 2.0


def test_parts_celibataire_1_enfant():
    """Test parts fiscales célibataire 1 enfant"""
    parts = calculer_parts_fiscales("celibataire", 1)
    assert parts == 1.5


def test_parts_couple_2_enfants():
    """Test parts fiscales couple 2 enfants"""
    parts = calculer_parts_fiscales("couple", 2)
    assert parts == 3.0  # 2 + 0.5 + 0.5


def test_parts_couple_3_enfants():
    """Test parts fiscales couple 3 enfants"""
    parts = calculer_parts_fiscales("couple", 3)
    assert parts == 4.0  # 2 + 0.5 + 0.5 + 1.0


def test_bareme_tranche_zero():
    """Test barème IR tranche 0%"""
    result = calculer_ir_brut_bareme(10000, 1.0)
    assert result["ir_brut"] == pytest.approx(0.0)


def test_bareme_tranche_11():
    """Test barème IR tranche 11%"""
    # Revenu 20 000€, 1 part
    # Quotient = 20 000€
    # IR = (20 000 - 11 294) × 11%
    result = calculer_ir_brut_bareme(20000, 1.0)
    ir_attendu = (20000 - 11294) * 0.11
    assert result["ir_brut"] == pytest.approx(ir_attendu)


def test_bareme_tranche_30():
    """Test barème IR tranche 30%"""
    # Revenu 50 000€, 1 part
    result = calculer_ir_brut_bareme(50000, 1.0)
    # Tranche 1 : 0 → 11 294 à 0%
    # Tranche 2 : 11 294 → 28 797 à 11%
    # Tranche 3 : 28 797 → 50 000 à 30%
    ir_attendu = 0 + (28797 - 11294) * 0.11 + (50000 - 28797) * 0.30
    assert result["ir_brut"] == pytest.approx(ir_attendu)


def test_tmi_tranche_zero():
    """Test TMI tranche 0%"""
    tmi = calculer_tmi(10000, 1.0)
    assert tmi == pytest.approx(0.0)


def test_tmi_tranche_11():
    """Test TMI tranche 11%"""
    tmi = calculer_tmi(20000, 1.0)
    assert tmi == pytest.approx(0.11)


def test_tmi_tranche_30():
    """Test TMI tranche 30%"""
    tmi = calculer_tmi(50000, 1.0)
    assert tmi == pytest.approx(0.30)


def test_tmi_tranche_41():
    """Test TMI tranche 41%"""
    tmi = calculer_tmi(100000, 1.0)
    assert tmi == pytest.approx(0.41)


def test_tmi_tranche_45():
    """Test TMI tranche 45%"""
    tmi = calculer_tmi(200000, 1.0)
    assert tmi == pytest.approx(0.45)


def test_decote_celibataire():
    """Test décote célibataire"""
    # IR brut = 1 000€ → décote = 1 929 - 0.75 × 1 000 = 1 179€
    decote = calculer_decote(1000, "celibataire")
    assert decote == pytest.approx(1929 - 0.75 * 1000)


def test_decote_couple():
    """Test décote couple"""
    # IR brut = 2 000€ → décote = 3 191 - 0.75 × 2 000 = 1 691€
    decote = calculer_decote(2000, "couple")
    assert decote == pytest.approx(3191 - 0.75 * 2000)


def test_decote_nulle():
    """Test décote nulle si IR élevé"""
    decote = calculer_decote(5000, "celibataire")
    assert decote == 0.0


def test_taux_moyen():
    """Test taux moyen"""
    taux = calculer_taux_moyen(5000, 50000)
    assert taux == pytest.approx(0.10)


def test_ir_complet_celibataire():
    """Test calcul IR complet célibataire"""
    result = calculer_ir_complet(50000, "celibataire", 0)
    assert result["parts"] == 1.0
    assert result["ir_brut"] > 0
    assert result["ir_net"] >= 0
    assert result["tmi"] == pytest.approx(0.30)


def test_ir_complet_couple_2_enfants():
    """Test calcul IR complet couple 2 enfants"""
    result = calculer_ir_complet(80000, "couple", 2)
    assert result["parts"] == 3.0
    assert result["quotient"] == pytest.approx(80000 / 3)
