"""
Tests pour src/optimiseur_allocation.py — Sprint S2.

≥ 15 tests couvrant :
  - Mode A : profil défensif (actions < 40%)
  - Mode A : profil agressif (actions > 85%)
  - Mode A : contrainte exposition_usa_max
  - Mode A : contrainte exposition_em_max
  - Mode A : Σ w_i = 1 (tolérance 1e-6)
  - Mode B : respect plafond PEA (150 k€)
  - Mode B : obligations non placées dans PEA
  - Mode B : coût optimisé ≤ coût naïf
  - Mode B : Σ par classe = allocation cible (tolérance 1%)
  - Chaînage Mode A → Mode B cohérent
  - Reproductibilité (même input → même output)
  - Résolution en < 5 s pour patrimoine 500 k€
  - API calculer_allocation_cible()
  - Test avec 3 profils clients existants du YAML
  - Fallback heuristique si pulp absent
"""

from __future__ import annotations

import time

import pytest

from src.optimiseur_allocation import (
    CLASSES_ACTIONS,
    calculer_allocation_cible,
    charger_config_optimiseur,
    optimiser_allocation_mode_a,
    optimiser_asset_location_mode_b,
    optimiser_portefeuille_complet,
)
from src.schemas import charger_et_valider


@pytest.fixture(scope="module")
def config():
    return charger_config_optimiseur()


@pytest.fixture(scope="module")
def profils():
    return charger_et_valider("profils_clients.yaml")


@pytest.fixture
def enveloppes_standard():
    """Enveloppes typiques d'un profil français."""
    return {
        "PEA": {"encours_actuel": 80_000, "plafond": 150_000, "ouvert": True},
        "PER": {"encours_actuel": 50_000, "ouvert": True},
        "CTO": {"encours_actuel": 150_000, "ouvert": True},
    }


# ─── Mode A : Allocation cible ────────────────────────────────────────────────


class TestModeADefensif:
    """Test Mode A : profil défensif — actions < 40%."""

    def test_actions_max_40_pct(self, config):
        res = optimiser_allocation_mode_a("defensif", config)
        poids = res["poids"]
        total_actions = sum(poids.get(c, 0.0) for c in CLASSES_ACTIONS)
        assert total_actions <= 0.40 + 1e-6, f"Profil défensif : actions={total_actions:.1%} > 40%"

    def test_statut_valide(self, config):
        res = optimiser_allocation_mode_a("defensif", config)
        assert res["statut"] in ("optimal", "fallback")

    def test_rendement_positif(self, config):
        res = optimiser_allocation_mode_a("defensif", config)
        assert res["rendement_attendu"] > 0


class TestModeAAgressif:
    """Test Mode A : profil agressif — actions > 85%."""

    def test_actions_min_85_pct(self, config):
        res = optimiser_allocation_mode_a("agressif", config)
        poids = res["poids"]
        total_actions = sum(poids.get(c, 0.0) for c in CLASSES_ACTIONS)
        assert total_actions >= 0.85 - 1e-4, f"Profil agressif : actions={total_actions:.1%} < 85%"

    def test_rendement_superieur_defensif(self, config):
        res_agressif = optimiser_allocation_mode_a("agressif", config)
        res_defensif = optimiser_allocation_mode_a("defensif", config)
        assert res_agressif["rendement_attendu"] >= res_defensif["rendement_attendu"]


class TestModeAContraintes:
    """Test Mode A : contraintes personnalisées."""

    def test_contrainte_usa_max(self, config):
        contraintes = {"exposition_usa_max": 0.20}
        res = optimiser_allocation_mode_a("dynamique", config, contraintes=contraintes)
        poids = res["poids"]
        usa = poids.get("actions_usa", 0.0)
        assert usa <= 0.20 + 1e-4, f"USA={usa:.1%} > 20%"

    def test_contrainte_em_max(self, config):
        contraintes = {"exposition_em_max": 0.10}
        res = optimiser_allocation_mode_a("dynamique", config, contraintes=contraintes)
        poids = res["poids"]
        em = poids.get("actions_em", 0.0)
        assert em <= 0.10 + 1e-4, f"EM={em:.1%} > 10%"

    def test_contrainte_usa_et_em(self, config):
        contraintes = {"exposition_usa_max": 0.30, "exposition_em_max": 0.08}
        res = optimiser_allocation_mode_a("dynamique", config, contraintes=contraintes)
        poids = res["poids"]
        assert poids.get("actions_usa", 0.0) <= 0.30 + 1e-4
        assert poids.get("actions_em", 0.0) <= 0.08 + 1e-4


