"""Tests pour CEHR et CDHR"""

import pytest

from src.fiscalite.pfu import calculer_cdhr, calculer_cehr


def test_cehr_celibataire_tranche_3_pct():
    """Test CEHR célibataire tranche 3% (RFR 250-500k)"""
    result = calculer_cehr(rfr=300000, revenus_capital=50000, situation="celibataire")

    assert result["taux"] == pytest.approx(0.03)
    assert result["cehr"] == pytest.approx(50000 * 0.03)


def test_cehr_celibataire_tranche_4_pct():
    """Test CEHR célibataire tranche 4% (RFR > 500k)"""
    result = calculer_cehr(rfr=600000, revenus_capital=50000, situation="celibataire")

    assert result["taux"] == pytest.approx(0.04)
    assert result["cehr"] == pytest.approx(50000 * 0.04)


def test_cehr_couple_tranche_3_pct():
    """Test CEHR couple tranche 3% (RFR 500k-1M)"""
    result = calculer_cehr(rfr=700000, revenus_capital=50000, situation="couple")

    assert result["taux"] == pytest.approx(0.03)
    assert result["cehr"] == pytest.approx(50000 * 0.03)


def test_cehr_couple_tranche_4_pct():
    """Test CEHR couple tranche 4% (RFR > 1M)"""
    result = calculer_cehr(rfr=1200000, revenus_capital=50000, situation="couple")

    assert result["taux"] == pytest.approx(0.04)
    assert result["cehr"] == pytest.approx(50000 * 0.04)


def test_cehr_non_applicable():
    """Test CEHR non applicable si RFR < seuil"""
    result = calculer_cehr(rfr=200000, revenus_capital=50000, situation="celibataire")

    assert result["taux"] == pytest.approx(0.0)
    assert result["cehr"] == pytest.approx(0.0)


def test_cdhr_plancher_20_pct_active():
    """Test CDHR plancher 20% activé"""
    # RFR 300k€, IR déjà payé 40k€ → taux effectif 13.3%
    # CDHR = 20% × 300k - 40k = 60k - 40k = 20k
    result = calculer_cdhr(
        rfr=300000, ir_total=40000, revenus_capital=50000, situation="celibataire"
    )

    assert result["applicable"] is True
    assert result["cdhr"] == pytest.approx(60000 - 40000)
    assert result["taux_effectif_apres"] == pytest.approx(0.20)


def test_cdhr_non_active_si_taux_suffisant():
    """Test CDHR non activée si taux effectif déjà > 20%"""
    # RFR 300k€, IR déjà payé 70k€ → taux effectif 23.3%
    result = calculer_cdhr(
        rfr=300000, ir_total=70000, revenus_capital=50000, situation="celibataire"
    )

    assert result["applicable"] is True
    assert result["cdhr"] == pytest.approx(0.0)


def test_cdhr_non_applicable_sous_seuil():
    """Test CDHR non applicable si RFR < seuil"""
    result = calculer_cdhr(
        rfr=200000, ir_total=30000, revenus_capital=50000, situation="celibataire"
    )

    assert result["applicable"] is False
    assert result["cdhr"] == pytest.approx(0.0)


def test_cumulabilite_cehr_cdhr():
    """Test cumulabilité CEHR + CDHR"""
    # Simulation : RFR élevé avec CEHR, mais taux effectif total < 20%
    rfr = 300000
    revenus_capital = 50000

    # CEHR
    cehr_result = calculer_cehr(rfr, revenus_capital, "celibataire")
    cehr = cehr_result["cehr"]

    # IR de base (exemple PFU)
    ir_base = revenus_capital * 0.128

    # CDHR sur IR total (IR base + CEHR)
    ir_total = ir_base + cehr
    cdhr_result = calculer_cdhr(rfr, ir_total, revenus_capital, "celibataire")

    # CDHR s'applique en complément de CEHR pour atteindre 20%
    assert cdhr_result["applicable"] is True
    total_impots = ir_total + cdhr_result["cdhr"]
    taux_effectif_final = total_impots / rfr
    assert taux_effectif_final >= 0.20 or taux_effectif_final == pytest.approx(0.20, abs=0.001)
