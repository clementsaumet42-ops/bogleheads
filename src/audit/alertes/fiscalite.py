from __future__ import annotations

import logging
from .base import Alerte, Severite, regle

logger = logging.getLogger(__name__)

_TAUX_PFU_IR = 0.128  # taux IR du PFU (12,8%) — CGI art. 200 A


@regle("R12", famille="Fiscalité gâchée")
def detecter_R12(profil) -> Alerte | None:
    """Fondement : CGI art. 150-0 A — imposition dividendes ETF distribuant en CTO."""
    try:
        tmi = getattr(profil, "tmi", 0) or 0
        if tmi < 0.30:
            return None

        composition = getattr(profil, "composition_actuelle", None) or []
        cto_distribuant = 0.0
        for ligne in composition:
            if isinstance(ligne, dict):
                env = ligne.get("enveloppe", "")
                libelle = ligne.get("libelle_libre", "")
                ticker = ligne.get("etf_ticker", "")
                montant = ligne.get("montant_eur", 0)
            else:
                env = getattr(ligne, "enveloppe", "")
                libelle = getattr(ligne, "libelle_libre", "")
                ticker = getattr(ligne, "etf_ticker", "")
                montant = getattr(ligne, "montant_eur", 0)

            if "CTO" in str(env).upper():
                if "DIST" in str(ticker or "").upper() or "DIST" in str(libelle or "").upper():
                    cto_distribuant += montant or 0

        if cto_distribuant < 10000:
            return None

        rendement_div = 0.025
        dividendes = cto_distribuant * rendement_div
        gain = dividendes * (tmi - _TAUX_PFU_IR)  # saving by switching from PFU (12.8%) to capitalizing

        return Alerte(
            code="R12",
            famille="Fiscalité gâchée",
            severite=Severite.ROUGE,
            titre="ETF distribuant en CTO avec TMI ≥30% — perte de capitalisation",
            description=(
                f"À TMI {tmi:.0%}, les dividendes des ETF distribuants en CTO sont imposés à 30% (PFU) "
                f"vs 0% avec un ETF capitalisant. Sur {cto_distribuant:,.0f} € d'ETF DIST."
            ),
            gain_eur_annuel=round(gain, 0),
            gain_eur_horizon=round(gain * 10, 0),
            action_concrete="Remplacer les ETF distribuants (DIST) par leurs équivalents capitalisants (ACC) en CTO.",
            sources=["CGI art. 150-0 A", "BOFiP BIC - Revenus de capitaux mobiliers"],
        )
    except Exception as e:
        logger.info(f"R12 skip: {e}")
        return None


@regle("R13", famille="Fiscalité gâchée")
def detecter_R13(profil) -> Alerte | None:
    """Fondement : CGI art. 150-0 D bis — PEA avec fonds actifs vs ETF éligibles."""
    try:
        composition = getattr(profil, "composition_actuelle", None) or []
        pea_fonds_actifs = 0.0

        for ligne in composition:
            if isinstance(ligne, dict):
                env = ligne.get("enveloppe", "")
                classe = ligne.get("classe_actif", "")
                libelle = ligne.get("libelle_libre", "")
                montant = ligne.get("montant_eur", 0)
            else:
                env = getattr(ligne, "enveloppe", "")
                classe = getattr(ligne, "classe_actif", "")
                libelle = getattr(ligne, "libelle_libre", "")
                montant = getattr(ligne, "montant_eur", 0)

            if "PEA" in str(env).upper():
                classe_str = str(classe or "").lower()
                libelle_str = str(libelle or "").lower()
                if any(k in classe_str or k in libelle_str for k in ["fonds actif", "opcvm", "sicav", "fcp"]):
                    pea_fonds_actifs += montant or 0

        if pea_fonds_actifs < 5000:
            return None

        gain = pea_fonds_actifs * 0.015
        return Alerte(
            code="R13",
            famille="Fiscalité gâchée",
            severite=Severite.JAUNE,
            titre="PEA investi en fonds actifs (au lieu d'ETF éligibles)",
            description=(
                "Le PEA offre une exonération d'IR après 5 ans. "
                f"Optimiser les {pea_fonds_actifs:,.0f} € en remplaçant les fonds actifs par des ETF PEA-éligibles."
            ),
            gain_eur_annuel=round(gain, 0),
            gain_eur_horizon=round(gain * 20, 0),
            action_concrete="Remplacer les OPCVM actifs par des ETF PEA-éligibles (Amundi ETF MSCI World, Lyxor PEA).",
            sources=["CGI art. 150-0 D bis"],
        )
    except Exception as e:
        logger.info(f"R13 skip: {e}")
        return None


