from __future__ import annotations

import logging

from . import (  # noqa: F401
    allocation,
    bonus,
    configuration,
    credit,
    epargne_salariale,
    fiscalite,
    frais,
    hygiene,
    liquidite,
    transmission,
)
from .base import _REGISTRY, Alerte, Severite

logger = logging.getLogger(__name__)

_SEVERITE_ORDER = {Severite.ROUGE: 0, Severite.JAUNE: 1, Severite.VERT: 2}


def detecter_alertes(profil) -> list[Alerte]:
    """Évalue les 40 règles S12 et retourne les alertes déclenchées, triées par priorité."""
    alertes = []
    for code, _famille, fn in _REGISTRY:
        try:
            alerte = fn(profil)
            if alerte is not None:
                alertes.append(alerte)
        except Exception as e:
            logger.info(f"[alertes] Règle {code} skipée: {e}")

    alertes.sort(
        key=lambda a: (
            _SEVERITE_ORDER[a.severite],
            -(a.gain_eur_horizon or 0),
            a.code,
        )
    )
    return alertes


__all__ = ["Alerte", "Severite", "detecter_alertes"]
