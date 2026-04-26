"""Pydantic v2 schemas for all YAML configuration files."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any, Literal

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
    isin: str | None = None
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
    # S11-B : champs d'audit qualité
    derniere_verification: date | None = None  # date de revue manuelle des données
    audit_status: str = "non_verifie"  # "ok", "warn", "fail", "non_verifie"
    audit_notes: str | None = None  # notes libres sur l'audit


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


class LigneExistante(_Lenient):
    """Une ligne de portefeuille déjà détenue par le client."""

    enveloppe: str
    etf_isin: str | None = None
    etf_ticker: str | None = None
    libelle_libre: str | None = None
    classe_actif: str
    montant_eur: float
    prix_revient_eur: float | None = None
    date_acquisition: date | None = None
    quantite: float | None = None


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


# ─── S2 — Optimiseur d'allocation ────────────────────────────────────────────


class ClasseActifConfig(_Lenient):
    """Paramètres d'une classe d'actifs pour l'optimiseur."""

    rendement_attendu_annuel: float = Field(ge=0)
    volatilite_annuelle: float = Field(ge=0)
    frais_ter_moyen: float = Field(ge=0, default=0.0)
    eligible_pea: bool = False
    eligible_per: bool = True
    eligible_av: bool = True
    eligible_cto: bool = True
    dividendes_eleves: bool = False


class ProfilAversionRisque(_Lenient):
    """Profil d'aversion au risque pour l'optimiseur Markowitz."""

    lambda_: float = Field(ge=0, le=1, alias="lambda")
    actions_min: float = Field(default=0.0, ge=0, le=1)
    actions_max: float = Field(default=1.0, ge=0, le=1)
    description: str | None = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class OptimiseurConfig(_Lenient):
    """Configuration complète de l'optimiseur d'allocation (config/optimiseur.yaml)."""

    classes_actifs: dict[str, ClasseActifConfig]
    correlations: dict[str, dict[str, float]] | None = None
    profils_aversion_risque: dict[str, ProfilAversionRisque]
    frais_gestion_enveloppes: dict[str, float] = Field(default_factory=dict)
    taux_sans_risque: float = Field(default=0.025, ge=0)


class ContraintesPersonnalisees(_Lenient):
    """Contraintes personnalisées d'allocation par profil client."""

    exposition_usa_max: float | None = Field(default=None, ge=0, le=1)
    exposition_em_max: float | None = Field(default=None, ge=0, le=1)
    exposition_geo_europe_min: float | None = Field(default=None, ge=0, le=1)
    actions_max: float | None = Field(default=None, ge=0, le=1)
    actions_min: float | None = Field(default=None, ge=0, le=1)
    obligations_min: float | None = Field(default=None, ge=0, le=1)


class ResultatOptimisation(_Lenient):
    """Résultat de l'optimisation d'allocation (Mode A)."""

    poids: dict[str, float]
    rendement_attendu: float
    volatilite_attendue: float
    ratio_sharpe: float
    statut: str = "optimal"  # "optimal", "fallback", "infeasible"
    message: str | None = None


class VentilationEnveloppe(_Lenient):
    """Ventilation d'une classe d'actifs par enveloppe (Mode B)."""

    classe: str
    enveloppe: str
    montant: float = Field(ge=0)


