"""Conversion profil MIF II → allocation cible standard.

4 allocations standards calibrées pour dirigeants IS :
- Défensif  : 40/60 (actions/obligations)
- Équilibré : 60/40
- Dynamique : 75/25
- Agressif  : 85/15
"""

from __future__ import annotations

ALLOCATIONS_STANDARD: dict[str, dict[str, float]] = {
    "defensif_40_60": {
        "actions_monde_developpe": 0.30,
        "actions_emergents": 0.10,
        "obligations_euro_agg": 0.45,
        "cash_eur": 0.15,
    },
    "equilibre_60_40": {
        "actions_monde_developpe": 0.45,
        "actions_emergents": 0.15,
        "obligations_euro_agg": 0.35,
        "cash_eur": 0.05,
    },
    "dynamique_75_25": {
        "actions_monde_developpe": 0.55,
        "actions_emergents": 0.20,
        "obligations_euro_agg": 0.20,
        "cash_eur": 0.05,
    },
    "agressif_85_15": {
        "actions_monde_developpe": 0.65,
        "actions_emergents": 0.20,
        "obligations_euro_agg": 0.10,
        "cash_eur": 0.05,
    },
}


def profil_vers_allocation(profil_risque: str) -> dict[str, float]:
    """Retourne l'allocation standard pour un profil MIF II. À implémenter S+1."""
    raise NotImplementedError("Sprint S+1")
