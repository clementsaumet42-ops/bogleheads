"""Tests Sprint S17 — Module hypothèses traçables.

Couvre :
- Chargement YAML
- get_hypothese : clé inconnue, filtrage par date
- Round-trip snapshot (créer → sauver → charger → comparer hash)
- Comparaison de snapshots (ajout / retrait / modification)
- Test de non-régression valeur-par-valeur
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


# ─── Chargement YAML ──────────────────────────────────────────────────────────


class TestChargementYAML:
    def test_charger_catalogue_renvoie_dict(self):
        """charger_catalogue() retourne un dict non vide."""
        from src.hypotheses.catalogue import charger_catalogue

        cat = charger_catalogue()
        assert isinstance(cat, dict)
        assert len(cat) > 0

    def test_toutes_les_hypotheses_parsent(self):
        """100 % des hypothèses du YAML parsent sans erreur."""
        from src.hypotheses.catalogue import charger_catalogue
        from src.hypotheses.source import Hypothese

        cat = charger_catalogue()
        for cle, hyp in cat.items():
            assert isinstance(hyp, Hypothese), f"Hypothèse '{cle}' invalide"
            assert hyp.cle == cle
            assert hyp.valeur is not None
            assert isinstance(hyp.date_validite_debut, date)

    def test_hypotheses_ont_des_sources(self):
        """Toutes les hypothèses Priority-1 ont au moins une source."""
        from src.hypotheses.catalogue import charger_catalogue

        priorite_1 = [
            "rendement_actions_monde",
            "rendement_obligations",
            "rendement_or",
            "rendement_immobilier_cote",
            "rendement_liquidites",
            "inflation_long_terme",
        ]
        cat = charger_catalogue()
        for cle in priorite_1:
            assert cle in cat, f"Hypothèse prioritaire absente : {cle}"
            assert len(cat[cle].sources) > 0, f"Pas de source pour : {cle}"

    def test_hypotheses_par_categorie(self):
        """lister_hypotheses_par_categorie() groupe correctement."""
        from src.hypotheses.catalogue import lister_hypotheses_par_categorie

        par_cat = lister_hypotheses_par_categorie()
        assert isinstance(par_cat, dict)
        assert "rendements" in par_cat
        assert len(par_cat["rendements"]) >= 5

    def test_categories_connues(self):
        """Les catégories utilisées sont parmi les catégories attendues."""
        from src.hypotheses.catalogue import lister_hypotheses_par_categorie

        categories_attendues = {
            "rendements",
            "inflation",
            "demographie",
            "fiscalite",
            "frais",
            "autres",
        }
        par_cat = lister_hypotheses_par_categorie()
        for cat in par_cat:
            assert cat in categories_attendues, f"Catégorie inconnue : {cat}"

    def test_au_moins_cinq_hypotheses(self):
        """Le catalogue contient au moins 5 hypothèses (sanity check)."""
        from src.hypotheses.catalogue import charger_catalogue

        cat = charger_catalogue()
        assert len(cat) >= 5


# ─── get_hypothese ────────────────────────────────────────────────────────────


class TestGetHypothese:
    def test_get_hypothese_renvoie_objet(self):
        """get_hypothese() retourne un objet Hypothese."""
        from src.hypotheses.catalogue import get_hypothese
        from src.hypotheses.source import Hypothese

        h = get_hypothese("rendement_actions_monde")
        assert isinstance(h, Hypothese)
        assert h.cle == "rendement_actions_monde"

    def test_cle_inexistante_leve_keyerror(self):
        """get_hypothese() lève KeyError pour une clé inconnue."""
        from src.hypotheses.catalogue import get_hypothese

        with pytest.raises(KeyError, match="inexistante"):
            get_hypothese("hypothese_inexistante_xyz")

    def test_filtrage_date_validite_debut(self):
        """get_hypothese() lève ValueError si date avant date_validite_debut."""
        from src.hypotheses.catalogue import get_hypothese

        # Une hypothèse valide à partir de 2026-01-01
        with pytest.raises(ValueError, match="pas encore valide"):
            get_hypothese("rendement_actions_monde", reference_date=date(2025, 1, 1))

    def test_filtrage_date_validite_fin(self, tmp_path, monkeypatch):
        """get_hypothese() lève ValueError si date après date_validite_fin."""
        import src.hypotheses.catalogue as cat_mod
        from src.hypotheses.catalogue import charger_catalogue, get_hypothese

        # Créer un YAML avec une hypothèse expirée
        yaml_content = """