class ResultatAssetLocation(_Lenient):
    """Résultat de l'optimisation d'asset location (Mode B)."""

    ventilation: list[VentilationEnveloppe]
    cout_annuel_optimise: float
    cout_annuel_naif: float
    economie_annuelle: float
    statut: str = "optimal"
    message: str | None = None


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
    # S2 — Optimiseur d'allocation
    profil_aversion_risque: str | None = None  # clé dans optimiseur.yaml
    contraintes_personnalisees: ContraintesPersonnalisees = Field(
        default_factory=ContraintesPersonnalisees
    )
    # S3.6 — rebalancement optimal
    regime_fiscal_detenteur: str = Field(
        default="IR"
    )  # "IR" (particulier) ou "IS" (personne morale)
    positions_detaillees: list[PositionDetaillee] = Field(default_factory=list)
    abattements_utilises: AbattementsUtilises = Field(default_factory=AbattementsUtilises)
    frais_courtier_par_transaction: float = Field(default=0.0, ge=0)  # € par transaction
    composition_actuelle: list[LigneExistante] = Field(default_factory=list)

    # ── Champs S12 — moteur d'alertes ────────────────────────────────────────
    revenu_fiscal_reference: float | None = None
    taeg_credits_conso: float | None = None
    taeg_credit_immo: float | None = None
    solde_credit_conso: float | None = None
    capital_restant_immo: float | None = None
    abondement_employeur_max: float | None = None
    abondement_employeur_actuel: float | None = None
    a_pee: bool | None = None
    a_perco: bool | None = None
    participation_versee_pee: bool | None = None
    est_en_couple: bool | None = None
    a_testament: bool | None = None
    clause_beneficiaire_demembree: bool | None = None
    clause_beneficiaire_renseignee: bool | None = None
    date_revue_patrimoine: str | None = None
    plafond_per_non_utilise: float | None = None
    a_utilise_ir_pme: bool | None = None
    a_utilise_donation: bool | None = None
    volume_ordres_annuel: float | None = None
    charges_mensuelles: float | None = None
    epargne_precaution: float | None = None
    a_livret_a: bool | None = None
    assurances_vie: list | None = None
    fond_de_fonds: bool | None = None
    pee_actions_entreprise_pct: float | None = None
    nb_credits_conso: int | None = None
    frais_entree_scpi: float | None = None
    ter_fonds_actifs: float | None = None


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


# ─── S3 — PDF client ─────────────────────────────────────────────────────────


class CabinetInfo(_Lenient):
    """Informations sur le cabinet CGP."""

    nom: str
    logo_path: str | None = None
    adresse: str | None = None
    telephone: str | None = None
    email: str | None = None
    site_web: str | None = None
    numero_orias: str | None = None
    mention_conformite: str | None = None


class PDFStyle(_Lenient):
    """Style graphique du PDF client."""

    couleur_primary: str = "#1a4d8f"
    couleur_accent: str = "#d4a017"
    couleur_neutral: str = "#333333"
    police: str = "Helvetica"
    format_page: str = "A4"
    marges_cm: float = Field(default=2.0, ge=0)


class PDFFooter(_Lenient):
    """Pied de page du PDF client."""

    mention_legale: str = "Document confidentiel — ne pas diffuser"
    avertissement_amf: str = (
        "Les performances passées ne préjugent pas des performances futures. "
        "Le présent document ne constitue pas un conseil en investissement "
        "personnalisé au sens de la directive MIF II."
    )


class CabinetConfig(_Lenient):
    """Configuration complète du cabinet (config/pdf_cabinet.yaml)."""

    cabinet: CabinetInfo
    style: PDFStyle = Field(default_factory=PDFStyle)
    footer: PDFFooter = Field(default_factory=PDFFooter)


class ResultatPDF(_Lenient):
    """Résultat de la génération d'un PDF client."""

    chemin: str
    taille_octets: int
    nb_pages: int
    profil_id: int
    date_generation: str


# ─── S8.2a — ETF enrichi ──────────────────────────────────────────────────────


class AlternativeEcartee(_Lenient):
    """Alternative ETF écartée avec justification."""

    ticker: str
    isin: str
    raison: str


