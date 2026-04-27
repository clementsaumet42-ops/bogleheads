"""Module hypothèses traçables — Sprint S17.

Fournit le registre central des hypothèses utilisées dans le tool,
avec sources citées, versionnage et snapshot figé par mission.
"""

from src.hypotheses.catalogue import (
    charger_catalogue,
    get_hypothese,
    lister_hypotheses_par_categorie,
)
from src.hypotheses.snapshot import (
    SnapshotHypotheses,
    charger_snapshot,
    creer_snapshot,
    lister_snapshots,
    sauvegarder_snapshot,
)
from src.hypotheses.source import Hypothese, Source
from src.hypotheses.versionnage import comparer_snapshots

__all__ = [
    "Source",
    "Hypothese",
    "charger_catalogue",
    "get_hypothese",
    "lister_hypotheses_par_categorie",
    "SnapshotHypotheses",
    "creer_snapshot",
    "sauvegarder_snapshot",
    "charger_snapshot",
    "lister_snapshots",
    "comparer_snapshots",
]