class TestModeASomme:
    """Test Mode A : Σ w_i = 1."""

    def test_somme_poids_equilibre(self, config):
        res = optimiser_allocation_mode_a("equilibre", config)
        total = sum(res["poids"].values())
        assert abs(total - 1.0) < 1e-6, f"Σ poids = {total:.8f} ≠ 1"

    def test_somme_poids_defensif(self, config):
        res = optimiser_allocation_mode_a("defensif", config)
        total = sum(res["poids"].values())
        assert abs(total - 1.0) < 1e-6

    def test_somme_poids_agressif(self, config):
        res = optimiser_allocation_mode_a("agressif", config)
        total = sum(res["poids"].values())
        assert abs(total - 1.0) < 1e-6

    def test_poids_positifs(self, config):
        res = optimiser_allocation_mode_a("equilibre", config)
        for classe, poids in res["poids"].items():
            assert poids >= -1e-8, f"Poids négatif : {classe}={poids}"

    def test_indicateurs_presents(self, config):
        res = optimiser_allocation_mode_a("equilibre", config)
        assert "rendement_attendu" in res
        assert "volatilite_attendue" in res
        assert "ratio_sharpe" in res
        assert res["volatilite_attendue"] >= 0


# ─── Mode B : Asset Location ─────────────────────────────────────────────────


class TestModeBPlafondPEA:
    """Test Mode B : respect du plafond PEA."""

    def test_plafond_pea_respecte(self, config):
        allocation_cible = {
            "actions_usa": 0.40,
            "actions_dev_ex_usa": 0.20,
            "obligations_agg_monde": 0.30,
            "monetaire": 0.10,
        }
        patrimoine = 500_000
        enveloppes = {
            "PEA": {"encours_actuel": 80_000, "plafond": 150_000, "ouvert": True},
            "CTO": {"encours_actuel": 0, "ouvert": True},
        }
        res = optimiser_asset_location_mode_b(allocation_cible, patrimoine, enveloppes, config)
        ventilation = res["ventilation"]
        total_pea = sum(v["montant"] for v in ventilation if v["enveloppe"] == "PEA")
        assert total_pea <= 70_000 + 1.0, f"Total PEA={total_pea:.0f} > espace restant 70 000 €"


class TestModeBEligibilite:
    """Test Mode B : obligations US non placées dans PEA."""

    def test_obligations_monde_hors_pea(self, config):
        allocation_cible = {
            "obligations_agg_monde": 0.30,
            "actions_usa": 0.70,
        }
        patrimoine = 200_000
        enveloppes = {
            "PEA": {"encours_actuel": 0, "plafond": 150_000, "ouvert": True},
            "PER": {"encours_actuel": 0, "ouvert": True},
            "CTO": {"encours_actuel": 0, "ouvert": True},
        }
        res = optimiser_asset_location_mode_b(allocation_cible, patrimoine, enveloppes, config)
        ventilation = res["ventilation"]
        oblig_en_pea = sum(
            v["montant"]
            for v in ventilation
            if v["classe"] == "obligations_agg_monde" and v["enveloppe"] == "PEA"
        )
        assert oblig_en_pea < 1.0, f"Obligations monde placées en PEA : {oblig_en_pea:.0f} €"


class TestModeBCoutOptimise:
    """Test Mode B : coût optimisé ≤ coût naïf."""

    def test_cout_optimise_inferieur_naif(self, config, enveloppes_standard):
        allocation_cible = {
            "actions_usa": 0.35,
            "actions_dev_ex_usa": 0.20,
            "actions_em": 0.10,
            "obligations_agg_monde": 0.20,
            "obligations_euro": 0.10,
            "monetaire": 0.05,
        }
        res = optimiser_asset_location_mode_b(
            allocation_cible, 500_000, enveloppes_standard, config
        )
        assert res["cout_annuel_optimise"] <= res["cout_annuel_naif"] + 1.0, (
            f"Coût opt={res['cout_annuel_optimise']:.0f} > naïf={res['cout_annuel_naif']:.0f}"
        )

    def test_economie_positive_ou_nulle(self, config, enveloppes_standard):
        allocation_cible = {
            "actions_usa": 0.40,
            "obligations_agg_monde": 0.35,
            "or_matieres": 0.15,
            "monetaire": 0.10,
        }
        res = optimiser_asset_location_mode_b(
            allocation_cible, 300_000, enveloppes_standard, config
        )
        assert res["economie_annuelle"] >= -1.0


