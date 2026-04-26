"""Optimiseur Best Provider — S13 Lot C.

Pour un profil donné et une allocation cible, classe les providers du moins cher au plus cher
sur un horizon de 10 ans.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal

logger = logging.getLogger(__name__)

# Hypothèses de calcul
_NB_REBAL_PAR_AN = 1  # rebalancement annuel estimé
_CROISSANCE_ANNUELLE = 0.06  # rendement moyen estimé pour encours moyen


@dataclass
class CoutTotalProvider:
    """Coût total estimé d'un provider sur un horizon donné."""

    provider_id: str
    provider_nom: str
    type_provider: Literal["broker", "assureur_av", "teneur_per"]
    enveloppe: str
    cout_total_10y_eur: float
    detail: dict = field(default_factory=dict)
    score: float = 0.0  # 0-100, normalisé vs meilleur de la catégorie


def _encours_moyen(
    montant_initial: float, horizon: int, croissance: float = _CROISSANCE_ANNUELLE
) -> float:
    """Encours moyen sur l'horizon (approximation trapèze)."""
    if horizon <= 0:
        return montant_initial
    encours_final = montant_initial * (1 + croissance) ** horizon
    return (montant_initial + encours_final) / 2


def _cout_broker(
    broker: Any,
    enveloppe: str,
    montant_eur: float,
    etfs_retenus: list[str],
    horizon_annees: int,
    univers_etf: list | None = None,
) -> CoutTotalProvider | None:
    """Calcule le coût total 10 ans pour un broker."""
    try:
        encours_moy = _encours_moyen(montant_eur, horizon_annees)

        # TER effectif moyen des ETF retenus
        ter_effectif = _ter_moyen(etfs_retenus, univers_etf)

        # Frais de garde annuels
        frais_garde_annuel = getattr(broker, "frais_garde_annuel_eur", 0.0) or 0.0

        # Courtage estimé : 1 rebal/an × frais par ordre (min EUR ou pct × montant)
        courtage_eur = getattr(broker, "frais_courtage_actions_euronext_eur", None)
        courtage_pct = getattr(broker, "frais_courtage_actions_euronext_pct", None)
        if courtage_eur is not None:
            courtage_annuel = courtage_eur * _NB_REBAL_PAR_AN * max(1, len(etfs_retenus))
        elif courtage_pct is not None:
            courtage_annuel = courtage_pct * montant_eur * _NB_REBAL_PAR_AN
        else:
            courtage_annuel = 0.0

        # Frais d'inactivité
        frais_inact = getattr(broker, "frais_inactivite_annuel_eur", 0.0) or 0.0

        # Coût total
        cout_ter = ter_effectif * encours_moy * horizon_annees
        cout_garde = frais_garde_annuel * horizon_annees
        cout_courtage = courtage_annuel * horizon_annees
        cout_inact = frais_inact * horizon_annees
        cout_total = cout_ter + cout_garde + cout_courtage + cout_inact

        return CoutTotalProvider(
            provider_id=broker.id,
            provider_nom=broker.nom,
            type_provider="broker",
            enveloppe=enveloppe,
            cout_total_10y_eur=round(cout_total, 2),
            detail={
                "ter_effectif_pct": round(ter_effectif * 100, 4),
                "frais_enveloppe_pct": 0.0,
                "courtage_estime_eur": round(cout_courtage, 2),
                "frais_garde_eur": round(cout_garde, 2),
                "frais_arbitrage_eur": 0.0,
            },
        )
    except Exception as exc:
        logger.debug("Erreur calcul broker %s : %s", getattr(broker, "id", "?"), exc)
        return None


