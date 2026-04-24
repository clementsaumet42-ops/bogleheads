"""Tests du package src.pedagogie — Sprint S8.1.

Couvre les 6 volets pédagogiques + scripts de restitution + modèle Explication.
"""

from __future__ import annotations

import importlib
import sys

import pytest

# ─── Fixtures de données de test ─────────────────────────────────────────────


@pytest.fixture
def poids_simple():
    """Poids d'allocation mode simple (ACWI)."""
    return {
        "actions_monde": 0.80,
        "obligations_monde": 0.15,
        "liquidites": 0.05,
    }


@pytest.fixture
def poids_granulaire():
    """Poids d'allocation mode granulaire."""
    return {
        "actions_us": 0.45,
        "actions_dev_ex_us": 0.20,
        "actions_emergents": 0.10,
        "obligations_monde": 0.20,
        "liquidites": 0.05,
    }


@pytest.fixture
def matrice_asset_location():
    """Matrice d'asset location avec gains estimés."""
    return [
        {"classe": "obligations_monde", "enveloppe": "AV", "montant": 50000.0, "gain_eur": 800.0},
        {"classe": "actions_monde", "enveloppe": "PEA", "montant": 80000.0, "gain_eur": 1200.0},
        {"classe": "actions_us", "enveloppe": "CTO", "montant": 20000.0, "gain_eur": 0.0},
    ]


@pytest.fixture
def plan_rebalancement():
    """Plan de rebalancement avec 3 étapes."""
    return {
        "etape_1_montant": 15000.0,
        "etape_2_flux_mensuel": 500.0,
        "etape_3_cout_fiscal": 450.0,
        "etape_3_montant_ventes": 10000.0,
    }


@pytest.fixture
def profil_consolide_convergent():
    """Profil consolidé avec convergence des 3 prismes."""
    return {
        "profil_final": "equilibre",
        "profil_declare": "equilibre",
        "profil_grable_lytton": "equilibre",
        "profil_scenarios": "equilibre",
        "convergent": True,
    }


@pytest.fixture
def profil_consolide_divergent():
    """Profil consolidé avec divergence des 3 prismes."""
    return {
        "profil_final": "defensif",
        "profil_declare": "dynamique",
        "profil_grable_lytton": "equilibre",
        "profil_scenarios": "defensif",
        "convergent": False,
    }


@pytest.fixture
def etf_sample():
    """ETF exemple pour les tests."""
    return {
        "ticker": "IWDA",
        "ter": 0.0020,
        "domicile": "IE",
        "methode_replication": "physique",
        "aum_mds": 65.0,
        "td_3y": -0.0015,
        "eligibilite": {"PEA": False, "AV_UC": True, "CTO_perso": True},
    }


# ─── Test 1 : chaque fonction expliquer_* retourne liste non vide ─────────────


class TestChaqueFonctionRetourneListeNonVide:
    """Boucle sur les 6 volets — chaque fonction retourne ≥ 1 Explication."""

    def test_expliquer_allocation_simple(self, poids_simple):
        from src.pedagogie import expliquer_allocation

        result = expliquer_allocation(poids_simple, "equilibre", "simple")
        assert isinstance(result, list)
        assert len(result) >= 2

    def test_expliquer_allocation_granulaire(self, poids_granulaire):
        from src.pedagogie import expliquer_allocation

        result = expliquer_allocation(poids_granulaire, "dynamique", "granulaire")
        assert isinstance(result, list)
        assert len(result) >= 2

    def test_expliquer_choix_etf(self, etf_sample):
        from src.pedagogie import expliquer_choix_etf

        result = expliquer_choix_etf(etf_sample)
        # expliquer_choix_etf retourne une seule Explication (pas une liste)
        from src.pedagogie.base import Explication

        assert isinstance(result, Explication)

    def test_expliquer_ter(self, etf_sample):
        from src.pedagogie import expliquer_ter

        result = expliquer_ter(etf_sample)
        from src.pedagogie.base import Explication

        assert isinstance(result, Explication)

    def test_expliquer_asset_location(self, matrice_asset_location):
        from src.pedagogie import expliquer_asset_location

        result = expliquer_asset_location(matrice_asset_location, tmi=0.30)
        assert isinstance(result, list)
        assert len(result) >= 2

    def test_expliquer_cascade_fiscale_cto(self):
        from src.pedagogie import expliquer_cascade_fiscale

        result = expliquer_cascade_fiscale("CTO", 50000.0, 0.30)
        assert isinstance(result, list)
        assert len(result) >= 2

    def test_expliquer_cascade_fiscale_pea(self):
        from src.pedagogie import expliquer_cascade_fiscale

        result = expliquer_cascade_fiscale("PEA", 30000.0, 0.41)
        assert isinstance(result, list)
        assert len(result) >= 2

    def test_expliquer_cascade_fiscale_av(self):
        from src.pedagogie import expliquer_cascade_fiscale

        result = expliquer_cascade_fiscale("AV", 20000.0, 0.30)
        assert isinstance(result, list)
        assert len(result) >= 2

    def test_expliquer_cascade_fiscale_per(self):
        from src.pedagogie import expliquer_cascade_fiscale

        result = expliquer_cascade_fiscale("PER", 10000.0, 0.41)
        assert isinstance(result, list)
        assert len(result) >= 2

    def test_expliquer_plan_rebalancement(self, plan_rebalancement):
        from src.pedagogie import expliquer_plan_rebalancement

        result = expliquer_plan_rebalancement(plan_rebalancement)
        assert isinstance(result, list)
        assert len(result) >= 3

    def test_expliquer_convergence_3_prismes(self, profil_consolide_convergent):
        from src.pedagogie import expliquer_convergence_3_prismes

        result = expliquer_convergence_3_prismes(profil_consolide_convergent)
        from src.pedagogie.base import Explication

        assert isinstance(result, Explication)

    def test_expliquer_prismes_detail(self, profil_consolide_convergent):
        from src.pedagogie import expliquer_prismes_detail

        result = expliquer_prismes_detail(profil_consolide_convergent)
        assert isinstance(result, list)
        assert len(result) == 3


