"""Helpers pour lecture/écriture YAML atomique avec backup — S13 Lot B."""

from __future__ import annotations

import csv
import io
import shutil
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = ROOT / "config"


def lire_yaml(filename: str) -> dict:
    """Lit un fichier YAML de config et retourne le contenu brut."""
    path = CONFIG_DIR / filename
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def sauvegarder_yaml(filename: str, data: dict) -> Path:
    """Écrit data dans config/filename avec backup .bak daté.

    Écriture atomique : backup avant écriture, safe_dump sans sort_keys.
    Retourne le chemin du fichier écrit.
    """
    path = CONFIG_DIR / filename

    # Créer backup daté si le fichier existe
    if path.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak_path = path.with_suffix(f".{ts}.bak")
        shutil.copy2(path, bak_path)

    # Écriture atomique via fichier temporaire
    tmp_path = path.with_suffix(".tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True, default_flow_style=False)
        tmp_path.replace(path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise

    return path


def diff_yaml(ancien: dict, nouveau: dict) -> str:
    """Retourne un diff unified entre deux états YAML."""
    import difflib

    ancien_str = yaml.safe_dump(ancien, sort_keys=False, allow_unicode=True)
    nouveau_str = yaml.safe_dump(nouveau, sort_keys=False, allow_unicode=True)

    diff = list(
        difflib.unified_diff(
            ancien_str.splitlines(keepends=True),
            nouveau_str.splitlines(keepends=True),
            fromfile="avant",
            tofile="après",
        )
    )
    return "".join(diff)


def importer_csv(content: str | bytes, colonnes_attendues: list[str] | None = None) -> list[dict]:
    """Parse un CSV (séparateur ';', encodage utf-8-sig) et retourne une liste de dicts."""
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(content), delimiter=";")
    rows = list(reader)

    if colonnes_attendues:
        for col in colonnes_attendues:
            if col not in (reader.fieldnames or []):
                raise ValueError(f"Colonne manquante dans le CSV : '{col}'")

    return rows
