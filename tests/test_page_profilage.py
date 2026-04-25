"""Tests de la page Profilage (03_Profilage.py)."""

from pathlib import Path

import yaml


def test_page_profilage_exists():
    assert Path("pages/03_Profilage.py").exists()


def test_questionnaire_grable_lytton_yaml_found():
    path = Path("config/questionnaire_grable_lytton.yaml")
    assert path.exists()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data.get("nb_questions") == 13


def test_grable_lytton_13_questions():
    path = Path("config/questionnaire_grable_lytton.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert len(data["questions"]) == 13


def test_grable_lytton_4_options_each():
    path = Path("config/questionnaire_grable_lytton.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for q in data["questions"]:
        assert len(q["options"]) == 4, f"Q{q['id']} n'a pas 4 options"


def test_page_uses_yaml_not_slider():
    source = Path("pages/03_Profilage.py").read_text(encoding="utf-8")
    assert "questionnaire_grable_lytton.yaml" in source


def test_amf_yaml_found():
    path = Path("config/questionnaire_amf.yaml")
    assert path.exists()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    total_questions = sum(len(s["questions"]) for s in data.get("sections", []))
    assert total_questions >= 5
