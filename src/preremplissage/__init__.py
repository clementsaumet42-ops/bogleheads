"""Module S18-B — Préremplissage intelligent."""

from src.preremplissage.deductions import (
    deduire_allocation_cible,
    deduire_esperance_vie,
    deduire_profil_risque,
    deduire_tmi,
)
from src.preremplissage.suggestions import (
    Suggestion,
    suggerer_allocation_cible,
    suggerer_esperance_vie,
    suggerer_profil_risque,
    suggerer_tmi,
)

__all__ = [
    "deduire_tmi",
    "deduire_profil_risque",
    "deduire_allocation_cible",
    "deduire_esperance_vie",
    "Suggestion",
    "suggerer_tmi",
    "suggerer_profil_risque",
    "suggerer_allocation_cible",
    "suggerer_esperance_vie",
]
