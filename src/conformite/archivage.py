"""Archivage horodaté des documents conformité CIF."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from src.schemas import DocumentConformite, PreuveSignature

_TYPE_TO_DIR = {
    "DER": "der",
    "LETTRE_MISSION": "lettre_mission",
    "RAPPORT_ADEQUATION": "rapport_adequation",
}


def archiver_document(
    document: DocumentConformite,
    preuve: PreuveSignature | None = None,
    racine_archive: Path = Path("output/clients"),
) -> Path:
    """Copie le PDF + preuve dans l'archive horodatée.

    Met à jour client_manifest.json (append-only).
    """
    racine_archive = Path(racine_archive)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    sous_dir = _TYPE_TO_DIR.get(document.type_doc, document.type_doc.lower())

    dest_dir = racine_archive / str(document.profil_id) / sous_dir
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Copy PDF
    src_pdf = Path(document.chemin_pdf)
    version = document.version_template.replace(" ", "_")
    dest_pdf = dest_dir / f"{ts}_{version}.pdf"
    shutil.copy2(src_pdf, dest_pdf)

    # Copy signature if present
    sig_src = src_pdf.with_suffix(".signature.json")
    if preuve is not None and sig_src.exists():
        dest_sig = dest_dir / f"{ts}_{version}.signature.json"
        shutil.copy2(sig_src, dest_sig)

    # Update type-specific manifest
    manifest_path = dest_dir / "manifest.json"
    _update_manifest(manifest_path, document, str(dest_pdf), preuve)

    # Update global client manifest
    client_manifest_path = racine_archive / str(document.profil_id) / "client_manifest.json"
    _update_manifest(client_manifest_path, document, str(dest_pdf), preuve)

    return dest_pdf


def _update_manifest(
    manifest_path: Path,
    document: DocumentConformite,
    dest_pdf: str,
    preuve: PreuveSignature | None,
) -> None:
    entries: list[dict] = []
    if manifest_path.exists():
        try:
            entries = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            entries = []

    entry = {
        "type_doc": document.type_doc,
        "profil_id": document.profil_id,
        "client_nom": document.client_nom,
        "date_generation": document.date_generation,
        "chemin_pdf": dest_pdf,
        "sha256": document.sha256,
        "version_template": document.version_template,
        "signe": preuve is not None,
        "date_signature": preuve.date_signature if preuve else None,
        "hash_signature": preuve.hash_signature if preuve else None,
    }
    entries.append(entry)
    manifest_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def lister_documents_client(
    profil_id: int,
    racine_archive: Path,
) -> list[DocumentConformite]:
    """Retourne tous les documents archivés du client (lecture du manifest)."""
    racine_archive = Path(racine_archive)
    manifest_path = racine_archive / str(profil_id) / "client_manifest.json"
    if not manifest_path.exists():
        return []

    try:
        entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return []

    docs = []
    for entry in sorted(entries, key=lambda x: x.get("date_generation", ""), reverse=True):
        try:
            docs.append(DocumentConformite.model_validate(entry))
        except Exception:
            continue
    return docs


def verifier_integrite_dossier(
    profil_id: int,
    racine_archive: Path,
) -> dict[str, bool]:
    """Vérifie que tous les hashes du manifest correspondent aux PDFs.

    Retourne {chemin: bool} pour audit.
    """
    racine_archive = Path(racine_archive)
    manifest_path = racine_archive / str(profil_id) / "client_manifest.json"
    if not manifest_path.exists():
        return {}

    try:
        entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return {}

    result: dict[str, bool] = {}
    for entry in entries:
        chemin = entry.get("chemin_pdf", "")
        expected_hash = entry.get("sha256", "")
        pdf_path = Path(chemin)
        if not pdf_path.exists():
            result[chemin] = False
            continue
        h = hashlib.sha256()
        with pdf_path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        result[chemin] = h.hexdigest() == expected_hash

    return result
