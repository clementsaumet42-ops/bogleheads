"""Registre central des hypothèses — chargement depuis config/hypotheses.yaml."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import yaml

from src.hypotheses.source import Hypothese, Source

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path(__file__).parent.parent.parent / "config" / "hypotheses.yaml"

# Cache module-level — rechargé si on appelle charger_catalogue() explicitement
_CATALOGUE_CACHE: dict[str, Hypothese] | None = None


def _parse_source(raw: dict) -> Source:
    return Source(
        nom=raw.get("nom", ""),
        organisme=raw.get("organisme", ""),
        url=raw.get("url"),
        date_publication=date.fromisoformat(str(raw["date_publication"])),
        date_consultation=date.fromisoformat(str(raw["date_consultation"])),
        type_source=raw.get("type_source", "interne"),
        extrait=raw.get("extrait"),
    )


def _parse_hypothese(cle: str, raw: dict) -> Hypothese:
    sources = tuple(_parse_source(s) for s in raw.get("sources", []))
    dvd = raw.get("date_validite_debut")
    dvf = raw.get("date_validite_fin")
    return Hypothese(
        cle=cle,
        valeur=raw["valeur"],
        unite=raw.get("unite", ""),
        description=raw.get("description", ""),
        sources=sources,
        date_validite_debut=date.fromisoformat(str(dvd)) if dvd else date(2026, 1, 1),
        date_validite_fin=date.fromisoformat(str(dvf)) if dvf else None,
        version=str(raw.get("version", "2026.1")),
        confiance=raw.get("confiance", "consensus"),
        categorie=raw.get("categorie", "autres"),
        commentaire_methodologique=raw.get("commentaire_methodologique"),
    )


def charger_catalogue(path: Path | None = None) -> dict[str, Hypothese]:
    """Lit config/hypotheses.yaml et retourne {cle: Hypothese}."""
    global _CATALOGUE_CACHE
    chemin = path or _DEFAULT_PATH
    with open(chemin, encoding="utf-8") as f:
        raw_yaml = yaml.safe_load(f)
    catalogue: dict[str, Hypothese] = {}
    for cle, val in raw_yaml.get("hypotheses", {}).items():
        try:
            catalogue[cle] = _parse_hypothese(cle, val)
        except Exception as exc:
            logger.warning("Hypothèse '%s' ignorée (erreur parsing) : %s", cle, exc)
    # N'invalide le cache global que pour le chemin par défaut
    if path is None or chemin == _DEFAULT_PATH:
        _CATALOGUE_CACHE = catalogue
    return catalogue


def _get_catalogue() -> dict[str, Hypothese]:
    """Retourne le catalogue (chargé depuis le cache ou depuis le YAML)."""
    global _CATALOGUE_CACHE
    if _CATALOGUE_CACHE is None:
        charger_catalogue()
    return _CATALOGUE_CACHE or {}


def get_hypothese(cle: str, *, reference_date: date | None = None) -> Hypothese:
    """Renvoie l'hypothèse active à la date donnée (aujourd'hui par défaut).

    Lève KeyError si la clé est inconnue.
    Lève ValueError si l'hypothèse n'est pas valide à la date donnée.
    """
    catalogue = _get_catalogue()
    if cle not in catalogue:
        raise KeyError(
            f"Hypothèse inconnue : '{cle}'. Clés disponibles : {sorted(catalogue.keys())}"
        )
    hyp = catalogue[cle]
    today = reference_date or date.today()
    if today < hyp.date_validite_debut:
        raise ValueError(
            f"Hypothèse '{cle}' pas encore valide au {today} (début : {hyp.date_validite_debut})"
        )
    if hyp.date_validite_fin and today > hyp.date_validite_fin:
        raise ValueError(f"Hypothèse '{cle}' expirée au {today} (fin : {hyp.date_validite_fin})")
    return hyp


def lister_hypotheses_par_categorie(
    path: Path | None = None,
) -> dict[str, list[Hypothese]]:
    """Retourne les hypothèses groupées par catégorie."""
    catalogue = charger_catalogue(path) if path else _get_catalogue()
    result: dict[str, list[Hypothese]] = {}
    for hyp in catalogue.values():
        result.setdefault(hyp.categorie, []).append(hyp)
    return result
