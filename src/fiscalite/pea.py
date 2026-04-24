"""
PEA et PEA-PME
Art. 150-0 A CGI, Art. 157 CGI
"""

from .cascade import ResultatFiscal
from .constantes import (
    PEA_DUREE_2_ANS,
    PEA_DUREE_5_ANS,
    PEA_PLAFOND_CUMUL,
    PEA_PLAFOND_VERSEMENTS,
    PEA_PME_PLAFOND_VERSEMENTS,
    TAUX_PFU_IR,
    TAUX_PS,
)
from .prelevements_sociaux import calculer_ps


def verifier_plafond_pea(versements_pea: float, versements_pea_pme: float = 0.0) -> dict:
    """
    Vérifie le respect des plafonds PEA/PEA-PME.

    Args:
        versements_pea: Total des versements PEA
        versements_pea_pme: Total des versements PEA-PME

    Returns:
        dict avec respect_plafond, depassement, details

    Source: Art. 163 quinquies D CGI
    """
    depassement_pea = max(0, versements_pea - PEA_PLAFOND_VERSEMENTS)
    depassement_pea_pme = max(0, versements_pea_pme - PEA_PME_PLAFOND_VERSEMENTS)
    depassement_cumul = max(0, versements_pea + versements_pea_pme - PEA_PLAFOND_CUMUL)

    respect_plafond = depassement_pea == 0 and depassement_pea_pme == 0 and depassement_cumul == 0

    return {
        "respect_plafond": respect_plafond,
        "depassement_pea": depassement_pea,
        "depassement_pea_pme": depassement_pea_pme,
        "depassement_cumul": depassement_cumul,
        "plafond_pea": PEA_PLAFOND_VERSEMENTS,
        "plafond_pea_pme": PEA_PME_PLAFOND_VERSEMENTS,
        "plafond_cumul": PEA_PLAFOND_CUMUL,
    }


