from __future__ import annotations

import logging
from .base import Alerte, Severite, regle

logger = logging.getLogger(__name__)


@regle("R25", famille="Épargne salariale")
def detecter_R25(profil) -> Alerte | None:
    """Fondement : Code du travail art. L3334-1 — PEE/PERCO disponible non alimenté."""
    try:
        a_pee = getattr(profil, "a_pee", None)
        a_perco = getattr(profil, "a_perco", None)

        if a_pee is None and a_perco is None:
            return None
        if not (a_pee or a_perco):
            return None

        composition = getattr(profil, "composition_actuelle", None) or []
        has_invested = any(
            "PEE" in str(getattr(l, "enveloppe", "") if not isinstance(l, dict) else l.get("enveloppe", "")).upper()
            or "PERCO" in str(getattr(l, "enveloppe", "") if not isinstance(l, dict) else l.get("enveloppe", "")).upper()
            for l in composition
        )
        if has_invested:
            return None

        return Alerte(
            code="R25",
            famille="Épargne salariale",
            severite=Severite.ROUGE,
            titre="PEE/PERCO disponible non alimenté",
            description=(
                "Votre entreprise propose un PEE/PERCO mais vous ne l'utilisez pas. "
                "C'est une opportunité d'épargne défiscalisée (exonération IR sur les sommes bloquées 5 ans)."
            ),
            gain_eur_annuel=None,
            gain_eur_horizon=None,
            action_concrete="Contacter le service RH pour souscrire au PEE/PERCO et effectuer un premier versement.",
            sources=["Code du travail art. L3334-1", "CGI art. 163 bis AA"],
        )
    except Exception as e:
        logger.info(f"R25 skip: {e}")
        return None


@regle("R26", famille="Épargne salariale")
def detecter_R26(profil) -> Alerte | None:
    """Fondement : AMF recommandation — PEE surconcentré en actions de l'entreprise."""
    try:
        pee_pct = getattr(profil, "pee_actions_entreprise_pct", None)
        if pee_pct is None or pee_pct <= 0.33:
            return None

        return Alerte(
            code="R26",
            famille="Épargne salariale",
            severite=Severite.ROUGE,
            titre=f"PEE investi à {pee_pct:.0%} en actions de l'entreprise",
            description=(
                f"Investir plus de 33% de son PEE en actions de son propre employeur crée un double risque : "
                "si l'entreprise fait faillite, vous perdez emploi ET épargne."
            ),
            gain_eur_annuel=None,
            gain_eur_horizon=None,
            action_concrete="Diversifier le PEE vers des fonds diversifiés (ETF monde, oblig) et réduire la part actions employeur sous 20%.",
            sources=["AMF recommandation diversification PEE"],
        )
    except Exception as e:
        logger.info(f"R26 skip: {e}")
        return None


@regle("R27", famille="Épargne salariale")
def detecter_R27(profil) -> Alerte | None:
    """Fondement : Code du travail art. L3332-11 — abondement employeur non maxé."""
    try:
        abondement_max = getattr(profil, "abondement_employeur_max", None)
        if abondement_max is None or abondement_max <= 0:
            return None

        abondement_actuel = getattr(profil, "abondement_employeur_actuel", None) or 0.0
        if abondement_actuel >= abondement_max * 0.95:
            return None

        manque = abondement_max - abondement_actuel
        return Alerte(
            code="R27",
            famille="Épargne salariale",
            severite=Severite.ROUGE,
            titre=f"Abondement employeur non maxé ({manque:,.0f} €/an non capté)",
            description=(
                f"Votre employeur abonde jusqu'à {abondement_max:,.0f} €/an. "
                f"Vous ne captez que {abondement_actuel:,.0f} € soit {manque:,.0f} € de salaire déguisé manqués."
            ),
            gain_eur_annuel=round(manque, 0),
            gain_eur_horizon=round(manque * 20, 0),
            action_concrete=f"Augmenter vos versements PEE pour atteindre le seuil déclenchant l'abondement maximal de {abondement_max:,.0f} €.",
            sources=["Code du travail art. L3332-11"],
        )
    except Exception as e:
        logger.info(f"R27 skip: {e}")
        return None


@regle("R28", famille="Épargne salariale")
def detecter_R28(profil) -> Alerte | None:
    """Fondement : CGI art. 163 bis AA — participation/intéressement imposable si non versé sur PEE."""
    try:
        participation_versee_pee = getattr(profil, "participation_versee_pee", None)
        if participation_versee_pee is True or participation_versee_pee is None:
            return None

        tmi = getattr(profil, "tmi", 0) or 0
        if tmi <= 0:
            return None

        return Alerte(
            code="R28",
            famille="Épargne salariale",
            severite=Severite.JAUNE,
            titre="Participation/intéressement non versé sur PEE — imposition évitable",
            description=(
                f"La participation/intéressement versée directement est imposable à TMI {tmi:.0%}. "
                "Versée sur PEE, elle est exonérée d'IR (seules les cotisations sociales s'appliquent)."
            ),
            gain_eur_annuel=None,
            gain_eur_horizon=None,
            action_concrete="Demander le versement de la participation/intéressement sur le PEE plutôt que le paiement direct.",
            sources=["CGI art. 163 bis AA", "Code du travail art. L3314-1"],
        )
    except Exception as e:
        logger.info(f"R28 skip: {e}")
        return None
