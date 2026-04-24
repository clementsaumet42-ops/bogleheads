"""
CTO Particulier (Compte-Titres Ordinaire)
Option PFU ou barème IR
Art. 200 A CGI, Art. 158 CGI
"""

from .cascade import ResultatFiscal
from .constantes import ABATTEMENT_DIVIDENDES_BAREME, TAUX_PFU_IR, TAUX_PS
from .pfu import calculer_pfu_complet
from .prelevements_sociaux import calculer_ps


def calculer_fiscalite_cession_cto(operation: dict, profil: dict) -> ResultatFiscal:
    """
    Calcule la fiscalité d'une cession de titres sur CTO particulier.

    Option par défaut : PFU 12.8% + PS 18.6%
    Option barème : IR au TMI + PS 18.6%

    Args:
        operation: dict avec
            - montant_brut: float (montant de la cession)
            - gains: float (plus-value)
            - option_bareme: bool (option barème IR)
            - type_revenu: "pv" (plus-value) ou "dividende"
        profil: dict avec situation, tmi, rfr

    Returns:
        ResultatFiscal avec cascade

    Source: Art. 200 A CGI
    """
    montant_brut = operation.get("montant_brut", 0.0)
    gains = operation.get("gains", montant_brut)
    option_bareme = operation.get("option_bareme", False)
    type_revenu = operation.get("type_revenu", "pv")
    tmi = profil.get("tmi", 0.30)

    resultat = ResultatFiscal(
        montant_brut=montant_brut,
        impot_ir=0.0,
        prelevements_sociaux=0.0,
        total_impots=0.0,
        montant_net=0.0,
        taux_effectif=0.0,
    )

    # Option PFU (par défaut)
    if not option_bareme:
        return calculer_pfu_complet(gains, profil, avec_cehr=True, avec_cdhr=False)

    # Option barème IR
    resultat.ajouter_ligne(
        libelle=f"CTO {type_revenu.upper()} (option barème IR)",
        montant=gains,
        formule="Option globale pour tous les revenus du capital de l'année",
        source="Art. 200 A-2 CGI",
    )
    resultat.ajouter_avertissement(
        "Option barème IR : irrévocable pour l'année fiscale, s'applique à TOUS les revenus du capital"
    )

    # Abattement dividendes si option barème
    if type_revenu == "dividende":
        abattement = gains * ABATTEMENT_DIVIDENDES_BAREME
        gains_apres_abattement = gains * (1 - ABATTEMENT_DIVIDENDES_BAREME)
        resultat.ajouter_ligne(
            libelle=f"Abattement dividendes ({ABATTEMENT_DIVIDENDES_BAREME:.0%})",
            montant=-abattement,
            formule=f"{gains:,.2f} × {ABATTEMENT_DIVIDENDES_BAREME:.0%}",
            source="Art. 158-3-2° CGI",
        )
    else:
        gains_apres_abattement = gains

    # IR au TMI
    ir = gains_apres_abattement * tmi
    resultat.impot_ir = ir
    resultat.ajouter_ligne(
        libelle=f"IR (barème, TMI {tmi:.1%})",
        montant=ir,
        formule=f"{gains_apres_abattement:,.2f} × {tmi:.1%}",
        source="Art. 158 CGI",
    )

    # Prélèvements sociaux (pas d'abattement)
    ps_result = calculer_ps(gains)
    resultat.prelevements_sociaux = ps_result["ps"]
    resultat.ajouter_ligne(
        libelle="Prélèvements sociaux",
        montant=ps_result["ps"],
        formule=f"{gains:,.2f} × {TAUX_PS:.1%}",
        source="Art. L.136-8 CSS",
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


def comparer_pfu_vs_bareme(gains: float, tmi: float, type_revenu: str = "pv") -> dict:
    """
    Compare l'option PFU vs barème IR.

    Args:
        gains: Montant des gains
        tmi: Taux marginal d'imposition
        type_revenu: "pv" ou "dividende"

    Returns:
        dict avec impots_pfu, impots_bareme, economie, meilleure_option
    """
    # PFU
    impots_pfu = gains * (TAUX_PFU_IR + TAUX_PS)

    # Barème
    if type_revenu == "dividende":
        gains_apres_abattement = gains * (1 - ABATTEMENT_DIVIDENDES_BAREME)
    else:
        gains_apres_abattement = gains

    ir_bareme = gains_apres_abattement * tmi
    ps_bareme = gains * TAUX_PS
    impots_bareme = ir_bareme + ps_bareme

    # Comparaison
    economie = impots_pfu - impots_bareme
    meilleure_option = "bareme" if economie > 0 else "pfu"

    return {
        "gains": gains,
        "tmi": tmi,
        "type_revenu": type_revenu,
        "impots_pfu": impots_pfu,
        "taux_effectif_pfu": TAUX_PFU_IR + TAUX_PS,
        "impots_bareme": impots_bareme,
        "taux_effectif_bareme": impots_bareme / gains if gains > 0 else 0.0,
        "economie": economie,
        "meilleure_option": meilleure_option,
    }
