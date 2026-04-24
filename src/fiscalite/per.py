"""
PER (Plan d'Épargne Retraite)
Art. 163 quatervicies CGI, Art. L.224-1 Code monétaire et financier
"""

from .cascade import ResultatFiscal
from .constantes import (
    PER_CAS_DEBLOCAGE_ANTICIPE,
    PER_PLAFOND_DEDUCTION_FORFAIT,
    PER_PLAFOND_DEDUCTION_MAX,
    PER_PLAFOND_DEDUCTION_MIN,
    TAUX_PS,
)
from .prelevements_sociaux import calculer_ps


def calculer_plafond_deduction_per(revenus_professionnels: float) -> float:
    """
    Calcule le plafond de déduction PER.

    Plafond = max(10% des revenus, 4 399 €) et plafonné à 35 194 € (8 PASS)

    Args:
        revenus_professionnels: Revenus professionnels nets

    Returns:
        Plafond de déduction en €

    Source: Art. 163 quatervicies CGI
    """
    plafond = max(
        revenus_professionnels * PER_PLAFOND_DEDUCTION_FORFAIT,
        PER_PLAFOND_DEDUCTION_MIN,
    )
    plafond = min(plafond, PER_PLAFOND_DEDUCTION_MAX)
    return plafond


def calculer_avantage_entree_per(versement: float, tmi: float) -> dict:
    """
    Calcule l'avantage fiscal à l'entrée du PER.

    Args:
        versement: Montant versé (déductible)
        tmi: Taux marginal d'imposition

    Returns:
        dict avec economie_impot, versement_net_apres_economie

    Source: Art. 163 quatervicies CGI
    """
    economie_impot = versement * tmi
    versement_net_apres_economie = versement - economie_impot

    return {
        "versement": versement,
        "tmi": tmi,
        "economie_impot": economie_impot,
        "versement_net_apres_economie": versement_net_apres_economie,
        "taux_avantage": tmi,
    }


