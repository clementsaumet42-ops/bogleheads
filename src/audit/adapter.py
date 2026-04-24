"""Adaptateur Profil → ContexteAudit — S8.2c.

Construit un ContexteAudit à partir d'un Profil existant sans modifier le schéma Profil.
Les champs absents (broker, contrat AV) reçoivent des valeurs par défaut documentées
et génèrent des avertissements dans le rapport final.
"""

from __future__ import annotations

import logging

from src.audit.master import ContexteAudit
from src.audit.opportunite import LigneEtf
from src.schemas import Broker, ContratAV, Profil

logger = logging.getLogger(__name__)

# ─── Valeurs par défaut documentées ─────────────────────────────────────────

# Broker générique par défaut si non renseigné dans le profil
_BROKER_DEFAUT_ID = "bourse_direct"

# Frais UC moyen d'un contrat AV standard (milieu de gamme)
_FRAIS_UC_DEFAUT = 0.0085  # 85 bps — contrat bancaire classique

# Frais fonds euros moyen
_FRAIS_FE_DEFAUT = 0.0060  # 60 bps

# Nom du broker hypothèse
_NOM_BROKER_DEFAUT = "Bourse Direct"


def _construire_broker_defaut() -> Broker:
    """Crée un broker Bourse Direct par défaut (données publiques 2025)."""
    return Broker(
        id="bourse_direct",
        nom="Bourse Direct",
        frais_courtage_actions_euronext_eur=0.99,
        frais_courtage_actions_euronext_pct=None,
        frais_courtage_actions_us_eur=2.50,
        frais_courtage_actions_us_pct=None,
        minimum_ordre_eur=0.0,
        frais_change_devise_pct=0.0025,
        frais_garde_annuel_eur=0.0,
        frais_inactivite_annuel_eur=0.0,
        pea_disponible=True,
        pea_pme_disponible=True,
        cto_disponible=True,
        per_disponible=True,
        av_disponible=False,
        plateforme_qualite=3,
        fiscalite_ifu_automatique=True,
        reporting_qualite=3,
        support_client_score=3,
        agrement="ACPR/AMF — prestataire de services d'investissement",
        annees_existence=25,
        sources=["https://www.boursedirect.fr/fr/tarifs"],
    )


def _construire_contrat_av_moyen_defaut() -> ContratAV:
    """Crée un contrat AV 'bancaire standard' par défaut (hypothèse milieu de gamme)."""
    return ContratAV(
        id="av_bancaire_generique",
        nom="Contrat AV bancaire (hypothèse)",
        assureur="Assureur générique",
        distributeur="Réseau bancaire",
        frais_gestion_uc_pct=_FRAIS_UC_DEFAUT,
        frais_gestion_fonds_euros_pct=_FRAIS_FE_DEFAUT,
        frais_entree_pct=0.0,
        frais_arbitrage_pct=0.0,
        nb_arbitrages_gratuits_an=None,
        nb_uc_total=100,
        nb_etf=5,
        nb_scpi=10,
        nb_sci=2,
        nb_private_equity=0,
        fonds_euros_disponible=True,
        fonds_euros_nom=None,
        rendement_fonds_euros_2024=None,
        rendement_fonds_euros_2023=None,
        versement_minimum_eur=500.0,
        versement_programme_min_eur=50.0,
        eligible_nue_propriete=False,
        eligible_gestion_pilotee=True,
        gestion_libre=True,
        notation_experts_moyenne=None,
        annees_existence=0,
        date_souscription_possible=None,
        sources=["Hypothèse milieu de gamme — contrat non renseigné dans le profil"],
    )


def _extraire_portefeuille(profil: Profil) -> list[LigneEtf]:
    """Extrait les lignes ETF depuis les positions détaillées du Profil.

    Utilise les `positions_detaillees` du Profil (champ S3.6).
    Si aucune position détaillée n'est renseignée, retourne une liste vide
    (le rapport d'audit le signalera via un avertissement).

    Args:
        profil: Profil client Pydantic.

    Returns:
        Liste de LigneEtf (peut être vide).
    """
    lignes: list[LigneEtf] = []

    if not profil.positions_detaillees:
        logger.debug("Profil %s : aucune position détaillée — portefeuille vide", profil.id)
        return lignes

    for pos in profil.positions_detaillees:
        # Mapping enveloppe Profil → enveloppe LigneEtf
        enveloppe_raw = pos.enveloppe
        enveloppe_map = {
            "PEA": "PEA",
            "PEA_PME": "PEA",
            "CTO_perso": "CTO",
            "CTO": "CTO",
            "CTO_IS": "CTO_IS",
            "AV": "AV",
            "AV_UC": "AV",
            "PER": "PER",
            "PEE": "PEE",
            "Contrat_Cap_IS": "Contrat_Cap_IS",
        }
        enveloppe = enveloppe_map.get(enveloppe_raw, "CTO")

        if pos.montant_actuel > 0 and pos.etf:
            # Utiliser le ticker comme ISIN provisoire si pas d'ISIN disponible
            # (les positions_detaillees utilisent ticker, pas isin)
            lignes.append(
                LigneEtf(
                    isin=pos.etf,  # ticker utilisé comme identifiant
                    montant_eur=pos.montant_actuel,
                    enveloppe=enveloppe,  # type: ignore[arg-type]
                )
            )

    return lignes


