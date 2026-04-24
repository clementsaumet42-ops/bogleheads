"""
PFU (Prélèvement Forfaitaire Unique) - Flat Tax
Avec CEHR et CDHR
Art. 200 A CGI, Art. 223 sexies CGI, Art. 223 terdecies CGI
"""

from .cascade import ResultatFiscal
from .constantes import (
    CDHR_SEUIL_CELIBATAIRE,
    CDHR_SEUIL_COUPLE,
    CDHR_TAUX_PLANCHER,
    CEHR_TRANCHES_CELIBATAIRE,
    CEHR_TRANCHES_COUPLE,
    TAUX_PFU_IR,
    TAUX_PS,
)
from .prelevements_sociaux import calculer_ps


def calculer_cehr(rfr: float, revenus_capital: float, situation: str = "celibataire") -> dict:
    """
    Calcule la CEHR (Contribution Exceptionnelle sur les Hauts Revenus).

    Args:
        rfr: Revenu Fiscal de Référence
        revenus_capital: Revenus du capital soumis à CEHR
        situation: "celibataire" ou "couple"

    Returns:
        dict avec taux, montant, tranche

    Source: Art. 223 sexies CGI
    """
    tranches = CEHR_TRANCHES_COUPLE if situation == "couple" else CEHR_TRANCHES_CELIBATAIRE

    taux_cehr = 0.0
    tranche_appliquee = None

    for tranche in tranches:
        rfr_min = tranche["rfr_min"]
        rfr_max = tranche.get("rfr_max")

        if rfr >= rfr_min:
            if rfr_max is None or rfr <= rfr_max:
                taux_cehr = tranche["taux"]
                tranche_appliquee = tranche
                break
            elif rfr > rfr_max:
                # Continue à la tranche suivante
                continue

    cehr = revenus_capital * taux_cehr

    return {
        "rfr": rfr,
        "taux": taux_cehr,
        "cehr": cehr,
        "assiette": revenus_capital,
        "tranche": tranche_appliquee,
    }


def calculer_cdhr(
    rfr: float, ir_total: float, revenus_capital: float, situation: str = "celibataire"
) -> dict:
    """
    Calcule la CDHR (Contribution Différentielle sur les Hauts Revenus).

    La CDHR assure un taux minimum d'imposition de 20% sur le RFR.

    Args:
        rfr: Revenu Fiscal de Référence
        ir_total: IR total déjà payé (IR + CEHR)
        revenus_capital: Revenus du capital
        situation: "celibataire" ou "couple"

    Returns:
        dict avec cdhr, taux_effectif_avant, taux_effectif_apres

    Source: Art. 223 terdecies CGI (LF 2025)
    """
    seuil = CDHR_SEUIL_COUPLE if situation == "couple" else CDHR_SEUIL_CELIBATAIRE

    # CDHR ne s'applique que si RFR > seuil
    if rfr <= seuil:
        return {
            "cdhr": 0.0,
            "taux_effectif_avant": ir_total / rfr if rfr > 0 else 0.0,
            "taux_effectif_apres": ir_total / rfr if rfr > 0 else 0.0,
            "applicable": False,
        }

    # Taux effectif avant CDHR
    taux_effectif_avant = ir_total / rfr if rfr > 0 else 0.0

    # Si taux effectif < 20%, CDHR = 20% × RFR - IR déjà payé
    if taux_effectif_avant < CDHR_TAUX_PLANCHER:
        cdhr = max(0, CDHR_TAUX_PLANCHER * rfr - ir_total)
    else:
        cdhr = 0.0

    taux_effectif_apres = (ir_total + cdhr) / rfr if rfr > 0 else 0.0

    return {
        "cdhr": cdhr,
        "taux_effectif_avant": taux_effectif_avant,
        "taux_effectif_apres": taux_effectif_apres,
        "taux_plancher": CDHR_TAUX_PLANCHER,
        "applicable": True,
    }


