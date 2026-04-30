"""Tests unitaires — module glide path (lifecycle investing)"""

import contextlib

import pytest

with contextlib.suppress(ImportError):
    from src.glide_path import (
        _evaluer_formule_glide,
        _interpoler_points,
        charger_glide_paths,
        glide_path_pour_profil,
    )

pytestmark = pytest.mark.skip(reason="Module archivé suite au pivot EC — voir archive/README.md")


def test_charger_glide_paths():
    gps = charger_glide_paths()
    assert "bogle_classique" in gps
    assert "target_date_2040" in gps
    assert "pre_retraite_glide_down" in gps


def test_evaluation_formule_bogle():
    # 110 - 30 = 80, borné à [20, 90]
    assert _evaluer_formule_glide("max(20, min(90, 110 - age))", 30) == 80
    # Pour âge 100 : 110 - 100 = 10, borné à 20
    assert _evaluer_formule_glide("max(20, min(90, 110 - age))", 100) == 20
    # Pour âge 5 : 110 - 5 = 105, borné à 90
    assert _evaluer_formule_glide("max(20, min(90, 110 - age))", 5) == 90


def test_evaluation_formule_securite():
    """Doit rejeter les expressions dangereuses."""
    with pytest.raises(ValueError):
        _evaluer_formule_glide("__import__('os').system('ls')", 30)
    with pytest.raises(ValueError):
        _evaluer_formule_glide("open('/etc/passwd').read()", 30)


def test_interpolation_points():
    pts = [{"age": 25, "actions": 90}, {"age": 65, "actions": 40}]
    # Milieu exact : (90 + 40) / 2 = 65
    assert _interpoler_points(pts, 45) == 65.0
    # Hors bornes basses
    assert _interpoler_points(pts, 20) == 90.0
    # Hors bornes hautes
    assert _interpoler_points(pts, 80) == 40.0


def test_part_actions_decroit_avec_age():
    gps = charger_glide_paths()
    gp = gps["bogle_classique"]
    assert gp.part_actions(30) > gp.part_actions(60)


def test_allocation_somme_1():
    gps = charger_glide_paths()
    for nom, gp in gps.items():
        for age in [25, 45, 65, 85]:
            alloc = gp.allocation_a_age(age)
            total = alloc.as_array().sum()
            assert abs(total - 1.0) < 1e-6, f"{nom} @ {age} : somme = {total}"


def test_glide_path_pour_profil():
    gp = glide_path_pour_profil("profil_5_jeune")
    assert gp.nom == "agressif"


def test_trajectoire():
    gps = charger_glide_paths()
    gp = gps["bogle_classique"]
    traj = gp.trajectoire(30, 65)
    assert len(traj) == 36  # 30 à 65 inclus
    ages = [age for age, _ in traj]
    assert ages == list(range(30, 66))
