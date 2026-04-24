from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Incoherence(BaseModel):
    type: str
    description: str
    gravite: str = Field(description="legere | forte")
    valeur_declaree: str | None = None
    valeur_calculee: str | None = None


class ProfilConsolide(BaseModel):
    aversion_declaree: str = Field(
        description="tres_faible | faible | moyenne | elevee | tres_elevee"
    )
    aversion_calculee_grable: str | None = None
    aversion_calculee_scenarios: float | None = None
    delta_confiance: str = Field(default="aligne")
    incoherences_detectees: list[Incoherence] = Field(default_factory=list)
    recommandation_allocation: str | None = None
    score_global: float | None = None


_ORDER = ["tres_faible", "faible", "moyenne", "elevee", "tres_elevee"]


def synthetiser_profil(
    aversion_declaree: str,
    profil_grable: Any = None,
    score_scenarios: float | None = None,
    comportemental: Any = None,
) -> ProfilConsolide:
    incoherences: list[Incoherence] = []
    delta = "aligne"
    aversion_grable = None
    if profil_grable is not None:
        aversion_grable = profil_grable.categorie
        decl_idx = _ORDER.index(aversion_declaree) if aversion_declaree in _ORDER else 2
        calc_idx = _ORDER.index(aversion_grable) if aversion_grable in _ORDER else 2
        diff = abs(decl_idx - calc_idx)
        if diff >= 2:
            delta = "tension_forte"
            incoherences.append(
                Incoherence(
                    type="grable_vs_declaree",
                    description=f"Profil déclaré ({aversion_declaree}) très différent du profil Grable-Lytton ({aversion_grable})",
                    gravite="forte",
                    valeur_declaree=aversion_declaree,
                    valeur_calculee=aversion_grable,
                )
            )
        elif diff == 1:
            if delta == "aligne":
                delta = "tension_legere"
            incoherences.append(
                Incoherence(
                    type="grable_vs_declaree",
                    description=f"Légère différence entre profil déclaré ({aversion_declaree}) et Grable-Lytton ({aversion_grable})",
                    gravite="legere",
                    valeur_declaree=aversion_declaree,
                    valeur_calculee=aversion_grable,
                )
            )
    scores_num = []
    poids = []
    decl_num = float(_ORDER.index(aversion_declaree)) if aversion_declaree in _ORDER else 2.0
    scores_num.append(decl_num)
    poids.append(1.0)
    if aversion_grable and aversion_grable in _ORDER:
        scores_num.append(float(_ORDER.index(aversion_grable)))
        poids.append(1.5)
    if score_scenarios is not None:
        sc_normalized = (score_scenarios + 2) / 4 * 4
        scores_num.append(sc_normalized)
        poids.append(1.0)
    score_global = sum(s * p for s, p in zip(scores_num, poids)) / sum(poids) if poids else 2.0
    idx_global = max(0, min(4, round(score_global)))
    return ProfilConsolide(
        aversion_declaree=aversion_declaree,
        aversion_calculee_grable=aversion_grable,
        aversion_calculee_scenarios=score_scenarios,
        delta_confiance=delta,
        incoherences_detectees=incoherences,
        recommandation_allocation=_ORDER[idx_global],
        score_global=score_global,
    )