class ETFEnrichi(ETF):
    """Extension de ETF avec les champs S8.2a (tracking difference, liquidité, alternatives)
    et S11-C (drag fiscal intra-NAV).
    """

    domicile_iso: str | None = None  # ISO-3166-1 alpha-2: IE, FR, LU, DE, etc.
    distribuant_capitalisant: str | None = None  # ACC | DIST
    tracking_difference_1y: float | None = None  # TD 1 an (négatif = sous-performance indice net)
    tracking_difference_3y: float | None = None  # TD 3 ans
    tracking_difference_5y: float | None = None  # TD 5 ans
    taux_retenue_source_effectif: float | None = Field(default=None, ge=0, le=1)
    securities_lending: bool | None = None
    revenu_sec_lending_bps_estim: float | None = Field(default=None, ge=0)
    spread_moyen_bps: float | None = Field(default=None, ge=0)
    volume_quotidien_m_eur: float | None = Field(default=None, ge=0)
    alternatives_ecartees: list[AlternativeEcartee] = Field(default_factory=list)
    # ─── S11-C : drag fiscal intra-NAV ──────────────────────────────────────
    # Ces 3 champs sont optionnels (None par défaut) pour ne pas casser les
    # fixtures existantes. Si l'un des trois manque, calculer_drag_fiscal_etf()
    # retourne 0.0 avec un warning logger.
    replication: Literal["physique_full", "physique_sampling", "synthetique_swap"] | None = None
    exposition_geo: (
        Literal["US", "Europe", "Monde_dev", "Monde_ACWI", "Emergents", "France", "Japon"] | None
    ) = None


# ─── S8.2a — Contrats d'assurance-vie ────────────────────────────────────────


class ContratAV(_Lenient):
    """Contrat d'assurance-vie français."""

    id: str
    nom: str
    assureur: str
    distributeur: str
    # Frais
    frais_gestion_uc_pct: float = Field(ge=0, le=0.05)
    frais_gestion_fonds_euros_pct: float = Field(ge=0, le=0.05)
    frais_entree_pct: float = Field(default=0.0, ge=0, le=0.10)
    frais_arbitrage_pct: float = Field(default=0.0, ge=0, le=0.05)
    nb_arbitrages_gratuits_an: int | None = None  # null = illimité
    # Univers
    nb_uc_total: int = Field(ge=0)
    nb_etf: int = Field(default=0, ge=0)
    nb_scpi: int = Field(default=0, ge=0)
    nb_sci: int = Field(default=0, ge=0)
    nb_private_equity: int = Field(default=0, ge=0)
    fonds_euros_disponible: bool = True
    fonds_euros_nom: str | None = None
    rendement_fonds_euros_2024: float | None = Field(default=None, ge=0, le=0.20)
    rendement_fonds_euros_2023: float | None = Field(default=None, ge=0, le=0.20)
    # Conditions
    versement_minimum_eur: float = Field(ge=0)
    versement_programme_min_eur: float = Field(default=0.0, ge=0)
    eligible_nue_propriete: bool = False
    eligible_gestion_pilotee: bool = False
    gestion_libre: bool = True
    # Qualité
    notation_experts_moyenne: float | None = Field(default=None, ge=0, le=5)
    annees_existence: int = Field(default=0, ge=0)
    # Fiscal
    date_souscription_possible: str | None = None  # ISO 8601
    # Meta
    sources: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def sources_non_vides(self) -> ContratAV:
        if not self.sources:
            raise ValueError(f"Contrat '{self.id}': au moins une source obligatoire")
        return self


class AssuranceVieConfig(_Lenient):
    """Root model pour contrats_av.yaml."""

    contrats_av: list[ContratAV]


# ─── S8.2a — Brokers ─────────────────────────────────────────────────────────


class Broker(_Lenient):
    """Broker disponible en France."""

    id: str
    nom: str
    # Frais ordres
    frais_courtage_actions_euronext_eur: float | None = Field(default=None, ge=0)
    frais_courtage_actions_euronext_pct: float | None = Field(default=None, ge=0, le=0.05)
    frais_courtage_actions_us_eur: float | None = Field(default=None, ge=0)
    frais_courtage_actions_us_pct: float | None = Field(default=None, ge=0, le=0.05)
    minimum_ordre_eur: float = Field(default=0.0, ge=0)
    # Frais change
    frais_change_devise_pct: float = Field(default=0.0, ge=0, le=0.05)
    # Frais garde
    frais_garde_annuel_eur: float = Field(default=0.0, ge=0)
    frais_inactivite_annuel_eur: float = Field(default=0.0, ge=0)
    # Éligibilité enveloppes
    pea_disponible: bool = False
    pea_pme_disponible: bool = False
    cto_disponible: bool = True
    per_disponible: bool = False
    av_disponible: bool = False
    # Qualité
    plateforme_qualite: int | None = Field(default=None, ge=1, le=5)
    fiscalite_ifu_automatique: bool = False
    reporting_qualite: int | None = Field(default=None, ge=1, le=5)
    support_client_score: int | None = Field(default=None, ge=1, le=5)
    # Meta
    agrement: str | None = None
    annees_existence: int = Field(default=0, ge=0)
    actionnariat: str | None = None
    sources: list[str] = Field(default_factory=list)


