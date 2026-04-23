"""Tests unitaires — projection patrimoniale Monte-Carlo"""

import numpy as np

from src.projection import (
    AllocationClasses,
    ParametresProjection,
    calculer_capital_net_impots,
    charger_params,
    probabilite_atteindre_objectif,
    simuler_monte_carlo,
)


def test_charger_params():
    params = charger_params()
    assert "classes_actifs" in params
    assert params["simulation"]["nb_tirages"] == 10000


def test_allocation_somme_1():
    a = AllocationClasses(actions_monde=0.6, obligations=0.4)
    assert abs(a.as_array().sum() - 1.0) < 1e-9


def test_simulation_reproductible():
    alloc = AllocationClasses(actions_monde=0.7, obligations=0.3)
    p = ParametresProjection(
        capital_initial=100_000,
        versement_annuel=0,
        horizon_annees=10,
        allocation=alloc,
        nb_tirages=1000,
        seed=42,
    )
    r1 = simuler_monte_carlo(p)
    r2 = simuler_monte_carlo(p)
    assert np.allclose(r1.trajectoires, r2.trajectoires)


def test_mediane_croit_avec_rendement_positif():
    """Sans versement, la médiane à 30 ans > capital initial si rendement > 0."""
    alloc = AllocationClasses(actions_monde=1.0)
    p = ParametresProjection(
        capital_initial=100_000,
        versement_annuel=0,
        horizon_annees=30,
        allocation=alloc,
        nb_tirages=2000,
        seed=1,
    )
    r = simuler_monte_carlo(p)
    assert r.capital_final_percentiles[50] > 100_000


def test_versement_augmente_capital():
    alloc = AllocationClasses(actions_monde=0.6, obligations=0.4)
    base = ParametresProjection(100_000, 0, 20, alloc, nb_tirages=1000, seed=1)
    avec = ParametresProjection(100_000, 10_000, 20, alloc, nb_tirages=1000, seed=1)
    r_base = simuler_monte_carlo(base)
    r_avec = simuler_monte_carlo(avec)
    assert r_avec.capital_final_percentiles[50] > r_base.capital_final_percentiles[50]


def test_fiscalite_sortie():
    # PV = 50k, taux 30% => net = 150k - 15k = 135k
    assert calculer_capital_net_impots(150_000, 100_000, 0.30) == 135_000


def test_probabilite_objectif():
    traj = np.array([[100, 120], [100, 90], [100, 150], [100, 200]])
    assert probabilite_atteindre_objectif(traj, 120) == 0.75


def test_trajectoires_shape():
    alloc = AllocationClasses(actions_monde=0.5, obligations=0.5)
    p = ParametresProjection(
        capital_initial=50_000,
        versement_annuel=5_000,
        horizon_annees=10,
        allocation=alloc,
        nb_tirages=500,
        seed=0,
    )
    r = simuler_monte_carlo(p)
    assert r.trajectoires.shape == (500, 11)
    assert r.capital_median_par_annee.shape == (11,)
    assert r.capital_p10_par_annee.shape == (11,)
    assert r.capital_p90_par_annee.shape == (11,)


def test_capital_initial_preservee():
    """L'année 0 doit être égale au capital initial pour toutes les trajectoires."""
    alloc = AllocationClasses(actions_monde=1.0)
    p = ParametresProjection(
        capital_initial=200_000,
        versement_annuel=0,
        horizon_annees=5,
        allocation=alloc,
        nb_tirages=100,
        seed=7,
    )
    r = simuler_monte_carlo(p)
    assert np.allclose(r.trajectoires[:, 0], 200_000)


def test_probabilite_objectif_valeurs_limites():
    traj = np.array([[100, 200], [100, 200], [100, 200]])
    # Objectif atteint par tous
    assert probabilite_atteindre_objectif(traj, 200) == 1.0
    # Objectif jamais atteint
    assert probabilite_atteindre_objectif(traj, 201) == 0.0


def test_allocation_classes_liste():
    alloc = AllocationClasses(actions_monde=0.6, obligations=0.4)
    classes = alloc.classes
    assert "actions_monde" in classes
    assert "obligations" in classes
    assert len(classes) == 9
