from __future__ import annotations

import logging
from .base import Alerte, Severite, regle

logger = logging.getLogger(__name__)


@regle("R19", famille="Configuration produit")
def detecter_R19(profil) -> Alerte | None:
    """Fondement : CGI art. 157 5°bis et 150-0 D bis — PEA non ouvert, horloge perdue."""
    try:
        age = getattr(profil, "age", None)
        if age is None or age >= 40:
            return None

        composition = getattr(profil, "composition_actuelle", None) or []
        enveloppes = getattr(profil, "enveloppes_disponibles", None) or {}

        has_pea = any(
            "PEA" in str(getattr(l, "enveloppe", "") if not isinstance(l, dict) else l.get("enveloppe", "")).upper()
            for l in composition
        )
        if not has_pea and isinstance(enveloppes, dict):
            has_pea = "PEA" in str(enveloppes).upper()

        if has_pea:
            return None

        horizon = 65 - age
        gain_horizon = 150000 * 0.07 * horizon * 0.128

        return Alerte(
            code="R19",
            famille="Configuration produit",
            severite=Severite.ROUGE,
            titre=f"PEA non ouvert à {age} ans — horloge fiscale perdue",
            description=(
                f"Ouvrir un PEA dès maintenant démarre l'horloge fiscale des 5 ans. "
                f"À {age} ans, il sera totalement libre d'IR à {age + 5} ans."
            ),
            gain_eur_annuel=None,
            gain_eur_horizon=round(gain_horizon, 0),
            action_concrete="Ouvrir un PEA chez un courtier en ligne (Boursorama, Fortuneo) avec un versement minimal immédiat.",
            sources=["CGI art. 157 5°bis", "CGI art. 150-0 D bis"],
        )
    except Exception as e:
        logger.info(f"R19 skip: {e}")
        return None


@regle("R20", famille="Configuration produit")
def detecter_R20(profil) -> Alerte | None:
    """Fondement : Code des assurances art. L132-12 — clause bénéficiaire AV."""
    try:
        composition = getattr(profil, "composition_actuelle", None) or []
        has_av = any(
            "AV" in str(getattr(l, "enveloppe", "") if not isinstance(l, dict) else l.get("enveloppe", "")).upper()
            or "ASSURANCE" in str(getattr(l, "enveloppe", "") if not isinstance(l, dict) else l.get("enveloppe", "")).upper()
            for l in composition
        )

        if not has_av:
            return None

        clause_renseignee = getattr(profil, "clause_beneficiaire_renseignee", None)
        if clause_renseignee is True:
            return None

        return Alerte(
            code="R20",
            famille="Configuration produit",
            severite=Severite.ROUGE,
            titre="Clause bénéficiaire AV non personnalisée",
            description=(
                "La clause bénéficiaire par défaut ('mon conjoint, à défaut mes enfants') est souvent sous-optimale. "
                "Elle peut entraîner une perte d'avantages fiscaux spécifiques."
            ),
            gain_eur_annuel=None,
            gain_eur_horizon=None,
            action_concrete="Rédiger une clause bénéficiaire sur-mesure avec un conseiller (démembrée, nominative, etc.).",
            sources=["Code des assurances art. L132-12"],
        )
    except Exception as e:
        logger.info(f"R20 skip: {e}")
        return None