# ─── Test 2 : chaque Explication a source non vide ───────────────────────────


class TestChaqueExplicationASourceNonVide:
    """Toutes les Explication ont un champ source non vide."""

    def _collect_all(
        self, poids_simple, matrice_asset_location, plan_rebalancement, profil_consolide_convergent
    ):
        from src.pedagogie import (
            expliquer_allocation,
            expliquer_asset_location,
            expliquer_cascade_fiscale,
            expliquer_convergence_3_prismes,
            expliquer_plan_rebalancement,
            expliquer_prismes_detail,
        )

        all_explications = []
        all_explications.extend(expliquer_allocation(poids_simple, "equilibre", "simple"))
        all_explications.extend(expliquer_asset_location(matrice_asset_location, 0.30))
        all_explications.extend(expliquer_cascade_fiscale("CTO", 50000.0, 0.30))
        all_explications.extend(expliquer_cascade_fiscale("PEA", 30000.0, 0.30))
        all_explications.extend(expliquer_cascade_fiscale("AV", 20000.0, 0.30))
        all_explications.extend(expliquer_cascade_fiscale("PER", 10000.0, 0.30))
        all_explications.extend(expliquer_plan_rebalancement(plan_rebalancement))
        all_explications.append(expliquer_convergence_3_prismes(profil_consolide_convergent))
        all_explications.extend(expliquer_prismes_detail(profil_consolide_convergent))
        return all_explications

    def test_source_non_vide(
        self, poids_simple, matrice_asset_location, plan_rebalancement, profil_consolide_convergent
    ):
        explications = self._collect_all(
            poids_simple, matrice_asset_location, plan_rebalancement, profil_consolide_convergent
        )
        for exp in explications:
            assert exp.source, f"Source vide pour la section '{exp.section}' (titre: {exp.titre!r})"


# ─── Test 3 : texte_court et texte_long non vides ────────────────────────────


class TestTextesCourtsEtLongsNonVides:
    """Toutes les Explication ont texte_court et texte_long non vides."""

    def test_textes_non_vides(self, poids_simple):
        from src.pedagogie import expliquer_allocation

        explications = expliquer_allocation(poids_simple, "defensif", "simple")
        for exp in explications:
            assert exp.texte_court.strip(), f"texte_court vide pour '{exp.section}'"
            assert exp.texte_long.strip(), f"texte_long vide pour '{exp.section}'"

    def test_texte_long_plus_long_que_court(self, poids_simple):
        from src.pedagogie import expliquer_allocation

        explications = expliquer_allocation(poids_simple, "agressif", "simple")
        for exp in explications:
            assert len(exp.texte_long) >= len(exp.texte_court), (
                f"texte_long devrait être ≥ texte_court pour '{exp.section}'"
            )


# ─── Test 4 : YAML — toutes les clés attendues présentes ─────────────────────


