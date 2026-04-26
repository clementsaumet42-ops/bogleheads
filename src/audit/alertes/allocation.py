from __future__ import annotations

import logging

from .base import Alerte, Severite, regle

logger = logging.getLogger(__name__)


@regle("R7", famille="Allocation absurde")
def detecter_R7(profil) -> Alerte | None:
    """Fondement : Théorie moderne du portefeuille — sur-pondération des liquidités."""
    try:
        age = getattr(profil, "age", None)
        if age is None or age >= 55:
            return None

        patrimoine = getattr(profil, "patrimoine_financier_total", 0) or 0
        composition = getattr(profil, "composition_actuelle", None) or []

        if patrimoine > 0:
            cash = sum(
                (
                    getattr(item, "montant_eur", 0)
                    if not isinstance(item, dict)
                    else item.get("montant_eur", 0)
                )
                or 0
                for item in composition
                if any(
                    k
                    in str(
                        getattr(item, "classe_actif", "")
                        if not isinstance(item, dict)
                        else item.get("classe_actif", "")
                    ).upper()
                    for k in ("LIQUID", "CASH", "LIVRET")
                )
            )
            ratio_cash = cash / patrimoine
        else:
            alloc = getattr(profil, "allocation_cible_bogleheads", None)
            ratio_cash = getattr(alloc, "liquidites", 0) or 0 if alloc else 0

        if ratio_cash <= 0.5:
            return None

        return Alerte(
            code="R7",
            famille="Allocation absurde",
            severite=Severite.ROUGE,
            titre=f"Cash >50% du patrimoine (à {age} ans)",
            description=(
                f"À {age} ans, conserver plus de 50% du patrimoine en cash/liquidités "
                f"({ratio_cash:.0%}) génère un coût d'opportunité élevé face à l'inflation."
            ),
            gain_eur_annuel=None,
            gain_eur_horizon=None,
            action_concrete="Définir un plan d'investissement progressif (DCA mensuel) pour déployer les liquidités excédentaires.",
            sources=["Markowitz, Portfolio Selection (1952)", "AMF guide investisseur"],
        )
    except Exception as e:
        logger.info(f"R7 skip: {e}")
        return None


@regle("R8", famille="Allocation absurde")
def detecter_R8(profil) -> Alerte | None:
    """Fondement : Théorie du cycle de vie — sous-pondération actions pour jeune profil."""
    try:
        age = getattr(profil, "age", None)
        if age is None or age >= 45:
            return None

        alloc = getattr(profil, "allocation_cible_bogleheads", None)
        if alloc is None:
            return None

        actions = getattr(alloc, "actions", 0) or 0
        if actions >= 0.20:
            return None

        patrimoine = getattr(profil, "patrimoine_financier_total", 0) or 0
        horizon = 65 - age
        gain_horizon = (
            round(patrimoine * (0.60 - actions) * (0.07 - 0.02) * horizon, 0)
            if patrimoine > 0
            else None
        )

        return Alerte(
            code="R8",
            famille="Allocation absurde",
            severite=Severite.ROUGE,
            titre=f"Sous-exposition actions (<20%) à {age} ans",
            description=(
                f"À {age} ans avec {horizon} ans d'horizon, une allocation de {actions:.0%} en actions "
                "est insuffisante. Le coût d'opportunité vs 60% actions est significatif."
            ),
            gain_eur_annuel=None,
            gain_eur_horizon=gain_horizon,
            action_concrete="Revoir l'allocation cible vers 60-80% actions adapté à l'horizon long terme.",
            sources=[
                "Vanguard Target Retirement methodology",
                "Bogle, The Little Book of Common Sense Investing",
            ],
        )
    except Exception as e:
        logger.info(f"R8 skip: {e}")
        return None


