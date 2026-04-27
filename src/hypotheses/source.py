"""Modèles de données pour les sources et hypothèses traçables — Sprint S17."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Source:
    """Référence bibliographique ou réglementaire citée pour une hypothèse."""

    nom: str  # "AMF — Étude rendements 2024"
    organisme: str  # "Autorité des marchés financiers"
    url: str | None  # lien si dispo
    date_publication: date
    date_consultation: date  # quand on l'a regardée
    type_source: str  # "etude" | "publication_legale" | "interne" | "consensus_marche"
    extrait: str | None  # citation ou phrase extraite


@dataclass(frozen=True)
class Hypothese:
    """Hypothèse métier versionnable, traçable et auditée."""

    cle: str  # "rendement_actions_monde"
    valeur: float | int | str
    unite: str  # "%/an" | "années" | "€" | "ratio"
    description: str  # une phrase pédagogique
    sources: tuple[Source, ...]
    date_validite_debut: date
    date_validite_fin: date | None
    version: str  # "2026.1"
    confiance: str  # "haute" | "moyenne" | "consensus"
    categorie: str  # "rendements" | "fiscalite" | "demographie" | "inflation" | "frais"
    commentaire_methodologique: str | None = None
