"""
Module enveloppes fiscales — règles métier
"""

from pathlib import Path

import yaml


def charger_enveloppes(chemin_yaml: str = None) -> list:
    """Charge les enveloppes depuis le fichier YAML."""
    if chemin_yaml is None:
        chemin_yaml = Path(__file__).parent.parent / "config" / "enveloppes.yaml"
    with open(chemin_yaml, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["enveloppes"]


def get_enveloppe_par_id(enveloppes: list, id_enveloppe: str) -> dict | None:
    """Retourne une enveloppe par son id."""
    for env in enveloppes:
        if env["id"] == id_enveloppe:
            return env
    return None


def verifier_eligibilite_etf(etf: dict, enveloppe_id: str) -> bool:
    """Vérifie si un ETF est éligible à une enveloppe donnée."""
    return etf.get("eligibilite", {}).get(enveloppe_id, False)


def calculer_plafond_restant(enveloppe: dict, encours_actuel: float) -> float | None:
    """Calcule le plafond restant pour une enveloppe (None si pas de plafond)."""
    plafond = enveloppe.get("plafond")
    if plafond is None:
        return None
    return max(0.0, plafond - encours_actuel)
