"""Moteur de decumulation fiscal-optimal.

Sequence les retraits sur les enveloppes (PEA, AV, CTO, PER, PEE) pour
generer un besoin annuel NET en minimisant la friction fiscale.

Phase de scope post-VISION (extension persona client retraite HNW).
Reste 100% local, traceable, defendable.
"""

from src.decumulation.optimiseur_retraits import (
    EnveloppeDecumulation,
    PlanDecumulation,
    Retrait,
    optimiser_retraits_annuels,
)
from src.decumulation.regles_enveloppes import (
    cout_marginal_retrait,
    fiscalite_retrait,
)
from src.decumulation.simulateur_annuel import (
    ProjectionDecumulation,
    simuler_decumulation,
)

__all__ = [
    "EnveloppeDecumulation",
    "Retrait",
    "PlanDecumulation",
    "optimiser_retraits_annuels",
    "cout_marginal_retrait",
    "fiscalite_retrait",
    "ProjectionDecumulation",
    "simuler_decumulation",
]
