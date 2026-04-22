# -*- coding: utf-8 -*-
"""
Module de rebalancement de portefeuille — approche Bogleheads.
Calcule les bandes de tolérance, le coût fiscal des arbitrages et
génère des recommandations de rééquilibrage.
"""

from __future__ import annotations
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Calcul des bandes de tolérance
# ---------------------------------------------------------------------------

def calculer_bandes_tolerance(
    pct_cible: float,
    methode: str = "relatif_5pct",
    largeur_absolue: float = 0.05,
    largeur_relative: float = 0.25,
) -> dict:
    """Calcule les bandes de tolérance autour d'une allocation cible.

    Deux méthodes disponibles :
    - 'absolu' : ±N points de pourcentage (ex: ±5 % autour de 60 % → [55 %, 65 %])
    - 'relatif_5pct' : ±5 points absolus (synonyme de 'absolu' pour cohérence nomenclature)
    - 'larry_swedroe' : ±25 % relatif (ex: 25 % de 60 % = ±15 → [45 %, 75 %])

    Source méthode Swedroe : Larry Swedroe, "The Only Guide to a Winning Bond Strategy You'll Ever Need"

    Args:
        pct_cible: Pourcentage cible (entre 0 et 1).
        methode: 'absolu', 'relatif_5pct' ou 'larry_swedroe'.
        largeur_absolue: Largeur de la bande en points absolus (pour méthode absolu).
        largeur_relative: Largeur relative (pour Larry Swedroe, défaut 25 %).

    Returns:
        Dictionnaire avec pct_min, pct_max, largeur, methode.

    Raises:
        ValueError: Si la méthode est inconnue.
    """
    if not (0.0 <= pct_cible <= 1.0):
        raise ValueError(f"pct_cible doit être entre 0 et 1 : {pct_cible}")

    methode_norm = methode.lower().strip()

    if methode_norm in ("absolu", "relatif_5pct", "absolu_5pct"):
        # Bande fixe en points absolus
        pct_min = max(0.0, pct_cible - largeur_absolue)
        pct_max = min(1.0, pct_cible + largeur_absolue)
        largeur_effective = largeur_absolue

    elif methode_norm in ("larry_swedroe", "swedroe", "relatif"):
        # Bande relative : ±25 % de la valeur cible (en points absolus)
        demi_bande = pct_cible * largeur_relative
        pct_min = max(0.0, pct_cible - demi_bande)
        pct_max = min(1.0, pct_cible + demi_bande)
        largeur_effective = demi_bande

    else:
        raise ValueError(
            f"Méthode inconnue : '{methode}'. "
            "Valeurs acceptées : 'absolu', 'relatif_5pct', 'larry_swedroe'."
        )

    return {
        "pct_cible": round(pct_cible, 4),
        "pct_min": round(pct_min, 4),
        "pct_max": round(pct_max, 4),
        "largeur": round(largeur_effective, 4),
        "methode": methode,
    }


# ---------------------------------------------------------------------------
# Calcul du coût fiscal d'un arbitrage
# ---------------------------------------------------------------------------

