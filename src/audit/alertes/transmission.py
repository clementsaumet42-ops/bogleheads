from __future__ import annotations

import logging
from .base import Alerte, Severite, regle

logger = logging.getLogger(__name__)


@regle("R32", famille="Couple/famille")
def detecter_R32(profil) -> Alerte | None:
    """Fondement : Code des assurances art. L132-12 — clause bénéficiaire AV démembrée."""
    try:
        est_en_couple = getattr(profil, "est_en_couple", None)
        if not est_en_couple:
            return None

        clause_demembree = getattr(profil, "clause_beneficiaire_demembree", None)
        if clause_demembree is True:
            return None

        composition = getattr(profil, "composition_actuelle", None) or []
        has_av = any(
            "AV" in str(getattr(l, "enveloppe", "") if not isinstance(l, dict) else l.get("enveloppe", "")).upper()
            or "ASSURANCE" in str(getattr(l, "enveloppe", "") if not isinstance(l, dict) else l.get("enveloppe", "")).upper()
            for l in composition
        )
        if not has_av:
            return None

        return Alerte(
            code="R32",
            famille="Couple/famille",
            severite=Severite.JAUNE,
            titre="Clause bénéficiaire AV non démembrée pour couple",
            description=(
                "Pour un couple marié, la clause bénéficiaire démembrée (usufruit conjoint / nue-propriété enfants) "
                "optimise la transmission et réduit les droits de succession."
            ),
            gain_eur_annuel=None,
            gain_eur_horizon=None,
            action_concrete="Consulter un notaire pour mettre en place une clause bénéficiaire démembrée.",
            sources=["Code des assurances art. L132-12", "CGI art. 787 B"],
        )
    except Exception as e:
        logger.info(f"R32 skip: {e}")
        return None


@regle("R33", famille="Couple/famille")
def detecter_R33(profil) -> Alerte | None:
    """Fondement : CGI art. 787 B — testament pour patrimoine > 500k€."""
    try:
        patrimoine = getattr(profil, "patrimoine_financier_total", 0) or 0
        if patrimoine < 500000:
            return None

        a_testament = getattr(profil, "a_testament", None)
        if a_testament is True:
            return None

        return Alerte(
            code="R33",
            famille="Couple/famille",
            severite=Severite.JAUNE,
            titre=f"Testament absent pour patrimoine de {patrimoine:,.0f} €",
            description=(
                f"Avec {patrimoine:,.0f} € de patrimoine, l'absence de testament expose vos héritiers "
                "à des droits de succession non optimisés et à des conflits de partage."
            ),
            gain_eur_annuel=None,
            gain_eur_horizon=None,
            action_concrete="Consulter un notaire pour rédiger un testament et étudier le Pacte Dutreil si transmission d'entreprise.",
            sources=["CGI art. 787 B", "Code civil art. 895"],
        )
    except Exception as e:
        logger.info(f"R33 skip: {e}")
        return None


@regle("R34", famille="Couple/famille")
def detecter_R34(profil) -> Alerte | None:
    """Fondement : CGI art. 194 — quotient familial couple non optimisé."""
    try:
        est_en_couple = getattr(profil, "est_en_couple", None)
        if not est_en_couple:
            return None

        tmi = getattr(profil, "tmi", 0) or 0
        if tmi < 0.30:
            return None

        rfr = getattr(profil, "rfr_annuel", None)
        if rfr is None:
            return None

        return Alerte(
            code="R34",
            famille="Couple/famille",
            severite=Severite.VERT,
            titre="Vérifier l'optimisation IR couple (quotient familial)",
            description=(
                f"En couple à TMI {tmi:.0%}, vérifier l'optimisation du quotient familial : "
                "déclaration commune, répartition des revenus, charges déductibles."
            ),
            gain_eur_annuel=None,
            gain_eur_horizon=None,
            action_concrete="Consulter un expert-comptable pour optimiser la déclaration IR commune et le quotient familial.",
            sources=["CGI art. 194", "BOFiP IR - Quotient familial"],
        )
    except Exception as e:
        logger.info(f"R34 skip: {e}")
        return None
