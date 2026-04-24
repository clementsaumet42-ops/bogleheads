from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

_TAUX_ACTUALISATION = {
    "tres_stable": 0.035,
    "stable": 0.055,
    "variable": 0.075,
    "tres_variable": 0.10,
}


class CapitalHumain(BaseModel):
    revenus_nets_annuels: float = Field(default=0.0, ge=0)
    annees_restantes: int = Field(default=0, ge=0, le=50)
    stabilite_emploi: str = Field(default="stable")
    taux_croissance_salaire: float = Field(default=0.02, ge=-0.05, le=0.10)
    secteur_naf: str | None = None
    concentration_sectorielle: bool = False
    valeur_actualisee_eur: float = Field(default=0.0, ge=0)
    part_bond_like: float = Field(default=0.0, ge=0, le=1)
    part_equity_like: float = Field(default=0.0, ge=0, le=1)

    @model_validator(mode="after")
    def calculer_valeur_actualisee(self) -> CapitalHumain:
        T = self.annees_restantes
        if T == 0 or self.revenus_nets_annuels == 0:
            self.valeur_actualisee_eur = 0.0
            self.part_bond_like = 0.0
            self.part_equity_like = 0.0
            return self
        r = _TAUX_ACTUALISATION.get(self.stabilite_emploi, 0.055)
        g = self.taux_croissance_salaire
        R0 = self.revenus_nets_annuels
        va = R0 * T if abs(r - g) < 1e-9 else R0 * (1 - ((1 + g) / (1 + r)) ** T) / (r - g)
        self.valeur_actualisee_eur = max(0.0, va)
        stabilite_to_bond = {
            "tres_stable": 0.80,
            "stable": 0.60,
            "variable": 0.40,
            "tres_variable": 0.20,
        }
        self.part_bond_like = stabilite_to_bond.get(self.stabilite_emploi, 0.60)
        self.part_equity_like = 1.0 - self.part_bond_like
        return self


def enrichir_contraintes_depuis_capital_humain(
    profil: Any, capital_humain: CapitalHumain
) -> dict[str, Any]:
    patrimoine_fin = 0.0
    if hasattr(profil, "patrimoine_financier_total"):
        patrimoine_fin = float(profil.patrimoine_financier_total or 0)
    elif isinstance(profil, dict):
        patrimoine_fin = float(profil.get("patrimoine_financier_total", 0) or 0)
    ch_va = capital_humain.valeur_actualisee_eur
    total_richesse = patrimoine_fin + ch_va
    contraintes: dict[str, Any] = {
        "valeur_capital_humain_eur": ch_va,
        "total_richesse_eur": total_richesse,
        "poids_capital_humain_pct": (ch_va / total_richesse * 100) if total_richesse > 0 else 0,
        "recommandation": "",
        "concentration_sectorielle": capital_humain.concentration_sectorielle,
    }
    if capital_humain.part_bond_like >= 0.60:
        contraintes["recommandation"] = (
            "Capital humain bond-like élevé — surpondérer les actions dans le portefeuille financier."
        )
    elif capital_humain.part_equity_like >= 0.60:
        contraintes["recommandation"] = (
            "Capital humain equity-like élevé — considérer davantage d'actifs défensifs."
        )
    else:
        contraintes["recommandation"] = (
            "Capital humain équilibré — allocation standard recommandée."
        )
    if capital_humain.concentration_sectorielle:
        contraintes["recommandation"] += " Risque de concentration sectorielle détecté."
    return contraintes