@regle("R9", famille="Allocation absurde")
def detecter_R9(profil) -> Alerte | None:
    """Fondement : Rendement long terme actions vs fonds euros — allocation sous-optimale."""
    try:
        age = getattr(profil, "age", None)
        if age is None or age >= 50:
            return None

        composition = getattr(profil, "composition_actuelle", None) or []
        av_total = 0.0
        fonds_euros_total = 0.0

        for ligne in composition:
            if isinstance(ligne, dict):
                env = ligne.get("enveloppe", "")
                classe = ligne.get("classe_actif", "")
                montant = ligne.get("montant_eur", 0)
            else:
                env = getattr(ligne, "enveloppe", "")
                classe = getattr(ligne, "classe_actif", "")
                montant = getattr(ligne, "montant_eur", 0)

            if "AV" in str(env).upper() or "ASSURANCE" in str(env).upper():
                av_total += montant or 0
                if any(k in str(classe).upper() for k in ("EURO", "FONDS_EURO", "FONDS EURO")):
                    fonds_euros_total += montant or 0

        if av_total < 10000 or fonds_euros_total == 0:
            return None
        if av_total == 0 or (fonds_euros_total / av_total) < 0.95:
            return None

        gain = fonds_euros_total * (0.07 - 0.03)
        return Alerte(
            code="R9",
            famille="Allocation absurde",
            severite=Severite.ROUGE,
            titre=f"100% fonds euros en AV à {age} ans",
            description=(
                f"À {age} ans, investir {fonds_euros_total:,.0f} € à 100% en fonds euros (≈3%/an) "
                f"vs une allocation avec 60% d'UC actions (≈7%/an) coûte environ {gain:,.0f} €/an."
            ),
            gain_eur_annuel=round(gain, 0),
            gain_eur_horizon=round(gain * (50 - age), 0),
            action_concrete="Arbitrer progressivement vers des UC actions (ETF World éligibles en AV).",
            sources=["Banque de France, rendement fonds euros 2023", "MSCI World 30-year return"],
        )
    except Exception as e:
        logger.info(f"R9 skip: {e}")
        return None


@regle("R10", famille="Allocation absurde")
def detecter_R10(profil) -> Alerte | None:
    """Fondement : Théorie moderne du portefeuille — diversification insuffisante."""
    try:
        composition = getattr(profil, "composition_actuelle", None) or []
        if not composition:
            return None

        classes = {
            str(
                getattr(item, "classe_actif", "")
                if not isinstance(item, dict)
                else item.get("classe_actif", "")
            ).strip()
            for item in composition
            if (
                getattr(item, "classe_actif", "")
                if not isinstance(item, dict)
                else item.get("classe_actif", "")
            )
        }

        if len(classes) >= 3:
            return None

        return Alerte(
            code="R10",
            famille="Allocation absurde",
            severite=Severite.JAUNE,
            titre=f"Diversification insuffisante ({len(classes)} classe(s) d'actifs)",
            description=(
                f"Votre patrimoine ne comprend que {len(classes)} classe(s) d'actifs. "
                "Une diversification minimale recommande au moins 3 classes (actions, obligations, immobilier)."
            ),
            gain_eur_annuel=None,
            gain_eur_horizon=None,
            action_concrete="Diversifier vers au moins : actions mondiales (ETF World), obligations (ETF Aggregate), et immobilier (SCPI/SIIC).",
            sources=["Markowitz, Portfolio Selection (1952)"],
        )
    except Exception as e:
        logger.info(f"R10 skip: {e}")
        return None


@regle("R11", famille="Allocation absurde")
def detecter_R11(profil) -> Alerte | None:
    """Fondement : Risque de concentration — over-weight émetteur unique."""
    try:
        composition = getattr(profil, "composition_actuelle", None) or []
        patrimoine = getattr(profil, "patrimoine_financier_total", 0) or 0

        if patrimoine <= 0 or not composition:
            return None

        lignes_par_emetteur: dict[str, float] = {}
        for ligne in composition:
            if isinstance(ligne, dict):
                libelle = ligne.get("libelle_libre", "")
                ticker = ligne.get("etf_ticker", "")
                montant = ligne.get("montant_eur", 0)
            else:
                libelle = getattr(ligne, "libelle_libre", "")
                ticker = getattr(ligne, "etf_ticker", "")
                montant = getattr(ligne, "montant_eur", 0)
            key = str(ticker or libelle or "inconnu")
            lignes_par_emetteur[key] = lignes_par_emetteur.get(key, 0) + (montant or 0)

        for emetteur, montant in lignes_par_emetteur.items():
            pct = montant / patrimoine
            if pct > 0.30:
                return Alerte(
                    code="R11",
                    famille="Allocation absurde",
                    severite=Severite.ROUGE,
                    titre=f"Sur-concentration {emetteur} ({pct:.0%} du patrimoine)",
                    description=(
                        f"La position {emetteur} représente {pct:.0%} de votre patrimoine ({montant:,.0f} €). "
                        "Au-delà de 30%, le risque émetteur devient préoccupant."
                    ),
                    gain_eur_annuel=None,
                    gain_eur_horizon=None,
                    action_concrete=f"Réduire la position {emetteur} en dessous de 20-30% par arbitrage progressif.",
                    sources=["AMF guide diversification", "Markowitz, Portfolio Selection (1952)"],
                    ligne_concernee=emetteur,
                )

        return None
    except Exception as e:
        logger.info(f"R11 skip: {e}")
        return None
