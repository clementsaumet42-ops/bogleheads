"""Tests S11-C — src/fiscalite/drag_etf.py.

Vérifie le calcul du drag fiscal intra-NAV par réplication × domicile × exposition.
"""

from __future__ import annotations

import logging

import pytest

from src.fiscalite.drag_etf import calculer_drag_fiscal_etf

# ─── Tests de base ───────────────────────────────────────────────────────────


def test_swap_drag_zero():
    """Tout ETF synthétique → drag = 0, quels que soient domicile / expo."""
    assert calculer_drag_fiscal_etf("synthetique_swap", "IE", "US") == 0.0
    assert calculer_drag_fiscal_etf("synthetique_swap", "LU", "US") == 0.0
    assert calculer_drag_fiscal_etf("synthetique_swap", "FR", "Emergents") == 0.0
    assert calculer_drag_fiscal_etf("synthetique_swap", "DE", "Monde_dev") == 0.0


def test_physique_ie_us():
    """ETF physique IE × exposition US → drag ~22 bps (traité IE-US 15%)."""
    drag = calculer_drag_fiscal_etf("physique_full", "IE", "US")
    # 15% × 1.5% × 10_000 = 22.5 bps
    assert 18 <= drag <= 25, f"Drag IE-US attendu 18–25 bps, obtenu {drag}"


def test_physique_lu_us():
    """ETF physique LU × exposition US → drag ~45 bps (30% sans traité)."""
    drag = calculer_drag_fiscal_etf("physique_sampling", "LU", "US")
    # 30% × 1.5% × 10_000 = 45.0 bps
    assert 40 <= drag <= 50, f"Drag LU-US attendu 40–50 bps, obtenu {drag}"


def test_physique_lu_us_superieur_ie_us():
    """Drag LU-US > drag IE-US (pas de traité fiscal favorable LU)."""
    drag_ie = calculer_drag_fiscal_etf("physique_full", "IE", "US")
    drag_lu = calculer_drag_fiscal_etf("physique_sampling", "LU", "US")
    assert drag_lu > drag_ie, f"LU-US ({drag_lu}) devrait être > IE-US ({drag_ie})"


def test_physique_emergents():
    """ETF physique × Emergents → drag entre 20 et 30 bps."""
    drag = calculer_drag_fiscal_etf("physique_sampling", "IE", "Emergents")
    # 10% × 2.5% × 10_000 = 25.0 bps
    assert 20 <= drag <= 30, f"Drag Emergents attendu 20–30 bps, obtenu {drag}"


def test_physique_europe_zero():
    """ETF physique UCITS sur sous-jacents européens → drag = 0."""
    assert calculer_drag_fiscal_etf("physique_sampling", "IE", "Europe") == 0.0
    assert calculer_drag_fiscal_etf("physique_full", "LU", "France") == 0.0
    assert calculer_drag_fiscal_etf("physique_sampling", "FR", "Europe") == 0.0


def test_champs_manquants(caplog):
    """Retourne 0.0 + log warning si un ou plusieurs champs manquent."""
    with caplog.at_level(logging.WARNING, logger="src.fiscalite.drag_etf"):
        r1 = calculer_drag_fiscal_etf(None, "IE", "US")
        r2 = calculer_drag_fiscal_etf("physique_full", None, "US")
        r3 = calculer_drag_fiscal_etf("physique_full", "IE", None)
        r4 = calculer_drag_fiscal_etf(None, None, None)

    assert r1 == 0.0
    assert r2 == 0.0
    assert r3 == 0.0
    assert r4 == 0.0
    # Au moins un warning doit avoir été émis
    assert len(caplog.records) >= 4


def test_yield_custom():
    """Un yield_brut_estime_pct custom remplace la valeur par défaut."""
    # Avec yield par défaut (1.5%) → 15% × 1.5% × 10_000 = 22.5 bps
    drag_defaut = calculer_drag_fiscal_etf("physique_full", "IE", "US")
    # Avec yield custom = 3.0% → 15% × 3.0% × 10_000 = 45.0 bps
    drag_custom = calculer_drag_fiscal_etf("physique_full", "IE", "US", yield_brut_estime_pct=3.0)
    assert drag_custom == pytest.approx(45.0, abs=0.1)
    assert drag_custom > drag_defaut


def test_physique_japon():
    """ETF physique × Japon → drag entre 25 et 35 bps."""
    drag = calculer_drag_fiscal_etf("physique_sampling", "IE", "Japon")
    # 15% × 2.0% × 10_000 = 30.0 bps
    assert 25 <= drag <= 35, f"Drag Japon attendu 25–35 bps, obtenu {drag}"
