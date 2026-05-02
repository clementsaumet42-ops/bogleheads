"""Diagnostic PDF 8 pages — vue synthétique de la situation patrimoniale IS.

Structure :
1. Couverture (1 page)
2. Situation patrimoniale globale (1 page)
3. Analyse fiscale IS : pièges identifiés (2 pages)
4. Potentiel d'optimisation chiffré (2 pages)
5. Recommandations préliminaires (1 page)
6. Avertissements réglementaires (1 page)
"""

from __future__ import annotations

from pathlib import Path


def generer_diagnostic_pdf(mission_id: str, data: dict, output_dir: Path) -> Path:
    """Génère le PDF diagnostic 8 pages. À implémenter S+1."""
    raise NotImplementedError("Sprint S+1")
