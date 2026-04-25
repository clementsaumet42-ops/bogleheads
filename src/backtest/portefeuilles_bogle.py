"""Définition des portefeuilles Bogle canoniques adaptés au contexte EUR/français."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class PortefeuilleBogle(BaseModel):
    nom: str
    description: str
    source: str
    allocations: dict[str, float]
    rebalancement_periodicite: Literal["annuel", "trimestriel"] = "annuel"
    seuil_rebalancement_pct: float = 0.05

    @model_validator(mode="after")
    def valider_allocations(self) -> "PortefeuilleBogle":
        total = sum(self.allocations.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"La somme des allocations doit être 1.0, obtenu {total:.6f}")
        for k, v in self.allocations.items():
            if not (0.0 <= v <= 1.0):
                raise ValueError(f"Poids hors [0,1] pour '{k}': {v}")
        return self


BOGLE_2_FUNDS_70_30 = PortefeuilleBogle(
    nom="BOGLE_2_FUNDS_70_30",
    description="Two-fund portfolio Boglehead : 70% actions monde développé + 30% obligations euro agrégat",
    source="https://www.bogleheads.org/wiki/Three-fund_portfolio",
    allocations={
        "actions_monde_developpe": 0.70,
        "obligations_euro_agg": 0.30,
    },
)

BOGLE_3_FUNDS_60_30_10 = PortefeuilleBogle(
    nom="BOGLE_3_FUNDS_60_30_10",
    description="Three-fund portfolio Boglehead : 60% World + 30% Euro Agg + 10% Emerging Markets",
    source="https://www.bogleheads.org/wiki/Three-fund_portfolio",
    allocations={
        "actions_monde_developpe": 0.60,
        "obligations_euro_agg": 0.30,
        "actions_emergents": 0.10,
    },
)

BOGLE_4_FUNDS = PortefeuilleBogle(
    nom="BOGLE_4_FUNDS",
    description="Four-fund portfolio variante française : 50% World + 20% EM + 20% Euro Agg + 10% Inflation Linked",
    source="https://www.bogleheads.org/wiki/Three-fund_portfolio",
    allocations={
        "actions_monde_developpe": 0.50,
        "actions_emergents": 0.20,
        "obligations_euro_agg": 0.20,
        "obligations_inflation_eur": 0.10,
    },
)

LAZY_PERMANENT_PORTFOLIO = PortefeuilleBogle(
    nom="LAZY_PERMANENT_PORTFOLIO",
    description="Permanent Portfolio de Harry Browne : 25% actions + 25% obligations LT + 25% cash + 25% or",
    source="Harry Browne, Fail-Safe Investing, 1999",
    allocations={
        "actions_monde_developpe": 0.25,
        "obligations_euro_souveraines": 0.25,
        "cash_eur": 0.25,
        "or": 0.25,
    },
)

ALL_WEATHER_RAY_DALIO = PortefeuilleBogle(
    nom="ALL_WEATHER_RAY_DALIO",
    description="All Weather de Ray Dalio : 30% actions + 40% obligations LT + 15% obligations IT + 7.5% matières premières + 7.5% or",
    source="Ray Dalio, Principles, 2017 (Bridgewater All Weather)",
    allocations={
        "actions_monde_developpe": 0.30,
        "obligations_euro_souveraines": 0.40,
        "obligations_euro_agg": 0.15,
        "matieres_premieres": 0.075,
        "or": 0.075,
    },
)

PORTEFEUILLES_DISPONIBLES: dict[str, PortefeuilleBogle] = {
    "BOGLE_2_FUNDS_70_30": BOGLE_2_FUNDS_70_30,
    "BOGLE_3_FUNDS_60_30_10": BOGLE_3_FUNDS_60_30_10,
    "BOGLE_4_FUNDS": BOGLE_4_FUNDS,
    "LAZY_PERMANENT_PORTFOLIO": LAZY_PERMANENT_PORTFOLIO,
    "ALL_WEATHER_RAY_DALIO": ALL_WEATHER_RAY_DALIO,
}
