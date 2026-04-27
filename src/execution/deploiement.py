"""Sprint S15 Lot C — Plan de déploiement.

Décide du rythme d'investissement (lump sum / DCA / hybride)
et de la séquence d'enveloppes, avec calendrier mois par mois.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ─── Seuils et règles métier ──────────────────────────────────────────────────

_SEUIL_LUMP_SUM_EUR = 50_000  # capital < 50k€ → lump sum
_SEUIL_DCA_EUR = 100_000  # capital ≥ 100k€ → DCA possible
_DUREE_DCA_MOIS_COURT = 6  # DCA court (profil agressif)
_DUREE_DCA_MOIS_LONG = 12  # DCA long (profil prudent)
_DUREE_HYBRIDE_MOIS = 6  # DCA de la tranche DCA en mode hybride
_PART_LUMP_HYBRIDE = 0.50  # 50% lump sum en mode hybride
_TMI_PER_SEUIL = 0.30  # TMI ≥ 30% → PER prioritaire


# Séquence d'enveloppes par défaut (modifiable par override)
_SEQUENCE_DEFAUT = ["PEA", "PER", "AV", "CTO"]

_PROFILS_PRUDENTS = {"prudent", "conservateur", "défensif", "defensif"}
_PROFILS_EQUILIBRES = {"équilibré", "equilibre", "modéré", "modere", "balanced"}
_PROFILS_DYNAMIQUES = {"dynamique", "croissance", "offensif", "agressif"}


def _determiner_mode(
    capital_total: float,
    profil: str,
    horizon_annees: int,
    duree_mois_override: int | None = None,
    mode_override: str | None = None,
) -> tuple[str, int]:
    """
    Détermine le mode de déploiement et la durée en mois.

    Returns
    -------
    (mode, duree_mois)
        mode : "lump_sum" | "DCA" | "hybride"
        duree_mois : durée du DCA (0 si lump sum)
    """
    if mode_override is not None:
        mode_override_norm = mode_override.lower().strip()
        if mode_override_norm in ("lump", "lump_sum"):
            return "lump_sum", 0
        if mode_override_norm in ("dca",):
            duree = duree_mois_override or _DUREE_DCA_MOIS_LONG
            return "DCA", duree
        if mode_override_norm in ("hybride", "hybrid"):
            duree = duree_mois_override or _DUREE_HYBRIDE_MOIS
            return "hybride", duree

    profil_norm = (profil or "").lower().strip()

    # Règle 1 : capital faible ou horizon long → lump sum
    if capital_total < _SEUIL_LUMP_SUM_EUR or horizon_annees > 15:
        if duree_mois_override:
            return "DCA", duree_mois_override
        return "lump_sum", 0

    # Règle 2 : capital élevé + profil prudent/équilibré → DCA
    if capital_total >= _SEUIL_DCA_EUR and profil_norm in _PROFILS_PRUDENTS | _PROFILS_EQUILIBRES:
        duree = duree_mois_override or _DUREE_DCA_MOIS_LONG
        return "DCA", duree

    # Règle 3 : profil prudent même avec capital moyen → DCA court
    if profil_norm in _PROFILS_PRUDENTS and capital_total >= _SEUIL_DCA_EUR:
        duree = duree_mois_override or _DUREE_DCA_MOIS_LONG
        return "DCA", duree

    # Règle 4 : profil intermédiaire avec capital moyen → hybride
    if capital_total >= _SEUIL_DCA_EUR and profil_norm in _PROFILS_EQUILIBRES:
        duree = duree_mois_override or _DUREE_HYBRIDE_MOIS
        return "hybride", duree

    # Défaut : lump sum si profil dynamique ou capital entre 50k€ et 100k€
    if duree_mois_override:
        return "DCA", duree_mois_override
    return "lump_sum", 0


def _sequence_enveloppes(
    enveloppes_disponibles: list[str],
    tmi: float = 0.0,
    age: int = 40,
) -> list[str]:
    """
    Calcule la séquence d'enveloppes optimale.

    Règles :
    1. PEA en premier (horloge fiscale 5 ans)
    2. PER si TMI ≥ 30% (optimisation IR)
    3. AV (succession + long terme)
    4. CTO en dernier

    Parameters
    ----------
    enveloppes_disponibles : list[str]
        Enveloppes disponibles pour ce client.
    tmi : float
        Tranche marginale d'imposition (ex 0.30 pour 30%).
    age : int
        Âge du client.
    """
    disponibles = {e.upper() for e in enveloppes_disponibles}
    sequence: list[str] = []

    # 1. PEA en premier
    if "PEA" in disponibles:
        sequence.append("PEA")

    # 2. PER si TMI ≥ 30%
    if "PER" in disponibles and tmi >= _TMI_PER_SEUIL:
        sequence.append("PER")

    # 3. AV
    if "AV" in disponibles:
        sequence.append("AV")

    # 4. PER si pas encore ajouté (TMI < 30%)
    if "PER" in disponibles and "PER" not in sequence:
        sequence.append("PER")

    # 5. CTO en dernier
    if "CTO" in disponibles:
        sequence.append("CTO")

    # Ajouter les autres enveloppes non traitées
    for env in enveloppes_disponibles:
        env_up = env.upper()
        if env_up not in sequence:
            sequence.append(env_up)

    return sequence


def _generer_tranches(
    capital_total: float,
    mode: str,
    duree_mois: int,
    sequence_enveloppes: list[str],
) -> list[dict]:
    """
    Génère les tranches d'investissement mois par mois.

    Returns
    -------
    list[dict]
        Chaque tranche : {mois, enveloppe, montant_eur, justification}.
    """
    tranches: list[dict] = []
    n_env = max(1, len(sequence_enveloppes))

    if mode == "lump_sum":
        # Tout en une fois, distribuée par enveloppe
        montant_par_env = capital_total / n_env
        for _i, env in enumerate(sequence_enveloppes):
            tranches.append(
                {
                    "mois": 0,
                    "enveloppe": env,
                    "montant_eur": round(montant_par_env, 2),
                    "justification": f"Lump sum — déploiement immédiat enveloppe {env}",
                }
            )

    elif mode == "DCA":
        montant_mensuel_total = capital_total / max(1, duree_mois)
        montant_par_env = montant_mensuel_total / n_env
        for mois in range(duree_mois):
            for env in sequence_enveloppes:
                tranches.append(
                    {
                        "mois": mois,
                        "enveloppe": env,
                        "montant_eur": round(montant_par_env, 2),
                        "justification": (
                            f"DCA mois {mois + 1}/{duree_mois} — "
                            f"lissage du risque de marché sur {duree_mois} mois"
                        ),
                    }
                )

    elif mode == "hybride":
        capital_lump = capital_total * _PART_LUMP_HYBRIDE
        capital_dca = capital_total - capital_lump
        # Tranche lump sum immédiate
        lump_par_env = capital_lump / n_env
        for env in sequence_enveloppes:
            tranches.append(
                {
                    "mois": 0,
                    "enveloppe": env,
                    "montant_eur": round(lump_par_env, 2),
                    "justification": f"Hybride — tranche initiale 50% lump sum ({env})",
                }
            )
        # Tranches DCA pour la partie restante
        mois_dca = max(1, duree_mois)
        dca_mensuel_par_env = capital_dca / (mois_dca * n_env)
        for mois in range(mois_dca):
            for env in sequence_enveloppes:
                tranches.append(
                    {
                        "mois": mois + 1,
                        "enveloppe": env,
                        "montant_eur": round(dca_mensuel_par_env, 2),
                        "justification": (
                            f"Hybride — DCA 50% restant, mois {mois + 1}/{mois_dca} ({env})"
                        ),
                    }
                )

    return tranches


def plan_deploiement(
    capital_total: float,
    profil: str,
    horizon_annees: int,
    age: int,
    rfr: float,
    enveloppes_disponibles: list[str],
    duree_mois_override: int | None = None,
    mode_override: str | None = None,
) -> dict:
    """
    Calcule le plan de déploiement optimal.

    Parameters
    ----------
    capital_total : float
        Capital total à investir en €.
    profil : str
        Profil de risque : "prudent" | "équilibré" | "dynamique" | etc.
    horizon_annees : int
        Horizon d'investissement en années.
    age : int
        Âge du client.
    rfr : float
        Revenu fiscal de référence annuel en €.
    enveloppes_disponibles : list[str]
        Enveloppes disponibles : ["PEA", "AV", "CTO", "PER"…].
    duree_mois_override : int | None
        Durée DCA imposée par l'utilisateur.
    mode_override : str | None
        Mode imposé : "lump_sum" | "DCA" | "hybride".

    Returns
    -------
    dict
        {
            'mode': 'DCA' | 'lump_sum' | 'hybride',
            'duree_mois': int,
            'sequence_enveloppes': list[str],
            'tranches': list[dict],
        }
    """
    # TMI estimée depuis le RFR (approximation simplifiée France 2026)
    tmi = _estimer_tmi(rfr)

    mode, duree_mois = _determiner_mode(
        capital_total, profil, horizon_annees, duree_mois_override, mode_override
    )
    sequence = _sequence_enveloppes(enveloppes_disponibles, tmi, age)
    tranches = _generer_tranches(capital_total, mode, duree_mois, sequence)

    return {
        "mode": mode,
        "duree_mois": duree_mois,
        "sequence_enveloppes": sequence,
        "tranches": tranches,
    }


def _estimer_tmi(rfr: float) -> float:
    """Estime la TMI à partir du revenu fiscal de référence (barème 2026 simplifié)."""
    if rfr <= 11_294:
        return 0.0
    if rfr <= 28_797:
        return 0.11
    if rfr <= 82_341:
        return 0.30
    if rfr <= 177_106:
        return 0.41
    return 0.45
