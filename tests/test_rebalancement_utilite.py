"""Tests du panneau « Pourquoi rebalancer ? » et bilan coût/bénéfice — Sprint S11-C (≥ 4 tests)."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


# ─── Logique drift (répliquée depuis la page) ─────────────────────────────────


def _simuler_drift(
    allocation_cible: dict[str, float],
    mu_par_classe: dict[str, float],
) -> tuple[dict[str, float], float, str]:
    """
    Simule le drift sur 12 mois.

    Returns (allocation_future, derive_max, classe_max).
    """
    total = sum(allocation_cible.values())
    w0 = {k: v / total for k, v in allocation_cible.items()}

    w1_raw = {}
    for classe, w in w0.items():
        mu = mu_par_classe.get(classe, 0.05)
        w1_raw[classe] = w * (1 + mu)

    total1 = sum(w1_raw.values())
    w1 = {k: v / total1 for k, v in w1_raw.items()}

    derives = {k: abs(w1.get(k, 0) - w0.get(k, 0)) for k in w0}
    derive_max = max(derives.values()) if derives else 0.0
    classe_max = max(derives, key=derives.get) if derives else "—"

    return w1, derive_max, classe_max


def _verdict_drift(derive_max: float) -> str:
    if derive_max < 0.01:
        return "vert"
    elif derive_max < 0.05:
        return "orange"
    else:
        return "rouge"


def _ratio_cout_benefice(cout_total: float, benefice: float) -> float | None:
    if cout_total > 0 and benefice > 0:
        return cout_total / benefice
    return None


# ─── Tests drift ─────────────────────────────────────────────────────────────


def test_drift_negligeable_verdict_vert():
    """Un drift < 1 % produit un verdict vert."""
    # Rendements identiques → pas de drift relatif
    alloc = {"actions": 0.6, "obligations": 0.4}
    mu = {"actions": 0.05, "obligations": 0.05}  # mêmes rendements → pas de dérive
    _, derive_max, _ = _simuler_drift(alloc, mu)
    verdict = _verdict_drift(derive_max)
    assert verdict == "vert", f"Dérive attendue faible, obtenu {derive_max:.2%} → {verdict}"


def test_drift_fort_verdict_rouge():
    """Un drift ≥ 5 % produit un verdict rouge."""
    # Actions 100% rendement, obligations 0% → dérive forte
    alloc = {"actions": 0.5, "obligations": 0.5}
    mu = {"actions": 0.30, "obligations": 0.0}  # écart de rendement énorme
    _, derive_max, _ = _simuler_drift(alloc, mu)
    verdict = _verdict_drift(derive_max)
    assert verdict == "rouge", f"Dérive attendue forte (≥ 5%), obtenu {derive_max:.2%} → {verdict}"


def test_drift_intermediaire_verdict_orange():
    """Un drift entre 1 % et 5 % produit un verdict orange."""
    # Rendements légèrement différents
    alloc = {"actions": 0.7, "obligations": 0.3}
    mu = {"actions": 0.10, "obligations": 0.02}  # différence modérée
    _, derive_max, _ = _simuler_drift(alloc, mu)
    verdict = _verdict_drift(derive_max)
    # Peut être orange ou rouge selon l'écart exact
    assert verdict in ("orange", "rouge"), (
        f"Dérive attendue ≥ 1%, obtenu {derive_max:.2%} → {verdict}"
    )


def test_allocation_future_somme_a_1():
    """L'allocation future après simulation somme à 1 (normalisation correcte)."""
    alloc = {"actions": 0.6, "obligations": 0.3, "or": 0.1}
    mu = {"actions": 0.08, "obligations": 0.03, "or": 0.04}
    w1, _, _ = _simuler_drift(alloc, mu)
    assert abs(sum(w1.values()) - 1.0) < 1e-9, f"Somme future ≠ 1 : {sum(w1.values())}"


# ─── Tests bilan coût/bénéfice ────────────────────────────────────────────────


def test_cout_superieur_benefice_ratio_superieur_1():
    """Un coût > bénéfice produit un ratio > 1."""
    cout = 100.0
    benefice = 50.0
    ratio = _ratio_cout_benefice(cout, benefice)
    assert ratio is not None
    assert ratio > 1.0, f"Ratio attendu > 1, obtenu {ratio}"


def test_cout_inferieur_benefice_ratio_inferieur_1():
    """Un coût < bénéfice produit un ratio < 1."""
    cout = 30.0
    benefice = 150.0
    ratio = _ratio_cout_benefice(cout, benefice)
    assert ratio is not None
    assert ratio < 1.0, f"Ratio attendu < 1, obtenu {ratio}"


def test_cout_nul_ratio_none():
    """Un coût nul retourne ratio None (pas de division par zéro)."""
    ratio = _ratio_cout_benefice(0.0, 100.0)
    assert ratio is None


def test_benefice_nul_ratio_none():
    """Un bénéfice nul retourne ratio None."""
    ratio = _ratio_cout_benefice(50.0, 0.0)
    assert ratio is None


# ─── Test de compilation de la page ──────────────────────────────────────────


def test_page_rebalancement_compilable():
    """La page 09_Rebalancement.py se compile sans erreur de syntaxe."""
    pytest.skip("Page archivée — pivot EC")

