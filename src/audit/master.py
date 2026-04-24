"""Orchestrateur audit patrimonial — S8.2c.

Agrège les 5 moteurs S8.2b en un rapport unifié, dédupliqué et trié par gain.
Le résultat est une liste rankée d'opportunités activables avec gain cumulé en €/an
et sur 30 ans — pour montrer au client, chiffre en main, combien il laisse sur la table.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any

from pydantic import BaseModel, Field

from src.audit.moteurs.dist_vs_cap import detecter_opportunites_dist_vs_cap
from src.audit.moteurs.frais_broker import detecter_opportunites_frais_broker
from src.audit.moteurs.frais_contrat_av import detecter_opportunites_frais_av
from src.audit.moteurs.tracking_difference import detecter_opportunites_td
from src.audit.moteurs.withholding import detecter_opportunites_withholding
from src.audit.opportunite import LigneEtf, Opportunite, capitaliser_30_ans
from src.schemas import Broker, ContratAV, ETFEnrichi, RetenuesSourceConfig

logger = logging.getLogger(__name__)

# Leviers connus — les 5 moteurs S8.2b
_LEVIERS = (
    "tracking_difference",
    "withholding_tax",
    "dist_vs_cap",
    "frais_contrat_av",
    "frais_broker",
)


class ContexteAudit(BaseModel):
    """Agrège tout ce qu'il faut pour lancer l'audit complet."""

    portefeuille: list[LigneEtf] = Field(default_factory=list)
    contrat_av_actuel: ContratAV | None = None
    montant_av_actuel_eur: float = 0.0
    versements_av_annuels_eur: float = 0.0
    broker_actuel: Broker | None = None
    nb_ordres_par_an_estim: int = 12
    montant_moyen_ordre_eur: float = 5000.0
    parts_ordres_us_pct: float = 0.5
    tmi_client: float = 0.30
    horizon_ans: int = 30
    taux_actualisation: float = 0.04


class RapportAudit(BaseModel):
    """Résultat complet de l'audit."""

    opportunites: list[Opportunite]
    """Opportunités triées par gain_30ans_eur décroissant."""

    gain_total_annuel_eur: float
    """Somme des gains annuels de toutes les opportunités activables."""

    gain_total_30ans_eur: float
    """Somme des gains capitalisés sur l'horizon d'actualisation."""

    nb_opportunites_haute_confiance: int
    """Nombre d'opportunités avec confiance='haute'."""

    nb_opportunites_activables_rapidement: int
    """Nombre d'opportunités avec delai_mise_en_oeuvre_jours <= 30."""

    synthese_par_levier: dict[str, dict[str, Any]]
    """Par levier : {nb, gain_annuel_eur, gain_30ans_eur}. Les 5 leviers sont toujours présents."""

    hypotheses_utilisees: dict[str, Any]
    """Taux d'actualisation, horizon, TMI, pondérations géo, rendements dividendes."""

    avertissements: list[str]
    """Données manquantes, confiance basse sur un levier, hypothèses fortes."""


def _dedupliquer(opportunites: list[Opportunite]) -> list[Opportunite]:
    """Déduplique les opportunités pour éviter le double comptage.

    Règle : si deux Opportunite ont le même (etf_source, etf_cible) — identifiable
    par l'id qui contient "{ticker_source}_vs_{ticker_cible}" — on garde uniquement
    celle avec le plus gros gain_annuel_eur.

    Principe conservateur : pas d'addition des gains de leviers compatibles,
    on prend le plus gros gain individuel. L'agrégation fine (simultanéité des
    leviers) sera traitée dans un sprint ultérieur.

    Args:
        opportunites: liste brute de toutes les opportunités des 5 moteurs.

    Returns:
        Liste dédupliquée — au plus une opportunité par paire (source, cible).
    """
    # Index par paire source-cible extraite de l'id
    # Format id : "prefix.levier.TICKER_SOURCE_vs_TICKER_CIBLE" ou "broker.frais.ID1_vers_ID2"
    paires: dict[str, Opportunite] = {}

    for opp in opportunites:
        # Extraire la clé de déduplication depuis l'id
        parts = opp.id.split(".")
        paire_key = parts[2] if len(parts) >= 3 else opp.id

        if paire_key not in paires:
            paires[paire_key] = opp
        else:
            existing = paires[paire_key]
            if opp.gain_annuel_eur > existing.gain_annuel_eur:
                paires[paire_key] = opp

    return list(paires.values())


