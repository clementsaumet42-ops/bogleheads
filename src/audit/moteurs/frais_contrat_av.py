"""Moteur 4 — Frais contrat assurance-vie (S8.2b).

Si le client détient une AV avec frais UC élevés (> 0.80%/an typiquement),
identifie les contrats du marché qui ont des frais UC ≥ 30 bps inférieurs
et donnent accès aux mêmes ETF.

Règles métier :
- Seuil de différence de frais : ≥ 30 bps (0.003)
- Complexité systématiquement = "elevee" (transfert AV = contrainte fiscale)
- But : documenter le coût d'opportunité, pas pousser au churn
- Contrainte fiscale : transfert AV taxant les plus-values si pré-2017
  (sauf transfert Fourgous vers fonds euros, ou isolation interne)
- Top 3 candidats retournés
"""

from __future__ import annotations

import logging

from src.audit.moteurs._constantes import (
    SEUIL_DIFF_FRAIS_AV,
    TAUX_ACTUALISATION_DEFAUT,
)
from src.audit.opportunite import Opportunite, capitaliser_30_ans
from src.schemas import ContratAV

logger = logging.getLogger(__name__)

_SOURCES = [
    "config/contrats_av.yaml — données S8.2a",
    "art. 125-0 A CGI — Fiscalité assurance-vie",
    "Instruction fiscale BOI-RPPM-RCM-20-10-20-60 — transfert AV",
]

TOP_N_CANDIDATS = 3


def detecter_opportunites_frais_av(
    contrat_actuel: ContratAV,
    montant_av_actuel_eur: float,
    versements_annuels_attendus_eur: float,
    contrats_marche: list[ContratAV],
) -> list[Opportunite]:
    """Identifie les contrats AV moins chers que le contrat actuel du client.

    1. Pour chaque contrat marché : si frais_uc < contrat_actuel.frais_uc - 0.003, candidat.
    2. Calcule gain_annuel = montant_av × (frais_actuel - frais_candidat).
    3. Marque les contraintes fiscales et la complexité élevée.
    4. Retourne top-3 candidats par gain décroissant.

    Note : l'objectif est de documenter le coût d'opportunité, pas de pousser
    au churn AV. Le client et l'EC doivent évaluer les contraintes fiscales
    et temporelles avant toute décision.

    Args:
        contrat_actuel: contrat AV actuel du client.
        montant_av_actuel_eur: encours total de l'AV actuelle.
        versements_annuels_attendus_eur: versements programmés/an prévus.
        contrats_marche: liste des contrats du marché (depuis contrats_av.yaml).

    Returns:
        Liste d'Opportunite (max TOP_N_CANDIDATS) triée par gain décroissant.
    """
    if montant_av_actuel_eur <= 0:
        logger.warning("montant_av_actuel_eur <= 0 — aucune opportunité calculable")
        return []

    frais_actuel = contrat_actuel.frais_gestion_uc_pct
    opportunites: list[Opportunite] = []

    for candidat in contrats_marche:
        if candidat.id == contrat_actuel.id:
            continue

        frais_candidat = candidat.frais_gestion_uc_pct
        diff_frais = frais_actuel - frais_candidat

        if diff_frais < SEUIL_DIFF_FRAIS_AV:
            continue

        # Vérifier versement minimum compatible
        if (
            versements_annuels_attendus_eur > 0
            and candidat.versement_programme_min_eur > versements_annuels_attendus_eur
        ):
            logger.debug(
                "Candidat %s : versement_programme_min=%s > %s attendu — skip",
                candidat.id,
                candidat.versement_programme_min_eur,
                versements_annuels_attendus_eur,
            )
            continue

        gain_annuel_eur = montant_av_actuel_eur * diff_frais
        gain_30ans = capitaliser_30_ans(gain_annuel_eur, TAUX_ACTUALISATION_DEFAUT)
        gain_bps = diff_frais * 10_000

        contraintes = [
            "Complexité élevée : transfert AV = acte juridique avec conseiller",
            "Contrainte fiscale : rachat partiel/total taxé si plus-value (PFU 30% ou option barème)",
            "Exception : transfert Fourgous (UC → fonds euros même assureur) neutre fiscalement",
            "Exception : transfert PACTE (depuis 2020) entre assureurs avec neutralité fiscale si >8 ans",
            f"Versement minimum nouveau contrat : {candidat.versement_minimum_eur:,.0f} €",
        ]

        note_ec = (
            f"Gain modélisé à hypothèses constantes ({frais_actuel * 100:.2f}% → {frais_candidat * 100:.2f}%, "
            f"encours stable {montant_av_actuel_eur:,.0f}€). "
            f"À comparer au coût fiscal immédiat du rachat si applicable. "
            f"Outil : ne pas recommander de racheter sans analyse complète de la situation fiscale."
        )

        opp = Opportunite(
            id=f"av.frais_contrat.{contrat_actuel.id}_vers_{candidat.id}",
            levier="frais_contrat_av",
            titre=(
                f"Transférer AV {contrat_actuel.nom} → {candidat.nom} "
                f"(-{diff_frais * 10000:.0f}bps frais UC)"
            ),
            gain_annuel_bps=round(gain_bps, 2),
            gain_annuel_eur=round(gain_annuel_eur, 2),
            gain_30ans_eur=round(gain_30ans, 0),
            montant_concerne_eur=montant_av_actuel_eur,
            avant={
                "contrat_id": contrat_actuel.id,
                "contrat_nom": contrat_actuel.nom,
                "frais_gestion_uc_pct": frais_actuel,
                "frais_annuels_eur": round(montant_av_actuel_eur * frais_actuel, 2),
                "nb_etf": contrat_actuel.nb_etf,
            },
            apres={
                "contrat_id": candidat.id,
                "contrat_nom": candidat.nom,
                "frais_gestion_uc_pct": frais_candidat,
                "frais_annuels_eur": round(montant_av_actuel_eur * frais_candidat, 2),
                "nb_etf": candidat.nb_etf,
            },
            formule=(
                f"gain_annuel = montant_av × (frais_actuel - frais_candidat) "
                f"= {montant_av_actuel_eur:,.0f}€ × {diff_frais:.4f} = {gain_annuel_eur:,.0f}€/an"
            ),
            sources=_SOURCES,
            complexite="elevee",
            delai_mise_en_oeuvre_jours=90,
            contraintes=contraintes,
            confiance="haute",
            note_ec=note_ec,
        )
        opportunites.append(opp)

    # Trier par gain décroissant, retourner top-3
    opportunites.sort(key=lambda o: o.gain_30ans_eur, reverse=True)
    return opportunites[:TOP_N_CANDIDATS]
