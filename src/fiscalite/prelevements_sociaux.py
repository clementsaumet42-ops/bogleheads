"""
Prélèvements sociaux (PS)
Art. L.136-8 CSS (Code de la Sécurité Sociale)
"""

from .constantes import TAUX_CRDS, TAUX_CSG, TAUX_PRELEVEMENT_SOLIDARITE, TAUX_PS


def calculer_ps(assiette: float, deja_preleves: bool = False) -> dict:
    """
    Calcule les prélèvements sociaux sur une assiette.

    Args:
        assiette: Montant soumis aux PS (gains, plus-values, revenus du capital)
        deja_preleves: True si PS déjà prélevés à la source (ex: fonds euro AV)

    Returns:
        dict avec assiette, ps, net, détail, note

    Source: Art. L.136-8 CSS
    """
    if deja_preleves:
        return {
            "assiette": assiette,
            "ps": 0.0,
            "net": assiette,
            "note": "PS déjà prélevés à la source (fonds euro AV)",
        }

    ps = assiette * TAUX_PS

    detail = {
        "csg": assiette * TAUX_CSG,
        "crds": assiette * TAUX_CRDS,
        "prelevement_solidarite": assiette * TAUX_PRELEVEMENT_SOLIDARITE,
    }

    return {
        "assiette": assiette,
        "ps": ps,
        "net": assiette - ps,
        "taux": TAUX_PS,
        "detail": detail,
        "note": f"CSG {TAUX_CSG:.1%} + CRDS {TAUX_CRDS:.1%} + PS {TAUX_PRELEVEMENT_SOLIDARITE:.1%}",
    }


def calculer_ps_av(gains: float, type_fonds: str = "uc", deja_preleves: bool = False) -> dict:
    """
    Calcule les PS sur gains d'assurance vie selon le type de fonds.

    Args:
        gains: Montant des gains
        type_fonds: "euro" (PS déjà prélevés) ou "uc" (PS à prélever)
        deja_preleves: Force le statut de prélèvement

    Returns:
        dict avec assiette, ps, net

    Source: Art. L.136-7 CSS
    """
    # Fonds euro : PS prélevés chaque année par l'assureur
    if type_fonds == "euro" or deja_preleves:
        return calculer_ps(gains, deja_preleves=True)

    # Unités de compte : PS dus au rachat
    return calculer_ps(gains, deja_preleves=False)


def taux_ps_effectif() -> float:
    """Retourne le taux PS effectif 2026."""
    return TAUX_PS