def _synthese_par_levier(
    opportunites: list[Opportunite],
    taux_actualisation: float,
    horizon_ans: int,
) -> dict[str, dict[str, Any]]:
    """Calcule la synthèse des gains par levier.

    Tous les 5 leviers sont présents dans le résultat, même à 0.

    Args:
        opportunites: liste des opportunités (après déduplication).
        taux_actualisation: taux pour recalculer gain_30ans si horizon différent.
        horizon_ans: horizon de capitalisation (peut différer de 30).

    Returns:
        {levier: {nb, gain_annuel_eur, gain_30ans_eur}}
    """
    synthese: dict[str, dict[str, Any]] = {
        levier: {"nb": 0, "gain_annuel_eur": 0.0, "gain_30ans_eur": 0.0} for levier in _LEVIERS
    }

    for opp in opportunites:
        levier = opp.levier
        if levier not in synthese:
            synthese[levier] = {"nb": 0, "gain_annuel_eur": 0.0, "gain_30ans_eur": 0.0}
        synthese[levier]["nb"] += 1
        synthese[levier]["gain_annuel_eur"] += opp.gain_annuel_eur
        # Recalculer le gain capitalisé sur l'horizon du contexte
        synthese[levier]["gain_30ans_eur"] += capitaliser_30_ans(
            opp.gain_annuel_eur, taux_actualisation, horizon_ans
        )

    # Arrondir
    for levier in synthese:
        synthese[levier]["gain_annuel_eur"] = round(synthese[levier]["gain_annuel_eur"], 2)
        synthese[levier]["gain_30ans_eur"] = round(synthese[levier]["gain_30ans_eur"], 0)

    return synthese


