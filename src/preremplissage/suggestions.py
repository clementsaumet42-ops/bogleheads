"""Module S18-B — API unifiée de suggestions pour les pages Streamlit.

Chaque suggestion est toujours marquée 💡 et rendue modifiable.
Jamais d'imposition silencieuse.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.preremplissage.deductions import (
    deduire_allocation_cible,
    deduire_esperance_vie,
    deduire_profil_risque,
    deduire_tmi,
)


@dataclass
class Suggestion:
    """Représente une suggestion de préremplissage affichable dans une page."""

    cle: str
    valeur: Any
    label: str
    message: str  # Texte affiché avec 💡
    modifiable: bool = True


def suggerer_tmi(
    revenu_net_annuel: float,
    situation: str = "celibataire",
    nb_enfants: int = 0,
) -> Suggestion:
    """Suggère la TMI estimée depuis le revenu net et la situation familiale.

    Args:
        revenu_net_annuel: Salaire net annuel en €.
        situation: "celibataire" ou "couple".
        nb_enfants: Nombre d'enfants à charge.

    Returns:
        Suggestion avec tmi (float 0–1) et message explicatif.
    """
    tmi = deduire_tmi(revenu_net_annuel, situation, nb_enfants)
    tmi_pct = int(tmi * 100)
    return Suggestion(
        cle="tmi",
        valeur=tmi,
        label="TMI estimée",
        message=f"💡 TMI estimée à {tmi_pct}% — modifiable",
        modifiable=True,
    )


def suggerer_profil_risque(age: int, horizon_annees: int | None = None) -> Suggestion:
    """Suggère un profil de risque selon l'âge et l'horizon.

    Args:
        age: Âge du client.
        horizon_annees: Horizon d'investissement (optionnel).

    Returns:
        Suggestion avec le profil risque (str) et message explicatif.
    """
    profil = deduire_profil_risque(age, horizon_annees)
    msg = f"💡 Profil risque suggéré : {profil} (règle 100-âge, âge={age}"
    if horizon_annees is not None:
        msg += f", horizon={horizon_annees} ans"
    msg += ") — modifiable"
    return Suggestion(
        cle="profil_risque",
        valeur=profil,
        label="Profil risque suggéré",
        message=msg,
        modifiable=True,
    )


def suggerer_allocation_cible(
    profil_risque: str,
    horizon_annees: int | None = None,
) -> Suggestion:
    """Suggère une allocation cible pré-calculée.

    Args:
        profil_risque: Profil risque du client.
        horizon_annees: Horizon d'investissement (optionnel).

    Returns:
        Suggestion avec l'allocation (dict) et message explicatif.
    """
    alloc = deduire_allocation_cible(profil_risque, horizon_annees)
    actions_pct = int(alloc.get("actions", 0) * 100)
    return Suggestion(
        cle="allocation_cible",
        valeur=alloc,
        label="Allocation cible pré-calculée",
        message=f"💡 Allocation pré-calculée — {actions_pct}% actions — vous pouvez l'ajuster",
        modifiable=True,
    )


def suggerer_esperance_vie(age: int, sexe: str = "homme") -> Suggestion:
    """Suggère l'espérance de vie résiduelle depuis les tables INSEE.

    Args:
        age: Âge du client.
        sexe: "homme" ou "femme".

    Returns:
        Suggestion avec l'espérance de vie (float, années) et message.
    """
    ev = deduire_esperance_vie(age, sexe)
    return Suggestion(
        cle="esperance_vie",
        valeur=ev,
        label="Espérance de vie résiduelle (tables INSEE)",
        message=f"💡 Espérance de vie résiduelle estimée : {ev} ans (tables INSEE 2023) — modifiable",
        modifiable=True,
    )
