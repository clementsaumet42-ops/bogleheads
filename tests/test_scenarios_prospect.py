from __future__ import annotations

from src.profilage.scenarios_prospect import calculer_score_scenarios, generer_scenarios


def test_cinq_scenarios():
    assert len(generer_scenarios()) == 5


def test_score_max():
    choix = {"sc1": "d", "sc2": "d", "sc3": "d", "sc4": "d", "sc5": "d"}
    assert calculer_score_scenarios(choix) == 2.0


def test_score_vide():
    assert calculer_score_scenarios({}) == 0.0
