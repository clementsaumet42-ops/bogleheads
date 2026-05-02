"""Shim — contrat de capitalisation IS comme alternative au CTO IS.

Réexporte depuis src.fiscalite.contrat_cap_is.
"""

from __future__ import annotations

from src.fiscalite.contrat_cap_is import (
    calculer_base_taxable_contrat_cap_is,
    calculer_is_contrat_cap,
    comparer_contrat_cap_vs_mtm,
)

__all__ = [
    "calculer_base_taxable_contrat_cap_is",
    "calculer_is_contrat_cap",
    "comparer_contrat_cap_vs_mtm",
]
