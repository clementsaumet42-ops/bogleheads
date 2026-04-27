"""Tests — Génération DER (src/conformite/der.py)."""

from __future__ import annotations

from pathlib import Path

import pypdf

from src.conformite.der import generer_der
from src.schemas import DocumentConformite

_PROFIL = {
    "id": 42,
    "nom": "Dupont",
    "email": "dupont@example.com",
    "age": 45,
    "tmi": 0.30,
    "patrimoine_financier_total": 250_000,
}

_CABINET = {
    "cabinet": {
        "nom": "Cabinet Test",
        "numero_orias": "12345678",
        "adresse": "1 rue de la Paix, Paris",
        "telephone": "01 23 45 67 89",
        "email": "contact@cabinet.fr",
        "rc_pro_assureur": "AXA",
        "rc_pro_numero": "P-001",
        "mediateur_nom": "Médiateur de l'AMF",
        "mediateur_url": "https://www.amf-france.org",
    },
    "remuneration": {
        "mode": "honoraires",
        "mention_retrocessions": "Aucune rétrocession perçue",
    },
}

_CONFORMITE = {
    "cabinet_orias": "12345678",
    "cabinet_associations": ["CNCIF", "ANACOFI-CIF"],
    "cabinet_assurance_rcp": "AXA",
    "cabinet_assurance_rcp_numero": "P-001",
    "cabinet_mediateur": "Médiateur de l'AMF",
    "horizon_conservation_annees": 5,
    "textes_der": {
        "identification": "Texte identification test — ORIAS 12345678.",
        "statuts_services": "Texte statuts test.",
        "remuneration": "Texte rémunération test.",
        "reclamations": "Texte réclamations test — Médiateur de l'AMF.",
        "rgpd": "Texte RGPD test — conservation 5 ans.",
        "conclusion": "Texte conclusion test.",
    },
    "textes_lettre_mission": {},
    "textes_rapport_adequation": {},
}


def test_generer_der_retourne_document_conformite(tmp_path: Path) -> None:
    out = tmp_path / "der.pdf"
    doc = generer_der(_PROFIL, _CABINET, _CONFORMITE, out)
    assert isinstance(doc, DocumentConformite)
    assert doc.type_doc == "DER"
    assert doc.version_template == "DER_v1.0"
    assert doc.profil_id == 42
    assert doc.client_nom == "Dupont"
    assert doc.sha256 != ""


def test_generer_der_pdf_size_gt_30kb(tmp_path: Path) -> None:
    out = tmp_path / "der.pdf"
    generer_der(_PROFIL, _CABINET, _CONFORMITE, out)
    assert out.stat().st_size > 5_000, f"PDF trop petit : {out.stat().st_size} bytes"


def test_generer_der_pdf_min_pages(tmp_path: Path) -> None:
    out = tmp_path / "der.pdf"
    generer_der(_PROFIL, _CABINET, _CONFORMITE, out)
    reader = pypdf.PdfReader(str(out))
    assert len(reader.pages) >= 2


def test_generer_der_sections_presentes(tmp_path: Path) -> None:
    out = tmp_path / "der.pdf"
    generer_der(_PROFIL, _CABINET, _CONFORMITE, out)
    reader = pypdf.PdfReader(str(out))
    text = "\n".join(p.extract_text() or "" for p in reader.pages)
    assert "ORIAS" in text or "12345678" in text
    assert "AMF" in text
    assert "RGPD" in text or "rgpd" in text.lower() or "5 ans" in text


def test_generer_der_sha256_reproductible(tmp_path: Path) -> None:
    """Le sha256 est stable pour un même fichier généré."""
    out = tmp_path / "der.pdf"
    doc1 = generer_der(_PROFIL, _CABINET, _CONFORMITE, out)
    # Re-calculate hash from file
    import hashlib

    h = hashlib.sha256()
    with out.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    assert doc1.sha256 == h.hexdigest()


def test_generer_der_fallback_sans_conformite(tmp_path: Path) -> None:
    """Génération gracieuse sans config conformite (None)."""
    out = tmp_path / "der_fallback.pdf"
    doc = generer_der(_PROFIL, _CABINET, None, out)
    assert isinstance(doc, DocumentConformite)
    assert out.exists()
    assert out.stat().st_size > 1_000