hypotheses:
  hyp_expiree:
    valeur: 0.05
    unite: "%/an"
    description: "Test hypothèse expirée"
    version: "2026.1"
    categorie: "rendements"
    date_validite_debut: 2020-01-01
    date_validite_fin: 2023-12-31
    confiance: "haute"
    sources: []
"""
        yaml_path = tmp_path / "test_hyp.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")
        # Isoler via monkeypatch pour ne pas polluer le cache global
        monkeypatch.setattr(cat_mod, "_DEFAULT_PATH", yaml_path)
        monkeypatch.setattr(cat_mod, "_CATALOGUE_CACHE", None)
        charger_catalogue()  # charge avec le path par défaut patché

        with pytest.raises(ValueError, match="expirée"):
            get_hypothese("hyp_expiree", reference_date=date(2026, 1, 1))

    def test_valeur_rendement_actions(self):
        """La valeur du rendement actions monde est 0.065 (non-régression)."""
        from src.hypotheses.catalogue import get_hypothese

        h = get_hypothese("rendement_actions_monde")
        assert h.valeur == 0.065

    def test_valeur_inflation(self):
        """La valeur de l'inflation long terme est 0.02 (non-régression)."""
        from src.hypotheses.catalogue import get_hypothese

        h = get_hypothese("inflation_long_terme")
        assert h.valeur == 0.02


# ─── Snapshot ─────────────────────────────────────────────────────────────────


class TestSnapshot:
    def test_creer_snapshot(self):
        """creer_snapshot() retourne un SnapshotHypotheses valide."""
        from src.hypotheses.snapshot import SnapshotHypotheses, creer_snapshot

        snap = creer_snapshot("test_mission_001")
        assert isinstance(snap, SnapshotHypotheses)
        assert snap.mission_id == "test_mission_001"
        assert len(snap.hypotheses) > 0
        assert len(snap.hash_integrite) == 64  # SHA256 hex

    def test_hash_deterministe(self):
        """Deux snapshots du même catalogue ont le même hash."""
        from src.hypotheses.snapshot import creer_snapshot

        snap1 = creer_snapshot("mission_a")
        snap2 = creer_snapshot("mission_a")
        assert snap1.hash_integrite == snap2.hash_integrite

    def test_round_trip_json(self, tmp_path):
        """Round-trip JSON : to_dict → from_dict → mêmes valeurs."""
        from src.hypotheses.snapshot import SnapshotHypotheses, creer_snapshot

        snap = creer_snapshot("test_rt")
        data = snap.to_dict()
        snap2 = SnapshotHypotheses.from_dict(data)

        assert snap2.mission_id == snap.mission_id
        assert snap2.hash_integrite == snap.hash_integrite
        assert set(snap2.hypotheses.keys()) == set(snap.hypotheses.keys())
        for cle in snap.hypotheses:
            assert snap.hypotheses[cle].valeur == snap2.hypotheses[cle].valeur

    def test_sauvegarder_et_charger(self, tmp_path, monkeypatch):
        """Round-trip disque : sauvegarder_snapshot → charger_snapshot."""
        import src.hypotheses.snapshot as snap_mod
        from src.hypotheses.snapshot import (
            charger_snapshot,
            creer_snapshot,
            sauvegarder_snapshot,
        )

        monkeypatch.setattr(snap_mod, "_DEFAULT_DATA_DIR", tmp_path)
        snap = creer_snapshot("mission_test_io")
        chemin = sauvegarder_snapshot(snap)
        assert chemin.exists()

        snap2 = charger_snapshot("mission_test_io")
        assert snap2.hash_integrite == snap.hash_integrite
        assert snap2.mission_id == snap.mission_id

    def test_charger_snapshot_inexistant_leve_error(self, tmp_path, monkeypatch):
        """charger_snapshot() lève FileNotFoundError pour mission inexistante."""
        import src.hypotheses.snapshot as snap_mod
        from src.hypotheses.snapshot import charger_snapshot

        monkeypatch.setattr(snap_mod, "_DEFAULT_DATA_DIR", tmp_path)
        with pytest.raises(FileNotFoundError):
            charger_snapshot("mission_inexistante_xyz")

    def test_hash_integrite_sha256(self):
        """Le hash d'intégrité est un SHA256 valide (64 hex chars)."""
        from src.hypotheses.snapshot import creer_snapshot

        snap = creer_snapshot("hash_test")
        assert len(snap.hash_integrite) == 64
        int(snap.hash_integrite, 16)  # doit être hexadécimal valide


