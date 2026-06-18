"""Tests d'intégration import PDF + mission — Sprint S20."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.import_patrimoine.audit import enregistrer_import, lire_audit
from src.import_patrimoine.modele import ImportPDF, LignePatrimoine
from src.mission.etat import EtatMission

# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def import_pdf_exemple() -> ImportPDF:
    ligne = LignePatrimoine(
        isin="FR0010315770",
        nom_actif="Lyxor CAC 40 ETF",
        quantite=10.0,
        valorisation_eur=1234.56,
        enveloppe="CTO",
        broker_emetteur="Bourse Direct",
        type_actif="ETF",
        source_pdf="releve_bourse_direct.pdf",
        source_page=1,
        methode_extraction="template:bourse_direct",
        confiance=90,
    )
    return ImportPDF(
        pdf_nom="releve_bourse_direct.pdf",
        pdf_hash="abc" * 21 + "d",
        timestamp_import="2024-01-15T10:30:00",
        emetteur_detecte="Bourse Direct",
        template_utilise="bourse_direct",
        lignes_validees=[ligne],
        lignes_rejetees=[],
    )


# ─── Tests EtatMission ───────────────────────────────────────────────────────


def test_ajouter_import_mission(import_pdf_exemple: ImportPDF) -> None:
    """Vérifie qu'un import s'ajoute bien à imports_patrimoine."""
    chemin = Path("data/missions/test_s20_temp.json")
    from datetime import date

    from src.mission.etat import _etapes_initiales

    mission = EtatMission(
        mission_id="test_s20_temp",
        nom_client="Test Client",
        conseiller="EC Test",
        date_creation=date.today(),
        date_derniere_maj=date.today(),
        etapes=_etapes_initiales(),
        chemin_persistance=chemin,
    )
    mission.ajouter_import(import_pdf_exemple)
    assert len(mission.imports_patrimoine) == 1
    assert mission.imports_patrimoine[0]["pdf_nom"] == "releve_bourse_direct.pdf"
    assert mission.imports_patrimoine[0]["emetteur_detecte"] == "Bourse Direct"


def test_serialisation_imports_patrimoine(import_pdf_exemple: ImportPDF) -> None:
    """Vérifie que imports_patrimoine est sérialisé dans to_dict()."""
    from datetime import date

    from src.mission.etat import _etapes_initiales

    chemin = Path("data/missions/test_s20_serial.json")
    mission = EtatMission(
        mission_id="test_s20_serial",
        nom_client="Test Client",
        conseiller="EC Test",
        date_creation=date.today(),
        date_derniere_maj=date.today(),
        etapes=_etapes_initiales(),
        chemin_persistance=chemin,
    )
    mission.ajouter_import(import_pdf_exemple)
    d = mission.to_dict()
    assert "imports_patrimoine" in d
    assert len(d["imports_patrimoine"]) == 1


def test_deserialisation_mission_sans_imports_patrimoine() -> None:
    """Rétro-compatibilité : une mission sans imports_patrimoine charge sans erreur."""
    from datetime import date

    from src.mission.etat import EtatMission

    chemin = Path("data/missions/test_s20_retro.json")
    data = {
        "mission_id": "test_s20_retro",
        "nom_client": "Client Retro",
        "conseiller": "EC",
        "date_creation": date.today().isoformat(),
        "date_derniere_maj": date.today().isoformat(),
        "etapes": {},
        "notes": {},
    }
    mission = EtatMission.from_dict(data, chemin)
    assert mission.imports_patrimoine == []


def test_mission_multiple_imports(import_pdf_exemple: ImportPDF) -> None:
    """Vérifie qu'on peut ajouter plusieurs imports successifs."""
    from datetime import date

    from src.mission.etat import _etapes_initiales

    chemin = Path("data/missions/test_s20_multi.json")
    mission = EtatMission(
        mission_id="test_s20_multi",
        nom_client="Client Multi",
        conseiller="EC",
        date_creation=date.today(),
        date_derniere_maj=date.today(),
        etapes=_etapes_initiales(),
        chemin_persistance=chemin,
    )
    mission.ajouter_import(import_pdf_exemple)
    mission.ajouter_import(import_pdf_exemple)
    assert len(mission.imports_patrimoine) == 2


# ─── Tests Audit ─────────────────────────────────────────────────────────────


def test_audit_append_only(tmp_path: Path, import_pdf_exemple: ImportPDF, monkeypatch) -> None:
    """Vérifie que l'audit est append-only (chaque appel ajoute une entrée)."""
    import src.import_patrimoine.audit as audit_module

    monkeypatch.setattr(audit_module, "_DEFAULT_DATA_DIR", tmp_path)

    enregistrer_import("mission_test", import_pdf_exemple)
    enregistrer_import("mission_test", import_pdf_exemple)

    audit = lire_audit("mission_test")
    assert len(audit) == 2
    assert audit[0]["import"]["pdf_nom"] == "releve_bourse_direct.pdf"
    assert audit[1]["import"]["pdf_nom"] == "releve_bourse_direct.pdf"


def test_audit_vide_si_absent(tmp_path: Path, monkeypatch) -> None:
    """lire_audit retourne [] si le fichier n'existe pas."""
    import src.import_patrimoine.audit as audit_module

    monkeypatch.setattr(audit_module, "_DEFAULT_DATA_DIR", tmp_path)

    audit = lire_audit("mission_inexistante")
    assert audit == []


def test_audit_contient_timestamp(
    tmp_path: Path, import_pdf_exemple: ImportPDF, monkeypatch
) -> None:
    """Chaque entrée d'audit contient un timestamp."""
    import src.import_patrimoine.audit as audit_module

    monkeypatch.setattr(audit_module, "_DEFAULT_DATA_DIR", tmp_path)
    enregistrer_import("mission_ts", import_pdf_exemple)

    audit = lire_audit("mission_ts")
    assert len(audit) == 1
    assert "timestamp" in audit[0]
    assert len(audit[0]["timestamp"]) > 0