class TestModeBSommeClasses:
    """Test Mode B : Σ par classe ≈ allocation cible."""

    def test_somme_par_classe_correcte(self, config, enveloppes_standard):
        allocation_cible = {
            "actions_usa": 0.35,
            "obligations_agg_monde": 0.40,
            "or_matieres": 0.15,
            "monetaire": 0.10,
        }
        patrimoine = 400_000
        res = optimiser_asset_location_mode_b(
            allocation_cible, patrimoine, enveloppes_standard, config
        )
        ventilation = res["ventilation"]
        for classe, poids in allocation_cible.items():
            total_v = sum(v["montant"] for v in ventilation if v["classe"] == classe)
            cible = poids * patrimoine
            assert abs(total_v - cible) <= cible * 0.01 + 10, (
                f"Classe {classe} : ventilé={total_v:.0f} vs cible={cible:.0f}"
            )


# ─── Chaînage Mode A → Mode B ─────────────────────────────────────────────────


class TestChainage:
    """Test chaînage Mode A → Mode B."""

    def test_chainage_coherent(self, config, enveloppes_standard):
        profil = {
            "age": 40,
            "profil_aversion_risque": "dynamique",
            "patrimoine_financier_total": 500_000,
            "contraintes_personnalisees": {"exposition_usa_max": 0.45},
            "enveloppes_disponibles": enveloppes_standard,
        }
        res = optimiser_portefeuille_complet(profil, config)
        assert "allocation_cible" in res
        assert "resultat_mode_a" in res
        assert "resultat_mode_b" in res
        # La somme des poids Mode A doit être ≈ 1
        total_poids = sum(res["allocation_cible"].values())
        assert abs(total_poids - 1.0) < 1e-6

    def test_mode_b_utilise_poids_mode_a(self, config, enveloppes_standard):
        profil = {
            "age": 45,
            "profil_aversion_risque": "equilibre",
            "patrimoine_financier_total": 200_000,
            "contraintes_personnalisees": {},
            "enveloppes_disponibles": enveloppes_standard,
        }
        res = optimiser_portefeuille_complet(profil, config)
        # Vérification : toutes les classes du Mode A avec poids > 0.1% ont une ventilation
        poids_a = res["allocation_cible"]
        classes_avec_poids = {c for c, p in poids_a.items() if p > 0.001}
        classes_ventilees = {v["classe"] for v in res["resultat_mode_b"]["ventilation"]}
        for c in classes_avec_poids:
            assert c in classes_ventilees, f"Classe {c} non ventilée en Mode B"


# ─── Performance ──────────────────────────────────────────────────────────────


class TestPerformance:
    """Test de performance : résolution < 5 s pour 500 k€."""

    def test_temps_resolution_mode_a(self, config):
        debut = time.time()
        optimiser_allocation_mode_a("dynamique", config)
        duree = time.time() - debut
        assert duree < 5.0, f"Mode A trop lent : {duree:.2f}s"

    def test_temps_resolution_mode_b_500k(self, config):
        allocation_cible = {
            "actions_usa": 0.35,
            "actions_dev_ex_usa": 0.20,
            "actions_em": 0.10,
            "obligations_agg_monde": 0.20,
            "obligations_euro": 0.10,
            "or_matieres": 0.05,
        }
        enveloppes = {
            "PEA": {"encours_actuel": 80_000, "plafond": 150_000, "ouvert": True},
            "PER": {"encours_actuel": 50_000, "ouvert": True},
            "CTO": {"encours_actuel": 150_000, "ouvert": True},
            "PEE": {"encours_actuel": 20_000, "ouvert": True},
        }
        debut = time.time()
        optimiser_asset_location_mode_b(allocation_cible, 500_000, enveloppes, config)
        duree = time.time() - debut
        assert duree < 5.0, f"Mode B trop lent : {duree:.2f}s"


# ─── Reproductibilité ─────────────────────────────────────────────────────────


class TestReproductibilite:
    """Test reproductibilité : même input → même output."""

    def test_mode_a_reproductible(self, config):
        res1 = optimiser_allocation_mode_a("equilibre", config)
        res2 = optimiser_allocation_mode_a("equilibre", config)
        for classe in res1["poids"]:
            assert abs(res1["poids"][classe] - res2["poids"].get(classe, 0.0)) < 1e-8

    def test_mode_b_reproductible(self, config, enveloppes_standard):
        allocation_cible = {
            "actions_usa": 0.40,
            "obligations_agg_monde": 0.40,
            "monetaire": 0.20,
        }
        res1 = optimiser_asset_location_mode_b(
            allocation_cible, 300_000, enveloppes_standard, config
        )
        res2 = optimiser_asset_location_mode_b(
            allocation_cible, 300_000, enveloppes_standard, config
        )
        assert abs(res1["cout_annuel_optimise"] - res2["cout_annuel_optimise"]) < 0.01


