"""Test : vérification absence d'emoji dans les pages UI — Sprint S20."""

from __future__ import annotations

import unicodedata
from pathlib import Path

PAGE_IMPORT = Path(__file__).parent.parent / "pages" / "24_Import_Patrimoine.py"

# Catégories Unicode qui correspondent à des emoji (So = Other Symbol, Sm = Math Symbol)
# Exclut les caractères de dessin de boîtes (box-drawing, U+2500-U+257F)
_BOX_DRAWING_RANGE = range(0x2500, 0x2580)


def _est_emoji(char: str) -> bool:
    """Retourne True si le caractère est un emoji Unicode."""
    cp = ord(char)
    # Exclure box-drawing et block elements (utilisés comme séparateurs visuels)
    if cp in _BOX_DRAWING_RANGE or 0x2580 <= cp <= 0x259F:
        return False
    cat = unicodedata.category(char)
    # So = Other Symbol (inclut beaucoup d'emoji), Sk = Modifier Symbol
    if cat in ("So",):
        return True
    # Plages d'emoji standards dans le BMP étendu (> U+1F000)
    return cp >= 0x1F000


def test_pas_demoji_dans_page_import() -> None:
    """La page 24_Import_Patrimoine.py ne doit contenir aucun emoji."""
    assert PAGE_IMPORT.exists(), f"Fichier introuvable : {PAGE_IMPORT}"
    contenu = PAGE_IMPORT.read_text(encoding="utf-8")

    trouvees = []
    for numero, ligne in enumerate(contenu.splitlines(), start=1):
        for char in ligne:
            if _est_emoji(char):
                trouvees.append((numero, char, ligne.strip()))

    assert trouvees == [], "Emoji(s) trouvé(s) dans 24_Import_Patrimoine.py :\n" + "\n".join(
        f"  Ligne {num}: '{em}' dans: {ctx}" for num, em, ctx in trouvees
    )