def calculer_cout_fiscal_arbitrage(
    pv_latente: float,
    taux_marginal_enveloppe: float,
    horizon_ans: int = 10,
    rendement_annuel_estime: float = 0.07,
) -> dict:
    """Calcule le coût fiscal d'un arbitrage et son impact sur la performance.

    Réaliser une plus-value latente pour rééquilibrer un portefeuille a un coût :
    l'impôt immédiat réduit le capital réinvesti. Ce calcul quantifie le manque
    à gagner par rapport à un report de l'imposition.

    Args:
        pv_latente: Plus-value latente à réaliser en euros.
        taux_marginal_enveloppe: Taux d'imposition applicable (ex: 0.314 pour PFU).
        horizon_ans: Horizon de placement en années pour estimer l'impact.
        rendement_annuel_estime: Rendement annuel attendu du capital.

    Returns:
        Dictionnaire avec impôt_immediat, capital_perd, cout_opportunite, recommandation.
    """
    # Impôt immédiat si l'arbitrage est réalisé
    impot_immediat = round(pv_latente * taux_marginal_enveloppe, 2)

    # Capital perdu immédiatement (le capital réinvesti est réduit d'autant)
    capital_perdu = impot_immediat

    # Coût d'opportunité : le capital perdu ne capitalisera plus pendant N ans
    # Formule : coût_opportunité = impôt × ((1 + r)^N - 1)
    cout_opportunite = round(
        impot_immediat * ((1 + rendement_annuel_estime) ** horizon_ans - 1), 2
    )

    # Recommandation qualitative
    seuil_cout_negligeable = 0.01  # Si l'impôt < 1 % du capital, arbitrage acceptable
    if taux_marginal_enveloppe == 0.0:
        recommandation = "Arbitrage sans coût fiscal — rééquilibrer librement"
    elif taux_marginal_enveloppe <= 0.172:
        recommandation = "Faible imposition (PS seulement) — arbitrage peu coûteux"
    elif cout_opportunite < pv_latente * seuil_cout_negligeable:
        recommandation = "Coût d'opportunité faible — arbitrage acceptable"
    else:
        recommandation = (
            f"Coût fiscal significatif ({taux_marginal_enveloppe:.1%}) — "
            "privilégier rééquilibrage par nouveaux versements"
        )

    return {
        "pv_latente": round(pv_latente, 2),
        "taux_fiscal": taux_marginal_enveloppe,
        "impot_immediat": impot_immediat,
        "capital_perdu": capital_perdu,
        "horizon_ans": horizon_ans,
        "rendement_estime": rendement_annuel_estime,
        "cout_opportunite": cout_opportunite,
        "recommandation": recommandation,
    }


# ---------------------------------------------------------------------------
# Dataclass pour représenter l'allocation actuelle
# ---------------------------------------------------------------------------

@dataclass
class AllocationsActuelles:
    """Snapshot de l'allocation actuelle du portefeuille.

    Attributes:
        actions: Montant en actions en euros.
        obligations: Montant en obligations en euros.
        liquidites: Montant en liquidités en euros.
    """

    actions: float = 0.0
    obligations: float = 0.0
    liquidites: float = 0.0

    @property
    def total(self) -> float:
        """Total du portefeuille en euros."""
        return self.actions + self.obligations + self.liquidites

    @property
    def pct_actions(self) -> float:
        """Pourcentage en actions."""
        return self.actions / self.total if self.total > 0 else 0.0

    @property
    def pct_obligations(self) -> float:
        """Pourcentage en obligations."""
        return self.obligations / self.total if self.total > 0 else 0.0

    @property
    def pct_liquidites(self) -> float:
        """Pourcentage en liquidités."""
        return self.liquidites / self.total if self.total > 0 else 0.0


# ---------------------------------------------------------------------------
# Recommandation de rééquilibrage
# ---------------------------------------------------------------------------

def recommander_rebalancement(
    allocation_actuelle: dict | AllocationsActuelles,
    allocation_cible: dict,
    valeur_totale: float,
    methode_tolerance: str = "relatif_5pct",
    taux_fiscal: float = 0.314,
) -> dict:
    """Génère des recommandations de rééquilibrage du portefeuille.

    Compare l'allocation actuelle avec la cible et détermine si un rééquilibrage
    est nécessaire, et quelle méthode employer (versements ou arbitrage direct).

    Args:
        allocation_actuelle: Allocation actuelle {classe: montant} ou AllocationsActuelles.
        allocation_cible: Allocation cible {classe: pct_cible}.
        valeur_totale: Valeur totale du portefeuille en euros.
        methode_tolerance: Méthode de calcul des bandes de tolérance.
        taux_fiscal: Taux fiscal applicable aux arbitrages.

    Returns:
        Dictionnaire complet de recommandations avec les actions à effectuer.
    """
    # Normalisation de l'entrée
    if isinstance(allocation_actuelle, AllocationsActuelles):
        actuelle = {
            "actions": allocation_actuelle.actions,
            "obligations": allocation_actuelle.obligations,
            "liquidites": allocation_actuelle.liquidites,
        }
    else:
        actuelle = dict(allocation_actuelle)

    recommandations = []
    rebalancement_necessaire = False

    for classe in ("actions", "obligations", "liquidites"):
        pct_cible = allocation_cible.get(f"pct_{classe}", 0.0)
        montant_actuel = actuelle.get(classe, 0.0)
        pct_actuel = montant_actuel / valeur_totale if valeur_totale > 0 else 0.0

        montant_cible = pct_cible * valeur_totale
        ecart_montant = montant_cible - montant_actuel
        ecart_pct = pct_cible - pct_actuel

        # Calcul des bandes de tolérance
        bandes = calculer_bandes_tolerance(pct_cible, methode_tolerance)
        hors_bandes = not (bandes["pct_min"] <= pct_actuel <= bandes["pct_max"])

        if hors_bandes:
            rebalancement_necessaire = True

        action = _determiner_action(ecart_montant, hors_bandes, taux_fiscal)

        recommandations.append({
            "classe_actifs": classe,
            "pct_actuel": round(pct_actuel, 4),
            "pct_cible": round(pct_cible, 4),
            "ecart_pct": round(ecart_pct, 4),
            "montant_actuel": round(montant_actuel, 2),
            "montant_cible": round(montant_cible, 2),
            "ecart_montant": round(ecart_montant, 2),
            "pct_min_tolerance": bandes["pct_min"],
            "pct_max_tolerance": bandes["pct_max"],
            "hors_bandes": hors_bandes,
            "action_recommandee": action,
        })

    # Synthèse globale
    classes_hors_bandes = [r["classe_actifs"] for r in recommandations if r["hors_bandes"]]

    synthese = _generer_synthese(
        rebalancement_necessaire,
        classes_hors_bandes,
        valeur_totale,
        taux_fiscal,
    )

    return {
        "rebalancement_necessaire": rebalancement_necessaire,
        "valeur_totale": round(valeur_totale, 2),
        "methode_tolerance": methode_tolerance,
        "recommandations_par_classe": recommandations,
        "classes_hors_bandes": classes_hors_bandes,
        "synthese": synthese,
    }


