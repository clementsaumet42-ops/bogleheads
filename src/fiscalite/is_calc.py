"""
Impôt sur les Sociétés (IS)
Art. 219 CGI
"""

from .constantes import IS_SEUIL, IS_TAUX_NORMAL, IS_TAUX_REDUIT


def calculer_is(benefice: float, params: dict = None) -> dict:
    """
    Calcule l'IS sur un bénéfice (taux réduit 15% + taux normal 25%).

    Args:
        benefice: Bénéfice imposable
        params: Paramètres fiscaux (non utilisé, présent pour compatibilité)

    Returns:
        dict avec is_du, net, taux_effectif, detail

    Source: Art. 219 CGI
    """
    if benefice <= 0:
        return {
            "benefice": benefice,
            "is_du": 0.0,
            "net": benefice,
            "taux_effectif": 0.0,
            "detail": [],
        }

    detail = []

    if benefice <= IS_SEUIL:
        # Taux réduit uniquement
        is_du = benefice * IS_TAUX_REDUIT
        taux_effectif = IS_TAUX_REDUIT
        detail.append(
            {
                "tranche": f"0 à {IS_SEUIL:,.0f}€",
                "base": benefice,
                "taux": IS_TAUX_REDUIT,
                "is": is_du,
            }
        )
    else:
        # Taux réduit + taux normal
        is_reduit = IS_SEUIL * IS_TAUX_REDUIT
        is_normal = (benefice - IS_SEUIL) * IS_TAUX_NORMAL
        is_du = is_reduit + is_normal
        taux_effectif = is_du / benefice

        detail.append(
            {
                "tranche": f"0 à {IS_SEUIL:,.0f}€",
                "base": IS_SEUIL,
                "taux": IS_TAUX_REDUIT,
                "is": is_reduit,
            }
        )
        detail.append(
            {
                "tranche": f"Au-delà de {IS_SEUIL:,.0f}€",
                "base": benefice - IS_SEUIL,
                "taux": IS_TAUX_NORMAL,
                "is": is_normal,
            }
        )

    return {
        "benefice": benefice,
        "is_du": is_du,
        "net": benefice - is_du,
        "taux_effectif": taux_effectif,
        "detail": detail,
    }
