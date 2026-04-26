"""Signature simple eIDAS pour documents conformité CIF."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from src.schemas import DocumentConformite, PreuveSignature


def calculer_hash_document(pdf_path: Path) -> str:
    """SHA256 du PDF. Blocs 64 KB."""
    h = hashlib.sha256()
    with pdf_path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def signer_document(
    document: DocumentConformite,
    nom_signataire: str,
    email_signataire: str,
    consentement_explicite: bool,
    ip_signataire: str | None = None,
    user_agent: str | None = None,
) -> PreuveSignature:
    """Signature simple eIDAS.

    Lève ValueError si consentement_explicite=False.
    """
    if not consentement_explicite:
        raise ValueError(
            "Le consentement explicite est requis pour la signature électronique eIDAS."
        )

    date_sig = datetime.now(timezone.utc).isoformat()

    # hash_signature = SHA256(document_sha256 + nom + email + date_signature)
    raw = document.sha256 + nom_signataire + email_signataire + date_sig
    hash_sig = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    preuve = PreuveSignature(
        document_sha256=document.sha256,
        nom_signataire=nom_signataire,
        email_signataire=email_signataire,
        date_signature=date_sig,
        ip_signataire=ip_signataire,
        user_agent=user_agent,
        hash_signature=hash_sig,
        version_protocole="SIMPLE_v1",
    )

    # Write .signature.json next to the PDF
    pdf_path = Path(document.chemin_pdf)
    sig_path = pdf_path.with_suffix(".signature.json")
    sig_path.write_text(
        json.dumps(preuve.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return preuve


def verifier_signature(pdf_path: Path, preuve_path: Path) -> bool:
    """Vérifie que le hash du PDF correspond à la preuve.

    Returns True/False.
    """
    try:
        preuve_data = json.loads(preuve_path.read_text(encoding="utf-8"))
        preuve = PreuveSignature.model_validate(preuve_data)
        current_hash = calculer_hash_document(pdf_path)
        return current_hash == preuve.document_sha256
    except Exception:
        return False
