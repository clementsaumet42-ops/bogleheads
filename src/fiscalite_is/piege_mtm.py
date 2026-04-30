"""Shim — détection du piège mark-to-market IS (Art. 209-0 A CGI).

Réexporte depuis src.fiscalite.cto_is.
"""

from __future__ import annotations

from src.fiscalite.cto_is import detecter_piege_mtm

__all__ = ["detecter_piege_mtm"]
