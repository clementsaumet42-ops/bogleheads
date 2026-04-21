"""Tests unitaires — chargement et validation des profils clients"""
import pytest
from pathlib import Path
import yaml
from src.allocation import charger_profils, get_profil_par_id, valider_allocation


@pytest.fixture
def profils_data():
    return charger_profils()


def test_charger_profils_yaml(profils_data):
    """Vérifie que le YAML se charge sans erreur."""
    assert "profils" in profils_data
    assert "disclaimer" in profils_data


def test_nombre_profils(profils_data):
    """Vérifie qu'il y a exactement 6 profils."""
    assert len(profils_data["profils"]) == 6


def test_champs_obligatoires(profils_data):
    """Vérifie que chaque profil a les champs requis."""
    champs_requis = [
        "id",
        "nom",
        "age",
        "tmi",
        "rfr_annuel",
        "patrimoine_financier_total",
        "allocation_cible_bogleheads",
        "capacite_epargne_annuelle",
        "horizon_placement_ans",
    ]
    for profil in profils_data["profils"]:
        for champ in champs_requis:
            assert champ in profil, (
                f"Champ '{champ}' manquant dans profil {profil.get('id')}"
            )


def test_allocation_somme_a_100(profils_data):
    """Vérifie que chaque allocation cible somme à ~100%."""
    for profil in profils_data["profils"]:
        alloc = profil["allocation_cible_bogleheads"]
        assert valider_allocation(alloc), (
            f"Profil {profil['id']}: allocation ne somme pas à 100% — {alloc}"
        )


def test_ages_coherents(profils_data):
    """Vérifie la cohérence âge/allocation (jeune = plus d'actions)."""
    profils = profils_data["profils"]
    jeune = next(p for p in profils if p["id"] == 5)
    pre_retraite = next(p for p in profils if p["id"] == 6)
    assert jeune["allocation_cible_bogleheads"]["actions"] > \
           pre_retraite["allocation_cible_bogleheads"]["actions"], \
        "Jeune cadre devrait avoir plus d'actions que le pré-retraité"


def test_get_profil_par_id(profils_data):
    profil = get_profil_par_id(profils_data, 1)
    assert profil["nom"] == "Cadre Supérieur Salarié"


def test_get_profil_inexistant(profils_data):
    with pytest.raises(ValueError):
        get_profil_par_id(profils_data, 99)


def test_tmi_valides(profils_data):
    """Vérifie que les TMI sont des valeurs légales françaises."""
    tmi_valides = {0.00, 0.11, 0.30, 0.41, 0.45}
    for profil in profils_data["profils"]:
        assert profil["tmi"] in tmi_valides, (
            f"TMI invalide: {profil['tmi']} pour profil {profil['id']}"
        )


def test_score_risque_plage(profils_data):
    """Vérifie que les scores de risque sont dans la plage SRRI [1, 7]."""
    for profil in profils_data["profils"]:
        score = profil.get("score_risque")
        assert 1 <= score <= 7, (
            f"Score de risque invalide: {score} pour profil {profil['id']}"
        )


def test_horizons_positifs(profils_data):
    """Vérifie que les horizons de placement sont positifs."""
    for profil in profils_data["profils"]:
        assert profil["horizon_placement_ans"] > 0, (
            f"Horizon invalide pour profil {profil['id']}"
        )


def test_allocations_actions_croissantes_inversement_age(profils_data):
    """Vérifie la tendance générale : plus on est jeune, plus les actions dominent."""
    profils = profils_data["profils"]
    jeune = next(p for p in profils if p["id"] == 5)   # 32 ans, 85% actions
    senior = next(p for p in profils if p["id"] == 6)  # 62 ans, 35% actions
    assert jeune["allocation_cible_bogleheads"]["actions"] > 0.70
    assert senior["allocation_cible_bogleheads"]["actions"] < 0.50


def test_profil_dirigeant_pme_a_holding(profils_data):
    """Vérifie que le profil 3 (Dirigeant PME) a bien une holding IS configurée."""
    profil = get_profil_par_id(profils_data, 3)
    assert profil["particularites_fiscales"]["holding_is"] is True
    env = profil["enveloppes_disponibles"]
    assert env.get("Contrat_Cap_IS") is not None
    assert env.get("CTO_IS") is not None


def test_profil_jeune_cadre_pea_non_5ans(profils_data):
    """Vérifie que le jeune cadre n'a pas encore l'avantage fiscal 5 ans sur son PEA."""
    profil = get_profil_par_id(profils_data, 5)
    pea = profil["enveloppes_disponibles"].get("PEA", {})
    assert pea.get("avantage_fiscal_5ans") is False