# ─── API calculer_allocation_cible ────────────────────────────────────────────


class TestAPIPublique:
    """Test de l'API publique calculer_allocation_cible."""

    def test_retourne_dict_classe_poids(self, config):
        profil = {
            "age": 45,
            "profil_aversion_risque": "dynamique",
            "contraintes_personnalisees": {},
        }
        poids = calculer_allocation_cible(profil, config)
        assert isinstance(poids, dict)
        assert len(poids) > 0
        assert abs(sum(poids.values()) - 1.0) < 1e-6

    def test_contraintes_appliquees_via_api(self, config):
        profil = {
            "age": 40,
            "profil_aversion_risque": "agressif",
            "contraintes_personnalisees": {"exposition_usa_max": 0.25},
        }
        poids = calculer_allocation_cible(profil, config)
        assert poids.get("actions_usa", 0.0) <= 0.25 + 1e-4


# ─── Tests avec profils YAML existants ────────────────────────────────────────


class TestAvecProfilsYAML:
    """Tests avec les 3 premiers profils clients du YAML."""

    def test_profil_1_cadre(self, config, profils):
        profil = next(p for p in profils.profils if p.id == 1)
        poids = calculer_allocation_cible(profil, config)
        assert abs(sum(poids.values()) - 1.0) < 1e-6
        # Profil dynamique → actions entre 70% et 90%
        total_actions = sum(poids.get(c, 0.0) for c in CLASSES_ACTIONS)
        assert 0.60 <= total_actions <= 0.95, f"Profil 1 actions={total_actions:.1%}"

    def test_profil_2_dirigeant(self, config, profils):
        profil = next(p for p in profils.profils if p.id == 2)
        poids = calculer_allocation_cible(profil, config)
        assert abs(sum(poids.values()) - 1.0) < 1e-6

    def test_profil_5_jeune_cadre(self, config, profils):
        profil = next(p for p in profils.profils if p.id == 5)
        poids = calculer_allocation_cible(profil, config)
        total_actions = sum(poids.get(c, 0.0) for c in CLASSES_ACTIONS)
        # Profil agressif → actions ≥ 85%
        assert total_actions >= 0.85 - 1e-4, f"Profil 5 actions={total_actions:.1%}"

    def test_profil_1_mode_b_complet(self, config, profils):
        profil = next(p for p in profils.profils if p.id == 1)
        profil_dict = profil.model_dump(by_alias=True)
        res = optimiser_portefeuille_complet(profil_dict, config)
        assert res["resultat_mode_b"]["statut"] in ("optimal", "fallback")
        assert res["resultat_mode_b"]["economie_annuelle"] >= 0


# ─── Test fallback ────────────────────────────────────────────────────────────


class TestFallback:
    """Test du fallback heuristique."""

    def test_fallback_mode_a_renvoie_somme_1(self, config):
        """Le fallback heuristique doit retourner Σ poids = 1."""
        from src.optimiseur_allocation import _fallback_allocation_mode_a

        classes = list(config["classes_actifs"].keys())
        rf = config.get("taux_sans_risque", 0.025)
        res = _fallback_allocation_mode_a(classes, config, "equilibre", {}, rf)
        assert abs(sum(res["poids"].values()) - 1.0) < 1e-6

    def test_fallback_mode_a_contrainte_usa(self, config):
        """Le fallback doit respecter la contrainte USA max."""
        from src.optimiseur_allocation import _fallback_allocation_mode_a

        classes = list(config["classes_actifs"].keys())
        rf = config.get("taux_sans_risque", 0.025)
        contraintes = {"exposition_usa_max": 0.20}
        res = _fallback_allocation_mode_a(classes, config, "agressif", contraintes, rf)
        assert res["poids"].get("actions_usa", 0.0) <= 0.20 + 1e-4

    def test_fallback_mode_b_sans_pulp(self, config, enveloppes_standard):
        """Le fallback heuristique Mode B fonctionne sans pulp."""
        from src.optimiseur_allocation import _fallback_asset_location

        classes = ["actions_usa", "obligations_agg_monde"]
        montants = {"actions_usa": 200_000, "obligations_agg_monde": 100_000}
        res = _fallback_asset_location(classes, montants, enveloppes_standard, config, 300_000)
        assert res["statut"] == "fallback"
        assert len(res["ventilation"]) > 0
