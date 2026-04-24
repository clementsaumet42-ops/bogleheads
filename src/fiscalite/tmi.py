"""
Barème IR 2026, quotient familial, TMI, décote
Art. 197 CGI, Art. 194 CGI
"""

from .constantes import (
    BAREME_IR_2026,
    DECOTE_FORMULE_CELIBATAIRE,
    DECOTE_FORMULE_COUPLE,
    QF_PARTS,
    QF_PLAFOND_DEMI_PART,
    QF_PLAFOND_PART_ENTIERE,
)


def calculer_parts_fiscales(situation: str, nb_enfants: int = 0) -> float:
    """
    Calcule le nombre de parts fiscales selon la situation familiale.

    Args:
        situation: "celibataire" ou "couple"
        nb_enfants: nombre d'enfants à charge

    Returns:
        Nombre de parts fiscales

    Source: Art. 194 CGI
    """
    parts = QF_PARTS["couple"] if situation == "couple" else QF_PARTS["celibataire"]

    # Enfants
    if nb_enfants >= 1:
        parts += QF_PARTS["enfant_1"]
    if nb_enfants >= 2:
        parts += QF_PARTS["enfant_2"]
    if nb_enfants >= 3:
        for _ in range(nb_enfants - 2):
            parts += QF_PARTS["enfant_3"]

    return parts


def calculer_ir_brut_bareme(revenu_imposable: float, parts: float) -> dict:
    """
    Calcule l'IR brut selon le barème progressif 2026.

    Args:
        revenu_imposable: Revenu net imposable
        parts: Nombre de parts fiscales

    Returns:
        dict avec ir_brut, quotient, tranches appliquées

    Source: Art. 197 CGI
    """
    if revenu_imposable <= 0:
        return {"ir_brut": 0.0, "quotient": 0.0, "tranches": []}

    quotient = revenu_imposable / parts
    impot_1_part = 0.0
    tranches_appliquees = []

    precedent = 0.0
    for tranche in BAREME_IR_2026:
        if "au_dela" in tranche and tranche["au_dela"]:
            # Dernière tranche : au-delà
            if quotient > precedent:
                montant_tranche = quotient - precedent
                impot_tranche = montant_tranche * tranche["taux"]
                impot_1_part += impot_tranche
                tranches_appliquees.append(
                    {
                        "de": precedent,
                        "a": quotient,
                        "taux": tranche["taux"],
                        "impot": impot_tranche,
                    }
                )
            break
        else:
            limite = tranche["jusqu_a"]
            if quotient > precedent:
                montant_tranche = min(quotient, limite) - precedent
                impot_tranche = montant_tranche * tranche["taux"]
                impot_1_part += impot_tranche
                tranches_appliquees.append(
                    {
                        "de": precedent,
                        "a": min(quotient, limite),
                        "taux": tranche["taux"],
                        "impot": impot_tranche,
                    }
                )
            precedent = limite
            if quotient <= limite:
                break

    ir_brut = impot_1_part * parts

    return {"ir_brut": ir_brut, "quotient": quotient, "tranches": tranches_appliquees}


def calculer_plafonnement_qf(
    ir_sans_avantage: float, ir_avec_avantage: float, parts_supplementaires: float
) -> float:
    """
    Calcule le plafonnement du quotient familial.

    Args:
        ir_sans_avantage: IR sans les parts supplémentaires
        ir_avec_avantage: IR avec les parts supplémentaires
        parts_supplementaires: Nombre de parts supplémentaires (0.5, 1.0, etc.)

    Returns:
        Avantage plafonné en €

    Source: Art. 197 CGI
    """
    avantage_brut = ir_sans_avantage - ir_avec_avantage

    # Plafond par part
    if parts_supplementaires == 0.5:
        plafond = QF_PLAFOND_DEMI_PART
    elif parts_supplementaires == 1.0:
        plafond = QF_PLAFOND_PART_ENTIERE
    else:
        # Parts multiples
        plafond = (
            int(parts_supplementaires) * QF_PLAFOND_PART_ENTIERE
            + (parts_supplementaires % 1) * QF_PLAFOND_DEMI_PART
        )

    return min(avantage_brut, plafond)


def calculer_decote(ir_brut: float, situation: str) -> float:
    """
    Calcule la décote de l'impôt sur le revenu.

    Args:
        ir_brut: IR brut avant décote
        situation: "celibataire" ou "couple"

    Returns:
        Montant de la décote en €

    Source: Art. 197 CGI
    """
    if situation == "couple":
        return DECOTE_FORMULE_COUPLE(ir_brut)
    else:
        return DECOTE_FORMULE_CELIBATAIRE(ir_brut)


def calculer_tmi(revenu_imposable: float, parts: float = 1.0) -> float:
    """
    Calcule le Taux Marginal d'Imposition (TMI).

    Args:
        revenu_imposable: Revenu net imposable
        parts: Nombre de parts fiscales

    Returns:
        TMI (0.00, 0.11, 0.30, 0.41, 0.45)

    Source: Art. 197 CGI
    """
    if revenu_imposable <= 0:
        return 0.0

    quotient = revenu_imposable / parts

    for _i, tranche in enumerate(BAREME_IR_2026):
        if ("au_dela" in tranche and tranche["au_dela"]) or quotient <= tranche.get(
            "jusqu_a", float("inf")
        ):
            return tranche["taux"]

    # Par défaut, dernière tranche
    return BAREME_IR_2026[-1]["taux"]


def calculer_taux_moyen(ir_net: float, revenu_imposable: float) -> float:
    """
    Calcule le taux moyen d'imposition.

    Args:
        ir_net: IR net (après décote)
        revenu_imposable: Revenu net imposable

    Returns:
        Taux moyen (IR / revenu)
    """
    if revenu_imposable <= 0:
        return 0.0
    return ir_net / revenu_imposable


def calculer_ir_complet(
    revenu_imposable: float, situation: str = "celibataire", nb_enfants: int = 0
) -> dict:
    """
    Calcule l'IR complet avec barème, QF, plafonnement, décote.

    Args:
        revenu_imposable: Revenu net imposable
        situation: "celibataire" ou "couple"
        nb_enfants: Nombre d'enfants à charge

    Returns:
        dict avec ir_net, ir_brut, decote, tmi, taux_moyen, parts, etc.

    Source: Art. 197 CGI, Art. 194 CGI
    """
    parts = calculer_parts_fiscales(situation, nb_enfants)
    resultat_bareme = calculer_ir_brut_bareme(revenu_imposable, parts)
    ir_brut = resultat_bareme["ir_brut"]

    # Décote
    decote = calculer_decote(ir_brut, situation)
    ir_net = max(0, ir_brut - decote)

    # TMI et taux moyen
    tmi = calculer_tmi(revenu_imposable, parts)
    taux_moyen = calculer_taux_moyen(ir_net, revenu_imposable)

    return {
        "revenu_imposable": revenu_imposable,
        "parts": parts,
        "quotient": resultat_bareme["quotient"],
        "ir_brut": ir_brut,
        "decote": decote,
        "ir_net": ir_net,
        "tmi": tmi,
        "taux_moyen": taux_moyen,
        "tranches": resultat_bareme["tranches"],
    }
