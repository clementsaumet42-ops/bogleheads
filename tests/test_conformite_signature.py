"""Tests — Signature eIDAS (src/conformite/signature.py)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.conformite.der import generer_der
from src.conformite.signature import calculer_hash_document, signer_document, verifier_signature
from src.schemas import DocumentConformite, PreuveSignature

_PROFIL = {"id": 1, "nom": "Test", "email": "test@test.com"}
_CABINET = {
    "cabinet": {
        "nom": "Cabinet",
        "numero_orias": "00000001",
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


def _make_doc(tmp_path: Path) -> DocumentConformite:
    out = tmp_path / "der_sig.pdf"
    return generer_der(_PROFIL, _CABINET, None, out)


def test_signer_sans_consentement_leve_value_error(tmp_path: Path) -> None:
    doc = _make_doc(tmp_path)
    with pytest.raises(ValueError, match="consentement"):
        signer_document(doc, "Alice", "alice@test.com", consentement_explicite=False)


def test_signer_avec_consentement_retourne_preuve(tmp_path: Path) -> None:
    doc = _make_doc(tmp_path)
    preuve = signer_document(doc, "Alice", "alice@test.com", consentement_explicite=True)
    assert isinstance(preuve, PreuveSignature)
    assert preuve.nom_signataire == "Alice"
    assert preuve.email_signataire == "alice@test.com"
    assert preuve.version_protocole == "SIMPLE_v1"
    assert len(preuve.hash_signature) == 64  # SHA256 hex


def test_hash_reproductible(tmp_path: Path) -> None:
    """Même fichier → même hash."""
    out = tmp_path / "der_hash.pdf"
    doc = generer_der(_PROFIL, _CABINET, None, out)
    h1 = calculer_hash_document(out)
    h2 = calculer_hash_document(out)
    assert h1 == h2
    assert h1 == doc.sha256


def test_verifier_signature_true_sur_doc_non_modifie(tmp_path: Path) -> None:
    doc = _make_doc(tmp_path)
    signer_document(doc, "Bob", "bob@test.com", consentement_explicite=True)
    pdf_path = Path(doc.chemin_pdf)
    sig_path = pdf_path.with_suffix(".signature.json")
    assert verifier_signature(pdf_path, sig_path) is True


def test_verifier_signature_false_sur_doc_altere(tmp_path: Path) -> None:
    doc = _make_doc(tmp_path)
    signer_document(doc, "Bob", "bob@test.com", consentement_explicite=True)
    pdf_path = Path(doc.chemin_pdf)
    sig_path = pdf_path.with_suffix(".signature.json")
    # Alterate the PDF
    with pdf_path.open("ab") as f:
        f.write(b"\x00\x00ALTERATION")
    assert verifier_signature(pdf_path, sig_path) is False


def test_fichier_signature_json_valide(tmp_path: Path) -> None:
    doc = _make_doc(tmp_path)
    signer_document(doc, "Charlie", "charlie@test.com", consentement_explicite=True)
    pdf_path = Path(doc.chemin_pdf)
    sig_path = pdf_path.with_suffix(".signature.json")
    assert sig_path.exists()
    data = json.loads(sig_path.read_text(encoding="utf-8"))
    preuve = PreuveSignature.model_validate(data)
    assert preuve.nom_signataire == "Charlie"
    assert preuve.email_signataire == "charlie@test.com"


def test_signer_ne_mute_pas_pdf(tmp_path: Path) -> None:
    """La signature ne modifie pas le PDF lui-même."""
    doc = _make_doc(tmp_path)
    pdf_path = Path(doc.chemin_pdf)
    hash_avant = calculer_hash_document(pdf_path)
    signer_document(doc, "Dave", "dave@test.com", consentement_explicite=True)
    hash_apres = calculer_hash_document(pdf_path)
    assert hash_avant == hash_apres


def test_calculer_hash_document(tmp_path: Path) -> None:
    """calculer_hash_document retourne un SHA256 valide."""
    f = tmp_path / "test.bin"
    f.write_bytes(b"hello world")
    expected = hashlib.sha256(b"hello world").hexdigest()
    assert calculer_hash_document(f) == expected