def contexte_depuis_profil(
    profil: Profil,
    broker_depuis_config: Broker | None = None,
    contrat_av_depuis_config: ContratAV | None = None,
) -> tuple[ContexteAudit, list[str]]:
    """Construit un ContexteAudit à partir d'un Profil.

    Extrait du Profil :
    - portefeuille (lignes ETF depuis positions_detaillees)
    - TMI client
    - horizon depuis profil.horizon_placement_ans (champ optionnel, défaut 30)
    - versements AV annuels (depuis capacite_epargne_annuelle si disponible)

    Valeurs par défaut si champs absents :
    - broker non renseigné → Bourse Direct (hypothèse documentée + avertissement)
    - contrat AV non renseigné → contrat bancaire générique 85 bps UC (+ avertissement)
    - montant AV → 0 si non détectable dans les enveloppes

    Note : ne modifie PAS le schéma Profil. L'adaptateur gère les champs absents
    avec defaults et avertissements. Modification du schéma Profil = sprint ultérieur.

    Args:
        profil: Profil client (depuis profils_clients.yaml).
        broker_depuis_config: Broker optionnel déjà chargé (évite une recherche).
        contrat_av_depuis_config: ContratAV optionnel déjà chargé.

    Returns:
        Tuple (ContexteAudit, liste d'avertissements) — les avertissements doivent
        être propagés dans le RapportAudit.
    """
    avertissements: list[str] = []

    # ── Portefeuille ──────────────────────────────────────────────────────────
    portefeuille = _extraire_portefeuille(profil)
    if not portefeuille:
        avertissements.append(
            "Portefeuille vide : aucune position_detaillee renseignée dans le profil. "
            "Renseigner les positions pour un audit ETF complet."
        )

    # ── TMI ────────────────────────────────────────────────────────────────────
    tmi = profil.tmi  # toujours présent (obligatoire dans le schéma)

    # ── Horizon ────────────────────────────────────────────────────────────────
    # Le champ horizon_placement_ans n'est pas dans le schéma Profil strict mais
    # peut être présent via extra="allow" (_Lenient). On utilise model_extra.
    horizon_ans = 30
    profil_extra = getattr(profil, "model_extra", {}) or {}
    if "horizon_placement_ans" in profil_extra:
        horizon_ans = int(profil_extra["horizon_placement_ans"])
    elif hasattr(profil, "horizon_placement_ans"):
        val = getattr(profil, "horizon_placement_ans", None)
        if val is not None:
            horizon_ans = int(val)

    # ── Broker ─────────────────────────────────────────────────────────────────
    broker_actuel: Broker | None = broker_depuis_config
    if broker_actuel is None:
        # Le profil ne contient pas (encore) de champ broker_actuel.
        # On utilise Bourse Direct comme hypothèse documentée.
        broker_actuel = _construire_broker_defaut()
        avertissements.append(
            f"Broker non renseigné dans le profil — hypothèse : {_NOM_BROKER_DEFAUT}. "
            "Renseigner broker_actuel dans le profil pour un audit frais broker précis."
        )

    # ── Montant AV ─────────────────────────────────────────────────────────────
    montant_av_eur = 0.0
    enveloppes = profil.enveloppes_disponibles or {}
    for cle, env in enveloppes.items():
        if "AV" in cle.upper() and isinstance(env, dict):
            montant_av_eur = float(env.get("encours_actuel", 0.0))
            break

    # ── Versements AV annuels ──────────────────────────────────────────────────
    versements_av = 0.0
    if "capacite_epargne_annuelle" in profil_extra:
        versements_av = float(profil_extra["capacite_epargne_annuelle"]) * 0.3
    elif hasattr(profil, "capacite_epargne_annuelle"):
        val = getattr(profil, "capacite_epargne_annuelle", None)
        if val is not None:
            versements_av = float(val) * 0.3  # hypothèse : 30% de l'épargne en AV

    # ── Contrat AV ─────────────────────────────────────────────────────────────
    contrat_av: ContratAV | None = contrat_av_depuis_config
    if contrat_av is None and montant_av_eur > 0:
        contrat_av = _construire_contrat_av_moyen_defaut()
        avertissements.append(
            f"Contrat AV non renseigné dans le profil (encours estimé {montant_av_eur:,.0f} €) "
            f"— hypothèse : contrat bancaire générique {_FRAIS_UC_DEFAUT * 100:.2f}% UC/an. "
            "Renseigner contrat_av_actuel dans le profil pour un audit frais AV précis."
        )

    contexte = ContexteAudit(
        portefeuille=portefeuille,
        contrat_av_actuel=contrat_av,
        montant_av_actuel_eur=montant_av_eur,
        versements_av_annuels_eur=versements_av,
        broker_actuel=broker_actuel,
        nb_ordres_par_an_estim=12,
        montant_moyen_ordre_eur=5000.0,
        parts_ordres_us_pct=0.5,
        tmi_client=tmi,
        horizon_ans=horizon_ans,
        taux_actualisation=0.04,
    )

    return contexte, avertissements
