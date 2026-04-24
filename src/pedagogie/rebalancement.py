"""Explications pédagogiques pour le plan de rebalancement."""

from __future__ import annotations

from src.pedagogie.base import Explication


def expliquer_plan_rebalancement(
    plan: dict,
) -> list[Explication]:
    """Retourne les explications pédagogiques du plan de rebalancement.

    Args:
        plan: Dictionnaire décrivant le plan de rebalancement avec au moins :
              - etape_1_montant (float) : montant arbitré en AV/PEA (coût zéro)
              - etape_2_flux_mensuel (float) : versements mensuels redirigés
              - etape_3_cout_fiscal (float) : coût fiscal des ventes CTO
              - etape_3_montant_ventes (float, optionnel)

    Returns:
        Liste de 3 Explication correspondant aux 3 étapes du rebalancement.
    """
    montant_etape1 = float(plan.get("etape_1_montant", 0.0))
    flux_mensuel = float(plan.get("etape_2_flux_mensuel", 0.0))
    cout_fiscal = float(plan.get("etape_3_cout_fiscal", 0.0))
    montant_ventes = float(plan.get("etape_3_montant_ventes", 0.0))

    return [
        Explication(
            section="rebalancement.etape_1_gratuit",
            titre="Étape 1 : arbitrages sans coût fiscal (AV / PEA)",
            texte_court=(
                f"Arbitrages internes AV/PEA : {montant_etape1:,.0f} € réalloués "
                "sans déclenchement d'imposition — on commence toujours par là."
            ),
            texte_long=(
                "La première étape du rebalancement consiste à exploiter les arbitrages "
                "internes aux enveloppes fiscalement protégées (assurance-vie et PEA). "
                "Au sein d'une AV, un arbitrage entre deux fonds/UC est neutre fiscalement : "
                "aucune plus-value réalisée, aucun impôt déclenché (Art. 125-0 A CGI). "
                "Au sein du PEA, les ventes/achats internes n'entraînent pas de sortie de "
                "l'enveloppe et restent non taxés jusqu'au retrait effectif. "
                f"Montant réalloué sans coût fiscal : {montant_etape1:,.0f} €. "
                "Cette étape doit toujours être épuisée avant de considérer des ventes CTO."
            ),
            source=(
                "Art. 125-0 A CGI (neutralité fiscale des arbitrages AV). "
                "Art. 163 quinquies D CGI (non-imposition des gains PEA tant qu'ils restent "
                "dans l'enveloppe)."
            ),
            gain_eur=0.0,
        ),
        Explication(
            section="rebalancement.etape_2_flux",
            titre="Étape 2 : orientation des flux vers les classes sous-pondérées",
            texte_court=(
                f"Versements futurs ({flux_mensuel:,.0f} €/mois) dirigés vers les classes "
                "sous-pondérées — rééquilibrage progressif sans vente."
            ),
            texte_long=(
                "La deuxième étape du rebalancement utilise les flux entrants (versements "
                "mensuels, dividendes, coupons) pour réduire les écarts à la cible sans céder "
                "d'actifs existants. Cette technique dite de « cashflow rebalancing » est "
                "fiscalement nulle : on achète les classes sous-pondérées sans vendre. "
                f"Avec {flux_mensuel:,.0f} €/mois, l'écart cible peut être absorbé sur "
                "plusieurs mois sans déclencher d'impôt. "
                "Avantage supplémentaire : le cost averaging (DCA) réduit le risque de "
                "mauvais timing d'achat (Dollar-Cost Averaging, Samuelson 1963)."
            ),
            source=(
                "Samuelson, P. (1963). Risk and Uncertainty: A Fallacy of Large Numbers. "
                "Scientia, 98, 108-113. "
                "Vanguard Research (2019). Getting back on track: A guide to smart rebalancing."
            ),
            gain_eur=0.0,
        ),
        Explication(
            section="rebalancement.etape_3_ventes",
            titre="Étape 3 : ventes CTO en dernier recours",
            texte_court=(
                f"Ventes CTO ({montant_ventes:,.0f} € en dernier recours) — "
                f"coût fiscal net estimé {cout_fiscal:,.0f} €. "
                "Priorité aux lignes en moins-value pour compenser fiscalement."
            ),
            texte_long=(
                "Lorsque les étapes 1 et 2 ne suffisent pas à ramener l'allocation dans les "
                "bandes de tolérance, des cessions CTO sont nécessaires. "
                "La stratégie optimale : céder en priorité les lignes en moins-value latente "
                "pour créer des déficits fiscaux (tax-loss harvesting, Art. 150-0 D CGI), "
                "puis les lignes en plus-value minimale. "
                "Les moins-values sont reportables 10 ans sur les plus-values de même nature. "
                f"Montant de ventes CTO : {montant_ventes:,.0f} €. "
                f"Coût fiscal net après imputation des moins-values : {cout_fiscal:,.0f} €."
            ),
            formule=("Impôt net = (PV brutes − MV imputables) × PFU 30 %"),
            source=(
                "Art. 150-0 A CGI (réalisation des PV). "
                "Art. 150-0 D CGI (imputation des moins-values, report 10 ans). "
                "Vanguard Research (2019). Getting back on track."
            ),
            gain_eur=round(-cout_fiscal, 2) if cout_fiscal else None,
        ),
    ]
