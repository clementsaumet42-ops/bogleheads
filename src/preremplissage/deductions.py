"""Module S18-B — Règles de déduction pour le préremplissage intelligent."""

from __future__ import annotations

# ─── Règle 1 : TMI suggéré ───────────────────────────────────────────────────


def deduire_tmi(
    revenu_net_annuel: float,
    situation: str = "celibataire",
    nb_enfants: int = 0,
) -> float:
    """Déduit la TMI estimée depuis le revenu net annuel et la situation familiale.

    Utilise le barème IR 2026 de src.fiscalite.tmi (pas de duplication).

    Args:
        revenu_net_annuel: Salaire net annuel en €.
        situation: "celibataire" ou "couple".
        nb_enfants: Nombre d'enfants à charge.

    Returns:
        TMI estimée (0.0, 0.11, 0.30, 0.41, 0.45).
    """
    from src.fiscalite.tmi import calculer_parts_fiscales, calculer_tmi

    if revenu_net_annuel <= 0:
        return 0.0

    # Approximation : revenu imposable ≈ 90% du revenu net (abattement 10% frais réels)
    revenu_imposable = revenu_net_annuel * 0.90
    parts = calculer_parts_fiscales(situation, nb_enfants)
    return calculer_tmi(revenu_imposable, parts)


# ─── Règle 2 : Profil risque selon âge + horizon ─────────────────────────────

# Mapping âge → profil risque (règle 100-âge adaptée)
_PROFILS_PAR_AGE = [
    (30, "dynamique"),
    (50, "equilibre"),
    (65, "prudent"),
]
_PROFIL_SENIOR = "conservateur"


def deduire_profil_risque(age: int, horizon_annees: int | None = None) -> str:
    """Déduit le profil de risque selon l'âge (règle 100-âge).

    Bornes :
    - < 30 ans → dynamique
    - 30–50 ans → équilibré
    - 50–65 ans → prudent
    - > 65 ans → conservateur

    Si horizon_annees est fourni, peut affiner vers prudent pour horizon court.

    Args:
        age: Âge du client en années.
        horizon_annees: Horizon d'investissement en années (optionnel).

    Returns:
        Profil de risque parmi : "dynamique", "equilibre", "prudent", "conservateur".
    """
    profil_age = _PROFIL_SENIOR
    for seuil, profil in _PROFILS_PAR_AGE:
        if age < seuil:
            profil_age = profil
            break

    # Affinage par horizon : si horizon < 5 ans → au moins prudent
    if horizon_annees is not None and horizon_annees < 5:
        ordre = ["conservateur", "prudent", "equilibre", "dynamique"]
        idx_age = ordre.index(profil_age) if profil_age in ordre else 0
        idx_horizon = ordre.index("prudent")
        profil_age = ordre[min(idx_age, idx_horizon)]

    return profil_age


# ─── Règle 3 : Allocation cible pré-calculée ─────────────────────────────────


def deduire_allocation_cible(
    profil_risque: str,
    horizon_annees: int | None = None,
) -> dict[str, float]:
    """Renvoie une allocation cible indicative selon le profil risque.

    Allocation basée sur la règle 100-âge adaptée par profil :
    - dynamique : 80% actions / 10% obligations / 10% liquidités
    - equilibre : 60% actions / 30% obligations / 10% liquidités
    - prudent : 40% actions / 45% obligations / 15% liquidités
    - conservateur : 20% actions / 55% obligations / 25% liquidités

    L'horizon peut légèrement réduire la part actions.

    Args:
        profil_risque: Profil parmi dynamique/equilibre/prudent/conservateur.
        horizon_annees: Horizon d'investissement (optionnel, affinage glide path).

    Returns:
        Dictionnaire {classe: poids} summing to 1.0.
    """
    _ALLOCATIONS_BASE: dict[str, dict[str, float]] = {
        "dynamique": {"actions": 0.80, "obligations": 0.10, "liquidites": 0.10},
        "equilibre": {"actions": 0.60, "obligations": 0.30, "liquidites": 0.10},
        "prudent": {"actions": 0.40, "obligations": 0.45, "liquidites": 0.15},
        "conservateur": {"actions": 0.20, "obligations": 0.55, "liquidites": 0.25},
    }

    alloc = dict(_ALLOCATIONS_BASE.get(profil_risque, _ALLOCATIONS_BASE["equilibre"]))

    # Affinage par horizon court : réduire actions si horizon < 3 ans
    if horizon_annees is not None and horizon_annees < 3:
        reduction = min(alloc["actions"] * 0.3, 0.20)
        alloc["actions"] -= reduction
        alloc["liquidites"] += reduction

    # Normalisation pour sommer à 1.0
    total = sum(alloc.values())
    if total > 0:
        alloc = {k: round(v / total, 4) for k, v in alloc.items()}

    return alloc


# ─── Règle 4 : Espérance de vie depuis tables INSEE ──────────────────────────

# Tables simplifiées INSEE 2023 (espérance de vie résiduelle à l'âge x)
_ESPERANCE_VIE_HOMME: dict[int, float] = {
    0: 80.0,
    20: 61.0,
    30: 51.3,
    40: 41.8,
    50: 32.6,
    60: 23.8,
    65: 19.6,
    70: 15.7,
    75: 12.1,
    80: 9.0,
    85: 6.5,
    90: 4.6,
}

_ESPERANCE_VIE_FEMME: dict[int, float] = {
    0: 85.7,
    20: 66.4,
    30: 56.6,
    40: 46.9,
    50: 37.4,
    60: 28.1,
    65: 23.6,
    70: 19.2,
    75: 15.1,
    80: 11.5,
    85: 8.4,
    90: 6.0,
}


def deduire_esperance_vie(age: int, sexe: str = "homme") -> float:
    """Estime l'espérance de vie résiduelle selon âge et sexe (tables INSEE).

    Args:
        age: Âge du client en années.
        sexe: "homme" ou "femme".

    Returns:
        Espérance de vie résiduelle en années.
    """
    table = _ESPERANCE_VIE_FEMME if sexe.lower() in ("femme", "f") else _ESPERANCE_VIE_HOMME

    # Interpolation linéaire entre les deux âges de référence les plus proches
    ages_ref = sorted(table.keys())
    if age <= ages_ref[0]:
        return table[ages_ref[0]]
    if age >= ages_ref[-1]:
        return table[ages_ref[-1]]

    # Trouver les deux bornes
    for i, a in enumerate(ages_ref[:-1]):
        a_sup = ages_ref[i + 1]
        if a <= age <= a_sup:
            t = (age - a) / (a_sup - a)
            return round(table[a] + t * (table[a_sup] - table[a]), 1)

    return table[ages_ref[-1]]
