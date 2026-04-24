"""
Tests unitaires ciblés pour les bugs d'allocation remontés.
"""

from __future__ import annotations

from src.allocation import allocation_bogleheads_par_age, valider_allocation
from src.optimiseur_allocation import (
    charger_config_optimiseur,
    optimiser_allocation_mode_a,
)

_CONFIG = charger_config_optimiseur()


class TestSomme100:
    """Test que l'allocation somme toujours à 100%."""

    def test_somme_100_mode_simple(self):
        for profil in ["defensif", "equilibre", "dynamique", "agressif"]:
            res = optimiser_allocation_mode_a(profil, _CONFIG, mode="simple")
            total = sum(res["poids"].values())
            assert abs(total - 1.0) < 1e-6, f"profil={profil}, Σ={total}"

    def test_somme_100_mode_granulaire(self):
        for profil in ["defensif", "equilibre", "dynamique", "agressif"]:
            res = optimiser_allocation_mode_a(profil, _CONFIG, mode="granulaire")
            total = sum(res["poids"].values())
            assert abs(total - 1.0) < 1e-6, f"profil={profil}, Σ={total}"

    def test_somme_100_bogleheads_par_age(self):
        for age in [20, 30, 45, 60, 75, 90]:
            alloc = allocation_bogleheads_par_age(age)
            total = sum(v for k, v in alloc.items() if not k.startswith("_"))
            assert abs(total - 1.0) < 1e-6, f"age={age}, Σ={total}"


class TestPasDeSurPonderationUSParDefautModeSimple:
    """En mode simple, aucune classe actions_usa ne devrait apparaître."""

    def test_pas_de_classe_usa_mode_simple(self):
        for profil in ["defensif", "equilibre", "dynamique", "agressif"]:
            res = optimiser_allocation_mode_a(profil, _CONFIG, mode="simple")
            poids = res["poids"]
            assert poids.get("actions_usa", 0.0) == 0.0, (
                f"profil={profil}: actions_usa={poids.get('actions_usa')} en mode simple"
            )
            assert poids.get("actions_dev_ex_usa", 0.0) == 0.0, (
                f"profil={profil}: actions_dev_ex_usa présent en mode simple"
            )

    def test_acwi_domine_profil_agressif_simple(self):
        res = optimiser_allocation_mode_a("agressif", _CONFIG, mode="simple")
        poids = res["poids"]
        acwi = poids.get("actions_monde_acwi", 0.0)
        TOL = 1e-9
        assert acwi >= 0.85 - TOL, f"profil agressif mode simple: actions_monde_acwi={acwi:.2%}"


class TestFallbackFlaggedVisible:
    """Test que le statut fallback est bien propagé."""

    def test_statut_present(self):
        res = optimiser_allocation_mode_a("equilibre", _CONFIG)
        assert "statut" in res
        assert res["statut"] in ("optimal", "fallback")

    def test_fallback_contient_message(self):
        from src.optimiseur_allocation import CLASSES_ACTIFS_ORDRE, _fallback_allocation_mode_a

        classes = [
            c
            for c in CLASSES_ACTIFS_ORDRE
            if c in _CONFIG["classes_actifs"]
            and c != "actions_usa"
            and c != "actions_dev_ex_usa"
            and c != "actions_em"
        ]
        res = _fallback_allocation_mode_a(classes, _CONFIG, "equilibre", {}, 0.025, mode="simple")
        assert res["statut"] == "fallback"
        assert res["message"] is not None


class TestCommentaireRenomme:
    """Test que _commentaire est bien utilisé (et commentaire ne l'est plus)."""

    def test_commentaire_remplace_par_underscore(self):
        alloc = allocation_bogleheads_par_age(40)
        assert "_commentaire" in alloc
        assert "commentaire" not in alloc

    def test_valider_allocation_ignore_underscore_commentaire(self):
        alloc = {
            "actions": 0.60,
            "obligations": 0.30,
            "or": 0.05,
            "liquidites": 0.05,
            "_commentaire": "Test",
        }
        assert valider_allocation(alloc) is True
