"""
Module de rebalancement Boglehead
Calcul des bandes de tolérance et du coût fiscal d'arbitrage
"""
from typing import Dict, Optional


def calculer_derive_allocation(
    allocation_actuelle: dict,
    allocation_cible: dict,
    bande_tolerance_abs: float = 0.05,
    bande_tolerance_rel: float = 0.25,
) -> dict:
    """
    Calcule la dérive de l'allocation par rapport à la cible.

    Méthode Larry Swedroe : rebalancer si dérive > 25% de la valeur cible (relatif)
    Ou méthode simplifiée : rebalancer si dérive > 5 points absolus

    Returns: dict avec dérive par classe et recommandation
    """
    resultats = {}
    rebalancement_necessaire = False

    for classe in allocation_cible:
        if classe == "commentaire":
            continue
        cible = allocation_cible[classe]
        actuelle = allocation_actuelle.get(classe, 0.0)
        derive_abs = actuelle - cible
        derive_rel = abs(derive_abs) / cible if cible > 0 else 0.0

        action = "OK"
        if abs(derive_abs) > bande_tolerance_abs or derive_rel > bande_tolerance_rel:
            action = "VENDRE" if derive_abs > 0 else "ACHETER"
            rebalancement_necessaire = True

        resultats[classe] = {
            "cible": cible,
            "actuelle": actuelle,
            "derive_abs": round(derive_abs, 4),
            "derive_rel": round(derive_rel, 4),
            "action": action,
        }

    return {
        "details": resultats,
        "rebalancement_necessaire": rebalancement_necessaire,
    }


def calculer_cout_fiscal_arbitrage(
    montant_cede: float,
    prix_revient: float,
    enveloppe_id: str,
    params_fiscaux: dict,
    rfr: float = 0.0,
) -> dict:
    """
    Calcule le coût fiscal d'un arbitrage (cession d'ETF) selon l'enveloppe.

    Returns: coût fiscal en € et en % de la plus-value
    """
    plus_value = montant_cede - prix_revient

    if plus_value <= 0:
        return {
            "plus_value": plus_value,
            "cout_fiscal": 0.0,
            "net_apres_impots": montant_cede,
            "taux_effectif": 0.0,
            "detail": "Moins-value ou neutre",
        }

    taux_ps = params_fiscaux["prelevements_sociaux"]["taux_global"]
    taux_ir = params_fiscaux["pfu"]["taux_ir"]

    if enveloppe_id in ("PEA", "PER", "PEE"):
        cout = 0.0
        detail = "Arbitrage intra-enveloppe — pas de fiscalité"
    elif enveloppe_id == "CTO_perso":
        cout = plus_value * (taux_ir + taux_ps)
        detail = f"PFU {(taux_ir + taux_ps) * 100:.1f}%"
    elif enveloppe_id in ("CTO_IS", "Contrat_Cap_IS"):
        taux_is = params_fiscaux["is"]["taux_reduit"]
        cout = plus_value * taux_is
        detail = f"IS {taux_is * 100:.0f}%"
    else:
        cout = 0.0
        detail = "Enveloppe inconnue"

    return {
        "plus_value": plus_value,
        "cout_fiscal": cout,
        "net_apres_impots": montant_cede - cout,
        "taux_effectif": cout / plus_value if plus_value > 0 else 0.0,
        "detail": detail,
    }


def recommander_rebalancement(
    allocation_actuelle: dict,
    allocation_cible: dict,
    patrimoine_total: float,
    versements_prevus: float,
    params_fiscaux: dict,
    enveloppes_actives: list,
) -> dict:
    """
    Recommande la méthode de rebalancement optimale :
    1. Par les versements (sans coût fiscal) — à privilégier
    2. Par arbitrage intra-enveloppe exonérée (PEA, PER, PEE)
    3. Par arbitrage CTO (coût fiscal)
    """
    derive = calculer_derive_allocation(allocation_actuelle, allocation_cible)

    recommandations = []

    for classe, info in derive["details"].items():
        if info["action"] == "ACHETER":
            manque = abs(info["derive_abs"]) * patrimoine_total
            if versements_prevus >= manque:
                recommandations.append(
                    {
                        "classe": classe,
                        "action": f"Orienter versements vers {classe}",
                        "methode": "Versement",
                        "cout_fiscal": 0,
                        "priorite": 1,
                    }
                )
            else:
                recommandations.append(
                    {
                        "classe": classe,
                        "action": f"Acheter {manque:.0f}€ de {classe}",
                        "methode": "Arbitrage PEA/PER si disponible, sinon CTO",
                        "cout_fiscal": "Variable selon enveloppe",
                        "priorite": 2,
                    }
                )
        elif info["action"] == "VENDRE":
            exces = info["derive_abs"] * patrimoine_total
            recommandations.append(
                {
                    "classe": classe,
                    "action": f"Réduire {exces:.0f}€ de {classe}",
                    "methode": "Arbitrage intra-enveloppe exonérée en priorité",
                    "cout_fiscal": "Variable selon enveloppe",
                    "priorite": 2,
                }
            )

    return {
        "derive": derive,
        "recommandations": recommandations,
        "methode_preferee": "Versements" if versements_prevus > 0 else "Arbitrage",
    }