class BrokersConfig(_Lenient):
    """Root model pour brokers.yaml."""

    brokers: list[Broker]


# ─── S8.2a — Retenues à la source ────────────────────────────────────────────

_ISO2_PATTERN = re.compile(r"^[A-Z]{2}$")


class RetenuesSourceConfig(_Lenient):
    """Matrice des retenues à la source sur dividendes (pays émetteur × domicile ETF)."""

    version: str
    date_mise_a_jour: str | None = None
    sources: list[str] = Field(default_factory=list)
    matrice: dict[str, dict[str, float]]
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def valider_matrice(self) -> RetenuesSourceConfig:
        domiciles_valides = {"IE", "LU", "FR"}
        for pays_emetteur, domiciles in self.matrice.items():
            if not _ISO2_PATTERN.match(pays_emetteur):
                raise ValueError(f"Pays émetteur invalide (doit être ISO-2): '{pays_emetteur}'")
            for domicile, taux in domiciles.items():
                if not _ISO2_PATTERN.match(domicile):
                    raise ValueError(f"Domicile invalide (doit être ISO-2): '{domicile}'")
                if domicile not in domiciles_valides:
                    raise ValueError(
                        f"Domicile '{domicile}' non supporté. Valeurs: {domiciles_valides}"
                    )
                if not (0.0 <= taux <= 0.35):
                    raise ValueError(
                        f"Taux {pays_emetteur}→{domicile}={taux} hors bornes [0, 0.35]"
                    )
        return self


# ─── Chargement et validation centralisés ────────────────────────────────────

# ─── S9 — Backtest ────────────────────────────────────────────────────────────


class ConfigFraisBacktest(_Lenient):
    ter_par_classe: dict[str, float] = Field(default_factory=dict)
    courtage_par_ordre_eur: float = Field(default=1.0, ge=0)
    spread_bps: float = Field(default=5.0, ge=0)
    frais_enveloppe_annuel_pct: dict[str, float] = Field(default_factory=dict)


class ConfigFiscaliteBacktest(_Lenient):
    pfu_taux: float = Field(default=0.30, ge=0, le=1)
    ps_taux: float = Field(default=0.172, ge=0, le=1)
    distribution_par_classe: dict[str, float] = Field(default_factory=dict)
    rebalancement_seuil_pct: float = Field(default=0.05, ge=0)


class BacktestParams(_Lenient):
    capital_initial_eur: float = Field(default=100_000.0, ge=0)
    date_debut: str = "2003-01-31"
    date_fin: str = "2024-12-31"
    frais: ConfigFraisBacktest = Field(default_factory=ConfigFraisBacktest)
    fiscalite: ConfigFiscaliteBacktest = Field(default_factory=ConfigFiscaliteBacktest)
    portefeuilles_actifs: list[str] = Field(default_factory=list)


class ConfigBacktest(_Lenient):
    backtest: BacktestParams


_SCHEMAS: dict = {
    "univers_etf.yaml": UniversETFWrapper,
    "enveloppes.yaml": EnveloppesWrapper,
    "profils_clients.yaml": ProfilsWrapper,
    "fiscalite_2026.yaml": Fiscalite2026,
    "projection_params.yaml": ParamsProjection,
    "glide_paths.yaml": GlidePath,
    "rebalancement_flux.yaml": RebalancementFlux,
    "optimiseur.yaml": OptimiseurConfig,
    "pdf_cabinet.yaml": CabinetConfig,
    # S8.2a — nouvelles configs
    "contrats_av.yaml": AssuranceVieConfig,
    "brokers.yaml": BrokersConfig,
    "retenues_source.yaml": RetenuesSourceConfig,
    # S9 — Backtest
    "backtest.yaml": ConfigBacktest,
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