@regle("R14", famille="Fiscalité gâchée")
def detecter_R14(profil) -> Alerte | None:
    """Fondement : CGI art. 125-0 A — AV optimisation fiscale rachats."""
    try:
        from datetime import date, datetime

        composition = getattr(profil, "composition_actuelle", None) or []

        for ligne in composition:
            if isinstance(ligne, dict):
                env = ligne.get("enveloppe", "")
                date_acq = ligne.get("date_acquisition", None)
            else:
                env = getattr(ligne, "enveloppe", "")
                date_acq = getattr(ligne, "date_acquisition", None)

            if "AV" in str(env).upper() or "ASSURANCE" in str(env).upper():
                if date_acq is not None:
                    if isinstance(date_acq, str):
                        try:
                            date_acq = datetime.fromisoformat(date_acq).date()
                        except Exception:
                            continue
                    age_contrat = (date.today() - date_acq).days / 365.25
                    if age_contrat < 8:
                        return Alerte(
                            code="R14",
                            famille="Fiscalité gâchée",
                            severite=Severite.JAUNE,
                            titre="AV non optimisée fiscalement (contrat < 8 ans)",
                            description=(
                                f"Votre contrat AV a moins de 8 ans ({age_contrat:.1f} ans). "
                                "Tout rachat avant 8 ans perd l'abattement annuel de 4 600 € (ou 9 200 € en couple)."
                            ),
                            gain_eur_annuel=None,
                            gain_eur_horizon=None,
                            action_concrete="Éviter tout rachat non indispensable avant la 8e année du contrat.",
                            sources=["CGI art. 125-0 A"],
                        )
        return None
    except Exception as e:
        logger.info(f"R14 skip: {e}")
        return None


@regle("R15", famille="Fiscalité gâchée")
def detecter_R15(profil) -> Alerte | None:
    """Fondement : CGI art. 125-0 A — AV <8 ans non alimentée, perte abattement futur."""
    try:
        from datetime import date, datetime

        composition = getattr(profil, "composition_actuelle", None) or []
        est_en_couple = getattr(profil, "est_en_couple", False) or False
        abattement = 9200 if est_en_couple else 4600

        for ligne in composition:
            if isinstance(ligne, dict):
                env = ligne.get("enveloppe", "")
                date_acq = ligne.get("date_acquisition", None)
            else:
                env = getattr(ligne, "enveloppe", "")
                date_acq = getattr(ligne, "date_acquisition", None)

            if "AV" in str(env).upper() or "ASSURANCE" in str(env).upper():
                if date_acq is not None:
                    if isinstance(date_acq, str):
                        try:
                            date_acq = datetime.fromisoformat(date_acq).date()
                        except Exception:
                            continue
                    age_contrat = (date.today() - date_acq).days / 365.25
                    if 0 < age_contrat < 8:
                        tmi = getattr(profil, "tmi", 0) or 0
                        gain_annuel = abattement * tmi
                        return Alerte(
                            code="R15",
                            famille="Fiscalité gâchée",
                            severite=Severite.JAUNE,
                            titre=f"AV <8 ans — alimenter pour activer l'abattement {abattement:,} €",
                            description=(
                                f"Votre contrat AV ouvert depuis {age_contrat:.1f} ans doit être alimenté "
                                f"pour déclencher l'abattement annuel de {abattement:,} € applicable après 8 ans."
                            ),
                            gain_eur_annuel=round(gain_annuel, 0),
                            gain_eur_horizon=round(gain_annuel * 20, 0),
                            action_concrete="Alimenter le contrat AV régulièrement et attendre les 8 ans pour les rachats.",
                            sources=["CGI art. 125-0 A"],
                        )
        return None
    except Exception as e:
        logger.info(f"R15 skip: {e}")
        return None