def calculer_pfu_complet(
    montant_brut: float,
    profil: dict,
    avec_cehr: bool = True,
    avec_cdhr: bool = False,
) -> ResultatFiscal:
    """
    Calcule le PFU complet avec IR, PS, CEHR, CDHR (optionnel).

    Args:
        montant_brut: Montant brut soumis au PFU
        profil: dict avec situation, rfr, tmi
        avec_cehr: Calculer la CEHR (True par défaut)
        avec_cdhr: Calculer la CDHR (False par défaut, calcul complexe)

    Returns:
        ResultatFiscal avec cascade complète

    Source: Art. 200 A CGI
    """
    situation = profil.get("situation", "celibataire")
    rfr = profil.get("rfr", 0.0)

    resultat = ResultatFiscal(
        montant_brut=montant_brut,
        impot_ir=0.0,
        prelevements_sociaux=0.0,
        cehr=0.0,
        cdhr=0.0,
        total_impots=0.0,
        montant_net=0.0,
        taux_effectif=0.0,
    )

    # 1. IR PFU
    ir_pfu = montant_brut * TAUX_PFU_IR
    resultat.impot_ir = ir_pfu
    resultat.ajouter_ligne(
        libelle="IR (PFU 12.8%)",
        montant=ir_pfu,
        formule=f"{montant_brut:,.2f} × {TAUX_PFU_IR:.1%}",
        source="Art. 200 A CGI",
    )

    # 2. Prélèvements sociaux
    ps_result = calculer_ps(montant_brut)
    resultat.prelevements_sociaux = ps_result["ps"]
    resultat.ajouter_ligne(
        libelle="Prélèvements sociaux",
        montant=ps_result["ps"],
        formule=f"{montant_brut:,.2f} × {TAUX_PS:.1%}",
        source="Art. L.136-8 CSS",
    )

    # 3. CEHR
    if avec_cehr and rfr > 0:
        cehr_result = calculer_cehr(rfr, montant_brut, situation)
        resultat.cehr = cehr_result["cehr"]
        if resultat.cehr > 0:
            resultat.ajouter_ligne(
                libelle=f"CEHR ({cehr_result['taux']:.1%})",
                montant=resultat.cehr,
                formule=f"{montant_brut:,.2f} × {cehr_result['taux']:.1%}",
                source="Art. 223 sexies CGI",
            )

    # 4. CDHR (optionnel, calcul complexe)
    if avec_cdhr and rfr > 0:
        ir_total_avant_cdhr = resultat.impot_ir + resultat.cehr
        cdhr_result = calculer_cdhr(rfr, ir_total_avant_cdhr, montant_brut, situation)
        resultat.cdhr = cdhr_result["cdhr"]
        if resultat.cdhr > 0:
            resultat.ajouter_ligne(
                libelle="CDHR (plancher 20%)",
                montant=resultat.cdhr,
                formule=f"max(0, {CDHR_TAUX_PLANCHER:.1%} × RFR - IR total)",
                source="Art. 223 terdecies CGI",
            )
            resultat.ajouter_avertissement(
                f"CDHR activée : taux effectif porté à {cdhr_result['taux_effectif_apres']:.1%}"
            )

    # Total
    resultat.total_impots = (
        resultat.impot_ir + resultat.prelevements_sociaux + resultat.cehr + resultat.cdhr
    )
    resultat.montant_net = montant_brut - resultat.total_impots
    resultat.taux_effectif = resultat.total_impots / montant_brut if montant_brut > 0 else 0.0

    # Ligne finale
    resultat.ajouter_ligne(
        libelle="TOTAL IMPÔTS",
        montant=resultat.total_impots,
        formule="IR + PS + CEHR + CDHR",
        source="",
    )
    resultat.ajouter_ligne(
        libelle="NET APRÈS IMPÔTS",
        montant=resultat.montant_net,
        formule=f"{montant_brut:,.2f} - {resultat.total_impots:,.2f}",
        source="",
    )

    return resultat
