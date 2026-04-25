from __future__ import annotations

import logging
from .base import Alerte, Severite, regle

logger = logging.getLogger(__name__)


@regle("R35", famille="Hygiène opérationnelle")
def detecter_R35(profil) -> Alerte | None:
    """Fondement : Bonne pratique patrimoniale — revue annuelle du patrimoine."""
    try:
        from datetime import date, datetime

        date_revue = getattr(profil, "date_revue_patrimoine", None)

        if date_revue is None:
            return Alerte(
                code="R35",
                famille="Hygiène opérationnelle",
                severite=Severite.JAUNE,
                titre="Pas de date de revue annuelle du patrimoine planifiée",
                description=(
                    "Aucune revue patrimoniale annuelle n'est planifiée. "
                    "Une revue annuelle permet d'ajuster l'allocation, de saisir les opportunités fiscales "
                    "et de s'assurer que la stratégie reste adaptée."
                ),
                gain_eur_annuel=None,
                gain_eur_horizon=None,
                action_concrete="Planifier une revue patrimoniale annuelle (idéalement en novembre/décembre avant la clôture fiscale).",
                sources=["AMF guide investisseur", "Bonne pratique CGP"],
            )

        if isinstance(date_revue, str):
            try:
                date_revue = datetime.fromisoformat(date_revue).date()
            except Exception:
                return None

        if isinstance(date_revue, date):
            age_revue_jours = (date.today() - date_revue).days
            if age_revue_jours > 365:
                return Alerte(
                    code="R35",
                    famille="Hygiène opérationnelle",
                    severite=Severite.JAUNE,
                    titre=f"Revue patrimoniale périmée ({age_revue_jours // 365} an(s) depuis la dernière)",
                    description=(
                        f"Votre dernière revue patrimoniale remonte à {age_revue_jours} jours. "
                        "Une revue annuelle est recommandée."
                    ),
                    gain_eur_annuel=None,
                    gain_eur_horizon=None,
                    action_concrete="Planifier une revue patrimoniale avec votre CGP avant fin d'année.",
                    sources=["AMF guide investisseur", "Bonne pratique CGP"],
                )

        return None
    except Exception as e:
        logger.info(f"R35 skip: {e}")
        return None
