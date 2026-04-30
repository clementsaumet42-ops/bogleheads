"""Saisie manuelle du patrimoine holding/SCI/SCPI.

Permet la saisie structurée des actifs détenus en société IS
(holding, SCI, SCPI) lorsque les relevés PDF ne sont pas disponibles.
"""

from __future__ import annotations


def saisir_actifs_holding(nom_societe: str, siren: str) -> dict:
    """Saisit les actifs d'une holding IS. À implémenter S+1."""
    raise NotImplementedError("Sprint S+1")


def saisir_sci(nom_sci: str, parts: float) -> dict:
    """Saisit une SCI avec quote-part. À implémenter S+1."""
    raise NotImplementedError("Sprint S+1")
