"""Modélisation de la fiscalité pour le backtest."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ConfigFiscalite(BaseModel):
    pfu_taux: float = Field(default=0.30, ge=0, le=1)
    ps_taux: float = Field(default=0.172, ge=0, le=1)
    distribution_par_classe: dict[str, float] = Field(default_factory=dict)
    rebalancement_seuil_pct: float = Field(default=0.05, ge=0)


def calculer_impot_dividendes_cto(
    valeur_par_classe: dict[str, float],
    config_fiscalite: ConfigFiscalite,
) -> float:
    """Calcule l'impôt sur dividendes CTO (PFU) pour une année."""
    impot_total = 0.0
    for classe, valeur in valeur_par_classe.items():
        taux_distrib = config_fiscalite.distribution_par_classe.get(classe, 0.0)
        dividendes = valeur * taux_distrib
        impot_total += dividendes * config_fiscalite.pfu_taux
    return impot_total


def calculer_impot_rebalancement_cto(
    ventes: dict[str, float],
    config_fiscalite: ConfigFiscalite,
    prix_revient: dict[str, float],
) -> float:
    """Calcule l'impôt sur plus-values lors du rebalancement CTO (PFU)."""
    impot_total = 0.0
    for classe, montant_vendu in ventes.items():
        pr = prix_revient.get(classe, montant_vendu)
        pv = max(0.0, montant_vendu - pr)
        impot_total += pv * config_fiscalite.pfu_taux
    return impot_total


def calculer_fiscalite_optimisee(
    valeur_par_classe: dict[str, float],
    ventilation_enveloppes: dict[str, str],
    config_fiscalite: ConfigFiscalite,
) -> float:
    """
    Calcule la fiscalité optimisée selon la ventilation enveloppes.
    Les actifs en PEA/AV/PER ont une fiscalité réduite vs CTO.
    """
    impot_total = 0.0
    for classe, valeur in valeur_par_classe.items():
        enveloppe = ventilation_enveloppes.get(classe, "CTO")
        taux_distrib = config_fiscalite.distribution_par_classe.get(classe, 0.0)
        dividendes = valeur * taux_distrib
        if enveloppe in ("PEA", "AV", "PER"):
            # Fiscalité réduite : seulement PS (pas IR) sur PEA après 5 ans, AV après 8 ans.
            # Hypothèse simplificatrice : on suppose les enveloppes en régime favorable
            # (durée de détention suffisante). À documenter dans les mentions de l'output.
            impot_total += dividendes * config_fiscalite.ps_taux
        else:
            impot_total += dividendes * config_fiscalite.pfu_taux
    return impot_total