def calculer_fiscalite_retrait_pea(operation: dict, profil: dict) -> ResultatFiscal:
    """
    Calcule la fiscalité d'un retrait PEA selon la durée de détention.

    Durée < 2 ans : IR au TMI + PS
    Durée 2-5 ans : IR 12.8% + PS
    Durée > 5 ans : Exonération IR, PS uniquement

    Args:
        operation: dict avec
            - montant_brut: float (montant du retrait)
            - gains: float (part de plus-value)
            - duree_detention: float (en années)
            - type_pea: "pea" ou "pea_pme"
            - cas_force_majeure: bool (optionnel)
        profil: dict avec situation, rfr, tmi

    Returns:
        ResultatFiscal avec cascade

    Source: Art. 150-0 A CGI
    """
    montant_brut = operation.get("montant_brut", 0.0)
    gains = operation.get("gains", montant_brut)
    duree_detention = operation.get("duree_detention", 0.0)
    type_pea = operation.get("type_pea", "pea")
    cas_force_majeure = operation.get("cas_force_majeure", False)
    tmi = profil.get("tmi", 0.30)

    resultat = ResultatFiscal(
        montant_brut=montant_brut,
        impot_ir=0.0,
        prelevements_sociaux=0.0,
        total_impots=0.0,
        montant_net=0.0,
        taux_effectif=0.0,
    )

    # Cas force majeure : exonération totale
    if cas_force_majeure:
        resultat.montant_net = montant_brut
        resultat.ajouter_ligne(
            libelle="Retrait PEA (cas force majeure)",
            montant=montant_brut,
            formule="Exonération totale IR + PS",
            source="Art. 150-0 A-II-1° CGI",
        )
        resultat.ajouter_avertissement(
            "Cas de force majeure : exonération totale IR et PS (invalidité, licenciement, etc.)"
        )
        return resultat

    # Durée > 5 ans : exonération IR, PS uniquement
    if duree_detention >= PEA_DUREE_5_ANS:
        ps_result = calculer_ps(gains)
        resultat.prelevements_sociaux = ps_result["ps"]
        resultat.ajouter_ligne(
            libelle=f"Gains {type_pea.upper()}",
            montant=gains,
            formule="Plus-values réalisées",
            source="Art. 150-0 A CGI",
        )
        resultat.ajouter_ligne(
            libelle="IR (exonération > 5 ans)",
            montant=0.0,
            formule="Exonération IR après 5 ans",
            source="Art. 150-0 A-I CGI",
        )
        resultat.ajouter_ligne(
            libelle="Prélèvements sociaux",
            montant=ps_result["ps"],
            formule=f"{gains:,.2f} × {TAUX_PS:.1%}",
            source="Art. L.136-8 CSS",
        )

    # Durée 2-5 ans : IR 12.8% + PS
    elif duree_detention >= PEA_DUREE_2_ANS:
        ir = gains * TAUX_PFU_IR
        ps_result = calculer_ps(gains)
        resultat.impot_ir = ir
        resultat.prelevements_sociaux = ps_result["ps"]
        resultat.ajouter_ligne(
            libelle=f"Gains {type_pea.upper()}",
            montant=gains,
            formule="Plus-values réalisées",
            source="Art. 150-0 A CGI",
        )
        resultat.ajouter_ligne(
            libelle="IR (12.8%, durée 2-5 ans)",
            montant=ir,
            formule=f"{gains:,.2f} × {TAUX_PFU_IR:.1%}",
            source="Art. 150-0 A-I-1°-b CGI",
        )
        resultat.ajouter_ligne(
            libelle="Prélèvements sociaux",
            montant=ps_result["ps"],
            formule=f"{gains:,.2f} × {TAUX_PS:.1%}",
            source="Art. L.136-8 CSS",
        )
        resultat.ajouter_avertissement("Retrait entre 2 et 5 ans : IR 12.8% + PS 18.6% = 31.4%")

    # Durée < 2 ans : IR au TMI + PS
    else:
        ir = gains * tmi
        ps_result = calculer_ps(gains)
        resultat.impot_ir = ir
        resultat.prelevements_sociaux = ps_result["ps"]
        resultat.ajouter_ligne(
            libelle=f"Gains {type_pea.upper()}",
            montant=gains,
            formule="Plus-values réalisées",
            source="Art. 150-0 A CGI",
        )
        resultat.ajouter_ligne(
            libelle=f"IR (TMI {tmi:.1%}, durée < 2 ans)",
            montant=ir,
            formule=f"{gains:,.2f} × {tmi:.1%}",
            source="Art. 150-0 A-I-1°-a CGI",
        )
        resultat.ajouter_ligne(
            libelle="Prélèvements sociaux",
            montant=ps_result["ps"],
            formule=f"{gains:,.2f} × {TAUX_PS:.1%}",
            source="Art. L.136-8 CSS",
        )
        resultat.ajouter_avertissement(
            f"Retrait avant 2 ans : IR au TMI ({tmi:.1%}) + PS 18.6% = {tmi + TAUX_PS:.1%}"
        )

    # Total
    resultat.total_impots = resultat.impot_ir + resultat.prelevements_sociaux
    resultat.montant_net = montant_brut - resultat.total_impots
    resultat.taux_effectif = resultat.total_impots / montant_brut if montant_brut > 0 else 0.0

    resultat.ajouter_ligne(
        libelle="TOTAL IMPÔTS",
        montant=resultat.total_impots,
        formule="IR + PS",
        source="",
    )
    resultat.ajouter_ligne(
        libelle="NET APRÈS IMPÔTS",
        montant=resultat.montant_net,
        formule=f"{montant_brut:,.2f} - {resultat.total_impots:,.2f}",
        source="",
    )

    return resultat


def avantage_pea_vs_cto(gains: float, duree_detention: float, tmi: float = 0.30) -> dict:
    """
    Compare l'avantage fiscal PEA vs CTO.

    Args:
        gains: Montant des gains
        duree_detention: Durée en années
        tmi: Taux marginal d'imposition

    Returns:
        dict avec économie, impots_pea, impots_cto
    """
    # PEA
    if duree_detention >= PEA_DUREE_5_ANS:
        impots_pea = gains * TAUX_PS
        taux_effectif_pea = TAUX_PS
    elif duree_detention >= PEA_DUREE_2_ANS:
        impots_pea = gains * (TAUX_PFU_IR + TAUX_PS)
        taux_effectif_pea = TAUX_PFU_IR + TAUX_PS
    else:
        impots_pea = gains * (tmi + TAUX_PS)
        taux_effectif_pea = tmi + TAUX_PS

    # CTO : PFU complet
    impots_cto = gains * (TAUX_PFU_IR + TAUX_PS)
    taux_effectif_cto = TAUX_PFU_IR + TAUX_PS

    economie = impots_cto - impots_pea

    return {
        "gains": gains,
        "duree_detention": duree_detention,
        "impots_pea": impots_pea,
        "impots_cto": impots_cto,
        "economie": economie,
        "taux_effectif_pea": taux_effectif_pea,
        "taux_effectif_cto": taux_effectif_cto,
    }
