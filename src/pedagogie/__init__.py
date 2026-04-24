"""Package src.pedagogie — Moteur d'explications pédagogiques Boglehead FR.

API publique :
    from src.pedagogie import (
        Explication,
        expliquer_allocation,
        expliquer_choix_etf,
        expliquer_ter,
        expliquer_asset_location,
        expliquer_cascade_fiscale,
        expliquer_plan_rebalancement,
        expliquer_convergence_3_prismes,
        expliquer_prismes_detail,
        charger_scripts_restitution,
        rendre_script,
    )
"""

from __future__ import annotations

from src.pedagogie.allocation import expliquer_allocation
from src.pedagogie.asset_location import expliquer_asset_location
from src.pedagogie.base import Explication
from src.pedagogie.etf import expliquer_choix_etf, expliquer_ter
from src.pedagogie.fiscalite import expliquer_cascade_fiscale
from src.pedagogie.profilage import expliquer_convergence_3_prismes, expliquer_prismes_detail
from src.pedagogie.rebalancement import expliquer_plan_rebalancement
from src.pedagogie.scripts import charger_scripts_restitution, rendre_script

__all__ = [
    "Explication",
    "expliquer_allocation",
    "expliquer_choix_etf",
    "expliquer_ter",
    "expliquer_asset_location",
    "expliquer_cascade_fiscale",
    "expliquer_plan_rebalancement",
    "expliquer_convergence_3_prismes",
    "expliquer_prismes_detail",
    "charger_scripts_restitution",
    "rendre_script",
]
