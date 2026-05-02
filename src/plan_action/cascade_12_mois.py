"""Shim — réexporte src.rebalancement_optimal pour le plan d'action 12 mois."""

from __future__ import annotations

from src.rebalancement_optimal import (
    PlanRebalancement,
    optimiser_rebalancement,
)

__all__ = [
    "PlanRebalancement",
    "optimiser_rebalancement",
]
