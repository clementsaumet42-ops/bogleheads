"""Tests pour le module OCR — Sprint S20."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _tesseract_disponible() -> bool:
    """Vérifie si Tesseract est disponible sur ce système."""
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def test_ocr_graceful_sans_pytesseract(tmp_path: Path) -> None:
    """Si pytesseract n'est pas installé, retourne une chaîne vide sans crash."""
    chemin = tmp_path / "scan.pdf"
    chemin.write_bytes(b"%PDF-1.4 fake")

    with patch.dict("sys.modules", {"pytesseract": None}):
        import importlib

        import src.import_patrimoine.ocr as ocr_module

        importlib.reload(ocr_module)
        resultat = ocr_module.extraire_via_ocr(chemin)
        assert isinstance(resultat, str)
        assert resultat == ""


def test_ocr_graceful_sans_tesseract_binaire(tmp_path: Path) -> None:
    """Si le binaire tesseract est absent, retourne '' sans crash."""
    chemin = tmp_path / "scan.pdf"
    chemin.write_bytes(b"%PDF-1.4 fake")

    mock_pytesseract = MagicMock()
    mock_pytesseract.get_tesseract_version.side_effect = Exception("tesseract not found")

    with patch.dict("sys.modules", {"pytesseract": mock_pytesseract, "pdf2image": MagicMock()}):
        import importlib

        import src.import_patrimoine.ocr as ocr_module

        importlib.reload(ocr_module)
        resultat = ocr_module.extraire_via_ocr(chemin)
        assert resultat == ""


def test_ocr_graceful_sans_pdf2image(tmp_path: Path) -> None:
    """Si pdf2image n'est pas installé, retourne '' sans crash."""
    chemin = tmp_path / "scan.pdf"
    chemin.write_bytes(b"%PDF-1.4 fake")

    mock_pytesseract = MagicMock()
    mock_pytesseract.get_tesseract_version.return_value = "5.0"

    with patch.dict("sys.modules", {"pytesseract": mock_pytesseract, "pdf2image": None}):
        import importlib

        import src.import_patrimoine.ocr as ocr_module

        importlib.reload(ocr_module)
        resultat = ocr_module.extraire_via_ocr(chemin)
        assert resultat == ""


@pytest.mark.skipif(
    not _tesseract_disponible(),
    reason="Tesseract non installé sur ce système",
)
def test_ocr_avec_tesseract_disponible(tmp_path: Path) -> None:
    """Si Tesseract est disponible, l'OCR doit retourner du texte (même vide)."""
    chemin = tmp_path / "scan.pdf"
    chemin.write_bytes(b"%PDF-1.4 fake")

    from src.import_patrimoine.ocr import extraire_via_ocr

    resultat = extraire_via_ocr(chemin)
    assert isinstance(resultat, str)


def test_detecter_pdf_scanne_peu_texte(tmp_path: Path) -> None:
    """Un PDF avec peu de texte natif est détecté comme scanné."""
    chemin = tmp_path / "test.pdf"
    chemin.write_bytes(b"%PDF-1.4 fake")

    mock_page = MagicMock()
    mock_page.extract_text.return_value = "AB"
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdf.__enter__ = lambda s: mock_pdf
    mock_pdf.__exit__ = MagicMock(return_value=False)

    with patch("pdfplumber.open", return_value=mock_pdf):
        from src.import_patrimoine.ocr import detecter_pdf_scanne

        assert detecter_pdf_scanne(chemin) is True
