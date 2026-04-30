"""Shim — réexporte src.cif.der et src.cif.lettre_mission."""

from __future__ import annotations

from src.cif.der import generer_der
from src.cif.lettre_mission import generer_lettre_mission

__all__ = [
    "generer_der",
    "generer_lettre_mission",
]
