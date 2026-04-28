"""OCR fallback via pytesseract + pdf2image pour les PDF scannés."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def detecter_pdf_scanne(chemin: Path) -> bool:
    """Retourne True si le PDF contient moins de 100 caractères de texte natif."""
    try:
        import pdfplumber

        with pdfplumber.open(str(chemin)) as pdf:
            texte = ""
            for page in pdf.pages:
                t = page.extract_text() or ""
                texte += t
                if len(texte) >= 100:
                    return False
        return len(texte) < 100
    except Exception as exc:
        logger.warning("Erreur détection PDF scanné : %s", exc)
        return False


def extraire_via_ocr(chemin: Path, langue: str = "fra") -> str:
    """OCR via pytesseract sur les images du PDF. Retourne le texte brut.

    Si Tesseract ou pdf2image n'est pas disponible, retourne une chaîne vide
    avec un message de log clair — pas de crash.
    """
    try:
        import pytesseract
    except ImportError:
        logger.warning(
            "pytesseract non installé. "
            "Installez les dépendances PDF : pip install bogleheads-fr[pdf]"
        )
        return ""

    try:
        from pdf2image import convert_from_path
    except ImportError:
        logger.warning(
            "pdf2image non installé. Installez les dépendances PDF : pip install bogleheads-fr[pdf]"
        )
        return ""

    try:
        pytesseract.get_tesseract_version()
    except Exception:
        logger.warning(
            "Tesseract OCR introuvable sur ce système. "
            "Installez-le : sudo apt-get install tesseract-ocr tesseract-ocr-fra"
        )
        return ""

    try:
        images = convert_from_path(str(chemin))
        textes: list[str] = []
        for img in images:
            t = pytesseract.image_to_string(img, lang=langue)
            textes.append(t)
        return "\n".join(textes)
    except Exception as exc:
        logger.warning("Erreur OCR sur %s : %s", chemin, exc)
        return ""
