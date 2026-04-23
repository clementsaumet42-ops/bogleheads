"""Tests for src/enveloppes.py"""

import pytest

from src.enveloppes import (
    calculer_plafond_restant,
    charger_enveloppes,
    get_enveloppe_par_id,
    verifier_eligibilite_etf,
)


@pytest.fixture
def enveloppes():
    return charger_enveloppes()


class TestChargerEnveloppes:
    def test_charge_liste(self, enveloppes):
        assert isinstance(enveloppes, list)
        assert len(enveloppes) > 0

    def test_chaque_env_a_un_id(self, enveloppes):
        for env in enveloppes:
            assert "id" in env
            assert isinstance(env["id"], str)

    def test_pea_present(self, enveloppes):
        ids = [env["id"] for env in enveloppes]
        assert "PEA" in ids

    def test_cto_present(self, enveloppes):
        ids = [env["id"] for env in enveloppes]
        assert "CTO_perso" in ids


class TestGetEnveloppeParId:
    def test_trouve_pea(self, enveloppes):
        pea = get_enveloppe_par_id(enveloppes, "PEA")
        assert pea is not None
        assert pea["id"] == "PEA"

    def test_inconnu_retourne_none(self, enveloppes):
        result = get_enveloppe_par_id(enveloppes, "INCONNU_XYZ")
        assert result is None


class TestVerifierEligibilite:
    def test_etf_eligible_pea(self):
        etf = {"eligibilite": {"PEA": True, "CTO_perso": True}}
        assert verifier_eligibilite_etf(etf, "PEA") is True

    def test_etf_non_eligible_pea(self):
        etf = {"eligibilite": {"PEA": False, "CTO_perso": True}}
        assert verifier_eligibilite_etf(etf, "PEA") is False

    def test_etf_sans_eligibilite(self):
        etf = {}
        assert verifier_eligibilite_etf(etf, "PEA") is False


class TestCalculerPlafondRestant:
    def test_plafond_avec_encours(self):
        env = {"id": "PEA", "plafond": 150000}
        result = calculer_plafond_restant(env, 80000)
        assert result == 70000.0

    def test_plafond_depasse_retourne_zero(self):
        env = {"id": "PEA", "plafond": 150000}
        result = calculer_plafond_restant(env, 160000)
        assert result == 0.0

    def test_sans_plafond_retourne_none(self):
        env = {"id": "CTO_perso", "plafond": None}
        result = calculer_plafond_restant(env, 500000)
        assert result is None
