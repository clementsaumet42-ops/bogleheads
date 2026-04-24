from __future__ import annotations

from src.profilage.grable_lytton import calculer_profil_grable_lytton


def test_score_minimum():
    r = {i: 1 for i in range(1, 14)}
    p = calculer_profil_grable_lytton(r)
    assert p.score_brut == 13
    assert p.categorie == "tres_faible"


def test_score_maximum():
    r = {i: 4 for i in range(1, 14)}
    p = calculer_profil_grable_lytton(r)
    assert p.score_brut == 47 or p.score_brut > 32
    assert p.categorie == "tres_elevee"


def test_score_moyen():
    r = {i: 2 for i in range(1, 14)}
    p = calculer_profil_grable_lytton(r)
    assert p.score_brut == 26
    assert p.categorie == "moyenne"