@regle("R16", famille="Fiscalité gâchée")
def detecter_R16(profil) -> Alerte | None:
    """Fondement : CGI art. 163 quatervicies — PER non alimenté."""
    try:
        plafond_per = getattr(profil, "plafond_per_non_utilise", None)
        if plafond_per is None or plafond_per <= 0:
            return None

        tmi = getattr(profil, "tmi", 0) or 0
        if tmi < 0.30:
            return None

        gain = plafond_per * tmi
        return Alerte(
            code="R16",
            famille="Fiscalité gâchée",
            severite=Severite.ROUGE,
            titre="PER non alimenté au plafond (déductibilité perdue)",
            description=(
                f"Votre plafond PER déductible non utilisé est de {plafond_per:,.0f} €. "
                f"À TMI {tmi:.0%}, l'économie d'IR est de {gain:,.0f} €."
            ),
            gain_eur_annuel=round(gain, 0),
            gain_eur_horizon=round(gain * 5, 0),
            action_concrete="Effectuer un versement PER avant le 31 décembre pour déduire du revenu imposable.",
            sources=["CGI art. 163 quatervicies"],
        )
    except Exception as e:
        logger.info(f"R16 skip: {e}")
        return None


@regle("R17", famille="Fiscalité gâchée")
def detecter_R17(profil) -> Alerte | None:
    """Fondement : CGI art. 157 5°bis — plafond PEA non utilisé."""
    try:
        PLAFOND_PEA = 150000.0
        age = getattr(profil, "age", None)
        if age is None or age >= 60:
            return None

        composition = getattr(profil, "composition_actuelle", None) or []
        montant_pea = sum(
            (getattr(l, "montant_eur", 0) if not isinstance(l, dict) else l.get("montant_eur", 0)) or 0
            for l in composition
            if "PEA" in str(getattr(l, "enveloppe", "") if not isinstance(l, dict) else l.get("enveloppe", "")).upper()
        )

        if montant_pea >= PLAFOND_PEA * 0.9:
            return None

        restant = PLAFOND_PEA - montant_pea
        horizon = max(65 - age, 5)
        gain_horizon = restant * 0.07 * horizon * _TAUX_PFU_IR

        return Alerte(
            code="R17",
            famille="Fiscalité gâchée",
            severite=Severite.JAUNE,
            titre=f"Plafond PEA non utilisé ({restant:,.0f} € disponibles)",
            description=(
                f"Il vous reste {restant:,.0f} € de capacité de versement PEA sur 150 000 €. "
                "Chaque € non versé est un € taxé à terme."
            ),
            gain_eur_annuel=None,
            gain_eur_horizon=round(gain_horizon, 0),
            action_concrete="Alimenter progressivement le PEA jusqu'au plafond de 150 000 € de versements.",
            sources=["CGI art. 157 5°bis", "CGI art. 150-0 D bis"],
        )
    except Exception as e:
        logger.info(f"R17 skip: {e}")
        return None


@regle("R18", famille="Fiscalité gâchée")
def detecter_R18(profil) -> Alerte | None:
    """Fondement : CGI art. 779 — droits de donation non utilisés."""
    try:
        age = getattr(profil, "age", None)
        if age is None or age < 50:
            return None

        a_utilise_donation = getattr(profil, "a_utilise_donation", None)
        if a_utilise_donation is True:
            return None

        patrimoine = getattr(profil, "patrimoine_financier_total", 0) or 0
        if patrimoine < 100000:
            return None

        return Alerte(
            code="R18",
            famille="Fiscalité gâchée",
            severite=Severite.VERT,
            titre="Droits de donation 100k€/15 ans non utilisés",
            description=(
                "Chaque parent peut donner 100 000 € par enfant tous les 15 ans en franchise fiscale. "
                f"À {age} ans, commencer les donations réduit les droits de succession futurs."
            ),
            gain_eur_annuel=None,
            gain_eur_horizon=None,
            action_concrete="Consulter un notaire pour planifier des donations avec utilisation de l'abattement de 100 000 €.",
            sources=["CGI art. 779"],
        )
    except Exception as e:
        logger.info(f"R18 skip: {e}")
        return None
