"""Pydantic v2 schemas for all YAML configuration files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
    sous_classe: str | None = None
    ter: float = Field(ge=0)
    devise: str
    domicile: str
    capitalisant: bool
    eur_hedged: bool
    eligibilite: ETFEligibilite = Field(default_factory=ETFEligibilite)
    notes: str | None = None
    methode_replication: str | None = None
    url_dic_kid: str | None = None
    date_verification_dic: str | None = None
    contrats_av_reference: list[str] = Field(default_factory=list)
    frais_entree_typique_pct: float = Field(default=0.0, ge=0)


class UniversETFWrapper(_Lenient):
    univers_etf: list[ETF]


# ─── Enveloppes ───────────────────────────────────────────────────────────────


class Enveloppe(_Lenient):
    id: str
    nom: str
    plafond: int | float | None = None
    fiscalite_entree: str | None = None
    fiscalite_courante: dict[str, Any] | None = None
    fiscalite_sortie: str | dict[str, Any] | None = None
    avantages: list[str] = Field(default_factory=list)
    inconvenients: list[str] = Field(default_factory=list)
    eligible_etf_types: list[str] = Field(default_factory=list)
    notes: str | None = None


class EnveloppesWrapper(_Lenient):
    enveloppes: list[Enveloppe]


# ─── Rebalancement Optimal — positions détaillées & lots ─────────────────────


class Lot(_Lenient):
    """Lot d'acquisition d'un ETF (pour méthode FIFO CTO/IS ou traçabilité)."""

    date_acquisition: str  # ISO 8601 : "YYYY-MM-DD"
    quantite: float = Field(ge=0)
    prix_unitaire: float = Field(ge=0)


class PositionDetaillee(_Lenient):
    """Position détaillée d'un ETF dans une enveloppe, avec lots et prix de revient."""

    etf: str  # ticker
    enveloppe: str  # ex. "PEA", "CTO_perso", "AV", "PER"
    quantite: float = Field(ge=0)
    prix_revient_moyen: float = Field(ge=0)  # CMP — pour CTO/IR et calcul PV
    lots: list[Lot] = Field(default_factory=list)  # pour FIFO (CTO/IS) et traçabilité
    montant_actuel: float = Field(ge=0)  # valeur de marché actuelle en €
    date_ouverture_enveloppe: str | None = None  # pour tests PEA ≥5 ans, AV ≥8 ans


class AbattementsUtilises(_Lenient):
    """Suivi des abattements annuels utilisés (reset au 1er janvier)."""

    av_abattement_annuel_restant: float = Field(
        default=4600.0, ge=0
    )  # 4 600 € (célibataire) ou 9 200 € (couple)


# ─── Profils clients ──────────────────────────────────────────────────────────


class AllocationCible(_Lenient):
    actions: float = Field(ge=0, le=1)
    obligations: float = Field(default=0.0, ge=0, le=1)
    immobilier_cote: float = Field(default=0.0, ge=0, le=1)
    or_: float = Field(default=0.0, ge=0, le=1, alias="or")
    liquidites: float = Field(default=0.0, ge=0, le=1)
    commentaire: str | None = None

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
    rfr_annuel: float | None = None
    patrimoine_financier_total: float = Field(default=0.0, ge=0)
    allocation_cible_bogleheads: AllocationCible
    enveloppes_disponibles: dict[str, Any] | None = None
    # S3.6 — rebalancement optimal
    regime_fiscal_detenteur: str = Field(
        default="IR"
    )  # "IR" (particulier) ou "IS" (personne morale)
    positions_detaillees: list[PositionDetaillee] = Field(default_factory=list)
    abattements_utilises: AbattementsUtilises = Field(default_factory=AbattementsUtilises)
    frais_courtier_par_transaction: float = Field(default=0.0, ge=0)  # € par transaction


class ProfilsWrapper(_Lenient):
    disclaimer: str
    profils: list[Profil]


# ─── Fiscalité 2026 ───────────────────────────────────────────────────────────


class PrelevementsSociaux(_Lenient):
    taux_global: float = Field(ge=0, le=1)
    detail: dict[str, float] | None = None


class PFU(_Lenient):
    taux_ir: float = Field(ge=0, le=1)
    taux_total_avec_ps: float = Field(ge=0, le=1)


class Fiscalite2026(_Lenient):
    annee: int
    prelevements_sociaux: PrelevementsSociaux
    pfu: PFU


# ─── Paramètres de projection ─────────────────────────────────────────────────


class ParamsProjection(_Lenient):
    classes_actifs: dict[str, Any]
    correlations: dict[str, Any] | None = None
    simulation: dict[str, Any] | None = None
    inflation_annuelle: float | None = None


# ─── Glide paths ──────────────────────────────────────────────────────────────


class GlidePath(_Lenient):
    glide_paths: dict[str, Any]
    repartition_actions_defaut: dict[str, Any] | None = None
    association_profils: dict[str, Any] | None = None


# ─── Rebalancement / flux ─────────────────────────────────────────────────────


class RebalancementFlux(_Lenient):
    bandes_tolerance: dict[str, Any]
    priorites_classes: list[str] | None = None
    hypothese_plus_value_latente_pct: float | None = None
    taux_fiscalite_par_enveloppe: dict[str, Any] | None = None


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
