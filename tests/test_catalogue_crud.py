"""Tests S13 Lot B — CRUD YAML atomique avec backup."""

from __future__ import annotations

import pytest
import yaml

# ─── Tests lire_yaml ──────────────────────────────────────────────────────────


class TestLireYaml:
    def test_lire_yaml_brokers(self):
        from src.catalogue.crud import lire_yaml

        data = lire_yaml("brokers.yaml")
        assert isinstance(data, dict)
        assert "brokers" in data
        assert len(data["brokers"]) > 0

    def test_lire_yaml_teneurs_per(self):
        from src.catalogue.crud import lire_yaml

        data = lire_yaml("teneurs_per.yaml")
        assert isinstance(data, dict)
        assert "teneurs_per" in data
        assert len(data["teneurs_per"]) >= 5

    def test_lire_yaml_contrats_av(self):
        from src.catalogue.crud import lire_yaml

        data = lire_yaml("contrats_av.yaml")
        assert isinstance(data, dict)
        assert "contrats_av" in data

    def test_lire_yaml_fichier_inexistant(self, tmp_path):
        from src.catalogue.crud import lire_yaml

        with pytest.raises(FileNotFoundError):
            lire_yaml("fichier_qui_nexiste_pas_s13.yaml")


# ─── Tests sauvegarder_yaml ───────────────────────────────────────────────────


class TestSauvegarderYaml:
    def test_sauvegarder_cree_fichier(self, tmp_path, monkeypatch):
        import src.catalogue.crud as crud_mod

        monkeypatch.setattr(crud_mod, "CONFIG_DIR", tmp_path)
        data = {"test": [{"id": "a", "valeur": 1}]}
        path = crud_mod.sauvegarder_yaml("test_s13.yaml", data)
        assert path.exists()
        contenu = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert contenu == data

    def test_sauvegarder_cree_backup(self, tmp_path, monkeypatch):
        import src.catalogue.crud as crud_mod

        monkeypatch.setattr(crud_mod, "CONFIG_DIR", tmp_path)
        data1 = {"items": [{"id": "v1"}]}
        data2 = {"items": [{"id": "v2"}]}
        # Première sauvegarde
        crud_mod.sauvegarder_yaml("test_bak.yaml", data1)
        # Deuxième sauvegarde → doit créer un backup
        crud_mod.sauvegarder_yaml("test_bak.yaml", data2)
        baks = list(tmp_path.glob("test_bak.*.bak"))
        assert len(baks) >= 1

    def test_sauvegarder_ecriture_atomique(self, tmp_path, monkeypatch):
        """Le fichier .tmp est nettoyé même si erreur."""
        import src.catalogue.crud as crud_mod

        monkeypatch.setattr(crud_mod, "CONFIG_DIR", tmp_path)
        data = {"key": "value"}
        crud_mod.sauvegarder_yaml("atomic_test.yaml", data)
        # Aucun fichier .tmp ne doit subsister
        tmps = list(tmp_path.glob("*.tmp"))
        assert len(tmps) == 0

    def test_sauvegarder_unicode(self, tmp_path, monkeypatch):
        import src.catalogue.crud as crud_mod

        monkeypatch.setattr(crud_mod, "CONFIG_DIR", tmp_path)
        data = {"nom": "Crédit Agricole — Épargne Retraite"}
        path = crud_mod.sauvegarder_yaml("unicode_test.yaml", data)
        contenu = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert contenu["nom"] == data["nom"]


# ─── Tests diff_yaml ──────────────────────────────────────────────────────────


class TestDiffYaml:
    def test_diff_vide_si_identiques(self):
        from src.catalogue.crud import diff_yaml

        data = {"key": "value", "num": 42}
        assert diff_yaml(data, data) == ""

    def test_diff_detecte_changement(self):
        from src.catalogue.crud import diff_yaml

        ancien = {"items": [{"id": "a", "val": 1}]}
        nouveau = {"items": [{"id": "a", "val": 2}]}
        diff = diff_yaml(ancien, nouveau)
        assert "-" in diff
        assert "+" in diff

    def test_diff_detecte_ajout(self):
        from src.catalogue.crud import diff_yaml

        ancien = {"items": []}
        nouveau = {"items": [{"id": "nouveau"}]}
        diff = diff_yaml(ancien, nouveau)
        assert "nouveau" in diff


# ─── Tests importer_csv ───────────────────────────────────────────────────────


class TestImporterCsv:
    def test_import_basique(self):
        from src.catalogue.crud import importer_csv

        content = "isin;ticker;nom;ter\nIE00B4L5Y983;IWDA;iShares Core MSCI World;0.0020\n"
        rows = importer_csv(content)
        assert len(rows) == 1
        assert rows[0]["isin"] == "IE00B4L5Y983"

    def test_import_bytes_utf8_sig(self):
        from src.catalogue.crud import importer_csv

        content = "isin;ticker;nom;ter\nFR0010315770;CW8;Amundi MSCI World;0.0038\n"
        rows = importer_csv(content.encode("utf-8-sig"))
        assert len(rows) == 1
        assert rows[0]["ticker"] == "CW8"

    def test_import_colonne_manquante(self):
        from src.catalogue.crud import importer_csv

        content = "isin;ticker\nIE00B4L5Y983;IWDA\n"
        with pytest.raises(ValueError, match="Colonne manquante"):
            importer_csv(content, colonnes_attendues=["isin", "ticker", "nom", "ter"])

    def test_import_lignes_multiples(self):
        from src.catalogue.crud import importer_csv

        lines = ["isin;ticker;nom;ter"]
        for i in range(5):
            lines.append(f"IE000000000{i};ETF{i};ETF Nom {i};0.002{i}")
        rows = importer_csv("\n".join(lines))
        assert len(rows) == 5
