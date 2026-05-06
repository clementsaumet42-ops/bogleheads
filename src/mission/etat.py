"""State machine d'une mission EC avec persistance JSON sur disque."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Répertoire de persistance (relatif à la racine du projet)
_DEFAULT_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "missions"


class EtatEtape(Enum):
    NON_COMMENCE = "⬜"
    EN_COURS = "🟡"
    VALIDE = "✅"
    BLOQUE = "🔴"
    SKIP = "⏭️"


@dataclass
class EtatMission:
    mission_id: str
    nom_client: str
    conseiller: str
    date_creation: date
    date_derniere_maj: date
    etapes: dict[str, EtatEtape]
    chemin_persistance: Path
    notes: dict[str, str] = field(default_factory=dict)
    # S18-A : snapshot de session_state pour auto-save (rétro-compatible)
    session_state_snapshot: dict[str, Any] | None = field(default=None)
    # S20 : imports patrimoine depuis PDF (rétro-compatible)
    imports_patrimoine: list[dict[str, Any]] = field(default_factory=list)

    def ajouter_import(self, import_pdf: Any) -> None:
        """Ajoute un ImportPDF à la liste des imports (S20)."""
        if hasattr(import_pdf, "model_dump"):
            self.imports_patrimoine.append(import_pdf.model_dump())
        else:
            self.imports_patrimoine.append(dict(import_pdf))

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "mission_id": self.mission_id,
            "nom_client": self.nom_client,
            "conseiller": self.conseiller,
            "date_creation": self.date_creation.isoformat(),
            "date_derniere_maj": self.date_derniere_maj.isoformat(),
            "etapes": {k: v.value for k, v in self.etapes.items()},
            "notes": self.notes,
        }
        if self.session_state_snapshot is not None:
            d["session_state_snapshot"] = self.session_state_snapshot
        if self.imports_patrimoine:
            d["imports_patrimoine"] = self.imports_patrimoine
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any], chemin: Path) -> EtatMission:
        etapes = {k: EtatEtape(v) for k, v in data.get("etapes", {}).items()}
        return cls(
            mission_id=data["mission_id"],
            nom_client=data["nom_client"],
            conseiller=data.get("conseiller")
            or data.get("cgp", ""),  # "cgp" : rétro-compat missions S16
            date_creation=date.fromisoformat(data["date_creation"]),
            date_derniere_maj=date.fromisoformat(data["date_derniere_maj"]),
            etapes=etapes,
            chemin_persistance=chemin,
            notes=data.get("notes", {}),
            session_state_snapshot=data.get("session_state_snapshot"),
            imports_patrimoine=data.get("imports_patrimoine", []),
        )


def _data_dir() -> Path:
    """Retourne le répertoire de persistance (créé si absent)."""
    _DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DEFAULT_DATA_DIR


def _mission_path(mission_id: str) -> Path:
    """Retourne le chemin sécurisé pour un mission_id.

    Lève ValueError si mission_id tente une traversée de répertoire.
    """
    data = _data_dir()
    chemin = (data / f"{mission_id}.json").resolve()
    if not chemin.is_relative_to(data.resolve()):
        raise ValueError(f"mission_id invalide (traversée de répertoire) : {mission_id!r}")
    return data / f"{mission_id}.json"


def _slug(text: str) -> str:
    """Transforme un texte en slug ASCII safe."""
    text = text.lower().strip()
    text = re.sub(r"[àâä]", "a", text)
    text = re.sub(r"[éèêë]", "e", text)
    text = re.sub(r"[îï]", "i", text)
    text = re.sub(r"[ôö]", "o", text)
    text = re.sub(r"[ùûü]", "u", text)
    text = re.sub(r"[ç]", "c", text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")
    return text


def _etapes_initiales() -> dict[str, EtatEtape]:
    """Retourne le dictionnaire d'étapes avec toutes les étapes à NON_COMMENCE."""
    from src.mission.checklist import ETAPES_CANONIQUES

    return {etape.cle: EtatEtape.NON_COMMENCE for etape in ETAPES_CANONIQUES}


def creer_mission(nom_client: str, conseiller: str) -> EtatMission:
    """Crée une nouvelle mission et la persiste."""
    today = date.today()
    base = f"{_slug(nom_client)}_{today.year}_{today.month:02d}"
    mission_id = base

    # Gestion des doublons
    chemin = _mission_path(mission_id)
    compteur = 1
    while chemin.exists():
        mission_id = f"{base}_{compteur}"
        chemin = _mission_path(mission_id)
        compteur += 1

    etat = EtatMission(
        mission_id=mission_id,
        nom_client=nom_client,
        conseiller=conseiller,
        date_creation=today,
        date_derniere_maj=today,
        etapes=_etapes_initiales(),
        chemin_persistance=chemin,
        notes={},
    )
    sauvegarder_mission(etat)
    return etat


def sauvegarder_mission(etat: EtatMission) -> None:
    """Persiste la mission sur disque (JSON)."""
    etat.date_derniere_maj = date.today()
    etat.chemin_persistance.parent.mkdir(parents=True, exist_ok=True)
    etat.chemin_persistance.write_text(
        json.dumps(etat.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.debug("Mission %s sauvegardée.", etat.mission_id)


def charger_mission(mission_id: str) -> EtatMission:
    """Charge une mission depuis son JSON."""
    chemin = _mission_path(mission_id)
    if not chemin.exists():
        raise FileNotFoundError(f"Mission introuvable : {mission_id}")
    data = json.loads(chemin.read_text(encoding="utf-8"))
    return EtatMission.from_dict(data, chemin)


def lister_missions() -> list[EtatMission]:
    """Liste toutes les missions persistées."""
    missions: list[EtatMission] = []
    for fichier in sorted(_data_dir().glob("*.json")):
        try:
            data = json.loads(fichier.read_text(encoding="utf-8"))
            missions.append(EtatMission.from_dict(data, fichier))
        except Exception as exc:
            logger.warning("Impossible de charger %s : %s", fichier, exc)
    return missions


def supprimer_mission(mission_id: str) -> None:
    """Supprime une mission du disque."""
    chemin = _mission_path(mission_id)
    if chemin.exists():
        chemin.unlink()
        logger.info("Mission %s supprimée.", mission_id)
