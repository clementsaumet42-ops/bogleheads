"""
Contrat de capitalisation à l'IS
Art. 238 septies E CGI
"""

from .cascade import ResultatFiscal
from .constantes import CONTRAT_CAP_IS_COEF, IS_SEUIL, IS_TAUX_NORMAL, IS_TAUX_REDUIT


def calculer_base_taxable_contrat_cap_is(prime: float, tme: float, params: dict) -> float:
    """
    Calcule la base taxable annuelle d'un contrat de capitalisation à l'IS.

    Formule : 105% × TME × prime versée

    Args:
        prime: Montant de la prime versée (capital investi)
        tme: TME (Taux Moyen des Emprunts d'État)
        params: Paramètres fiscaux (non utilisé, présent pour compatibilité)

    Returns:
        Base taxable en €

    Source: Art. 238 septies E CGI
    """
    return CONTRAT_CAP_IS_COEF * tme * prime


def calculer_is_contrat_cap(prime: float, tme: float, annees: int = 1) -> ResultatFiscal:
    """
    Calcule l'IS annuel sur un contrat de capitalisation IS.

    Args:
        prime: Prime versée (capital investi)
        tme: TME
        annees: Nombre d'années (pour cumul)

    Returns:
        ResultatFiscal avec cascade
    """
    resultat = ResultatFiscal(
        montant_brut=prime,
        impot_ir=0.0,  # IS, pas IR
        prelevements_sociaux=0.0,
        total_impots=0.0,
        montant_net=0.0,
        taux_effectif=0.0,
    )

    # Base taxable annuelle
    base_annuelle = calculer_base_taxable_contrat_cap_is(prime, tme, {})

    resultat.ajouter_ligne(
        libelle="Prime versée",
        montant=prime,
        formule="Capital investi",
        source="Art. 238 septies E CGI",
    )

    resultat.ajouter_ligne(
        libelle=f"Base taxable annuelle (105% × {tme:.1%} × prime)",
        montant=base_annuelle,
        formule=f"{CONTRAT_CAP_IS_COEF:.2f} × {tme:.3f} × {prime:,.2f}",
        source="Art. 238 septies E CGI",
    )

    # IS annuel
    if base_annuelle <= IS_SEUIL:
        is_annuel = base_annuelle * IS_TAUX_REDUIT
        taux_is = IS_TAUX_REDUIT
    else:
        is_annuel = IS_SEUIL * IS_TAUX_REDUIT + (base_annuelle - IS_SEUIL) * IS_TAUX_NORMAL
        taux_is = is_annuel / base_annuelle

    resultat.ajouter_ligne(
        libelle=f"IS annuel (taux effectif {taux_is:.1%})",
        montant=is_annuel,
        formule=f"{base_annuelle:,.2f} × IS",
        source="Art. 219 CGI",
    )

    # Cumul sur plusieurs années
    is_cumule = is_annuel * annees

    if annees > 1:
        resultat.ajouter_ligne(
            libelle=f"IS cumulé sur {annees} ans",
            montant=is_cumule,
            formule=f"{is_annuel:,.2f} × {annees}",
            source="",
        )
    else:
        is_cumule = is_annuel

    resultat.total_impots = is_cumule
    resultat.montant_net = prime - is_cumule
    resultat.taux_effectif = is_cumule / prime if prime > 0 else 0.0

    resultat.ajouter_ligne(
        libelle="TOTAL IS",
        montant=is_cumule,
        formule="IS cumulé",
        source="",
    )

    resultat.ajouter_avertissement(
        "À la cession : régularisation = IS sur PV réelle - IS forfaitaire déjà payé"
    )
    resultat.ajouter_avertissement(
        f"Base taxable très faible si TME bas (ici {tme:.1%}) : {base_annuelle / prime:.2%} du capital"
    )

    return resultat


def comparer_contrat_cap_vs_mtm(
    capital: float,
    rendement_reel: float,
    tme: float,
    horizon_ans: int,
) -> dict:
    """
    Compare contrat cap IS (base forfaitaire) vs CTO IS (MTM).

    Args:
        capital: Capital initial
        rendement_reel: Rendement réel du portefeuille (ex: 0.06)
        tme: TME (base forfaitaire)
        horizon_ans: Horizon en années

    Returns:
        dict avec comparaison détaillée
    """
    # Contrat cap : base forfaitaire
    base_forfaitaire_annuelle = calculer_base_taxable_contrat_cap_is(capital, tme, {})
    if base_forfaitaire_annuelle <= IS_SEUIL:
        is_forfait_annuel = base_forfaitaire_annuelle * IS_TAUX_REDUIT
    else:
        is_forfait_annuel = (
            IS_SEUIL * IS_TAUX_REDUIT + (base_forfaitaire_annuelle - IS_SEUIL) * IS_TAUX_NORMAL
        )
    is_forfait_cumule = is_forfait_annuel * horizon_ans

    # MTM : imposition réelle sur gains annuels
    capital_mtm = capital
    is_mtm_cumule = 0.0
    for _annee in range(1, horizon_ans + 1):
        gain_annuel = capital_mtm * rendement_reel
        if gain_annuel <= IS_SEUIL:
            is_mtm_annuel = gain_annuel * IS_TAUX_REDUIT
        else:
            is_mtm_annuel = IS_SEUIL * IS_TAUX_REDUIT + (gain_annuel - IS_SEUIL) * IS_TAUX_NORMAL
        is_mtm_cumule += is_mtm_annuel
        capital_mtm += gain_annuel - is_mtm_annuel

    # Capital final contrat cap (croissance après IS forfaitaire)
    capital_contrat = capital
    for _annee in range(1, horizon_ans + 1):
        gain_annuel = capital_contrat * rendement_reel
        capital_contrat += gain_annuel - is_forfait_annuel

    # Avantage
    economie_is = is_mtm_cumule - is_forfait_cumule
    avantage_capital = capital_contrat - capital_mtm

    return {
        "capital_initial": capital,
        "rendement_reel": rendement_reel,
        "tme": tme,
        "horizon_ans": horizon_ans,
        "base_forfaitaire_annuelle": base_forfaitaire_annuelle,
        "is_forfait_annuel": is_forfait_annuel,
        "is_forfait_cumule": is_forfait_cumule,
        "is_mtm_cumule": is_mtm_cumule,
        "capital_final_contrat_cap": capital_contrat,
        "capital_final_mtm": capital_mtm,
        "economie_is": economie_is,
        "avantage_capital": avantage_capital,
        "avantage_pct": avantage_capital / capital if capital > 0 else 0.0,
        "conclusion": "Contrat cap IS avantageux si rendement réel > TME"
        if rendement_reel > tme
        else "MTM neutre ou avantageux si rendement réel ≤ TME",
    }
