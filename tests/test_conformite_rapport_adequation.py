"""Tests — Génération Rapport d'Adéquation (src/conformite/rapport_adequation.py)."""

from __future__ import annotations

import copy
from pathlib import Path

import pypdf

from src.conformite.rapport_adequation import generer_rapport_adequation
from src.schemas import DocumentConformite

_PROFIL = {
    "id": 99,
    "nom": "Bernard",
    "email": "bernard@example.com",
    "age": 38,
    "tmi": 0.30,
    "patrimoine_financier_total": 150_000,
    "score_risque": 6,
    "horizon_placement": 20,
}

_CABINET = {
    "cabinet": {
        "nom": "Cabinet Bernard Finance",
        "numero_orias": "11223344",
        "adresse": "5 rue du Commerce, Bordeaux",
        "email": "contact@bernard-finance.fr",
    },
    "remuneration": {"mode": "honoraires"},
}

_CONFORMITE = {
    "cabinet_orias": "11223344",
    "cabinet_associations": ["CNCIF"],
    "cabinet_assurance_rcp": "Generali",
    "cabinet_assurance_rcp_numero": "GEN-001",
    "cabinet_mediateur": "Médiateur de l'AMF",
    "horizon_conservation_annees": 5,
    "textes_der": {},
    "textes_lettre_mission": {},
    "textes_rapport_adequation": {
        "introduction": "Introduction test rapport adéquation MIF II art. 25(6).",
        "avertissements": "Avertissements test.",
        "obligation_maj": "Obligation MAJ annuelle art. 325-5.",
    },
}

_ALLOCATION = {"Actions": 0.70, "Obligations": 0.20, "Monétaire": 0.10}

_ETFS = [
    {"ticker": "IWDA", "nom": "iShares Core MSCI World", "classe_actifs": "Actions", "ter": 0.20},
    {
        "ticker": "AGGH",
        "nom": "iShares Core Global Aggregate",
        "classe_actifs": "Obligations",
        "ter": 0.10,
    },
]


def test_generer_rapport_adequation_retourne_doc(tmp_path: Path) -> None:
    out = tmp_path / "ra.pdf"
    doc = generer_rapport_adequation(_PROFIL, _CABINET, _CONFORMITE, _ALLOCATION, _ETFS, out)
    assert isinstance(doc, DocumentConformite)
    assert doc.type_doc == "RAPPORT_ADEQUATION"
    assert doc.version_template == "RA_v1.0"
    assert doc.profil_id == 99
    assert doc.client_nom == "Bernard"


def test_generer_rapport_adequation_pdf_valide(tmp_path: Path) -> None:
    out = tmp_path / "ra.pdf"
    generer_rapport_adequation(_PROFIL, _CABINET, _CONFORMITE, _ALLOCATION, _ETFS, out)
    assert out.exists()
    assert out.stat().st_size > 5_000


def test_generer_rapport_adequation_sections_presentes(tmp_path: Path) -> None:
    out = tmp_path / "ra.pdf"
    generer_rapport_adequation(_PROFIL, _CABINET, _CONFORMITE, _ALLOCATION, _ETFS, out)
    reader = pypdf.PdfReader(str(out))
    text = "\n".join(p.extract_text() or "" for p in reader.pages)
    assert "MIF" in text or "25(6)" in text or "adéquation" in text.lower()


def test_generer_rapport_adequation_etfs(tmp_path: Path) -> None:
    out = tmp_path / "ra_etfs.pdf"
    doc = generer_rapport_adequation(_PROFIL, _CABINET, _CONFORMITE, _ALLOCATION, _ETFS, out)
    assert isinstance(doc, DocumentConformite)
    reader = pypdf.PdfReader(str(out))
    text = "\n".join(p.extract_text() or "" for p in reader.pages)
    # At least one ETF ticker should appear
    assert "IWDA" in text or "AGGH" in text


def test_generer_rapport_adequation_pas_mutation_profil(tmp_path: Path) -> None:
    profil_copy = copy.deepcopy(_PROFIL)
    out = tmp_path / "ra.pdf"
    generer_rapport_adequation(_PROFIL, _CABINET, _CONFORMITE, _ALLOCATION, _ETFS, out)
    assert profil_copy == _PROFIL, "Le profil a été muté par la génération du rapport"


def test_generer_rapport_adequation_allocation_cible(tmp_path: Path) -> None:
    out = tmp_path / "ra_alloc.pdf"
    generer_rapport_adequation(_PROFIL, _CABINET, _CONFORMITE, _ALLOCATION, _ETFS, out)
    reader = pypdf.PdfReader(str(out))
    text = "\n".join(p.extract_text() or "" for p in reader.pages)
    # Allocation percentages should be present
    assert "70" in text or "Actions" in text
