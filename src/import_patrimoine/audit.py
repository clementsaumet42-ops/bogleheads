"""Journal d'audit append-only pour les imports patrimoine."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from src.import_patrimoine.modele import ImportPDF

logger = logging.getLogger(__name__)

_DEFAULT_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "missions"


def _audit_path(mission_id: str) -> Path:
    """Retourne le chemin du fichier audit pour une mission."""
    data = _DEFAULT_DATA_DIR / mission_id
    data.mkdir(parents=True, exist_ok=True)
    return data / "audit.json"


def enregistrer_import(mission_id: str, import_pdf: ImportPDF) -> None:
    """Enregistre un import PDF dans le journal d'audit de la mission (append-only)."""
    chemin = _audit_path(mission_id)
    entrees: list[dict] = []
    if chemin.exists():
        try:
            entrees = json.loads(chemin.read_text(encoding="utf-8"))
        except Exception:
            entrees = []

    entrees.append(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "import": import_pdf.model_dump(),
        }
    )
    chemin.write_text(json.dumps(entrees, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.debug("Audit import enregistré pour mission %s.", mission_id)


def lire_audit(mission_id: str) -> list[dict]:
    """Lit le journal d'audit d'une mission. Retourne liste vide si absent."""
    chemin = _audit_path(mission_id)
    if not chemin.exists():
        return []
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Impossible de lire l'audit %s : %s", chemin, exc)
        return []