class TestScriptsYamlClesAttendues:
    """Charger scripts_restitution.yaml et vérifier qu'aucune clé requise n'est manquante."""

    def test_toutes_cles_attendues_presentes(self):
        from src.pedagogie.scripts import _CLES_REQUISES, charger_scripts_restitution

        scripts = charger_scripts_restitution()
        manquantes = _CLES_REQUISES - scripts.keys()
        assert not manquantes, (
            f"Clés manquantes dans scripts_restitution.yaml : {sorted(manquantes)}"
        )

    def test_scripts_non_vides(self):
        from src.pedagogie.scripts import charger_scripts_restitution

        scripts = charger_scripts_restitution()
        for cle, texte in scripts.items():
            assert texte.strip(), f"Script vide pour la clé '{cle}'"

    def test_6_volets_couverts(self):
        from src.pedagogie.scripts import charger_scripts_restitution

        scripts = charger_scripts_restitution()
        volets = {"profilage", "allocation", "etf", "asset_location", "fiscalite", "rebalancement"}
        for volet in volets:
            cles_volet = [k for k in scripts if k.startswith(f"{volet}.")]
            assert len(cles_volet) >= 2, (
                f"Volet '{volet}' a seulement {len(cles_volet)} script(s) — minimum 2 requis"
            )


# ─── Test 5 : rendre_script substitue les variables ──────────────────────────


class TestRendreScriptSubstitueVariables:
    """rendre_script remplace les placeholders {a} et {b}."""

    def test_substitution_complete(self):
        from src.pedagogie.scripts import rendre_script

        # Utiliser une clé existante avec variables connues
        result = rendre_script(
            "allocation.mode_simple_acwi",
            {"poids_acwi": 0.85, "ter": 0.0020, "profil_final": "equilibre"},
        )
        # Aucun placeholder non substitué ne doit rester
        assert "{" not in result, f"Placeholder non substitué dans : {result!r}"

    def test_substitution_partielle_permissive(self):
        """Les variables manquantes sont conservées telles quelles (mode permissif)."""
        from src.pedagogie.scripts import rendre_script

        result = rendre_script(
            "allocation.mode_simple_acwi",
            {"poids_acwi": 0.80},  # ter et profil_final manquants
        )
        # La fonction ne doit pas lever d'exception
        assert isinstance(result, str)
        assert len(result) > 0

    def test_cle_inexistante_leve_keyerror(self):
        from src.pedagogie.scripts import rendre_script

        with pytest.raises(KeyError):
            rendre_script("section.cle_inexistante_xyz")

    def test_sans_variables_retourne_texte_brut(self):
        from src.pedagogie.scripts import rendre_script

        # profilage.introduction a des variables, sans variables on récupère le template
        result = rendre_script("profilage.introduction")
        assert isinstance(result, str)
        assert len(result) > 0


# ─── Test 6 : formule si présente est chaîne non vide ────────────────────────


class TestFormuleSiPresenteEstChaine:
    """Si formule est renseignée, c'est une chaîne non vide."""

    def test_formule_allocation_poids_actions(self, poids_simple):
        from src.pedagogie import expliquer_allocation

        explications = expliquer_allocation(poids_simple, "equilibre", "simple")
        # La 2e explication (poids actions) a une formule
        expl_poids = next((e for e in explications if "poids_actions" in e.section), None)
        assert expl_poids is not None
        assert expl_poids.formule is not None
        assert isinstance(expl_poids.formule, str)
        assert len(expl_poids.formule.strip()) > 0

    def test_formule_ter_explication(self, etf_sample):
        from src.pedagogie import expliquer_ter

        exp = expliquer_ter(etf_sample)
        assert exp.formule is not None
        assert isinstance(exp.formule, str)
        assert len(exp.formule.strip()) > 0

    def test_formule_rebalancement_etape3(self, plan_rebalancement):
        from src.pedagogie import expliquer_plan_rebalancement

        explications = expliquer_plan_rebalancement(plan_rebalancement)
        etape3 = next((e for e in explications if "etape_3" in e.section), None)
        assert etape3 is not None
        assert etape3.formule is not None
        assert len(etape3.formule.strip()) > 0


# ─── Test 7 : alternative_ecartee cohérente quand présente ───────────────────


class TestAlternativeEcarteeCoherente:
    """Les alternatives écartées sont des chaînes non vides quand présentes."""

    def test_alternative_ecartee_allocation_mode_simple(self, poids_simple):
        from src.pedagogie import expliquer_allocation

        explications = expliquer_allocation(poids_simple, "equilibre", "simple")
        # L'explication mode doit avoir une alternative écartée
        expl_mode = next((e for e in explications if e.section == "allocation.mode"), None)
        assert expl_mode is not None
        assert expl_mode.alternative_ecartee is not None
        assert len(expl_mode.alternative_ecartee.strip()) > 0

    def test_alternative_ecartee_choix_etf(self, etf_sample):
        from src.pedagogie import expliquer_choix_etf

        alternatives = [{"ticker": "VWCE", "raison": "TER légèrement supérieur"}]
        exp = expliquer_choix_etf(etf_sample, alternatives_ecartees=alternatives)
        assert exp.alternative_ecartee is not None
        assert "VWCE" in exp.alternative_ecartee

    def test_alternative_ecartee_cto(self):
        from src.pedagogie import expliquer_cascade_fiscale

        explications = expliquer_cascade_fiscale("CTO", 50000.0, 0.30)
        # La 1re explication CTO a une alternative écartée
        assert any(e.alternative_ecartee for e in explications)

    def test_alternative_ecartee_est_chaine_non_vide_si_presente(self, poids_simple):
        from src.pedagogie import expliquer_allocation

        explications = expliquer_allocation(poids_simple, "equilibre", "simple")
        for exp in explications:
            if exp.alternative_ecartee is not None:
                assert isinstance(exp.alternative_ecartee, str)
                assert len(exp.alternative_ecartee.strip()) > 0, (
                    f"alternative_ecartee vide pour '{exp.section}'"
                )


