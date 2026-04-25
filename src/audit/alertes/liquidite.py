from __future__ import annotations

import logging
from .base import Alerte, Severite, regle

logger = logging.getLogger(__name__)


@regle("R21", famille="Liquidité & sécurité")
def detecter_R21(profil) -> Alerte | None:
    """Fondement : Règle des 3-6 mois de charges — épargne de précaution insuffisante."""
    try:
        charges_mensuelles = getattr(profil, "charges_mensuelles", None)
        epargne_precaution = getattr(profil, "epargne_precaution", None)

        if charges_mensuelles is None or charges_mensuelles <= 0:
            return None
        if epargne_precaution is None:
            return None

        seuil_3_mois = charges_mensuelles * 3
        if epargne_precaution >= seuil_3_mois:
            return None

        manque = seuil_3_mois - epargne_precaution
        return Alerte(
            code="R21",
            famille="Liquidité & sécurité",
            severite=Severite.ROUGE,
            titre="Épargne de précaution < 3 mois de charges",
            description=(
                f"Votre épargne de précaution ({epargne_precaution:,.0f} €) est inférieure à 3 mois de charges "
                f"({seuil_3_mois:,.0f} €). Il manque {manque:,.0f} € pour atteindre le seuil minimal."
            ),
            gain_eur_annuel=None,
            gain_eur_horizon=None,
            action_concrete=f"Alimenter votre Livret A / LDDS jusqu'à {seuil_3_mois:,.0f} € avant tout investissement.",
            sources=["Banque de France, guide épargne de précaution", "AMF guide investisseur"],
        )
    except Exception as e:
        logger.info(f"R21 skip: {e}")
        return None


@regle("R22", famille="Liquidité & sécurité")
def detecter_R22(profil) -> Alerte | None:
    """Fondement : Livret A taux réglementé — opportunité d'épargne sans risque."""
    try:
        a_livret_a = getattr(profil, "a_livret_a", None)
        if a_livret_a is True:
            return None
        if a_livret_a is None:
            return None

        composition = getattr(profil, "composition_actuelle", None) or []
        has_livret = any(
            "LIVRET" in str(getattr(l, "classe_actif", "") if not isinstance(l, dict) else l.get("classe_actif", "")).upper()
            or "LIVRET" in str(getattr(l, "libelle_libre", "") if not isinstance(l, dict) else l.get("libelle_libre", "")).upper()
            for l in composition
        )
        if has_livret:
            return None

        return Alerte(
            code="R22",
            famille="Liquidité & sécurité",
            severite=Severite.JAUNE,
            titre="Livret A non ouvert — épargne de précaution non optimisée",
            description=(
                "Le Livret A offre un taux réglementé (3%), exonéré d'impôt, garanti par l'État, "
                "avec disponibilité immédiate. À ouvrir en priorité."
            ),
            gain_eur_annuel=None,
            gain_eur_horizon=None,
            action_concrete="Ouvrir un Livret A (plafond 22 950 €) dans n'importe quelle banque.",
            sources=["Banque de France, taux Livret A", "Loi n°2008-776 du 4 août 2008"],
        )
    except Exception as e:
        logger.info(f"R22 skip: {e}")
        return None


@regle("R23", famille="Liquidité & sécurité")
def detecter_R23(profil) -> Alerte | None:
    """Fondement : Coût d'opportunité — excès de liquidités court terme."""
    try:
        charges_mensuelles = getattr(profil, "charges_mensuelles", None)
        epargne_precaution = getattr(profil, "epargne_precaution", None)

        if charges_mensuelles is None or charges_mensuelles <= 0:
            return None
        if epargne_precaution is None:
            return None

        seuil_12_mois = charges_mensuelles * 12
        if epargne_precaution <= seuil_12_mois:
            return None

        exces = epargne_precaution - seuil_12_mois
        gain = exces * (0.07 - 0.03)

        return Alerte(
            code="R23",
            famille="Liquidité & sécurité",
            severite=Severite.JAUNE,
            titre=f"Excès de liquidités ({epargne_precaution:,.0f} € > 12 mois charges)",
            description=(
                "Votre épargne de précaution dépasse 12 mois de charges. "
                f"Les {exces:,.0f} € excédentaires perdent environ {gain:,.0f} €/an vs investissement long terme."
            ),
            gain_eur_annuel=round(gain, 0),
            gain_eur_horizon=round(gain * 20, 0),
            action_concrete="Déployer l'excédent de précaution vers des enveloppes long terme (PEA, AV, PER).",
            sources=["AMF guide investisseur", "Bogle, Common Sense Investing"],
        )
    except Exception as e:
        logger.info(f"R23 skip: {e}")
        return None


@regle("R24", famille="Liquidité & sécurité")
def detecter_R24(profil) -> Alerte | None:
    """Fondement : Banque de France, taux Livret A — Livret A prioritaire avant fonds euros."""
    try:
        PLAFOND_LIVRET_A = 22950.0

        composition = getattr(profil, "composition_actuelle", None) or []
        montant_livret_a = 0.0
        montant_fonds_euros = 0.0

        for ligne in composition:
            if isinstance(ligne, dict):
                libelle = str(ligne.get("libelle_libre", "") or "")
                classe = str(ligne.get("classe_actif", "") or "")
                montant = ligne.get("montant_eur", 0) or 0
            else:
                libelle = str(getattr(ligne, "libelle_libre", "") or "")
                classe = str(getattr(ligne, "classe_actif", "") or "")
                montant = getattr(ligne, "montant_eur", 0) or 0

            if "LIVRET A" in libelle.upper() or "LIVRET_A" in libelle.upper():
                montant_livret_a += montant
            if "EURO" in classe.upper() or "FONDS EURO" in libelle.upper() or "FONDS_EURO" in classe.upper():
                montant_fonds_euros += montant

        if montant_livret_a >= PLAFOND_LIVRET_A * 0.9:
            return None
        if montant_fonds_euros <= 0:
            return None

        restant_livret = PLAFOND_LIVRET_A - montant_livret_a
        gain = restant_livret * 0.005

        return Alerte(
            code="R24",
            famille="Liquidité & sécurité",
            severite=Severite.JAUNE,
            titre=f"Livret A non plein avant fonds euros ({restant_livret:,.0f} € disponibles)",
            description=(
                "Le Livret A (3%, exonéré d'impôt) est plus avantageux que les fonds euros (≈2,5%, PS 17,2%). "
                f"Il reste {restant_livret:,.0f} € de capacité."
            ),
            gain_eur_annuel=round(gain, 0),
            gain_eur_horizon=round(gain * 10, 0),
            action_concrete=f"Alimenter le Livret A jusqu'à son plafond de {PLAFOND_LIVRET_A:,.0f} € avant les fonds euros AV.",
            sources=["Banque de France, taux Livret A"],
        )
    except Exception as e:
        logger.info(f"R24 skip: {e}")
        return None
