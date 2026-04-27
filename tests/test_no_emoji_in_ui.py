"""Test : vérification absence d'emoji dans les pages UI — Sprint S20."""

from __future__ import annotations

import re
from pathlib import Path

# Regex pour détecter les emojis Unicode (exclut les caractères de dessin de boîtes U+2500-U+25FF)
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001f600-\U0001f64f"  # emoticons
    "\U0001f300-\U0001f5ff"  # symbols & pictographs
    "\U0001f680-\U0001f6ff"  # transport & map
    "\U0001f1e0-\U0001f1ff"  # flags
    "\U00002702-\U000027b0"  # dingbats
    "\U000024c2-\U000024ff"  # enclosed alphanumerics (exclut box-drawing U+2500+)
    "\U0001f900-\U0001f9ff"  # supplemental symbols
    "]+",
    flags=re.UNICODE,
)

PAGE_IMPORT = Path(__file__).parent.parent / "pages" / "24_Import_Patrimoine.py"


def test_pas_demoji_dans_page_import() -> None:
    """La page 24_Import_Patrimoine.py ne doit contenir aucun emoji."""
    assert PAGE_IMPORT.exists(), f"Fichier introuvable : {PAGE_IMPORT}"
    contenu = PAGE_IMPORT.read_text(encoding="utf-8")

    trouvees = []
    for numero, ligne in enumerate(contenu.splitlines(), start=1):
        matches = _EMOJI_PATTERN.findall(ligne)
        for m in matches:
            trouvees.append((numero, m, ligne.strip()))

    assert trouvees == [], "Emoji(s) trouvé(s) dans 24_Import_Patrimoine.py :\n" + "\n".join(
        f"  Ligne {num}: '{em}' dans: {ctx}" for num, em, ctx in trouvees
    )
