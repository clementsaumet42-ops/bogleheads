"""Shim de rétro-compatibilité — src/optimiseur_allocation.py.

Ce module est déplacé vers src/allocation/asset_location_milp.py.
Ce shim réexporte toute l'API publique pour ne pas casser les imports existants.
"""

from src.allocation.asset_location_milp import *  # noqa: F401, F403
from src.allocation.asset_location_milp import (
    CLASSES_ACTIONS,
    CLASSES_OBLIGATIONS,
    _construire_matrice_covariance,
    _fallback_allocation_mode_a,
    _fallback_asset_location,
    calculer_allocation_cible,
    charger_config_optimiseur,
    optimiser_allocation_mode_a,
    optimiser_asset_location_mode_b,
    optimiser_portefeuille_complet,
)

__all__ = [
    "CLASSES_ACTIONS",
    "CLASSES_OBLIGATIONS",
    "_construire_matrice_covariance",
    "_fallback_allocation_mode_a",
    "_fallback_asset_location",
    "calculer_allocation_cible",
    "charger_config_optimiseur",
    "optimiser_allocation_mode_a",
    "optimiser_asset_location_mode_b",
    "optimiser_portefeuille_complet",
]
