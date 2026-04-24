"""Moteur 1 — Tracking Difference (S8.2b).

Pour chaque ETF du portefeuille client, identifie s'il existe un concurrent
couvrant le même indice avec une tracking_difference_3y plus favorable.

Règles métier :
- « Même indice » défini par GROUPES_INDICES_EQUIVALENTS dans _constantes.py
  (MSCI World ≠ MSCI ACWI — pas de confusion entre univers différents)
- AUM minimum : 500 M€ (liquidité)
- Seuil de recommandation : delta TD > 5 bps/an
- Confiance dégradée si TD basée sur < 3 ans ou estimée
"""

from __future__ import annotations

import logging
import warnings

from src.audit.moteurs._constantes import (
    AUM_MINIMUM_M_EUR,
    DOMICILES_ACCEPTABLES,
    GROUPES_INDICES_EQUIVALENTS,
    SOUS_CLASSE_VERS_INDICE,
    TAUX_ACTUALISATION_DEFAUT,
    TD_SEUIL_BPSPAR_AN,
)
from src.audit.opportunite import LigneEtf, Opportunite, capitaliser_30_ans
from src.schemas import ETFEnrichi

logger = logging.getLogger(__name__)

# ─── Sources de référence ────────────────────────────────────────────────────
_SOURCES = [
    "justETF.com — tracking difference tracker 2024",
    "trackingdifferences.com — base de données TD ETF",
    "config/univers_etf.yaml — données S8.2a",
]


def _indice_pour_sous_classe(sous_classe: str | None) -> str | None:
    """Retourne l'identifiant d'indice normalisé depuis la sous_classe YAML."""
    if not sous_classe:
        return None
    return SOUS_CLASSE_VERS_INDICE.get(sous_classe)


def _meme_groupe_indice(indice_a: str, indice_b: str) -> tuple[bool, bool]:
    """Retourne (sont_comparables, sont_equivalents_notes).

    sont_comparables: True si même groupe d'indices.
    sont_equivalents_notes: True si comparaison avec note de mise en garde
    (ex: MSCI_ACWI vs FTSE_ALL_WORLD).
    """
    if indice_a == indice_b:
        return True, False
    for groupe in GROUPES_INDICES_EQUIVALENTS:
        if indice_a in groupe and indice_b in groupe:
            return True, len(groupe) > 1  # note si groupé avec différents indices
    return False, False


def _confiance_td(etf: ETFEnrichi) -> str:
    """Détermine le niveau de confiance selon la qualité des données TD."""
    if etf.tracking_difference_3y is not None:
        return "haute"
    if etf.tracking_difference_1y is not None:
        return "moyenne"
    return "basse"


def _td_principal(etf: ETFEnrichi) -> float | None:
    """Retourne la TD la plus fiable disponible (3y > 1y > None)."""
    if etf.tracking_difference_3y is not None:
        return etf.tracking_difference_3y
    if etf.tracking_difference_1y is not None:
        return etf.tracking_difference_1y
    return None


def _eligibilite_ok(etf: ETFEnrichi, enveloppe: str) -> bool:
    """Vérifie que l'ETF est éligible dans l'enveloppe du client."""
    elig = etf.eligibilite
    mapping = {
        "PEA": elig.PEA,
        "PER": elig.PER,
        "CTO": elig.CTO_perso,
        "AV": elig.AV_UC,
        "PEE": elig.PEE,
        "CTO_IS": elig.CTO_IS,
        "Contrat_Cap_IS": elig.Contrat_Cap_IS,
    }
    return mapping.get(enveloppe, True)


