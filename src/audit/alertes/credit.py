from __future__ import annotations

import logging
from .base import Alerte, Severite, regle

logger = logging.getLogger(__name__)

_TAUX_MARCHE_IMMO_REF = 0.038  # taux marché immobilier référence — à réviser annuellement


@regle("R29", famille="Crédit & cash")
def detecter_R29(profil) -> Alerte | None:
    """Fondement : Code de la consommation art. L312-1 — crédit conso TAEG > 5%."""
    try:
        taeg_conso = getattr(profil, "taeg_credits_conso", None)
        solde_conso = getattr(profil, "solde_credit_conso", None)

        if taeg_conso is None or solde_conso is None:
            return None
        if taeg_conso <= 0.05 or solde_conso <= 0:
            return None

        epargne = getattr(profil, "epargne_precaution", 0) or 0
        if epargne < 30000 and epargne < solde_conso:
            return None

        gain = solde_conso * (taeg_conso - 0.02)
        return Alerte(
            code="R29",
            famille="Crédit & cash",
            severite=Severite.ROUGE,
            titre=f"Crédit conso TAEG {taeg_conso:.1%} avec cash disponible",
            description=(
                f"Vous portez un crédit consommation à {taeg_conso:.1%} TAEG alors que vous avez du cash disponible. "
                f"Rembourser ce crédit de {solde_conso:,.0f} € économise {gain:,.0f} €/an."
            ),
            gain_eur_annuel=round(gain, 0),
            gain_eur_horizon=round(gain * 3, 0),
            action_concrete="Rembourser le crédit consommation par anticipation avec les liquidités disponibles.",
            sources=["Code de la consommation art. L312-1"],
        )
    except Exception as e:
        logger.info(f"R29 skip: {e}")
        return None


@regle("R30", famille="Crédit & cash")
def detecter_R30(profil) -> Alerte | None:
    """Fondement : Banque de France, taux immobiliers — renégociation crédit immo."""
    try:
        taeg_immo = getattr(profil, "taeg_credit_immo", None)
        capital_restant = getattr(profil, "capital_restant_immo", None)

        if taeg_immo is None or capital_restant is None:
            return None
        if taeg_immo <= _TAUX_MARCHE_IMMO_REF + 0.01 or capital_restant <= 0:
            return None

        gain = capital_restant * (taeg_immo - _TAUX_MARCHE_IMMO_REF)
        return Alerte(
            code="R30",
            famille="Crédit & cash",
            severite=Severite.JAUNE,
            titre=f"Crédit immo TAEG {taeg_immo:.1%} renégociable",
            description=(
                f"Votre crédit immo est à {taeg_immo:.1%} alors que le taux marché est ~{_TAUX_MARCHE_IMMO_REF:.1%}. "
                f"Sur {capital_restant:,.0f} € restants, la renégociation économise ~{gain:,.0f} €/an."
            ),
            gain_eur_annuel=round(gain, 0),
            gain_eur_horizon=round(gain * 5, 0),
            action_concrete="Contacter votre banque ou un courtier (CAFPI, Meilleurtaux) pour renégocier ou racheter le crédit.",
            sources=["Banque de France, statistiques taux immobiliers"],
        )
    except Exception as e:
        logger.info(f"R30 skip: {e}")
        return None


@regle("R31", famille="Crédit & cash")
def detecter_R31(profil) -> Alerte | None:
    """Fondement : Code de la consommation — rachat de crédits multiples."""
    try:
        nb_credits_conso = getattr(profil, "nb_credits_conso", None)
        if nb_credits_conso is None or nb_credits_conso <= 1:
            return None

        return Alerte(
            code="R31",
            famille="Crédit & cash",
            severite=Severite.JAUNE,
            titre=f"Rachat de crédit envisageable ({nb_credits_conso} crédits conso)",
            description=(
                f"Vous avez {nb_credits_conso} crédits consommation. "
                "Un rachat de crédits peut réduire le TAEG moyen et simplifier la gestion."
            ),
            gain_eur_annuel=None,
            gain_eur_horizon=None,
            action_concrete="Consulter un courtier en rachat de crédits pour regrouper vos crédits à un taux inférieur.",
            sources=["Code de la consommation art. L313-1"],
        )
    except Exception as e:
        logger.info(f"R31 skip: {e}")
        return None
