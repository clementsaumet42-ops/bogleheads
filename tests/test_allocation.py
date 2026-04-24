"""Tests for src/allocation.py"""

import pytest

from src.allocation import (
    allocation_bogleheads_par_age,
    charger_profils,
    get_profil_par_id,
    valider_allocation,
)


class TestValiderAllocation:
    def test_allocation_valide(self):
        alloc = {"actions": 0.60, "obligations": 0.30, "or": 0.05, "liquidites": 0.05}
        assert valider_allocation(alloc) is True

    def test_allocation_invalide(self):
        alloc = {"actions": 0.60, "obligations": 0.30}
        assert valider_allocation(alloc) is False

    def test_allocation_ignore_commentaire(self):
        alloc = {
            "actions": 0.60,
            "obligations": 0.30,
            "or": 0.05,
            "liquidites": 0.05,
            "_commentaire": "Test",
        }
        assert valider_allocation(alloc) is True

    def test_allocation_zero_invalide(self):
        alloc = {"actions": 0.0, "obligations": 0.0}
        assert valider_allocation(alloc) is False


class TestAllocationParAge:
    def test_jeune_plus_actions(self):
        alloc_jeune = allocation_bogleheads_par_age(25)
        alloc_senior = allocation_bogleheads_par_age(60)
        assert alloc_jeune["actions"] > alloc_senior["actions"]

    def test_senior_plus_obligations(self):
        alloc_jeune = allocation_bogleheads_par_age(25)
        alloc_senior = allocation_bogleheads_par_age(60)
        assert alloc_senior["obligations"] > alloc_jeune["obligations"]

    def test_somme_proche_1(self):
        for age in [20, 30, 45, 60, 75]:
            alloc = allocation_bogleheads_par_age(age)
            total = sum(v for k, v in alloc.items() if not k.startswith("_"))
            assert abs(total - 1.0) < 0.01, f"age={age}, total={total}"

    def test_toutes_classes_presentes(self):
        alloc = allocation_bogleheads_par_age(40)
        for key in ["actions", "obligations", "immobilier_cote", "or", "liquidites"]:
            assert key in alloc

    def test_commentaire_present(self):
        alloc = allocation_bogleheads_par_age(40)
        assert "_commentaire" in alloc
        assert "40" in alloc["_commentaire"]


class TestChargerProfils:
    def test_charge_profils(self):
        data = charger_profils()
        assert "profils" in data
        assert len(data["profils"]) > 0

    def test_profil_par_id(self):
        data = charger_profils()
        profil = get_profil_par_id(data, 1)
        assert profil["id"] == 1

    def test_profil_inexistant(self):
        data = charger_profils()
        with pytest.raises(ValueError):
            get_profil_par_id(data, 9999)

    def test_profils_ont_allocation(self):
        data = charger_profils()
        for profil in data["profils"]:
            assert "allocation_cible_bogleheads" in profil
