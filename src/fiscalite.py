"""
Module de calcul fiscal — Boglehead FR 2026
Règles fiscales : PFU, PS, CEHR, CDHR, IS, Contrat Capitalisation IS
"""

from pathlib import Path

import yaml


def charger_params_fiscaux(chemin_yaml: str = None) -> dict:
    """Charge les paramètres fiscaux depuis le fichier YAML."""
    if chemin_yaml is None:
        chemin_yaml = Path(__file__).parent.parent / "config" / "fiscalite_2026.yaml"
    with open(chemin_yaml, encoding="utf-8") as f:
        return yaml.safe_load(f)


def calculer_pfu(montant_brut: float, params: dict) -> dict:
    """
    Calcule le PFU (Prélèvement Forfaitaire Unique) sur dividendes ou plus-values.

    Returns dict avec: ir, ps, total, net
    """
    taux_ir = params["pfu"]["taux_ir"]
    taux_ps = params["prelevements_sociaux"]["taux_global"]
    ir = montant_brut * taux_ir
    ps = montant_brut * taux_ps
    total = ir + ps
    return {
        "brut": montant_brut,
        "ir": ir,
        "ps": ps,
        "total_impots": total,
        "net": montant_brut - total,
        "taux_effectif": total / montant_brut if montant_brut > 0 else 0,
    }


def calculer_taux_marginal_reel(
    rfr: float,
    tmi: float,
    params: dict,
    situation: str = "celibataire",
) -> float:
    """
    Calcule le taux marginal réel sur les revenus du capital (PFU + CEHR + CDHR).

    Args:
        rfr: Revenu Fiscal de Référence annuel
        tmi: Taux Marginal d'Imposition (0.30, 0.41, 0.45)
        params: paramètres fiscaux chargés depuis YAML
        situation: 'celibataire' ou 'couple'

    Returns:
        Taux marginal effectif sur les revenus du capital
    """
    taux_ps = params["prelevements_sociaux"]["taux_global"]
    taux_ir_pfu = params["pfu"]["taux_ir"]
    taux_base = taux_ir_pfu + taux_ps  # PFU + PS

    # CEHR
    cehr_taux = 0.0
    tranches_cehr = params["cehr"][f"tranches_{situation}"]
    for tranche in tranches_cehr:
        if rfr >= tranche["rfr_min"]:
            cehr_taux = tranche["taux"]

    # CDHR : assure plancher de 20% sur taux effectif global
    # Calcul précis de la CDHR nécessite un simulateur fiscal complet (hors scope ici)
    # On se contente d'indiquer son applicabilité via le taux total retourné

    taux_total = taux_base + cehr_taux
    return taux_total


def calculer_is(benefice: float, params: dict) -> dict:
    """
    Calcule l'IS sur un bénéfice (taux réduit 15% + taux normal 25%).
    """
    seuil = params["is"]["seuil_taux_reduit"]
    taux_reduit = params["is"]["taux_reduit"]
    taux_normal = params["is"]["taux_normal"]

    if benefice <= seuil:
        is_du = benefice * taux_reduit
        taux_effectif = taux_reduit
    else:
        is_du = seuil * taux_reduit + (benefice - seuil) * taux_normal
        taux_effectif = is_du / benefice

    return {
        "benefice": benefice,
        "is_du": is_du,
        "net": benefice - is_du,
        "taux_effectif": taux_effectif,
    }


def calculer_base_taxable_contrat_cap_is(prime: float, tme: float, params: dict) -> float:
    """
    Calcule la base taxable annuelle d'un contrat de capitalisation à l'IS.
    Formule : 105% × TME × prime
    Art. 238 septies E CGI
    """
    return 1.05 * tme * prime


def avantage_fiscal_pea(gain: float, params: dict, apres_5_ans: bool = True) -> dict:
    """
    Calcule l'avantage fiscal PEA vs CTO perso.

    Après 5 ans : seuls les PS (18,6%) sont dus sur les gains.
    CTO : PFU 31,4%.
    """
    taux_ps = params["prelevements_sociaux"]["taux_global"]
    taux_ir_pfu = params["pfu"]["taux_ir"]

    if apres_5_ans:
        impots_pea = gain * taux_ps
        taux_effectif_pea = taux_ps
    else:
        impots_pea = gain * (taux_ir_pfu + taux_ps)
        taux_effectif_pea = taux_ir_pfu + taux_ps

    # CTO perso : PFU complet
    impots_cto = gain * (taux_ir_pfu + taux_ps)

    return {
        "gain": gain,
        "impots_pea": impots_pea,
        "impots_cto_ref": impots_cto,
        "economie": impots_cto - impots_pea,
        "taux_effectif_pea": taux_effectif_pea,
        "apres_5_ans": apres_5_ans,
    }


def calculer_avantage_per(
    versement: float,
    tmi_actuelle: float,
    tmi_retraite: float,
    rendement_annuel: float,
    horizon_ans: int,
    params: dict,
) -> dict:
    """
    Compare l'investissement via PER (déduction + fiscalité sortie) vs CTO perso.

    Returns: économie nette estimée en € sur l'horizon
    """
    taux_ps = params["prelevements_sociaux"]["taux_global"]
    taux_ir_pfu = params["pfu"]["taux_ir"]

    economie_entree = versement * tmi_actuelle

    # Croissance du capital
    capital_per_brut = versement * ((1 + rendement_annuel) ** horizon_ans)
    capital_cto_brut = versement * ((1 + rendement_annuel) ** horizon_ans)

    # Fiscalité sortie PER : IR sur capital + PS sur gains
    gains_per = capital_per_brut - versement
    impots_sortie_per = (versement * tmi_retraite) + (gains_per * taux_ps)
    # L'économie d'entrée est elle-même réinvestie
    capital_per_net = (
        capital_per_brut
        - impots_sortie_per
        + (economie_entree * ((1 + rendement_annuel) ** horizon_ans))
    )

    # Fiscalité CTO : PFU sur gains à la cession
    gains_cto = capital_cto_brut - versement
    impots_cto = gains_cto * (taux_ir_pfu + taux_ps)
    capital_cto_net = capital_cto_brut - impots_cto

    return {
        "versement_initial": versement,
        "capital_per_net": capital_per_net,
        "capital_cto_net": capital_cto_net,
        "avantage_per": capital_per_net - capital_cto_net,
        "horizon_ans": horizon_ans,
    }
