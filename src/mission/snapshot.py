"""Génération et vérification des snapshots SHA-256 de mission.

Chaque mission est associée à un hash SHA-256 calculé sur l'ensemble
des fichiers du dossier mission au moment de la signature.
"""

from __future__ import annotations

from pathlib import Path


def calculer_snapshot(chemin_dossier: Path) -> str:
    """Calcule le SHA-256 agrégé d'un dossier mission. À implémenter S+1."""
    raise NotImplementedError("Sprint S+1")


def verifier_snapshot(chemin_dossier: Path, snapshot_attendu: str) -> bool:
    """Vérifie l'intégrité d'un dossier mission via son snapshot. À implémenter S+1."""
    raise NotImplementedError("Sprint S+1")
