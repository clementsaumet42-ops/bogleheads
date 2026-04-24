"""Modèle commun Opportunite — S8.2b.

Représente une opportunité d'optimisation chiffrée en € capitalisés sur 30 ans.
Chaque moteur retourne une liste d'Opportunite standardisée, prête à être agrégée en S8.2c.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LigneEtf(BaseModel):
    """Ligne de portefeuille ETF du client."""

    isin: str
    montant_eur: float = Field(gt=0)
    enveloppe: Literal["PEA", "AV", "CTO", "PER", "PEE", "CTO_IS", "Contrat_Cap_IS"]


class Opportunite(BaseModel):
    """Opportunité d'optimisation chiffrée — modèle commun S8.2b.

    Tous les gains sont calculés à hypothèses constantes (rendements, taux, frais).
    Ne JAMAIS lire comme une promesse : 'économie modélisée à hypothèses constantes'.
    """

    # IDENTITÉ
    id: str  # ex: "etf.tracking_difference.IWDA_vs_CW8"
    levier: Literal[
        "tracking_difference",
        "withholding_tax",
        "dist_vs_cap",
        "frais_contrat_av",
        "frais_broker",
    ]
    titre: str  # ex: "Switcher CW8 → IWDA pour gain TD"

    # IMPACT
    gain_annuel_bps: float  # économie en bps/an (négatif = perte)
    gain_annuel_eur: float  # économie en €/an au montant courant
    gain_30ans_eur: float  # capitalisé 30 ans au taux d'actualisation défaut 4%
    montant_concerne_eur: float  # base de calcul

    # JUSTIFICATION
    avant: dict  # snapshot état actuel (TER, TD, frais, etc.)
    apres: dict  # snapshot état optimisé
    formule: str  # texte explicatif court
    sources: list[str]  # URLs / docs S8.2a

    # FAISABILITÉ
    complexite: Literal["faible", "moyenne", "elevee"]
    delai_mise_en_oeuvre_jours: int  # estimation EC
    contraintes: list[str]  # ex: ["client doit avoir un PEA", "switch fiscalement gratuit en AV"]

    # MÉTA
    confiance: Literal["haute", "moyenne", "basse"]  # haute si donnée fraîche + formule simple
    note_ec: str | None = None  # alerte si hypothèses fortes


def capitaliser_30_ans(
    gain_annuel_eur: float,
    taux_actualisation: float = 0.04,
    horizon_ans: int = 30,
) -> float:
    """Somme actualisée d'un flux constant sur N ans à taux i.

    Formule de l'annuité : gain_annuel × ((1+i)^N - 1) / i

    Exemple :
        capitaliser_30_ans(1000, 0.04, 30) ≈ 56 085 €

    Args:
        gain_annuel_eur: économie annuelle en €
        taux_actualisation: taux d'actualisation annuel (défaut 4%)
        horizon_ans: horizon de capitalisation en années (défaut 30)

    Returns:
        Valeur future capitalisée de l'économie annuelle.
    """
    if taux_actualisation == 0:
        return gain_annuel_eur * horizon_ans
    return gain_annuel_eur * ((1 + taux_actualisation) ** horizon_ans - 1) / taux_actualisation
