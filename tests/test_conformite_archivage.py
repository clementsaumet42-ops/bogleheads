"""Tests — Archivage (src/conformite/archivage.py)."""

from __future__ import annotations

import time
from pathlib import Path

from src.conformite.archivage import (
    archiver_document,
    lister_documents_client,
    verifier_integrite_dossier,
)
from src.conformite.der import generer_der
from src.conformite.lettre_mission import generer_lettre_mission
from src.conformite.rapport_adequation import generer_rapport_adequation
from src.schemas import DocumentConformite

_PROFIL = {"id": 55, "nom": "Archivage", "email": "arch@test.com"}
_CABINET = {
    "cabinet": {
        "nom": "Cabinet Archivage",
        "numero_orias": "55555555",
        "adresse": "",
        "telephone": "",
        "email": "",
        "rc_pro_assureur": "",
        "rc_pro_numero": "",
        "mediateur_nom": "AMF",
        "mediateur_url": "https://amf-france.org",
    },
    "remuneration": {"mode": "honoraires"},
}
_PARAMS = {
    "objet": "Test",
    "perimetre": ["audit"],
    "honoraires_eur": 1000.0,
    "honoraires_modalite": "forfait",
    "duree_mois": 6,
    "date_debut": "2025-01-01",
}


def _gen_der(tmp_path: Path) -> DocumentConformite:
    out = tmp_path / "der.pdf"
    return generer_der(_PROFIL, _CABINET, None, out)


def test_archiver_cree_structure_dossiers(tmp_path: Path) -> None:
    doc = _gen_der(tmp_path)
    archive = tmp_path / "clients"
    dest = archiver_document(doc, racine_archive=archive)
    assert dest.exists()
    assert (archive / "55" / "der").is_dir()
    assert (archive / "55" / "client_manifest.json").exists()
    assert (archive / "55" / "der" / "manifest.json").exists()


def test_manifest_append_only(tmp_path: Path) -> None:
    doc1 = _gen_der(tmp_path)
    archive = tmp_path / "clients"
    archiver_document(doc1, racine_archive=archive)
    # Generate a second doc
    out2 = tmp_path / "der2.pdf"
    doc2 = generer_der(_PROFIL, _CABINET, None, out2)
    time.sleep(0.01)  # ensure different timestamp
    archiver_document(doc2, racine_archive=archive)
    docs = lister_documents_client(55, archive)
    assert len(docs) >= 2


def test_lister_documents_ordonne_par_date(tmp_path: Path) -> None:
    archive = tmp_path / "clients"
    for _ in range(3):
        doc = _gen_der(tmp_path)
        archiver_document(doc, racine_archive=archive)
        time.sleep(0.01)
    docs = lister_documents_client(55, archive)
    assert len(docs) >= 3
    dates = [d.date_generation for d in docs]
    assert dates == sorted(dates, reverse=True)


def test_verifier_integrite_detecte_alteration(tmp_path: Path) -> None:
    doc = _gen_der(tmp_path)
    archive = tmp_path / "clients"
    dest = archiver_document(doc, racine_archive=archive)
    # Alterate archived PDF
    with dest.open("ab") as f:
        f.write(b"\x00ALTERATION")
    resultats = verifier_integrite_dossier(55, archive)
    assert str(dest) in resultats
    assert resultats[str(dest)] is False


def test_archiver_idempotent_pas_doublon_timestamps_differents(tmp_path: Path) -> None:
    """Archiver 2 fois génère 2 entrées (timestamps différents = fichiers différents)."""
    doc = _gen_der(tmp_path)
    archive = tmp_path / "clients"
    archiver_document(doc, racine_archive=archive)
    time.sleep(0.05)
    archiver_document(doc, racine_archive=archive)
    docs = lister_documents_client(55, archive)
    assert len(docs) >= 2


def test_client_manifest_contient_tous_types(tmp_path: Path) -> None:
    archive = tmp_path / "clients"

    # DER
    der_doc = _gen_der(tmp_path)
    archiver_document(der_doc, racine_archive=archive)

    # LM
    lm_out = tmp_path / "lm.pdf"
    lm_doc = generer_lettre_mission(_PROFIL, _CABINET, None, _PARAMS, lm_out)
    archiver_document(lm_doc, racine_archive=archive)

    # RA
    ra_out = tmp_path / "ra.pdf"
    ra_doc = generer_rapport_adequation(_PROFIL, _CABINET, None, {}, [], ra_out)
    archiver_document(ra_doc, racine_archive=archive)

    docs = lister_documents_client(55, archive)
    types = {d.type_doc for d in docs}
    assert "DER" in types
    assert "LETTRE_MISSION" in types
    assert "RAPPORT_ADEQUATION" in types
