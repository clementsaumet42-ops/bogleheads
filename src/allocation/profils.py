"""
Module allocation cible Boglehead
"""

from pathlib import Path

import yaml


def charger_profils(chemin_yaml: str = None) -> dict:
    """Charge les profils clients depuis le fichier YAML."""
    if chemin_yaml is None:
        chemin_yaml = Path(__file__).parent.parent.parent / "config" / "profils_clients.yaml"
    with open(chemin_yaml, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_profil_par_id(profils_data: dict, profil_id: int) -> dict:
    """Retourne un profil par son id."""
    for profil in profils_data["profils"]:
        if profil["id"] == profil_id:
            return profil
    raise ValueError(f"Profil {profil_id} non trouvé")


def valider_allocation(allocation: dict) -> bool:
    """
    Valide que l'allocation cible somme à 100%.
    Ignore les clés 'commentaire' et les clés préfixées par '_'.
    """
    valeurs = {k: v for k, v in allocation.items() if k != "commentaire" and not k.startswith("_")}
    total = sum(valeurs.values())
    return abs(total - 1.0) < 0.001


def allocation_bogleheads_par_age(age: int) -> dict:
    """
    Règle d'allocation Boglehead simplifiée basée sur l'âge.
    Règle heuristique : % obligations ≈ clip((age-10)/100, 5%, 60%).
    Somme garantie = 1.0.
    """
    pct_obligations = max(0.05, min(0.60, (age - 10) / 100))
    pct_or = 0.05
    pct_immo = 0.05
    pct_liquidites = 0.05
    pct_actions = 1.0 - (pct_obligations + pct_or + pct_immo + pct_liquidites)

    total = pct_actions + pct_obligations + pct_immo + pct_or + pct_liquidites
    assert abs(total - 1.0) < 1e-9, f"Invariant violé : total={total}"

    return {
        "actions": round(pct_actions, 3),
        "obligations": round(pct_obligations, 3),
        "immobilier_cote": round(pct_immo, 3),
        "or": round(pct_or, 3),
        "liquidites": round(pct_liquidites, 3),
        "_commentaire": f"Allocation automatique basée sur l'âge ({age} ans)",
    }
