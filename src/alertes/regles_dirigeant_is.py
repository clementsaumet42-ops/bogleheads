"""Filtre les alertes pertinentes pour dirigeants IS parmi les 40 règles existantes.

Les 12 règles retenues sont documentées dans REGLES_RETENUES.md.
"""

from __future__ import annotations

# Identifiants des 12 règles dirigeant IS retenues (voir REGLES_RETENUES.md)
REGLES_DIRIGEANT_IS = frozenset(
    [
        "piege_mtm_opcvm_is",
        "contrat_cap_is_alternatif",
        "plafond_pea_atteint",
        "pea_eligible_sortie",
        "av_8ans_abattement",
        "cehr_tranche_superieure",
        "tlh_opportunite",
        "apport_cession_eligible",
        "holding_tresorerie_excedentaire",
        "is_taux_reduit_eligible",
        "liquidites_non_optimisees",
        "der_a_renouveler",
    ]
)


def filtrer_alertes_dirigeant_is(alertes: list[dict]) -> list[dict]:
    """Filtre les alertes pertinentes pour un dirigeant IS.

    Parameters
    ----------
    alertes : list[dict]
        Liste complète des alertes générées par le moteur (jusqu'à 40).

    Returns
    -------
    list[dict]
        Sous-ensemble des 12 règles dirigeant IS.
    """
    return [a for a in alertes if a.get("regle_id") in REGLES_DIRIGEANT_IS]
