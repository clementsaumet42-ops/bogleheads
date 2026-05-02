"""Calendrier trimestriel d'exécution du plan d'action.

Découpe le plan de rebalancement en 4 fenêtres trimestrielles
avec prise en compte des contraintes fiscales IS (clôture exercice,
acomptes IS, règle des 12 jours de coupon couru).
"""

from __future__ import annotations


def generer_calendrier(plan: dict, date_debut_iso: str) -> list[dict]:
    """Génère le calendrier trimestriel. À implémenter S+1."""
    raise NotImplementedError("Sprint S+1")
