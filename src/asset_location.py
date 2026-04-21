"""
Module d'asset location multi-enveloppes
Logique de répartition optimale des ETF entre les enveloppes fiscales
"""
from typing import List, Dict, Optional


# Règles de priorité d'asset location Boglehead FR
PRIORITES_ASSET_LOCATION = {
    "Actions_PEA": ["PEA", "CTO_perso", "PER"],
    "Actions_monde_synth": ["PEA", "PER", "CTO_perso"],
    "Actions_hors_PEA": ["PER", "CTO_perso", "Contrat_Cap_IS"],
    "Obligations": ["PER", "Contrat_Cap_IS", "CTO_IS", "CTO_perso"],
    "REIT": ["PER", "CTO_perso"],
    "Or_ETC": ["CTO_perso", "PER"],
    "Monetaire": ["CTO_IS", "CTO_perso"],
    "Actions_IS": ["Contrat_Cap_IS", "CTO_IS"],
}


def calculer_gain_fiscal_enveloppe(
    etf: dict,
    enveloppe_id: str,
    montant: float,
    horizon_ans: int,
    rendement_annuel: float,
    params_fiscaux: dict,
) -> dict:
    """
    Calcule le gain net après impôts pour un ETF dans une enveloppe donnée.
    Comparé au scénario naïf CTO perso.
    """
    taux_ps = params_fiscaux["prelevements_sociaux"]["taux_global"]
    taux_ir_pfu = params_fiscaux["pfu"]["taux_ir"]

    capital_brut = montant * ((1 + rendement_annuel) ** horizon_ans)
    gain_brut = capital_brut - montant

    if enveloppe_id == "PEA":
        # Après 5 ans : PS uniquement
        impots = gain_brut * taux_ps
        taux_effectif = taux_ps
    elif enveloppe_id == "PER":
        # PS sur gains à la sortie (simplifié)
        impots = gain_brut * taux_ps
        taux_effectif = taux_ps
    elif enveloppe_id == "PEE":
        # Exonération IR, PS sur gains
        impots = gain_brut * taux_ps
        taux_effectif = taux_ps
    elif enveloppe_id in ("CTO_IS", "Contrat_Cap_IS"):
        taux_is = params_fiscaux["is"]["taux_reduit"]  # taux simplifié
        impots = gain_brut * taux_is
        taux_effectif = taux_is
    else:  # CTO_perso — référence
        impots = gain_brut * (taux_ir_pfu + taux_ps)
        taux_effectif = taux_ir_pfu + taux_ps

    capital_net = capital_brut - impots

    # Scénario naïf CTO perso
    impots_cto = gain_brut * (taux_ir_pfu + taux_ps)
    capital_cto = capital_brut - impots_cto

    return {
        "enveloppe": enveloppe_id,
        "montant_initial": montant,
        "capital_brut": capital_brut,
        "impots": impots,
        "capital_net": capital_net,
        "taux_effectif": taux_effectif,
        "avantage_vs_cto": capital_net - capital_cto,
        "horizon_ans": horizon_ans,
    }


def suggerer_asset_location(
    etfs: List[dict],
    enveloppes_dispo: List[str],
    allocation_cible: dict,
    patrimoine_total: float,
) -> List[dict]:
    """
    Suggère une répartition ETF × Enveloppe basée sur les règles Boglehead FR.

    Returns: liste de suggestions (isin, enveloppe_suggeree, raison)
    """
    suggestions = []

    for etf in etfs:
        meilleure_env = None
        for env_id in enveloppes_dispo:
            if etf.get("eligibilite", {}).get(env_id, False):
                meilleure_env = env_id
                break

        if meilleure_env:
            suggestions.append(
                {
                    "isin": etf.get("isin"),
                    "nom": etf.get("nom"),
                    "enveloppe_suggeree": meilleure_env,
                    "raison": f"Éligible {meilleure_env} — optimisation fiscale",
                }
            )

    return suggestions
