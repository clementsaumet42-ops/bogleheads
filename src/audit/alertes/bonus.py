from __future__ import annotations

import logging
from .base import Alerte, Severite, regle

logger = logging.getLogger(__name__)


@regle("R36", famille="Bonus retenus")
def detecter_R36(profil) -> Alerte | None:
    """Fondement : CGI art. 163 quatervicies — déductibilité PER non utilisée au plafond."""
    try:
        plafond_per = getattr(profil, "plafond_per_non_utilise", None)
        if plafond_per is None or plafond_per <= 0:
            return None

        tmi = getattr(profil, "tmi", 0) or 0
        if tmi < 0.11:
            return None

        gain = plafond_per * tmi
        return Alerte(
            code="R36",
            famille="Bonus retenus",
            severite=Severite.VERT,
            titre=f"PER déductibilité non utilisée ({plafond_per:,.0f} € de plafond restant)",
            description=(
                f"Versement déductible PER restant : {plafond_per:,.0f} €. "
                f"À TMI {tmi:.0%}, l'économie d'impôt immédiate est de {gain:,.0f} €."
            ),
            gain_eur_annuel=round(gain, 0),
            gain_eur_horizon=round(gain * 3, 0),
            action_concrete="Effectuer un versement PER avant le 31/12 pour réduire l'IR de l'année en cours.",
            sources=["CGI art. 163 quatervicies", "BOFiP PER déductibilité"],
        )
    except Exception as e:
        logger.info(f"R36 skip: {e}")
        return None


@regle("R37", famille="Bonus retenus")
def detecter_R37(profil) -> Alerte | None:
    """Fondement : CGI art. 199 terdecies-0 A — réduction IR-PME (Madelin) non utilisée."""
    try:
        a_utilise_ir_pme = getattr(profil, "a_utilise_ir_pme", None)
        if a_utilise_ir_pme is True or a_utilise_ir_pme is None:
            return None

        tmi = getattr(profil, "tmi", 0) or 0
        if tmi < 0.30:
            return None

        gain = 10000 * 0.18
        return Alerte(
            code="R37",
            famille="Bonus retenus",
            severite=Severite.VERT,
            titre="Réduction IR-PME (Madelin) non utilisée",
            description=(
                f"L'investissement dans des PME via le dispositif Madelin permet une réduction d'IR de 18% "
                f"(plafond 10 000 €), soit {gain:,.0f} € d'économie."
            ),
            gain_eur_annuel=round(gain, 0),
            gain_eur_horizon=round(gain * 3, 0),
            action_concrete="Investir via des plateformes de crowdequity agréées (Wiseed, Tudigo) avant le 31/12.",
            sources=["CGI art. 199 terdecies-0 A"],
        )
    except Exception as e:
        logger.info(f"R37 skip: {e}")
        return None


@regle("R38", famille="Bonus retenus")
def detecter_R38(profil) -> Alerte | None:
    """Fondement : CGI art. 779 — abattement donation 100k€/15 ans non utilisé."""
    try:
        age = getattr(profil, "age", None)
        if age is None or age < 50:
            return None

        a_utilise_donation = getattr(profil, "a_utilise_donation", None)
        if a_utilise_donation is True or a_utilise_donation is None:
            return None

        patrimoine = getattr(profil, "patrimoine_financier_total", 0) or 0
        if patrimoine < 100000:
            return None

        return Alerte(
            code="R38",
            famille="Bonus retenus",
            severite=Severite.VERT,
            titre="Abattement donation 100k€/15 ans non activé",
            description=(
                "Chaque parent peut donner 100 000 € par enfant en franchise de droits tous les 15 ans. "
                f"À {age} ans, ne pas commencer maintenant réduira la fenêtre d'opportunité."
            ),
            gain_eur_annuel=None,
            gain_eur_horizon=None,
            action_concrete="Consulter un notaire pour initier des donations et activer le compteur des 15 ans.",
            sources=["CGI art. 779"],
        )
    except Exception as e:
        logger.info(f"R38 skip: {e}")
        return None


@regle("R39", famille="Bonus retenus")
def detecter_R39(profil) -> Alerte | None:
    """Fondement : CGI art. 757 B — AV : primes avant 70 ans exonérées pour bénéficiaires."""
    try:
        age = getattr(profil, "age", None)
        if age is None or not (65 <= age <= 75):
            return None

        composition = getattr(profil, "composition_actuelle", None) or []
        has_av = any(
            "AV" in str(getattr(l, "enveloppe", "") if not isinstance(l, dict) else l.get("enveloppe", "")).upper()
            or "ASSURANCE" in str(getattr(l, "enveloppe", "") if not isinstance(l, dict) else l.get("enveloppe", "")).upper()
            for l in composition
        )
        if not has_av:
            return None

        if age >= 70:
            description = "Les primes versées après 70 ans sont soumises aux droits de succession au-delà de 30 500 €."
            action = "Maximiser les versements AV avant vos 70 ans pour bénéficier de l'exonération complète."
        else:
            description = "Avant 70 ans, les primes AV sont exonérées de droits de succession jusqu'à 152 500 € par bénéficiaire."
            action = "Alimenter l'AV avant 70 ans pour maximiser la transmission hors droits de succession."

        return Alerte(
            code="R39",
            famille="Bonus retenus",
            severite=Severite.VERT,
            titre=f"Optimisation versements AV avant/après 70 ans (vous avez {age} ans)",
            description=description,
            gain_eur_annuel=None,
            gain_eur_horizon=None,
            action_concrete=action,
            sources=["CGI art. 757 B"],
        )
    except Exception as e:
        logger.info(f"R39 skip: {e}")
        return None


@regle("R40", famille="Bonus retenus")
def detecter_R40(profil) -> Alerte | None:
    """Fondement : CGI art. 199 terdecies-0 A — FCPI/FIP réduction IR non utilisée."""
    try:
        a_utilise_ir_pme = getattr(profil, "a_utilise_ir_pme", None)
        if a_utilise_ir_pme is True or a_utilise_ir_pme is None:
            return None

        tmi = getattr(profil, "tmi", 0) or 0
        if tmi < 0.30:
            return None

        est_en_couple = getattr(profil, "est_en_couple", False) or False
        plafond = 24000 if est_en_couple else 12000
        gain = plafond * 0.18

        return Alerte(
            code="R40",
            famille="Bonus retenus",
            severite=Severite.VERT,
            titre=f"FCPI/FIP — réduction IR {gain:,.0f} € non utilisée",
            description=(
                f"Les FCPI/FIP permettent une réduction d'IR de 18% sur {plafond:,.0f} € max "
                f"{'(couple)' if est_en_couple else '(célibataire)'}, soit {gain:,.0f} € d'économie."
            ),
            gain_eur_annuel=round(gain, 0),
            gain_eur_horizon=round(gain, 0),
            action_concrete="Investir dans des FCPI/FIP agréés AMF avant le 31/12 (Bpifrance, Eurazeo, Andera Partners).",
            sources=["CGI art. 199 terdecies-0 A"],
        )
    except Exception as e:
        logger.info(f"R40 skip: {e}")
        return None