def auditer_patrimoine(
    contexte: ContexteAudit,
    univers_etf: list[ETFEnrichi],
    contrats_av_marche: list[ContratAV],
    brokers_marche: list[Broker],
    matrice_retenues: RetenuesSourceConfig,
) -> RapportAudit:
    """Orchestre les 5 moteurs S8.2b et produit un rapport d'audit complet.

    Étapes :
    1. Appelle les 5 moteurs en séquence (CPU-light, pas besoin d'async).
    2. Concatène toutes les Opportunite retournées.
    3. Déduplique : si deux opportunités ciblent la même paire (source, cible),
       on garde uniquement celle avec le plus gros gain_annuel_eur (pas d'addition,
       pour rester conservateur et éviter le double comptage).
    4. Trie par gain_30ans_eur décroissant.
    5. Calcule les agrégats pour le rapport.
    6. Collecte les avertissements depuis les moteurs (données manquantes, hypothèses fortes).

    Note sur la déduplication (principe conservateur S8.2c) :
        Deux leviers peuvent porter sur le même switch ETF (ex: TD + withholding).
        On ne les additionne PAS pour éviter le double comptage.
        L'agrégation fine (simultanéité des leviers) sera traitée en sprint ultérieur.

    Args:
        contexte: paramètres du client (portefeuille, contrat AV, broker, TMI, horizon).
        univers_etf: catalogue ETF enrichi S8.2a.
        contrats_av_marche: contrats AV disponibles sur le marché.
        brokers_marche: brokers disponibles sur le marché.
        matrice_retenues: matrice de retenues à la source par pays × domicile ETF.

    Returns:
        RapportAudit avec opportunités triées par gain 30 ans, synthèse par levier,
        hypothèses utilisées et avertissements.
    """
    avertissements: list[str] = []
    toutes_opportunites: list[Opportunite] = []

    # ── Moteur 1 : Tracking Difference ────────────────────────────────────────
    if contexte.portefeuille and univers_etf:
        with warnings.catch_warnings(record=True) as w_td:
            warnings.simplefilter("always")
            opps_td = detecter_opportunites_td(contexte.portefeuille, univers_etf)
            for warning in w_td:
                avertissements.append(f"[tracking_difference] {warning.message}")
        toutes_opportunites.extend(opps_td)
        logger.debug("tracking_difference: %d opportunités", len(opps_td))
    else:
        avertissements.append(
            "tracking_difference : portefeuille ou univers ETF vide — moteur ignoré"
        )

    # ── Moteur 2 : Withholding Tax ─────────────────────────────────────────────
    if contexte.portefeuille and univers_etf:
        with warnings.catch_warnings(record=True) as w_wh:
            warnings.simplefilter("always")
            opps_wh = detecter_opportunites_withholding(
                contexte.portefeuille, univers_etf, matrice_retenues
            )
            for warning in w_wh:
                avertissements.append(f"[withholding] {warning.message}")
        toutes_opportunites.extend(opps_wh)
        logger.debug("withholding: %d opportunités", len(opps_wh))
    else:
        avertissements.append("withholding : portefeuille ou univers ETF vide — moteur ignoré")

    # ── Moteur 3 : Distribution vs Capitalisation ──────────────────────────────
    if contexte.portefeuille and univers_etf:
        with warnings.catch_warnings(record=True) as w_dc:
            warnings.simplefilter("always")
            opps_dc = detecter_opportunites_dist_vs_cap(
                contexte.portefeuille, univers_etf, contexte.tmi_client
            )
            for warning in w_dc:
                avertissements.append(f"[dist_vs_cap] {warning.message}")
        toutes_opportunites.extend(opps_dc)
        logger.debug("dist_vs_cap: %d opportunités", len(opps_dc))
    else:
        avertissements.append("dist_vs_cap : portefeuille ou univers ETF vide — moteur ignoré")

    # ── Moteur 4 : Frais contrat AV ────────────────────────────────────────────
    if contexte.contrat_av_actuel is not None and contexte.montant_av_actuel_eur > 0:
        opps_av = detecter_opportunites_frais_av(
            contexte.contrat_av_actuel,
            contexte.montant_av_actuel_eur,
            contexte.versements_av_annuels_eur,
            contrats_av_marche,
        )
        toutes_opportunites.extend(opps_av)
        logger.debug("frais_contrat_av: %d opportunités", len(opps_av))
    else:
        avertissements.append(
            "frais_contrat_av : contrat AV non renseigné ou montant nul — moteur ignoré"
        )

    # ── Moteur 5 : Frais broker ────────────────────────────────────────────────
    if contexte.broker_actuel is not None:
        opps_broker = detecter_opportunites_frais_broker(
            contexte.broker_actuel,
            contexte.nb_ordres_par_an_estim,
            contexte.montant_moyen_ordre_eur,
            contexte.parts_ordres_us_pct,
            brokers_marche,
        )
        toutes_opportunites.extend(opps_broker)
        logger.debug("frais_broker: %d opportunités", len(opps_broker))
    else:
        avertissements.append(
            "frais_broker : broker non renseigné dans le profil, hypothèse : Bourse Direct"
        )

    # ── Déduplication ──────────────────────────────────────────────────────────
    opportunites_dedup = _dedupliquer(toutes_opportunites)

    # ── Recalcul des gains 30 ans avec l'horizon du contexte ──────────────────
    # Les moteurs utilisent leur propre horizon (30 ans / taux 4% par défaut).
    # Si le contexte diffère, on recalcule pour la cohérence du rapport.
    if contexte.horizon_ans != 30 or contexte.taux_actualisation != 0.04:
        opportunites_recalculees = []
        for opp in opportunites_dedup:
            gain_recalc = capitaliser_30_ans(
                opp.gain_annuel_eur, contexte.taux_actualisation, contexte.horizon_ans
            )
            opportunites_recalculees.append(
                opp.model_copy(update={"gain_30ans_eur": round(gain_recalc, 0)})
            )
        opportunites_dedup = opportunites_recalculees

    # ── Tri par gain 30 ans décroissant ────────────────────────────────────────
    opportunites_dedup.sort(key=lambda o: o.gain_30ans_eur, reverse=True)

    # ── Agrégats ───────────────────────────────────────────────────────────────
    gain_total_annuel = sum(o.gain_annuel_eur for o in opportunites_dedup)
    gain_total_30ans = sum(o.gain_30ans_eur for o in opportunites_dedup)
    nb_haute_confiance = sum(1 for o in opportunites_dedup if o.confiance == "haute")
    nb_activables_rapide = sum(1 for o in opportunites_dedup if o.delai_mise_en_oeuvre_jours <= 30)

    synthese = _synthese_par_levier(
        opportunites_dedup, contexte.taux_actualisation, contexte.horizon_ans
    )

    hypotheses: dict[str, Any] = {
        "taux_actualisation": contexte.taux_actualisation,
        "horizon_ans": contexte.horizon_ans,
        "tmi_client": contexte.tmi_client,
        "ponderation_geo": "MSCI_ACWI (60% US, 28% Dev hors US, 12% EM) par défaut",
        "rendement_dividende_defaut": "1.8%/an (MSCI_ACWI, source Bloomberg 2024)",
        "rendement_total_actions": "7%/an nominal (DMS 2024)",
        "nb_ordres_par_an": contexte.nb_ordres_par_an_estim,
        "montant_moyen_ordre_eur": contexte.montant_moyen_ordre_eur,
        "parts_ordres_us_pct": contexte.parts_ordres_us_pct,
    }

    # Avertissement si portefeuille vide
    if not contexte.portefeuille:
        avertissements.append(
            "Portefeuille vide : aucun ETF renseigné, résultats non représentatifs"
        )

    return RapportAudit(
        opportunites=opportunites_dedup,
        gain_total_annuel_eur=round(gain_total_annuel, 2),
        gain_total_30ans_eur=round(gain_total_30ans, 0),
        nb_opportunites_haute_confiance=nb_haute_confiance,
        nb_opportunites_activables_rapidement=nb_activables_rapide,
        synthese_par_levier=synthese,
        hypotheses_utilisees=hypotheses,
        avertissements=avertissements,
    )