def _cout_contrat_av(
    contrat: Any,
    montant_eur: float,
    etfs_retenus: list[str],
    horizon_annees: int,
    univers_etf: list | None = None,
) -> CoutTotalProvider | None:
    """Calcule le coût total 10 ans pour un contrat AV."""
    try:
        encours_moy = _encours_moyen(montant_eur, horizon_annees)

        ter_effectif = _ter_moyen(etfs_retenus, univers_etf)
        frais_gestion_uc = getattr(contrat, "frais_gestion_uc_pct", 0.0) or 0.0
        frais_entree = getattr(contrat, "frais_entree_pct", 0.0) or 0.0
        frais_arb = getattr(contrat, "frais_arbitrage_pct", 0.0) or 0.0

        cout_ter = ter_effectif * encours_moy * horizon_annees
        cout_gestion = frais_gestion_uc * encours_moy * horizon_annees
        cout_entree = frais_entree * montant_eur  # 1 fois
        cout_arb = frais_arb * encours_moy * _NB_REBAL_PAR_AN * horizon_annees
        cout_total = cout_ter + cout_gestion + cout_entree + cout_arb

        return CoutTotalProvider(
            provider_id=contrat.id,
            provider_nom=contrat.nom,
            type_provider="assureur_av",
            enveloppe="AV",
            cout_total_10y_eur=round(cout_total, 2),
            detail={
                "ter_effectif_pct": round(ter_effectif * 100, 4),
                "frais_enveloppe_pct": round(frais_gestion_uc * 100, 4),
                "courtage_estime_eur": 0.0,
                "frais_garde_eur": 0.0,
                "frais_arbitrage_eur": round(cout_arb, 2),
            },
        )
    except Exception as exc:
        logger.debug("Erreur calcul contrat AV %s : %s", getattr(contrat, "id", "?"), exc)
        return None


def _cout_teneur_per(
    teneur: Any,
    montant_eur: float,
    etfs_retenus: list[str],
    horizon_annees: int,
    univers_etf: list | None = None,
) -> CoutTotalProvider | None:
    """Calcule le coût total 10 ans pour un teneur PER."""
    try:
        encours_moy = _encours_moyen(montant_eur, horizon_annees)

        ter_effectif = _ter_moyen(etfs_retenus, univers_etf)
        frais_gestion = getattr(teneur, "frais_gestion_uc_pct", 0.0) or 0.0
        frais_entree = getattr(teneur, "frais_entree_pct", 0.0) or 0.0
        frais_arb = getattr(teneur, "frais_arbitrage_pct", 0.0) or 0.0
        frais_versement = getattr(teneur, "frais_versement_pct", 0.0) or 0.0

        cout_ter = ter_effectif * encours_moy * horizon_annees
        cout_gestion = frais_gestion * encours_moy * horizon_annees
        cout_entree = frais_entree * montant_eur
        cout_arb = frais_arb * encours_moy * _NB_REBAL_PAR_AN * horizon_annees
        cout_versement = frais_versement * montant_eur
        cout_total = cout_ter + cout_gestion + cout_entree + cout_arb + cout_versement

        return CoutTotalProvider(
            provider_id=teneur.id,
            provider_nom=teneur.nom,
            type_provider="teneur_per",
            enveloppe="PER",
            cout_total_10y_eur=round(cout_total, 2),
            detail={
                "ter_effectif_pct": round(ter_effectif * 100, 4),
                "frais_enveloppe_pct": round(frais_gestion * 100, 4),
                "courtage_estime_eur": 0.0,
                "frais_garde_eur": 0.0,
                "frais_arbitrage_eur": round(cout_arb, 2),
            },
        )
    except Exception as exc:
        logger.debug("Erreur calcul teneur PER %s : %s", getattr(teneur, "id", "?"), exc)
        return None


# TER par défaut (30 bps) utilisé quand aucune donnée ETF n'est disponible
_TER_DEFAUT = 0.003


def _ter_moyen(etfs_retenus: list[str], univers_etf: list | None) -> float:
    """Calcule le TER moyen pondéré des ETF retenus."""
    if not etfs_retenus or not univers_etf:
        return _TER_DEFAUT

    ters = []
    for isin in etfs_retenus:
        for etf in univers_etf:
            etf_isin = getattr(etf, "isin", None) or ""
            if etf_isin.upper() == isin.upper():
                ter = getattr(etf, "ter", None)
                if ter is not None:
                    ters.append(ter)
                break

    return sum(ters) / len(ters) if ters else _TER_DEFAUT


def _filtre_enveloppe_broker(broker: Any, enveloppe: str) -> bool:
    """Retourne True si le broker supporte l'enveloppe."""
    enveloppe_map = {
        "PEA": "pea_disponible",
        "PEA-PME": "pea_pme_disponible",
        "CTO": "cto_disponible",
        "CTO_perso": "cto_disponible",
        "CTO_IS": "cto_disponible",
        "AV": "av_disponible",
        "AV_UC": "av_disponible",
        "PER": "per_disponible",
    }
    field_name = enveloppe_map.get(enveloppe.upper(), enveloppe_map.get(enveloppe))
    if field_name is None:
        return True  # enveloppe inconnue → ne pas filtrer
    return bool(getattr(broker, field_name, False))


