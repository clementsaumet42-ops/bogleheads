"""
Module allocation cible Boglehead
"""
import yaml
from pathlib import Path


def charger_profils(chemin_yaml: str = None) -> dict:
    """Charge les profils clients depuis le fichier YAML."""
    if chemin_yaml is None:
        chemin_yaml = Path(__file__).parent.parent / "config" / "profils_clients.yaml"
    with open(chemin_yaml, "r", encoding="utf-8") as f:
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
    Ignore la clé 'commentaire'.
    """
    valeurs = {k: v for k, v in allocation.items() if k != "commentaire"}
    total = sum(valeurs.values())
    return abs(total - 1.0) < 0.001


def allocation_bogleheads_par_age(age: int) -> dict:
    """
    Règle d'allocation Boglehead simplifiée basée sur l'âge.
    Règle heuristique : % obligations ≈ age - 10 (à adapter selon profil risque).
    """
    pct_obligations = max(0.05, min(0.60, (age - 10) / 100))
    pct_actions = max(0.30, 1.0 - pct_obligations - 0.10)
    pct_or = 0.05
    pct_immo = 0.05
    pct_liquidites = max(0.02, 1.0 - pct_actions - pct_obligations - pct_or - pct_immo)

    # Normalisation
    total = pct_actions + pct_obligations + pct_immo + pct_or + pct_liquidites
    return {
        "actions": round(pct_actions / total, 3),
        "obligations": round(pct_obligations / total, 3),
        "immobilier_cote": round(pct_immo / total, 3),
        "or": round(pct_or / total, 3),
        "liquidites": round(pct_liquidites / total, 3),
        "commentaire": f"Allocation automatique basée sur l'âge ({age} ans)",
    }
