"""
Module de calcul fiscal — Boglehead FR 2026
Sub-package reorganization with full backward compatibility

This package replaces the old src/fiscalite.py module while maintaining
the exact same public API for existing tests.
"""

from pathlib import Path

import yaml

# Import all sub-modules first (fix E402 errors)
from .assurance_vie import (
    ContratAV,
    RachatAV,
    VersementAV,
    calculer_fiscalite_rachat,
)
from .cascade import (
    LigneCalcul,
    ResultatFiscal,
    calculer_fiscalite_operation,
)
from .constantes import (
    AV_ABATTEMENT_CELIBATAIRE,
    AV_ABATTEMENT_COUPLE,
    AV_SEUIL_150K,
    AV_SEUIL_300K,
    BAREME_IR_2026,
    CDHR_TAUX_PLANCHER,
    CEHR_TRANCHES_CELIBATAIRE,
    CEHR_TRANCHES_COUPLE,
    IS_SEUIL,
    IS_TAUX_NORMAL,
    IS_TAUX_REDUIT,
    PEA_PLAFOND_VERSEMENTS,
    PEA_PME_PLAFOND_VERSEMENTS,
    PER_PLAFOND_DEDUCTION_FORFAIT,
    TAUX_PFU_IR,
    TAUX_PFU_TOTAL,
    TAUX_PS,
)
from .contrat_cap_is import (
    calculer_base_taxable_contrat_cap_is,
    calculer_is_contrat_cap,
    comparer_contrat_cap_vs_mtm,
)
from .cto_ir import (
    calculer_fiscalite_cession_cto,
    comparer_pfu_vs_bareme,
)
from .cto_is import (
    calculer_mtm_annuel,
    comparer_cto_is_vs_contrat_cap_is,
    detecter_piege_mtm,
)
from .is_calc import calculer_is
from .pea import (
    avantage_pea_vs_cto,
    calculer_fiscalite_retrait_pea,
    verifier_plafond_pea,
)
from .per import (
    calculer_avantage_entree_per,
    calculer_fiscalite_sortie_per,
    calculer_plafond_deduction_per,
    comparer_per_vs_cto,
)
from .pfu import (
    calculer_cdhr,
    calculer_cehr,
    calculer_pfu_complet,
)
from .prelevements_sociaux import (
    calculer_ps,
    calculer_ps_av,
    taux_ps_effectif,
)
from .tmi import (
    calculer_decote,
    calculer_ir_brut_bareme,
    calculer_ir_complet,
    calculer_parts_fiscales,
    calculer_plafonnement_qf,
    calculer_taux_moyen,
    calculer_tmi,
)

# ============================================================================
# BACKWARD COMPATIBILITY: Re-export all functions from old fiscalite.py
# These functions ensure existing code continues to work unchanged
# ============================================================================


# Original function from fiscalite.py
def charger_params_fiscaux(chemin_yaml: str = None) -> dict:
    """
    Charge les paramètres fiscaux depuis le fichier YAML.

    This is the original function from fiscalite.py, kept for backward compatibility.
    """
    if chemin_yaml is None:
        chemin_yaml = Path(__file__).parent.parent.parent / "config" / "fiscalite_2026.yaml"
    with open(chemin_yaml, encoding="utf-8") as f:
        return yaml.safe_load(f)


# Original calculer_pfu from fiscalite.py
def calculer_pfu(montant_brut: float, params: dict) -> dict:
    """
    Calcule le PFU (Prélèvement Forfaitaire Unique) sur dividendes ou plus-values.

    Returns dict avec: ir, ps, total, net

    Original function signature preserved for backward compatibility.
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


# Original calculer_taux_marginal_reel from fiscalite.py
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

    Original function signature preserved for backward compatibility.
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

    taux_total = taux_base + cehr_taux
    return taux_total


# Original avantage_fiscal_pea from fiscalite.py
def avantage_fiscal_pea(gain: float, params: dict, apres_5_ans: bool = True) -> dict:
    """
    Calcule l'avantage fiscal PEA vs CTO perso.

    Après 5 ans : seuls les PS (18,6%) sont dus sur les gains.
    CTO : PFU 31,4%.

    Original function signature preserved for backward compatibility.
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


# Original calculer_avantage_per from fiscalite.py
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

    Original function signature preserved for backward compatibility.
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


# Export all for convenient import
__all__ = [
    # Backward compatibility (old API)
    "charger_params_fiscaux",
    "calculer_pfu",
    "calculer_taux_marginal_reel",
    "calculer_is",
    "calculer_base_taxable_contrat_cap_is",
    "avantage_fiscal_pea",
    "calculer_avantage_per",
    # Constants
    "TAUX_PS",
    "TAUX_PFU_IR",
    "TAUX_PFU_TOTAL",
    "IS_SEUIL",
    "IS_TAUX_REDUIT",
    "IS_TAUX_NORMAL",
    "BAREME_IR_2026",
    "CEHR_TRANCHES_CELIBATAIRE",
    "CEHR_TRANCHES_COUPLE",
    "CDHR_TAUX_PLANCHER",
    "AV_SEUIL_150K",
    "AV_SEUIL_300K",
    "AV_ABATTEMENT_CELIBATAIRE",
    "AV_ABATTEMENT_COUPLE",
    "PEA_PLAFOND_VERSEMENTS",
    "PEA_PME_PLAFOND_VERSEMENTS",
    "PER_PLAFOND_DEDUCTION_FORFAIT",
    # Cascade
    "LigneCalcul",
    "ResultatFiscal",
    "calculer_fiscalite_operation",
    # PS
    "calculer_ps",
    "calculer_ps_av",
    "taux_ps_effectif",
    # TMI
    "calculer_parts_fiscales",
    "calculer_ir_brut_bareme",
    "calculer_plafonnement_qf",
    "calculer_decote",
    "calculer_tmi",
    "calculer_taux_moyen",
    "calculer_ir_complet",
    # PFU
    "calculer_cehr",
    "calculer_cdhr",
    "calculer_pfu_complet",
    # PEA
    "verifier_plafond_pea",
    "calculer_fiscalite_retrait_pea",
    "avantage_pea_vs_cto",
    # PER
    "calculer_plafond_deduction_per",
    "calculer_avantage_entree_per",
    "calculer_fiscalite_sortie_per",
    "comparer_per_vs_cto",
    # AV
    "VersementAV",
    "RachatAV",
    "ContratAV",
    "calculer_fiscalite_rachat",
    # CTO IR
    "calculer_fiscalite_cession_cto",
    "comparer_pfu_vs_bareme",
    # CTO IS
    "detecter_piege_mtm",
    "calculer_mtm_annuel",
    "comparer_cto_is_vs_contrat_cap_is",
    # Contrat cap IS
    "calculer_is_contrat_cap",
    "comparer_contrat_cap_vs_mtm",
]
