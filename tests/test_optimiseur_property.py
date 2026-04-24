"""
Tests property-based de l'optimiseur d'allocation.
Vérifie que l'allocation est toujours valide pour tout profil/âge/contrainte.
"""
from __future__ import annotations

import pytest

pytest.importorskip("hypothesis")

from hypothesis import given, settings, strategies as st

from src.optimiseur_allocation import (
    CLASSES_ACTIONS,
    calculer_allocation_cible,
    charger_config_optimiseur,
    optimiser_allocation_mode_a,
)

_CONFIG = charger_config_optimiseur()


@given(
    profil=st.sampled_from(["defensif", "equilibre", "dynamique", "agressif"]),
    age=st.integers(min_value=18, max_value=90),
    usa_max=st.floats(min_value=0.0, max_value=1.0),
    em_max=st.floats(min_value=0.0, max_value=0.5),
    mode=st.sampled_from(["simple", "granulaire"]),
)
@settings(max_examples=50, deadline=5000)
def test_allocation_toujours_valide(profil, age, usa_max, em_max, mode):
    """Σ poids == 1, tous poids ∈ [0,1], contraintes respectées."""
    contraintes = {
        "exposition_usa_max": usa_max,
        "exposition_em_max": em_max,
    }
    resultat = optimiser_allocation_mode_a(
        profil_aversion=profil,
        config=_CONFIG,
        contraintes=contraintes,
        age=age,
        mode=mode,
    )
    poids = resultat["poids"]

    # Somme = 1
    total = sum(poids.values())
    assert abs(total - 1.0) < 1e-4, f"Σ poids = {total:.6f} ≠ 1.0 (profil={profil}, mode={mode})"

    # Tous les poids dans [0, 1]
    for k, v in poids.items():
        assert -1e-6 <= v <= 1.0 + 1e-6, f"poids[{k}] = {v:.6f} hors [0,1]"

    # Respect de actions_max
    profil_ar = _CONFIG["profils_aversion_risque"][profil]
    actions_max = float(profil_ar.get("actions_max", 1.0))
    total_actions = sum(poids.get(c, 0.0) for c in CLASSES_ACTIONS)
    assert total_actions <= actions_max + 1e-4, (
        f"total_actions={total_actions:.4f} > actions_max={actions_max} (profil={profil})"
    )

    # Respect de actions_min
    actions_min = float(profil_ar.get("actions_min", 0.0))
    assert total_actions >= actions_min - 1e-4, (
        f"total_actions={total_actions:.4f} < actions_min={actions_min} (profil={profil})"
    )