# ─── Comparaison de snapshots ─────────────────────────────────────────────────


class TestComparaisonSnapshots:
    def _snap_avec_hypotheses(self, hyps_dict: dict, mission_id: str = "test"):
        """Crée un SnapshotHypotheses factice à partir d'un dict {cle: valeur}."""
        from src.hypotheses.snapshot import SnapshotHypotheses, _calculer_hash
        from src.hypotheses.source import Hypothese

        hypotheses = {}
        for cle, valeur in hyps_dict.items():
            hypotheses[cle] = Hypothese(
                cle=cle,
                valeur=valeur,
                unite="%/an",
                description=f"Test {cle}",
                sources=(),
                date_validite_debut=date(2026, 1, 1),
                date_validite_fin=None,
                version="2026.1",
                confiance="consensus",
                categorie="rendements",
            )
        return SnapshotHypotheses(
            mission_id=mission_id,
            date_snapshot=datetime(2026, 1, 1),
            hypotheses=hypotheses,
            hash_integrite=_calculer_hash(hypotheses),
        )

    def test_snapshots_identiques(self):
        """Deux snapshots identiques → aucune différence."""
        from src.hypotheses.versionnage import comparer_snapshots

        snap = self._snap_avec_hypotheses({"a": 0.07, "b": 0.02})
        diff = comparer_snapshots(snap, snap)
        assert diff["ajoutees"] == []
        assert diff["retirees"] == []
        assert diff["modifiees"] == []
        assert "a" in diff["inchangees"]

    def test_hypothese_ajoutee(self):
        """Une hypothèse présente dans B mais pas A → dans 'ajoutees'."""
        from src.hypotheses.versionnage import comparer_snapshots

        snap_a = self._snap_avec_hypotheses({"a": 0.07})
        snap_b = self._snap_avec_hypotheses({"a": 0.07, "b": 0.02})
        diff = comparer_snapshots(snap_a, snap_b)
        assert len(diff["ajoutees"]) == 1
        assert diff["ajoutees"][0].cle == "b"

    def test_hypothese_retiree(self):
        """Une hypothèse présente dans A mais pas B → dans 'retirees'."""
        from src.hypotheses.versionnage import comparer_snapshots

        snap_a = self._snap_avec_hypotheses({"a": 0.07, "b": 0.02})
        snap_b = self._snap_avec_hypotheses({"a": 0.07})
        diff = comparer_snapshots(snap_a, snap_b)
        assert len(diff["retirees"]) == 1
        assert diff["retirees"][0].cle == "b"

    def test_hypothese_modifiee(self):
        """Une hypothèse avec valeur différente → dans 'modifiees'."""
        from src.hypotheses.versionnage import comparer_snapshots

        snap_a = self._snap_avec_hypotheses({"a": 0.07})
        snap_b = self._snap_avec_hypotheses({"a": 0.065})
        diff = comparer_snapshots(snap_a, snap_b)
        assert len(diff["modifiees"]) == 1
        assert diff["modifiees"][0]["cle"] == "a"
        assert "0.07" in diff["modifiees"][0]["delta_valeur"]
        assert "0.065" in diff["modifiees"][0]["delta_valeur"]

    def test_comparaison_mixte(self):
        """Scénario mixte : ajout + retrait + modification."""
        from src.hypotheses.versionnage import comparer_snapshots

        snap_a = self._snap_avec_hypotheses({"a": 0.07, "b": 0.02, "c": 0.03})
        snap_b = self._snap_avec_hypotheses({"a": 0.065, "c": 0.03, "d": 0.01})
        diff = comparer_snapshots(snap_a, snap_b)
        assert len(diff["ajoutees"]) == 1  # d
        assert len(diff["retirees"]) == 1  # b
        assert len(diff["modifiees"]) == 1  # a
        assert len(diff["inchangees"]) == 1  # c


