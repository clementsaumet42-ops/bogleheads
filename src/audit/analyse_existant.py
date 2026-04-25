"""Analyse du patrimoine existant vs allocation cible.

Calcule les drifts, concentration, coût fiscal annuel estimé et +values latentes.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

TAUX_DISTRIBUTION: dict[str, float] = {
    "actions_usa": 0.018,
    "actions_dev_ex_usa": 0.025,
    "actions_em": 0.022,
    "actions_monde_acwi": 0.018,
    "obligations_euro": 0.022,
    "obligations_gov_euro": 0.020,
    "obligations_hy": 0.045,
    "immobilier_cote": 0.040,
    "or_matieres": 0.0,
    "monetaire": 0.035,
}

TAUX_IMPOSITION_DIVIDENDES: dict[str, float] = {
    "PEA": 0.0,
    "PEA_PME": 0.0,
    "AV": 0.0,
    "PER": 0.0,
    "CTO": 0.30,
    "CTO_IS": 0.25,
    "Contrat_Cap_IS": 0.25,
}


class DiagnosticExistant(BaseModel):
    montant_total_eur: float = 0.0
    repartition_par_classe: dict[str, float] = Field(default_factory=dict)
    repartition_par_enveloppe: dict[str, float] = Field(default_factory=dict)
    pourcentage_par_classe: dict[str, float] = Field(default_factory=dict)
    pourcentage_par_enveloppe: dict[str, float] = Field(default_factory=dict)
    drift_par_classe: dict[str, float] = Field(default_factory=dict)
    classes_sur_ponderees: list[str] = Field(default_factory=list)
    classes_sous_ponderees: list[str] = Field(default_factory=list)
    concentration_max_enveloppe_pct: float = 0.0
    risque_concentration: bool = False
    cout_fiscal_annuel_estime_eur: float = 0.0
    plus_values_latentes_eur: float = 0.0


def analyser_existant(
    profil: object,
    allocation_cible: dict[str, float],
    univers_etf: list | None = None,
    taux_distribution_par_classe: dict[str, float] | None = None,
) -> DiagnosticExistant:
    """Diagnostique le patrimoine existant vs allocation cible."""
    taux_dist = taux_distribution_par_classe or TAUX_DISTRIBUTION

    composition = []
    if hasattr(profil, "composition_actuelle"):
        composition = profil.composition_actuelle or []
    elif isinstance(profil, dict):
        composition = profil.get("composition_actuelle", []) or []

    if not composition:
        return DiagnosticExistant()

    rep_classe: dict[str, float] = {}
    rep_env: dict[str, float] = {}
    pv_latentes = 0.0
    cout_fiscal = 0.0
    total = 0.0

    for ligne in composition:
        if hasattr(ligne, "model_dump"):
            data = ligne.model_dump()
        elif isinstance(ligne, dict):
            data = ligne
        else:
            continue

        montant = float(data.get("montant_eur", 0) or 0)
        env = str(data.get("enveloppe", ""))
        classe = str(data.get("classe_actif", ""))
        prix_rev = data.get("prix_revient_eur")

        total += montant
        rep_classe[classe] = rep_classe.get(classe, 0.0) + montant
        rep_env[env] = rep_env.get(env, 0.0) + montant

        if prix_rev is not None:
            pv_latentes += montant - float(prix_rev)

        taux_div = taux_dist.get(classe, 0.018)
        dividendes = montant * taux_div
        taux_imp = 0.0
        for key, rate in TAUX_IMPOSITION_DIVIDENDES.items():
            if env.startswith(key) or env == key:
                taux_imp = rate
                break
        cout_fiscal += dividendes * taux_imp

    pct_classe = {k: v / total for k, v in rep_classe.items()} if total > 0 else {}
    pct_env = {k: v / total for k, v in rep_env.items()} if total > 0 else {}

    max_env_pct = max(pct_env.values()) if pct_env else 0.0

    drift: dict[str, float] = {}
    for classe, cible in allocation_cible.items():
        actuel = pct_classe.get(classe, 0.0)
        drift[classe] = round(actuel - cible, 4)

    sur_pond = [k for k, v in drift.items() if v > 0.05]
    sous_pond = [k for k, v in drift.items() if v < -0.05]

    return DiagnosticExistant(
        montant_total_eur=round(total, 2),
        repartition_par_classe=rep_classe,
        repartition_par_enveloppe=rep_env,
        pourcentage_par_classe={k: round(v, 4) for k, v in pct_classe.items()},
        pourcentage_par_enveloppe={k: round(v, 4) for k, v in pct_env.items()},
        drift_par_classe=drift,
        classes_sur_ponderees=sur_pond,
        classes_sous_ponderees=sous_pond,
        concentration_max_enveloppe_pct=round(max_env_pct, 4),
        risque_concentration=max_env_pct > 0.80,
        cout_fiscal_annuel_estime_eur=round(cout_fiscal, 2),
        plus_values_latentes_eur=round(pv_latentes, 2),
    )
