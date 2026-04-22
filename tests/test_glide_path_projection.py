"""Tests d'intégration — glide path + Monte-Carlo"""
import numpy as np
from src.glide_path import charger_glide_paths
from src.projection import simuler_monte_carlo_glide_path


def test_projection_avec_glide_path_reproductible():
    gp = charger_glide_paths()["bogle_classique"]
    r1 = simuler_monte_carlo_glide_path(
        capital_initial=100_000, versement_annuel=5_000,
        age_debut=35, horizon_annees=30,
        glide_path=gp, nb_tirages=1000, seed=42,
    )
    r2 = simuler_monte_carlo_glide_path(
        capital_initial=100_000, versement_annuel=5_000,
        age_debut=35, horizon_annees=30,
        glide_path=gp, nb_tirages=1000, seed=42,
    )
    assert np.allclose(r1.trajectoires, r2.trajectoires)


def test_glide_path_plus_conservateur_mediane_plus_basse_mais_p10_plus_haute():
    """Un glide path plus conservateur devrait réduire la volatilité :
    médiane potentiellement plus basse mais P10 plus élevé (downside protection)."""
    gps = charger_glide_paths()
    gp_agressif = gps["agressif"]
    gp_conservateur = gps["conservateur"]

    kwargs = dict(
        capital_initial=100_000, versement_annuel=0,
        age_debut=50, horizon_annees=30,
        nb_tirages=2000, seed=7,
    )
    r_a = simuler_monte_carlo_glide_path(glide_path=gp_agressif, **kwargs)
    r_c = simuler_monte_carlo_glide_path(glide_path=gp_conservateur, **kwargs)

    # Le P10 du conservateur devrait être au moins aussi haut que celui de l'agressif
    assert r_c.capital_final_percentiles[10] >= r_a.capital_final_percentiles[10] * 0.9
