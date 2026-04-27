"""Détection automatique de l'émetteur d'un relevé PDF à partir de son texte."""

from __future__ import annotations

import re
from pathlib import Path

import yaml


def _charger_templates() -> list[dict]:
    """Charge tous les fichiers YAML de templates depuis le répertoire templates/."""
    templates_dir = Path(__file__).parent / "templates"
    templates = []
    for fichier in sorted(templates_dir.glob("*.yaml")):
        try:
            with fichier.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
                data["_fichier"] = fichier.stem
                templates.append(data)
        except Exception:
            pass
    return templates


def detecter_emetteur(texte: str) -> tuple[str | None, str | None]:
    """Détecte l'émetteur d'un relevé PDF à partir du texte brut.

    Retourne (nom_emetteur, nom_template) ou (None, None) si non détecté.
    """
    templates = _charger_templates()
    for tpl in templates:
        emetteur = tpl.get("emetteur", {})
        signatures = emetteur.get("signatures", [])
        for sig in signatures:
            if re.search(re.escape(sig), texte, re.IGNORECASE):
                return emetteur.get("nom"), tpl.get("_fichier")
    return None, None
