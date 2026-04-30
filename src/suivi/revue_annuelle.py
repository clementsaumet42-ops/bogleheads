"""Revue annuelle de mission — comparaison situation initiale vs actuelle.

Produit un rapport de suivi chiffrant :
- L'écart d'allocation par rapport à la cible
- Le delta fiscal réalisé vs estimé
- Les nouvelles alertes détectées
- Les recommandations de mise à jour
"""

from __future__ import annotations


def generer_revue_annuelle(mission_id: str, data_actuelle: dict) -> dict:
    """Génère la revue annuelle. À implémenter S+1."""
    raise NotImplementedError("Sprint S+1")
