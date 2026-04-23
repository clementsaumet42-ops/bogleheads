"""Pydantic v2 schemas for all YAML configuration files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).parent.parent
CONFIG_DIR = ROOT / "config"


# ─── Base config ─────────────────────────────────────────────────────────────


class _Lenient(BaseModel):
    """Base model that allows extra fields (forward-compat)."""

    model_config = ConfigDict(extra="allow")


# ─── ETF / Univers ETF ────────────────────────────────────────────────────────


class ETFEligibilite(_Lenient):
    PEA: bool = False
    PER: bool = False
    PEE: bool = False
    CTO_perso: bool = False
    CTO_IS: bool = False
    Contrat_Cap_IS: bool = False
    AV_UC: bool = False


class ETF(_Lenient):
    isin: str
    ticker: str
    nom: str
    emetteur: str
    classe_actifs: str
    sous_classe: Optional[str] = None
    ter: float = Field(ge=0)
    devise: str
    domicile: str
    capitalisant: bool
    eur_hedged: bool
    eligibilite: ETFEligibilite = Field(default_factory=ETFEligibilite)
    notes: Optional[str] = None
    methode_replication: Optional[str] = None
    url_dic_kid: Optional[str] = None
    date_verification_dic: Optional[str] = None
    contrats_av_reference: List[str] = Field(default_factory=list)
    frais_entree_typique_pct: float = Field(default=0.0, ge=0)


class UniversETFWrapper(_Lenient):
    univers_etf: List[ETF]


# ─── Enveloppes ───────────────────────────────────────────────────────────────


class Enveloppe(_Lenient):
    id: str
    nom: str
    plafond: Optional[Union[int, float]] = None
    fiscalite_entree: Optional[str] = None
    fiscalite_courante: Optional[Dict[str, Any]] = None
    fiscalite_sortie: Optional[Union[str, Dict[str, Any]]] = None
    avantages: List[str] = Field(default_factory=list)
    inconvenients: List[str] = Field(default_factory=list)
    eligible_etf_types: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class EnveloppesWrapper(_Lenient):
    enveloppes: List[Enveloppe]


# ─── Profils clients ──────────────────────────────────────────────────────────


class AllocationCible(_Lenient):
    actions: float = Field(ge=0, le=1)
    obligations: float = Field(default=0.0, ge=0, le=1)
    immobilier_cote: float = Field(default=0.0, ge=0, le=1)
    or_: float = Field(default=0.0, ge=0, le=1, alias="or")
    liquidites: float = Field(default=0.0, ge=0, le=1)
    commentaire: Optional[str] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @model_validator(mode="after")
    def somme_proche_de_1(self) -> AllocationCible:
        total = self.actions + self.obligations + self.immobilier_cote + self.or_ + self.liquidites
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"La somme des allocations doit être ≈ 1, obtenu {total:.4f}")
        return self


class Profil(_Lenient):
    id: int
    code: str
    nom: str
    age: int = Field(ge=0, le=120)
    tmi: float = Field(ge=0, le=1)
    rfr_annuel: Optional[float] = None
    patrimoine_financier_total: float = Field(default=0.0, ge=0)
    allocation_cible_bogleheads: AllocationCible
    enveloppes_disponibles: Optional[Dict[str, Any]] = None


class ProfilsWrapper(_Lenient):
    disclaimer: str
    profils: List[Profil]


# ─── Fiscalité 2026 ───────────────────────────────────────────────────────────


class PrelevementsSociaux(_Lenient):
    taux_global: float = Field(ge=0, le=1)
    detail: Optional[Dict[str, float]] = None


class PFU(_Lenient):
    taux_ir: float = Field(ge=0, le=1)
    taux_total_avec_ps: float = Field(ge=0, le=1)


class Fiscalite2026(_Lenient):
    annee: int
    prelevements_sociaux: PrelevementsSociaux
    pfu: PFU


# ─── Paramètres de projection ─────────────────────────────────────────────────


class ParamsProjection(_Lenient):
    classes_actifs: Dict[str, Any]
    correlations: Optional[Dict[str, Any]] = None
    simulation: Optional[Dict[str, Any]] = None
    inflation_annuelle: Optional[float] = None


# ─── Glide paths ──────────────────────────────────────────────────────────────


class GlidePath(_Lenient):
    glide_paths: Dict[str, Any]
    repartition_actions_defaut: Optional[Dict[str, Any]] = None
    association_profils: Optional[Dict[str, Any]] = None


# ─── Rebalancement / flux ─────────────────────────────────────────────────────


class RebalancementFlux(_Lenient):
    bandes_tolerance: Dict[str, Any]
    priorites_classes: Optional[List[str]] = None
    hypothese_plus_value_latente_pct: Optional[float] = None
    taux_fiscalite_par_enveloppe: Optional[Dict[str, Any]] = None


# ─── Chargement et validation centralisés ────────────────────────────────────

_SCHEMAS: dict = {
    "univers_etf.yaml": UniversETFWrapper,
    "enveloppes.yaml": EnveloppesWrapper,
    "profils_clients.yaml": ProfilsWrapper,
    "fiscalite_2026.yaml": Fiscalite2026,
    "projection_params.yaml": ParamsProjection,
    "glide_paths.yaml": GlidePath,
    "rebalancement_flux.yaml": RebalancementFlux,
}


def charger_et_valider(filename: str) -> Any:
    """Load a YAML config file and return a validated Pydantic model instance."""
    schema = _SCHEMAS.get(filename)
    if schema is None:
        raise KeyError(f"No schema registered for '{filename}'")

    path = CONFIG_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    return schema.model_validate(raw)
