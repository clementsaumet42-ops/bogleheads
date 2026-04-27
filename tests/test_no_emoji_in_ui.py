"""Tests S19 — Détection d'emojis dans l'UI (pages/ et src/ui/).

Vérifie qu'aucun caractère emoji n'apparaît dans les strings affichés aux
utilisateurs. Les commentaires, docstrings et page_icon= sont whitelistés.
"""

from __future__ import annotations

import re
from pathlib import Path

# ─── Périmètre de scan ────────────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).parent.parent
_DIRS_A_SCANNER = [
    _REPO_ROOT / "pages",
    _REPO_ROOT / "src" / "ui",
]

# Pattern emoji — couvre les plages Unicode principales
# Note: on exclut U+2400-U+25FF (box drawing, block elements, geometric shapes)
#       qui ne sont pas des emojis
_EMOJI_RE = re.compile(
    "["
    "\U0001f300-\U0001f9ff"  # Misc symbols, emoticons, transport, etc.
    "\U0001f1e0-\U0001f1ff"  # Drapeaux
    "\U00002600-\U000027bf"  # Misc symbols (soleil, étoiles, dés...)
    "\U0001fa00-\U0001fa6f"  # Chess, symbols extended-A
    "\U0001fa70-\U0001faff"  # Symbols extended-B
    "]+",
    flags=re.UNICODE,
)

# Whitelist — noms de fonctions/variables ou contextes acceptables
# page_icon= dans st.set_page_config : icône navigateur, pas UI rendue
_WHITELIST_PATTERNS = [
    re.compile(r'page_icon\s*=\s*["\'].*["\']'),
    re.compile(r"^\s*#"),  # ligne de commentaire
    re.compile(r'^\s*"""'),  # début de docstring
    re.compile(r"^\s*'''"),  # début de docstring simple quotes
    re.compile(r"^\s*\*"),  # ligne de doc (bullet dans docstring)
]

# Fonctions Streamlit dont les arguments sont affichés dans l'UI
_ST_DISPLAY_FUNCTIONS = {
    "st.title",
    "st.header",
    "st.subheader",
    "st.write",
    "st.info",
    "st.warning",
    "st.error",
    "st.success",
    "st.caption",
    "st.text",
    "st.markdown",
    "st.metric",
    "st.button",
    "st.download_button",
    "st.selectbox",
    "st.radio",
    "st.multiselect",
    "st.expander",
    "st.tab",
    "st.tabs",
    "st.popover",
}


def _collect_py_files() -> list[Path]:
    """Collecte tous les fichiers .py dans les répertoires de scan."""
    files = []
    for directory in _DIRS_A_SCANNER:
        if directory.exists():
            files.extend(directory.rglob("*.py"))
    return sorted(files)


def _is_in_docstring_or_comment(source_lines: list[str], lineno: int) -> bool:
    """Heuristique : vérifie si la ligne est dans un commentaire ou docstring."""
    line = source_lines[lineno - 1]
    stripped = line.strip()
    # Commentaire inline
    if "#" in line:
        code_part = line[: line.index("#")]
        comment_part = line[line.index("#") :]
        # Si l'emoji est dans le commentaire seulement, c'est OK
        if not _EMOJI_RE.search(code_part) and _EMOJI_RE.search(comment_part):
            return True
    # Ligne de pure docstring / commentaire
    return stripped.startswith(("#", '"""', "'''", "*", "Raises:", "Returns:", "Args:", "Note:"))


def _is_page_icon_line(line: str) -> bool:
    """Détecte si la ligne contient page_icon= (whitelisté)."""
    return bool(re.search(r"page_icon\s*=", line))


def _find_emojis_in_file(path: Path) -> list[tuple[int, str]]:
    """Retourne les (numéro_ligne, contenu) avec emoji hors whitelist."""
    try:
        source = path.read_text(encoding="utf-8")
    except Exception:
        return []

    source_lines = source.split("\n")
    violations = []

    for lineno, line in enumerate(source_lines, 1):
        if not _EMOJI_RE.search(line):
            continue

        # Whitelist : page_icon=
        if _is_page_icon_line(line):
            continue

        # Whitelist : commentaire ou docstring
        if _is_in_docstring_or_comment(source_lines, lineno):
            continue

        violations.append((lineno, line.strip()))

    return violations


# ─── Tests ────────────────────────────────────────────────────────────────────


def test_aucun_emoji_dans_pages():
    """Aucun emoji dans les pages Streamlit (hors page_icon= et commentaires)."""
    violations = []
    for path in _collect_py_files():
        if "pages" not in str(path):
            continue
        found = _find_emojis_in_file(path)
        for lineno, content in found:
            violations.append(f"{path.relative_to(_REPO_ROOT)}:{lineno}: {content}")

    if violations:
        msg = "Emojis détectés dans pages/ :\n" + "\n".join(violations)
        raise AssertionError(msg)


def test_aucun_emoji_dans_src_ui():
    """Aucun emoji dans src/ui/ (hors commentaires/docstrings)."""
    violations = []
    for path in _collect_py_files():
        if "src/ui" not in str(path) and "src\\ui" not in str(path):
            continue
        # Whitelist : components.py peut contenir des refs dans des strings de mapping
        # uniquement en commentaires ou variables de documentation
        found = _find_emojis_in_file(path)
        for lineno, content in found:
            violations.append(f"{path.relative_to(_REPO_ROOT)}:{lineno}: {content}")

    if violations:
        msg = "Emojis détectés dans src/ui/ :\n" + "\n".join(violations)
        raise AssertionError(msg)


def test_fichiers_scannables():
    """Au moins un fichier est trouvé dans chaque répertoire scanné."""
    files = _collect_py_files()
    page_files = [f for f in files if "pages" in str(f)]
    ui_files = [f for f in files if "src/ui" in str(f) or "src\\ui" in str(f)]

    assert len(page_files) > 0, "Aucun fichier .py trouvé dans pages/"
    assert len(ui_files) > 0, "Aucun fichier .py trouvé dans src/ui/"


def test_theme_py_sans_emoji():
    """src/ui/theme.py ne contient pas d'emojis dans le CSS injecté."""
    from src.ui.theme import _CSS

    assert not _EMOJI_RE.search(_CSS), "Le CSS du thème contient des emojis"


def test_components_py_sans_emoji_dans_html():
    """src/ui/components.py ne génère pas de HTML avec emojis visibles."""
    from unittest.mock import MagicMock, patch

    from src.ui.components import (
        kpi_card,
        panneau_avertissement,
        titre_page,
    )

    html_outputs = []
    mock_st = MagicMock()
    mock_st.markdown = MagicMock()
    mock_st.button = MagicMock(return_value=False)

    with patch("src.ui.components.st", mock_st):
        titre_page("Titre de test")
        kpi_card("Label", "Valeur")
        panneau_avertissement("info", "Titre", "Description")

    for call in mock_st.markdown.call_args_list:
        if call[0]:
            html_outputs.append(call[0][0])

    for html in html_outputs:
        match = _EMOJI_RE.search(html)
        assert not match, f"Emoji trouvé dans le HTML généré: {match.group()!r}"