def _determiner_action(ecart_montant: float, hors_bandes: bool, taux_fiscal: float) -> str:
    """Détermine l'action recommandée pour une classe d'actifs.

    Args:
        ecart_montant: Écart en euros entre cible et actuel (positif = sous-pondéré).
        hors_bandes: Indique si la classe est hors bandes de tolérance.
        taux_fiscal: Taux fiscal applicable.

    Returns:
        Description textuelle de l'action recommandée.
    """
    if not hors_bandes:
        return "Dans les bandes — aucune action requise"

    if ecart_montant > 0:
        # Sous-pondéré — besoin d'acheter
        return f"Acheter {abs(ecart_montant):.0f} € — via nouveaux versements de préférence"
    else:
        # Sur-pondéré — besoin de vendre
        if taux_fiscal > 0.0:
            return (
                f"Vendre {abs(ecart_montant):.0f} € — arbitrage fiscal à {taux_fiscal:.1%} ; "
                "préférer rééquilibrer par versements si possible"
            )
        return f"Vendre {abs(ecart_montant):.0f} € — pas de coût fiscal (enveloppe exonérée)"


def _generer_synthese(
    necessaire: bool,
    classes_hors_bandes: list[str],
    valeur_totale: float,
    taux_fiscal: float,
) -> str:
    """Génère un texte de synthèse de la recommandation.

    Args:
        necessaire: Indique si le rééquilibrage est nécessaire.
        classes_hors_bandes: Classes d'actifs hors bandes.
        valeur_totale: Valeur totale du portefeuille.
        taux_fiscal: Taux fiscal applicable.

    Returns:
        Texte de synthèse.
    """
    if not necessaire:
        return "✅ Portefeuille équilibré — allocation dans les bandes de tolérance."

    classes_str = ", ".join(classes_hors_bandes)
    conseil_versements = (
        "💡 Conseil Bogleheads : Rééquilibrer en priorité par de nouveaux versements "
        "(cash-flow rebalancing) pour éviter l'imposition sur plus-values latentes."
    )

    if taux_fiscal > 0.0:
        return (
            f"⚠️ Rééquilibrage nécessaire : {classes_str} hors bandes. "
            f"Portefeuille : {valeur_totale:,.0f} €. "
            f"Taux fiscal applicable : {taux_fiscal:.1%}. "
            f"{conseil_versements}"
        )
    else:
        return (
            f"⚠️ Rééquilibrage nécessaire : {classes_str} hors bandes. "
            f"Portefeuille : {valeur_totale:,.0f} €. "
            "Enveloppe fiscalement exonérée — arbitrage sans coût fiscal possible."
        )