# ─── Tests de non-régression valeur-par-valeur ────────────────────────────────


class TestNonRegression:
    """Vérifie que les valeurs du YAML sont identiques aux constantes en dur dans le code."""

    def test_rendement_actions_monde_egal_pdf_builder(self):
        """YAML rendement_actions_monde == constante _chart_projection_mc."""
        from src.hypotheses.catalogue import get_hypothese

        h = get_hypothese("rendement_actions_monde")
        # Valeur en dur dans src/pdf_builder.py ligne ~284
        assert h.valeur == pytest.approx(0.065)

    def test_rendement_obligations_egal_pdf_builder(self):
        """YAML rendement_obligations == constante _chart_projection_mc."""
        from src.hypotheses.catalogue import get_hypothese

        h = get_hypothese("rendement_obligations")
        # Valeur en dur dans src/pdf_builder.py ligne ~285
        assert h.valeur == pytest.approx(0.025)

    def test_rendement_or_egal_pdf_builder(self):
        """YAML rendement_or == constante _chart_projection_mc."""
        from src.hypotheses.catalogue import get_hypothese

        h = get_hypothese("rendement_or")
        # Valeur en dur dans src/pdf_builder.py ligne ~286
        assert h.valeur == pytest.approx(0.03)

    def test_rendement_immobilier_egal_pdf_builder(self):
        """YAML rendement_immobilier_cote == constante _chart_projection_mc."""
        from src.hypotheses.catalogue import get_hypothese

        h = get_hypothese("rendement_immobilier_cote")
        # Valeur en dur dans src/pdf_builder.py ligne ~287
        assert h.valeur == pytest.approx(0.04)

    def test_rendement_liquidites_egal_pdf_builder(self):
        """YAML rendement_liquidites == constante _chart_projection_mc."""
        from src.hypotheses.catalogue import get_hypothese

        h = get_hypothese("rendement_liquidites")
        # Valeur en dur dans src/pdf_builder.py ligne ~288
        assert h.valeur == pytest.approx(0.015)

    def test_inflation_egal_projection_params(self):
        """YAML inflation_long_terme == inflation_annuelle dans projection_params.yaml."""
        import yaml

        from src.hypotheses.catalogue import get_hypothese

        h = get_hypothese("inflation_long_terme")
        params_path = ROOT / "config" / "projection_params.yaml"
        with open(params_path, encoding="utf-8") as f:
            params = yaml.safe_load(f)
        assert h.valeur == pytest.approx(params["inflation_annuelle"])

    def test_taux_sans_risque_egal_optimiseur(self):
        """YAML taux_sans_risque == TAUX_SANS_RISQUE_DEFAUT dans optimiseur_allocation."""
        from src.hypotheses.catalogue import get_hypothese
        from src.optimiseur_allocation import TAUX_SANS_RISQUE_DEFAUT

        h = get_hypothese("taux_sans_risque")
        assert h.valeur == pytest.approx(TAUX_SANS_RISQUE_DEFAUT)

    def test_taux_pfu_correct(self):
        """YAML taux_pfu == 0.30 (PFU 30%)."""
        from src.hypotheses.catalogue import get_hypothese

        h = get_hypothese("taux_pfu")
        assert h.valeur == pytest.approx(0.30)

    def test_plafond_pea_correct(self):
        """YAML plafond_pea == constante PEA_PLAFOND_VERSEMENTS dans fiscalite."""
        from src.fiscalite.constantes import PEA_PLAFOND_VERSEMENTS
        from src.hypotheses.catalogue import get_hypothese

        h = get_hypothese("plafond_pea")
        assert int(h.valeur) == PEA_PLAFOND_VERSEMENTS
