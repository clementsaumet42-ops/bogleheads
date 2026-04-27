"""Snapshot figé des hypothèses actives au moment d'une mission — Sprint S17."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.hypotheses.catalogue import _get_catalogue
from src.hypotheses.source import Hypothese

logger = logging.getLogger(__name__)

_DEFAULT_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "missions"


def _hypothese_to_dict(h: Hypothese) -> dict[str, Any]:
    """Sérialise une Hypothese en dict JSON-compatible."""
    d: dict[str, Any] = {
        "cle": h.cle,
        "valeur": h.valeur,
        "unite": h.unite,
        "description": h.description,
        "version": h.version,
        "confiance": h.confiance,
        "categorie": h.categorie,
        "date_validite_debut": h.date_validite_debut.isoformat(),
        "date_validite_fin": h.date_validite_fin.isoformat() if h.date_validite_fin else None,
        "commentaire_methodologique": h.commentaire_methodologique,
        "sources": [
            {
                "nom": s.nom,
                "organisme": s.organisme,
                "url": s.url,
                "date_publication": s.date_publication.isoformat(),
                "date_consultation": s.date_consultation.isoformat(),
                "type_source": s.type_source,
                "extrait": s.extrait,
            }
            for s in h.sources
        ],
    }
    return d


@dataclass
class SnapshotHypotheses:
    """Instantané figé des hypothèses actives au moment de la génération d'un livrable."""

    mission_id: str
    date_snapshot: datetime
    hypotheses: dict[str, Hypothese]  # copie figée
    hash_integrite: str  # SHA256 du contenu sérialisé

    def to_dict(self) -> dict[str, Any]:
        hyps_serial = {cle: _hypothese_to_dict(h) for cle, h in self.hypotheses.items()}
        return {
            "mission_id": self.mission_id,
            "date_snapshot": self.date_snapshot.isoformat(),
            "hypotheses": hyps_serial,
            "hash_integrite": self.hash_integrite,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SnapshotHypotheses:
        from src.hypotheses.source import Hypothese, Source

        hypotheses: dict[str, Hypothese] = {}
        for cle, hd in data.get("hypotheses", {}).items():
            sources = tuple(
                Source(
                    nom=s["nom"],
                    organisme=s["organisme"],
                    url=s.get("url"),
                    date_publication=date.fromisoformat(s["date_publication"]),
                    date_consultation=date.fromisoformat(s["date_consultation"]),
                    type_source=s.get("type_source", "interne"),
                    extrait=s.get("extrait"),
                )
                for s in hd.get("sources", [])
            )
            dvd = hd.get("date_validite_debut")
            dvf = hd.get("date_validite_fin")
            hypotheses[cle] = Hypothese(
                cle=cle,
                valeur=hd["valeur"],
                unite=hd.get("unite", ""),
                description=hd.get("description", ""),
                sources=sources,
                date_validite_debut=date.fromisoformat(dvd) if dvd else date(2026, 1, 1),
                date_validite_fin=date.fromisoformat(dvf) if dvf else None,
                version=str(hd.get("version", "2026.1")),
                confiance=hd.get("confiance", "consensus"),
                categorie=hd.get("categorie", "autres"),
                commentaire_methodologique=hd.get("commentaire_methodologique"),
            )
        return cls(
            mission_id=data["mission_id"],
            date_snapshot=datetime.fromisoformat(data["date_snapshot"]),
            hypotheses=hypotheses,
            hash_integrite=data["hash_integrite"],
        )


def _calculer_hash(hypotheses: dict[str, Hypothese]) -> str:
    """Calcule un SHA256 déterministe sur le contenu des hypothèses."""
    serial = {cle: _hypothese_to_dict(h) for cle, h in sorted(hypotheses.items())}
    contenu = json.dumps(serial, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(contenu.encode("utf-8")).hexdigest()


def creer_snapshot(mission_id: str) -> SnapshotHypotheses:
    """Fige un snapshot de toutes les hypothèses actives pour la mission."""
    hypotheses = dict(_get_catalogue())
    hash_integrite = _calculer_hash(hypotheses)
    return SnapshotHypotheses(
        mission_id=mission_id,
        date_snapshot=datetime.now(),
        hypotheses=hypotheses,
        hash_integrite=hash_integrite,
    )


def sauvegarder_snapshot(snapshot: SnapshotHypotheses) -> Path:
    """Persiste le snapshot dans data/missions/{mission_id}/snapshots/{YYYYMMDD-HHMMSS}.json."""
    ts = snapshot.date_snapshot.strftime("%Y%m%d-%H%M%S")
    dossier = _DEFAULT_DATA_DIR / snapshot.mission_id / "snapshots"
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"{ts}.json"
    chemin.write_text(
        json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.debug("Snapshot sauvegardé : %s", chemin)
    return chemin


def charger_snapshot(mission_id: str, dt: datetime | None = None) -> SnapshotHypotheses:
    """Charge le snapshot le plus récent (ou celui le plus proche de `dt`)."""
    dossier = _DEFAULT_DATA_DIR / mission_id / "snapshots"
    if not dossier.exists():
        raise FileNotFoundError(f"Aucun snapshot trouvé pour la mission : {mission_id}")
    fichiers = sorted(dossier.glob("*.json"))
    if not fichiers:
        raise FileNotFoundError(f"Aucun fichier snapshot dans : {dossier}")

    if dt is None:
        chemin = fichiers[-1]  # le plus récent
    else:
        # le plus proche par date
        ts_cible = dt.timestamp()
        chemin = min(
            fichiers,
            key=lambda f: abs(
                datetime.fromisoformat(f.stem.replace("-", "T", 1).replace("-", ":")).timestamp()
                - ts_cible
            ),
        )
    data = json.loads(chemin.read_text(encoding="utf-8"))
    return SnapshotHypotheses.from_dict(data)


def lister_snapshots(mission_id: str) -> list[Path]:
    """Liste les chemins de tous les snapshots d'une mission, triés chronologiquement."""
    dossier = _DEFAULT_DATA_DIR / mission_id / "snapshots"
    if not dossier.exists():
        return []
    return sorted(dossier.glob("*.json"))