def _filtre_etf_broker(broker: Any, etfs_retenus: list[str]) -> bool:
    """Retourne True si le broker propose tous les ETF retenus (ou si liste non renseignée)."""
    etfs_dispo = getattr(broker, "etfs_disponibles", None)
    if etfs_dispo is None:
        return True  # catalogue large supposé exhaustif
    return all(isin in etfs_dispo for isin in etfs_retenus)


def classer_providers(
    profil: Any,
    allocation_cible: dict[str, float],
    etfs_retenus: list[str],
    horizon_annees: int = 10,
    brokers: list | None = None,
    contrats_av: list | None = None,
    teneurs_per: list | None = None,
    univers_etf: list | None = None,
) -> dict[str, list[CoutTotalProvider]]:
    """Pour chaque enveloppe utilisée, classe les providers du moins cher au plus cher.

    Retourne un dict {enveloppe: [CoutTotalProvider...]}, trié par cout_total_10y_eur asc.
    """
    if brokers is None:
        brokers = []
    if contrats_av is None:
        contrats_av = []
    if teneurs_per is None:
        teneurs_per = []

    # Détecter les enveloppes utilisées dans le profil
    enveloppes_utilisees: set[str] = set()
    composition = list(getattr(profil, "composition_actuelle", None) or [])
    for ligne in composition:
        env = getattr(ligne, "enveloppe", None)
        if env:
            enveloppes_utilisees.add(env)

    # Si allocation_cible explicite des enveloppes
    for env in allocation_cible:
        if allocation_cible[env] > 0:
            enveloppes_utilisees.add(env)

    if not enveloppes_utilisees:
        # Fallback: toutes les enveloppes standard
        enveloppes_utilisees = {"PEA", "CTO", "AV", "PER"}

    patrimoine = float(getattr(profil, "patrimoine_financier_total", 100_000) or 100_000)

    result: dict[str, list[CoutTotalProvider]] = {}

    for enveloppe in enveloppes_utilisees:
        env_upper = enveloppe.upper()
        poids = allocation_cible.get(enveloppe, allocation_cible.get(env_upper, 0.25))
        montant_env = patrimoine * poids
        if montant_env <= 0:
            montant_env = patrimoine * 0.25

        candidats: list[CoutTotalProvider] = []

        # Brokers (PEA, CTO, PEA-PME, PER éventuellement)
        if env_upper in ("PEA", "PEA-PME", "CTO", "CTO_PERSO", "CTO_IS"):
            for broker in brokers:
                if not _filtre_enveloppe_broker(broker, enveloppe):
                    continue
                if not _filtre_etf_broker(broker, etfs_retenus):
                    continue
                cout = _cout_broker(
                    broker, enveloppe, montant_env, etfs_retenus, horizon_annees, univers_etf
                )
                if cout is not None:
                    candidats.append(cout)

        # Contrats AV
        if env_upper in ("AV", "AV_UC"):
            for contrat in contrats_av:
                cout = _cout_contrat_av(
                    contrat, montant_env, etfs_retenus, horizon_annees, univers_etf
                )
                if cout is not None:
                    candidats.append(cout)

        # Teneurs PER
        if env_upper == "PER":
            for teneur in teneurs_per:
                cout = _cout_teneur_per(
                    teneur, montant_env, etfs_retenus, horizon_annees, univers_etf
                )
                if cout is not None:
                    candidats.append(cout)

        # Trier par coût croissant
        candidats.sort(key=lambda x: x.cout_total_10y_eur)

        # Normaliser les scores (0-100, meilleur = 100)
        if candidats:
            cout_min = candidats[0].cout_total_10y_eur
            cout_max = candidats[-1].cout_total_10y_eur
            for c in candidats:
                if cout_max > cout_min:
                    c.score = round(
                        100 * (1 - (c.cout_total_10y_eur - cout_min) / (cout_max - cout_min)), 1
                    )
                else:
                    c.score = 100.0

        result[enveloppe] = candidats

    return result
