"""Shim de compatibilité — réexporte src/import_patrimoine.

Point d'entrée public de l'import PDF dans la nouvelle architecture.
"""

from __future__ import annotations

from src.import_patrimoine.extracteur import extraire_pdf
from src.import_patrimoine.modele import ImportPDF, LignePatrimoine, ResultatExtraction

__all__ = [
    "extraire_pdf",
    "ImportPDF",
    "LignePatrimoine",
    "ResultatExtraction",
]