def calculer_fiscalite_sortie_per(operation: dict, profil: dict) -> ResultatFiscal:
    """
    Calcule la fiscalité de sortie PER (capital ou rente).

    Sortie capital :
        - Versements déduits : IR au TMI sur tout le capital + PS sur gains
        - Versements non déduits : IR au TMI sur gains uniquement + PS sur gains

    Sortie rente :
        - Versements déduits : RVTO (Rente Viagère à Titre Onéreux) 100% imposable
        - Versements non déduits : RVTO selon barème âge

    Args:
        operation: dict avec
            - type_sortie: "capital" ou "rente"
            - montant_brut: float (capital ou rente annuelle)
            - versements_deduits: float (part déductible)
            - versements_non_deduits: float (part non déductible)
            - gains: float (plus-values)
            - cas_deblocage_anticipe: str (optionnel)
        profil: dict avec tmi, situation

    Returns:
        ResultatFiscal avec cascade

    Source: Art. 163 quatervicies CGI
    """
    type_sortie = operation.get("type_sortie", "capital")
    montant_brut = operation.get("montant_brut", 0.0)
    versements_deduits = operation.get("versements_deduits", 0.0)
    versements_non_deduits = operation.get("versements_non_deduits", 0.0)
    gains = operation.get("gains", 0.0)
    cas_deblocage = operation.get("cas_deblocage_anticipe")
    tmi = profil.get("tmi", 0.30)

    resultat = ResultatFiscal(
        montant_brut=montant_brut,
        impot_ir=0.0,
        prelevements_sociaux=0.0,
        total_impots=0.0,
        montant_net=0.0,
        taux_effectif=0.0,
    )

    # Vérifier cas déblocage anticipé
    if cas_deblocage and cas_deblocage in PER_CAS_DEBLOCAGE_ANTICIPE:
        resultat.ajouter_avertissement(
            f"Cas de déblocage anticipé : {cas_deblocage} (Art. L.224-4 CMF)"
        )

    # SORTIE EN CAPITAL
    if type_sortie == "capital":
        # Versements déduits : IR sur TOUT le capital
        if versements_deduits > 0:
            assiette_ir_deduit = montant_brut
            ir_deduit = assiette_ir_deduit * tmi
            resultat.impot_ir += ir_deduit
            resultat.ajouter_ligne(
                libelle=f"IR sur capital (versements déduits, TMI {tmi:.1%})",
                montant=ir_deduit,
                formule=f"{assiette_ir_deduit:,.2f} × {tmi:.1%}",
                source="Art. 163 quatervicies-2° CGI",
            )

        # Versements non déduits : IR sur gains uniquement
        if versements_non_deduits > 0:
            assiette_ir_non_deduit = gains
            ir_non_deduit = assiette_ir_non_deduit * tmi
            resultat.impot_ir += ir_non_deduit
            resultat.ajouter_ligne(
                libelle=f"IR sur gains (versements non déduits, TMI {tmi:.1%})",
                montant=ir_non_deduit,
                formule=f"{assiette_ir_non_deduit:,.2f} × {tmi:.1%}",
                source="Art. 163 quatervicies-2° CGI",
            )

        # PS sur gains
        ps_result = calculer_ps(gains)
        resultat.prelevements_sociaux = ps_result["ps"]
        resultat.ajouter_ligne(
            libelle="Prélèvements sociaux (sur gains)",
            montant=ps_result["ps"],
            formule=f"{gains:,.2f} × {TAUX_PS:.1%}",
            source="Art. L.136-8 CSS",
        )

    # SORTIE EN RENTE
    elif type_sortie == "rente":
        # Versements déduits : 100% imposable IR
        if versements_deduits > 0:
            assiette_ir_rente_deduit = montant_brut
            ir_rente_deduit = assiette_ir_rente_deduit * tmi
            resultat.impot_ir += ir_rente_deduit
            resultat.ajouter_ligne(
                libelle=f"IR sur rente (versements déduits, TMI {tmi:.1%})",
                montant=ir_rente_deduit,
                formule=f"{assiette_ir_rente_deduit:,.2f} × {tmi:.1%}",
                source="Art. 163 quatervicies-3° CGI",
            )

        # Versements non déduits : RVTO selon barème âge
        # Simplification : 30% imposable (âge moyen 60-69 ans)
        if versements_non_deduits > 0:
            taux_rvto = 0.30  # 30% imposable (simplification)
            assiette_ir_rente_non_deduit = montant_brut * taux_rvto
            ir_rente_non_deduit = assiette_ir_rente_non_deduit * tmi
            resultat.impot_ir += ir_rente_non_deduit
            resultat.ajouter_ligne(
                libelle=f"IR sur rente (versements non déduits, RVTO {taux_rvto:.0%})",
                montant=ir_rente_non_deduit,
                formule=f"{montant_brut:,.2f} × {taux_rvto:.0%} × {tmi:.1%}",
                source="Art. 158-6 CGI",
            )
            resultat.ajouter_avertissement(
                "RVTO : taux imposable dépend de l'âge au 1er versement de la rente"
            )

        # PS sur fraction imposable
        fraction_imposable_ps = montant_brut * 0.30  # Simplification
        ps_result = calculer_ps(fraction_imposable_ps)
        resultat.prelevements_sociaux = ps_result["ps"]
        resultat.ajouter_ligne(
            libelle="Prélèvements sociaux (sur fraction imposable)",
            montant=ps_result["ps"],
            formule=f"{fraction_imposable_ps:,.2f} × {TAUX_PS:.1%}",
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


def comparer_per_vs_cto(
    versement: float,
    tmi_actuel: float,
    tmi_retraite: float,
    rendement_annuel: float,
    horizon_ans: int,
) -> dict:
    """
    Compare PER vs CTO sur un horizon donné.

    Args:
        versement: Montant initial
        tmi_actuel: TMI actuel (avantage déduction)
        tmi_retraite: TMI à la retraite (sortie)
        rendement_annuel: Rendement annuel (ex: 0.06)
        horizon_ans: Horizon en années

    Returns:
        dict avec capital_per_net, capital_cto_net, avantage_per
    """

    # Économie d'entrée PER
    economie_entree = versement * tmi_actuel

    # Croissance capital
    capital_brut = versement * ((1 + rendement_annuel) ** horizon_ans)
    gains = capital_brut - versement

    # PER : IR sur tout le capital + PS sur gains
    impot_ir_per = capital_brut * tmi_retraite
    ps_per = gains * TAUX_PS
    capital_per_net = (
        capital_brut
        - impot_ir_per
        - ps_per
        + (economie_entree * ((1 + rendement_annuel) ** horizon_ans))
    )

    # CTO : PFU sur gains
    impot_cto = gains * (0.128 + TAUX_PS)
    capital_cto_net = capital_brut - impot_cto

    avantage_per = capital_per_net - capital_cto_net

    return {
        "versement": versement,
        "economie_entree": economie_entree,
        "capital_per_net": capital_per_net,
        "capital_cto_net": capital_cto_net,
        "avantage_per": avantage_per,
        "tmi_actuel": tmi_actuel,
        "tmi_retraite": tmi_retraite,
        "horizon_ans": horizon_ans,
    }
