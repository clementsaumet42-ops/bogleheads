"""Modélisation des frais pour le backtest."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ConfigFrais(BaseModel):
    ter_par_classe: dict[str, float] = Field(default_factory=dict)
    courtage_par_ordre_eur: float = Field(default=1.0, ge=0)
    spread_bps: float = Field(default=5.0, ge=0)
    frais_enveloppe_annuel_pct: dict[str, float] = Field(default_factory=dict)


def appliquer_ter_mensuel(valeur: float, ter_annuel: float) -> float:
    """Applique le TER annuel sur une période mensuelle.

    valeur_après = valeur × (1 - ter_annuel)^(1/12)
    """
    return valeur * (1 - ter_annuel) ** (1 / 12)


def appliquer_frais_transaction(montant: float, config: ConfigFrais) -> float:
    """Applique les frais de transaction (courtage + spread) sur un montant."""
    spread_cost = montant * config.spread_bps / 10_000
    return montant - config.courtage_par_ordre_eur - spread_cost
