"""Calcul du score de confiance (0-100) pour une ligne patrimoine extraite."""

from __future__ import annotations

from src.import_patrimoine.modele import LignePatrimoine


def calculer_confiance(
    ligne: LignePatrimoine,
    template_matche: bool = False,
    valorisation_ambigue: bool = False,
    via_ocr: bool = False,
) -> int:
    """Retourne un score de confiance 0-100 selon les critères d'extraction.

    Barème :
    - Template correspondant trouvé : +40
    - ISIN extrait et valide        : +25
    - Valorisation sans ambiguïté   : +20
    - Enveloppe identifiée          : +10
    - Texte natif (pas d'OCR)       : +5
    """
    score = 0

    if template_matche:
        score += 40

    if ligne.isin is not None:
        score += 25

    if not valorisation_ambigue and ligne.valorisation_eur > 0:
        score += 20

    if ligne.enveloppe and ligne.enveloppe not in ("", "Inconnu"):
        score += 10

    if not via_ocr:
        score += 5

    return max(0, min(100, score))
