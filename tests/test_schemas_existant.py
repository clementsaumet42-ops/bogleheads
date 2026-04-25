"""Tests pour LigneExistante et composition_actuelle dans Profil."""

import json

from src.schemas import LigneExistante, Profil


def test_ligne_existante_creation():
    ligne = LigneExistante(
        enveloppe="CTO_IS", classe_actif="actions_monde_acwi", montant_eur=10000.0
    )
    assert ligne.enveloppe == "CTO_IS"
    assert ligne.montant_eur == 10000.0


def test_profil_composition_actuelle_optional():
    profil_dict = {
        "id": 1,
        "code": "TEST",
        "nom": "Test",
        "age": 45,
        "tmi": 0.30,
        "allocation_cible_bogleheads": {"actions": 0.6, "obligations": 0.4},
    }
    p = Profil.model_validate(profil_dict)
    assert p.composition_actuelle == []


def test_profil_avec_composition():
    profil_dict = {
        "id": 1,
        "code": "TEST",
        "nom": "Test",
        "age": 45,
        "tmi": 0.30,
        "allocation_cible_bogleheads": {"actions": 0.6, "obligations": 0.4},
        "composition_actuelle": [
            {"enveloppe": "CTO_IS", "classe_actif": "actions_monde_acwi", "montant_eur": 50000.0}
        ],
    }
    p = Profil.model_validate(profil_dict)
    assert len(p.composition_actuelle) == 1
    assert p.composition_actuelle[0].montant_eur == 50000.0


def test_profil_serialise_json():
    profil_dict = {
        "id": 1,
        "code": "TEST",
        "nom": "Test",
        "age": 45,
        "tmi": 0.30,
        "allocation_cible_bogleheads": {"actions": 0.6, "obligations": 0.4},
        "composition_actuelle": [
            {
                "enveloppe": "PEA",
                "classe_actif": "actions_usa",
                "montant_eur": 20000.0,
                "prix_revient_eur": 15000.0,
            }
        ],
    }
    p = Profil.model_validate(profil_dict)
    j = p.model_dump_json()
    data = json.loads(j)
    assert data["composition_actuelle"][0]["prix_revient_eur"] == 15000.0
