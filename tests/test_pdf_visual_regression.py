"""Tests S19 — Régression visuelle PDF.

Vérifie que le PDF généré :
- Contient toujours le bon nombre de pages
- Contient le nom du client et le patrimoine total dans le texte extrait
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import pytest

# ─── Fixture profil minimaliste ───────────────────────────────────────────────


@pytest.fixture
def profil_test():
    """Profil client minimal pour générer un PDF de test."""
    return {
        "nom": "Dupont Jean",
        "age": 45,
        "situation_familiale": "marié",
        "tmi": 0.30,
        "regime_fiscal": "IR",
        "rfr_annuel": 80000,
        "patrimoine_financier_total": 350000,
        "patrimoine_immobilier": 200000,
        "capacite_epargne_annuelle": 12000,
        "horizon_placement_ans": 20,
        "score_risque": 4,
        "objectif_principal": "Préparer la retraite",
        "objectifs_secondaires": ["Transmission patrimoniale"],
        "enveloppes_disponibles": {
            "PEA": {"encours_actuel": 80000, "plafond": 150000},
            "AV": {"encours_actuel": 120000},
            "CTO": {"encours_actuel": 50000},
            "PER": {"encours_actuel": 100000},
        },
    }


@pytest.fixture
def config_test():
    """Config PDF minimale."""
    return {
        "cabinet": {
            "nom": "Cabinet Test S19",
            "telephone": "01 23 45 67 89",
            "email": "contact@cabinet-test.fr",
            "numero_orias": "00000000",
            "mention_conformite": "CIF enregistré AMF",
        }
    }


# ─── Test nb pages ────────────────────────────────────────────────────────────


def test_pdf_nb_pages(profil_test, config_test):
    """Le PDF généré contient le bon nombre de pages (NB_PAGES constant)."""
    pytest.importorskip("pypdf")
    from src.pdf_builder import NB_PAGES, generer_pdf

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = Path(tmp_dir) / "test_s19.pdf"
        resultat = generer_pdf(profil_test, config_test, str(out_path))

    assert out_path.exists() or resultat is not None  # le PDF a été généré

    # Lire depuis bytes si disponible
    try:
        from pypdf import PdfReader

        if out_path.exists():
            reader = PdfReader(str(out_path))
        elif hasattr(resultat, "pdf_bytes") and resultat.pdf_bytes:
            reader = PdfReader(io.BytesIO(resultat.pdf_bytes))
        else:
            pytest.skip("Impossible de lire le PDF généré")

        nb = len(reader.pages)
        assert nb == NB_PAGES, (
            f"Le PDF contient {nb} pages au lieu de {NB_PAGES}. "
            "Aucune page ne doit avoir été ajoutée ou retirée (garde-fou S19)."
        )
    except ImportError:
        pytest.skip("pypdf non disponible")


def test_pdf_contient_nom_client(profil_test, config_test):
    """Le PDF contient le nom du client dans son texte."""
    pytest.importorskip("pypdf")
    from src.pdf_builder import generer_pdf

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = Path(tmp_dir) / "test_s19_nom.pdf"
        resultat = generer_pdf(profil_test, config_test, str(out_path))

    try:
        from pypdf import PdfReader

        if out_path.exists():
            reader = PdfReader(str(out_path))
        elif hasattr(resultat, "pdf_bytes") and resultat.pdf_bytes:
            reader = PdfReader(io.BytesIO(resultat.pdf_bytes))
        else:
            pytest.skip("Impossible de lire le PDF généré")

        texte_complet = " ".join(page.extract_text() or "" for page in reader.pages)
        assert "Dupont" in texte_complet, (
            "Le nom du client 'Dupont' n'est pas trouvé dans le PDF. "
            "Le contenu textuel ne doit pas avoir changé (garde-fou S19)."
        )
    except ImportError:
        pytest.skip("pypdf non disponible")


def test_pdf_contient_patrimoine(profil_test, config_test):
    """Le PDF contient le patrimoine total dans son texte."""
    pytest.importorskip("pypdf")
    from src.pdf_builder import generer_pdf

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = Path(tmp_dir) / "test_s19_patrimoine.pdf"
        resultat = generer_pdf(profil_test, config_test, str(out_path))

    try:
        from pypdf import PdfReader

        if out_path.exists():
            reader = PdfReader(str(out_path))
        elif hasattr(resultat, "pdf_bytes") and resultat.pdf_bytes:
            reader = PdfReader(io.BytesIO(resultat.pdf_bytes))
        else:
            pytest.skip("Impossible de lire le PDF généré")

        texte_complet = " ".join(page.extract_text() or "" for page in reader.pages)
        # 350 000 € — chercher au moins "350" dans le texte
        assert "350" in texte_complet, (
            "Le patrimoine total '350000' n'est pas trouvé dans le PDF. "
            "Le contenu chiffré ne doit pas avoir changé (garde-fou S19)."
        )
    except ImportError:
        pytest.skip("pypdf non disponible")


# ─── Test palette (sanity) ────────────────────────────────────────────────────


def test_palette_pdf_bleu_nuit():
    """La palette PDF utilise bien le bleu nuit S19 (#0B1929) comme couleur principale."""
    from src.pdf_builder import _PRIMARY

    assert _PRIMARY.lower() == "#0b1929", (
        f"_PRIMARY vaut {_PRIMARY!r} au lieu de '#0B1929'. La palette S19 doit être appliquée."
    )


def test_palette_pdf_or_vieilli():
    """La palette PDF utilise l'or vieilli (#8B6F47) comme accent."""
    from src.pdf_builder import _ACCENT

    assert _ACCENT.lower() == "#8b6f47", (
        f"_ACCENT vaut {_ACCENT!r} au lieu de '#8B6F47'. La palette S19 doit être appliquée."
    )


def test_nb_pages_constant_non_zero():
    """La constante NB_PAGES est positive et raisonnable."""
    from src.pdf_builder import NB_PAGES

    assert NB_PAGES > 0
    assert NB_PAGES <= 30  # sanity : pas un nombre absurde