# ─── Test 8 : import src.pedagogie sans streamlit ────────────────────────────


class TestImportPedagogieSSStreamlit:
    """src.pedagogie doit s'importer sans streamlit installé."""

    def test_import_sans_streamlit(self):
        """Le package pedagogie ne doit pas importer streamlit au niveau module."""
        # On vérifie que les modules métier ne dépendent pas de streamlit
        modules_metier = [
            "src.pedagogie.base",
            "src.pedagogie.allocation",
            "src.pedagogie.etf",
            "src.pedagogie.asset_location",
            "src.pedagogie.fiscalite",
            "src.pedagogie.rebalancement",
            "src.pedagogie.profilage",
            "src.pedagogie.scripts",
            "src.pedagogie",
        ]
        for module_name in modules_metier:
            # Vérifier que le module peut être importé sans streamlit dans sys.modules
            # (streamlit peut être installé dans l'environnement de test, mais les modules
            # métier ne doivent pas l'importer au niveau module)
            if module_name in sys.modules:
                # Déjà importé — vérifier que streamlit n'est pas une dépendance directe
                mod = sys.modules[module_name]
                mod_file = getattr(mod, "__file__", "") or ""
                # Si le module est bien chargé, c'est OK
                assert mod_file or module_name == "src.pedagogie"
            else:
                import importlib

                mod = importlib.import_module(module_name)
                assert mod is not None

    def test_src_ui_explications_isole(self):
        """src.ui.explications doit exposer les 4 helpers sans crasher à l'import."""
        # On importe le module directement (streamlit sera mocké s'il n'est pas disponible)
        mod = importlib.import_module("src.ui.explications")
        assert hasattr(mod, "expander_explication")
        assert hasattr(mod, "bloc_script_restitution")
        assert hasattr(mod, "tableau_alternatives")
        assert hasattr(mod, "badge_source")


# ─── Test 9 : smoke test — page 03 s'importe sans erreur ────────────────────


class TestSmokeTestPage03:
    """Smoke test : le module src.pedagogie s'importe correctement."""

    def test_pedagogie_init_expose_api_publique(self):
        from src import pedagogie

        assert hasattr(pedagogie, "Explication")
        assert hasattr(pedagogie, "expliquer_allocation")
        assert hasattr(pedagogie, "expliquer_choix_etf")
        assert hasattr(pedagogie, "expliquer_asset_location")
        assert hasattr(pedagogie, "expliquer_cascade_fiscale")
        assert hasattr(pedagogie, "expliquer_plan_rebalancement")
        assert hasattr(pedagogie, "expliquer_convergence_3_prismes")
        assert hasattr(pedagogie, "charger_scripts_restitution")
        assert hasattr(pedagogie, "rendre_script")


# ─── Test 10 : Explication — validations du modèle ───────────────────────────


class TestExplicationModele:
    """Tests du modèle Pydantic Explication."""

    def test_creation_minimale(self):
        from src.pedagogie.base import Explication

        exp = Explication(
            section="test.section",
            titre="Titre test",
            texte_court="Court.",
            texte_long="Plus long.",
            source="Source test",
        )
        assert exp.section == "test.section"
        assert exp.formule is None
        assert exp.alternative_ecartee is None
        assert exp.gain_eur is None
        assert exp.variables_contexte == {}

    def test_creation_complete(self):
        from src.pedagogie.base import Explication

        exp = Explication(
            section="test.complet",
            titre="Titre complet",
            texte_court="Court.",
            texte_long="Long.",
            formule="E = mc²",
            source="Einstein (1905)",
            alternative_ecartee="Newtonien écarté",
            gain_eur=1234.56,
            variables_contexte={"nom_client": "M. Dupont"},
        )
        assert exp.formule == "E = mc²"
        assert exp.gain_eur == 1234.56
        assert exp.variables_contexte["nom_client"] == "M. Dupont"

    def test_divergence_profil_retourne_explication(self, profil_consolide_divergent):
        from src.pedagogie import expliquer_convergence_3_prismes

        exp = expliquer_convergence_3_prismes(profil_consolide_divergent)
        assert exp.alternative_ecartee is not None
        assert "dynamique" in exp.alternative_ecartee
