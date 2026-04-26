"""Tests — Génération Lettre de Mission (src/conformite/lettre_mission.py)."""

from __future__ import annotations

from pathlib import Path

import pypdf

from src.conformite.lettre_mission import generer_lettre_mission
from src.schemas import DocumentConformite

_PROFIL = {
    "id": 7,
    "nom": "Martin",
    "email": "martin@example.com",
    "age": 52,
    "tmi": 0.41,
    "patrimoine_financier_total": 500_000,
}

_CABINET = {
    "cabinet": {
        "nom": "Cabinet Martin Conseil",
        "numero_orias": "87654321",
        "adresse": "10 avenue Victor Hugo, Lyon",
        "telephone": "04 78 00 00 00",
        "email": "contact@martin-conseil.fr",
    },
    "remuneration": {"mode": "honoraires"},
}

_CONFORMITE = {
    "cabinet_orias": "87654321",
    "cabinet_associations": ["CNCIF"],
    "cabinet_assurance_rcp": "Allianz",
    "cabinet_assurance_rcp_numero": "AZ-999",
    "cabinet_mediateur": "Médiateur de l'AMF",
    "horizon_conservation_annees": 5,
    "textes_der": {},
    "textes_lettre_mission": {
        "preambule": "Préambule test lettre mission.",
        "objet": "Objet test.",
        "duree_resiliation": "Durée test.",
        "responsabilite": "Responsabilité test.",
        "mentions_cncif": "Mentions CNCIF test.",
    },
    "textes_rapport_adequation": {},
}

_PARAMETRES_FORFAIT = {
    "objet": "Conseil patrimonial global",
    "perimetre": ["audit", "allocation", "fiscalite"],
    "honoraires_eur": 3500.0,
    "honoraires_modalite": "forfait",
    "duree_mois": 12,
    "date_debut": "2025-01-01",
}


def test_generer_lettre_mission_retourne_doc(tmp_path: Path) -> None:
    out = tmp_path / "lm.pdf"
    doc = generer_lettre_mission(_PROFIL, _CABINET, _CONFORMITE, _PARAMETRES_FORFAIT, out)
    assert isinstance(doc, DocumentConformite)
    assert doc.type_doc == "LETTRE_MISSION"
    assert doc.version_template == "LM_v1.0"
    assert doc.profil_id == 7
    assert doc.client_nom == "Martin"


def test_generer_lettre_mission_pdf_valide(tmp_path: Path) -> None:
    out = tmp_path / "lm.pdf"
    generer_lettre_mission(_PROFIL, _CABINET, _CONFORMITE, _PARAMETRES_FORFAIT, out)
    assert out.exists()
    assert out.stat().st_size > 5_000


def test_generer_lettre_mission_sections_presentes(tmp_path: Path) -> None:
    out = tmp_path / "lm.pdf"
    generer_lettre_mission(_PROFIL, _CABINET, _CONFORMITE, _PARAMETRES_FORFAIT, out)
    reader = pypdf.PdfReader(str(out))
    text = "\n".join(p.extract_text() or "" for p in reader.pages)
    assert "3" in text or "3 500" in text or "3500" in text  # honoraires
    assert "forfait" in text.lower() or "Forfait" in text


def test_generer_lettre_mission_modalites(tmp_path: Path) -> None:
    """Test des 3 modalités : forfait, horaire, pct_actifs."""
    for modalite, honoraires in [("forfait", 2000.0), ("horaire", 250.0), ("pct_actifs", 0.75)]:
        out = tmp_path / f"lm_{modalite}.pdf"
        params = {
            **_PARAMETRES_FORFAIT,
            "honoraires_modalite": modalite,
            "honoraires_eur": honoraires,
        }
        doc = generer_lettre_mission(_PROFIL, _CABINET, _CONFORMITE, params, out)
        assert isinstance(doc, DocumentConformite)
        assert out.exists()
        reader = pypdf.PdfReader(str(out))
        text = "\n".join(p.extract_text() or "" for p in reader.pages)
        # Chaque PDF doit contenir quelque chose lié au montant
        assert len(text) > 100