def detecter_opportunites_td(
    portefeuille_actuel: list[LigneEtf],
    univers: list[ETFEnrichi],
) -> list[Opportunite]:
    """Détecte les opportunités d'amélioration de tracking difference.

    Pour chaque ligne du portefeuille :
    1. Trouve les ETF de l'univers couvrant le même indice.
    2. Filtre : AUM ≥ 500 M€, domicile IE/LU/FR acceptable, éligibilité enveloppe OK.
    3. Calcule delta_td = TD_actuelle - TD_alternative (positif = alternative meilleure).
    4. Si delta_td > 5 bps/an et faisable, crée une Opportunite.

    Args:
        portefeuille_actuel: lignes ETF du client avec ISIN, montant € et enveloppe.
        univers: liste des ETFEnrichi depuis univers_etf.yaml.

    Returns:
        Liste d'Opportunite triée par gain_30ans_eur décroissant.
    """
    # Index ISIN → ETFEnrichi pour lookup rapide
    index_isin: dict[str, ETFEnrichi] = {etf.isin: etf for etf in univers}

    opportunites: list[Opportunite] = []

    for ligne in portefeuille_actuel:
        etf_actuel = index_isin.get(ligne.isin)
        if etf_actuel is None:
            warnings.warn(
                f"ISIN {ligne.isin} absent de l'univers ETF — ligne ignorée",
                stacklevel=2,
            )
            logger.warning("ISIN %s absent de l'univers — ligne ignorée", ligne.isin)
            continue

        td_actuelle = _td_principal(etf_actuel)
        if td_actuelle is None:
            warnings.warn(
                f"ETF {etf_actuel.ticker} : tracking_difference null → ligne ignorée",
                stacklevel=2,
            )
            logger.warning(
                "ETF %s : TD null — impossible de quantifier, ligne ignorée",
                etf_actuel.ticker,
            )
            continue

        indice_actuel = _indice_pour_sous_classe(etf_actuel.sous_classe)
        if indice_actuel is None:
            logger.warning(
                "ETF %s : sous_classe '%s' non reconnue → skip",
                etf_actuel.ticker,
                etf_actuel.sous_classe,
            )
            continue

        # Cherche les alternatives
        for alt in univers:
            if alt.isin == etf_actuel.isin:
                continue  # même ETF

            indice_alt = _indice_pour_sous_classe(alt.sous_classe)
            if indice_alt is None:
                continue

            comparables, avec_note = _meme_groupe_indice(indice_actuel, indice_alt)
            if not comparables:
                continue

            # Filtre AUM : si données disponibles, vérifier liquidité ≥ 500 M€/j équivalent
            if (
                alt.volume_quotidien_m_eur is not None
                and alt.volume_quotidien_m_eur < AUM_MINIMUM_M_EUR
            ):
                logger.debug(
                    "ETF %s : volume_quotidien_m_eur=%.1f < %.0f M€ — filtre liquidité",
                    alt.ticker,
                    alt.volume_quotidien_m_eur,
                    AUM_MINIMUM_M_EUR,
                )
                continue
            if alt.volume_quotidien_m_eur is None:
                # Données de liquidité absentes — on ne filtre pas (conservative)
                logger.debug(
                    "ETF %s : volume_quotidien_m_eur null — filtre AUM non applicable, ETF conservé",
                    alt.ticker,
                )

            # Filtre domicile
            domicile_alt = alt.domicile_iso or (alt.domicile[:2].upper() if alt.domicile else None)
            if domicile_alt and domicile_alt not in DOMICILES_ACCEPTABLES:
                continue

            # Filtre éligibilité enveloppe
            if not _eligibilite_ok(alt, ligne.enveloppe):
                continue

            td_alt = _td_principal(alt)
            if td_alt is None:
                logger.debug(
                    "ETF alternatif %s : TD null → skip",
                    alt.ticker,
                )
                continue

            # delta_td positif = alternative meilleure (TD moins négative = moins de drag)
            # Convention: TD négative = ETF surperforme l'indice net (prêt de titres, etc.)
            # Plus TD est basse (plus négative), meilleur est l'ETF
            delta_td = td_actuelle - td_alt  # positif si actuel > alt (alt meilleur)
            delta_bps = delta_td * 10_000

            if delta_bps < TD_SEUIL_BPSPAR_AN:
                continue

            gain_annuel_eur = ligne.montant_eur * delta_td
            gain_30ans = capitaliser_30_ans(gain_annuel_eur, TAUX_ACTUALISATION_DEFAUT)

            confiance_actuel = _confiance_td(etf_actuel)
            confiance_alt = _confiance_td(alt)
            # La confiance globale est le minimum des deux
            niveaux = {"haute": 2, "moyenne": 1, "basse": 0}
            niv_global = min(niveaux[confiance_actuel], niveaux[confiance_alt])
            confiance_map = {2: "haute", 1: "moyenne", 0: "basse"}
            confiance = confiance_map[niv_global]

            if avec_note:
                confiance = "moyenne" if confiance == "haute" else confiance
                note_ec = (
                    f"Comparaison entre indices proches mais distincts "
                    f"({indice_actuel} vs {indice_alt}) — vérifier composition"
                )
            else:
                note_ec = None

            if confiance == "basse":
                note_ec = (
                    (note_ec or "")
                    + " TD estimée depuis TER (données insuffisantes) — à confirmer."
                ).strip()

            contraintes = []
            if ligne.enveloppe == "PEA" and not alt.eligibilite.PEA:
                contraintes.append("ETF alternatif non éligible PEA")
            if ligne.enveloppe == "AV":
                contraintes.append(
                    "Vérifier la disponibilité de l'ETF alternatif dans votre contrat AV"
                )
            contraintes.append("Switch fiscalement neutre en AV et PEA — vérifier si CTO")

            opp = Opportunite(
                id=f"etf.tracking_difference.{etf_actuel.ticker}_vs_{alt.ticker}",
                levier="tracking_difference",
                titre=f"Switcher {etf_actuel.ticker} → {alt.ticker} pour gain TD",
                gain_annuel_bps=round(delta_bps, 2),
                gain_annuel_eur=round(gain_annuel_eur, 2),
                gain_30ans_eur=round(gain_30ans, 0),
                montant_concerne_eur=ligne.montant_eur,
                avant={
                    "isin": etf_actuel.isin,
                    "ticker": etf_actuel.ticker,
                    "ter": etf_actuel.ter,
                    "tracking_difference_3y": etf_actuel.tracking_difference_3y,
                    "tracking_difference_1y": etf_actuel.tracking_difference_1y,
                },
                apres={
                    "isin": alt.isin,
                    "ticker": alt.ticker,
                    "ter": alt.ter,
                    "tracking_difference_3y": alt.tracking_difference_3y,
                    "tracking_difference_1y": alt.tracking_difference_1y,
                },
                formule=(
                    f"delta_TD = {etf_actuel.ticker}_TD({td_actuelle * 10000:.1f}bps) "
                    f"- {alt.ticker}_TD({td_alt * 10000:.1f}bps) = {delta_bps:.1f}bps/an ; "
                    f"gain = montant × delta_TD = {ligne.montant_eur:,.0f}€ × {delta_td:.4f} "
                    f"= {gain_annuel_eur:.0f}€/an"
                ),
                sources=_SOURCES,
                complexite="faible",
                delai_mise_en_oeuvre_jours=7,
                contraintes=contraintes,
                confiance=confiance,
                note_ec=note_ec or None,
            )
            opportunites.append(opp)

    # Trier par gain décroissant, dédupliquer (garder meilleure alternative par ligne)
    opportunites.sort(key=lambda o: o.gain_30ans_eur, reverse=True)

    # Déduplier : pour un ETF actuel donné, garder seulement la meilleure alternative
    vus: dict[str, Opportunite] = {}
    for opp in opportunites:
        # L'ID contient "ticker_actuel_vs_ticker_alt" — on regroupe par ticker_actuel
        partie_actuel = opp.id.split(".")[2].split("_vs_")[0]
        if partie_actuel not in vus:
            vus[partie_actuel] = opp

    return list(vus.values())
