"""Test de régression — Mission Cadre Sup IR.

Pipeline: inputs.yaml → alertes → allocation cible → fiscal → compare expected_outputs.json
Tolérance: 1e-6 pour fractions, 0.01€ pour montants.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

MISSION_DIR = Path(__file__).parent
INPUTS_PATH = MISSION_DIR / "inputs.yaml"
EXPECTED_PATH = MISSION_DIR / "expected_outputs.json"


@pytest.fixture(autouse=True)
def _fige_timestamp(monkeypatch):
    monkeypatch.setenv("MISSION_TEST_FROZEN_TIME", "2026-01-15T10:00:00")


@pytest.fixture(scope="module")
def profil():
    from src.schemas import AllocationCible, Profil

    with open(INPUTS_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    pd = data["profil"]
    alloc_d = pd.pop("allocation_cible_bogleheads")
    pd["allocation_cible_bogleheads"] = AllocationCible(**alloc_d)
    return Profil(**pd)


@pytest.fixture(scope="module")
def expected():
    with open(EXPECTED_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def alertes(profil):
    from src.audit.alertes import detecter_alertes

    return detecter_alertes(profil)


@pytest.fixture(scope="module")
def allocation_cible(profil):
    from src.allocation.asset_location_milp import calculer_allocation_cible

    return calculer_allocation_cible(profil, None)


class TestAlertes:
    def test_codes_alertes_attendus_presents(self, alertes, expected):
        codes = [a.code for a in alertes]
        for code in expected["alertes_codes"]:
            assert code in codes, f"Alerte {code} attendue mais absente. Codes: {codes}"

    def test_nb_alertes_minimum(self, alertes, expected):
        assert len(alertes) >= expected["nb_alertes_min"]


class TestAllocationCible:
    def test_actions_monde_acwi(self, allocation_cible, expected):
        tol = expected.get("allocation_tolerance", 1e-6)
        attendu = expected["allocation_cible"]["actions_monde_acwi"]
        assert abs(allocation_cible.get("actions_monde_acwi", 0) - attendu) <= tol

    def test_obligations_agg_monde(self, allocation_cible, expected):
        tol = expected.get("allocation_tolerance", 1e-6)
        attendu = expected["allocation_cible"]["obligations_agg_monde"]
        assert abs(allocation_cible.get("obligations_agg_monde", 0) - attendu) <= tol

    def test_allocation_somme_a_1(self, allocation_cible):
        total = sum(v for v in allocation_cible.values() if isinstance(v, (int, float)))
        assert abs(total - 1.0) < 1e-6, f"Allocation ne somme pas à 1: {total}"


class TestFiscal:
    def test_taux_pfu_total(self, expected):
        from src.fiscalite.constantes import TAUX_PFU_TOTAL

        assert abs(TAUX_PFU_TOTAL - expected["fiscal"]["taux_pfu_total"]) < 1e-6

    def test_taux_ps(self, expected):
        from src.fiscalite.constantes import TAUX_PS

        assert abs(TAUX_PS - expected["fiscal"]["taux_ps"]) < 1e-6

    def test_regime_is(self, profil, expected):
        assert (profil.regime_fiscal_detenteur == "IS") == expected["fiscal"]["regime_is"]

    def test_is_taux_normal(self, expected):
        from src.fiscalite.constantes import IS_TAUX_NORMAL

        assert abs(IS_TAUX_NORMAL - expected["fiscal"]["is_taux_normal"]) < 1e-6

    def test_pea_plafond_atteint(self, expected):
        from src.fiscalite.constantes import PEA_PLAFOND_VERSEMENTS
        from src.fiscalite.pea import verifier_plafond_pea

        pea_versements = 100000.0  # from inputs.yaml versements_cumules
        result = verifier_plafond_pea(pea_versements)
        is_atteint = result["respect_plafond"] and pea_versements >= PEA_PLAFOND_VERSEMENTS
        assert is_atteint == expected["pea_plafond_atteint"]

    def test_per_deduction_cadre(self, profil, expected):
        from src.fiscalite.per import calculer_plafond_deduction_per

        ded = calculer_plafond_deduction_per(profil.rfr_annuel)
        assert abs(ded - expected["per_deduction_max_eur"]) <= 0.01
