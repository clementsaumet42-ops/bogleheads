"""Moteur 2 — Withholding Tax / Retenue à la source (S8.2b).

Pour chaque ETF actions du portefeuille client, calcule la retenue à la source
effective et identifie si un changement de domicile ETF (IE vs LU vs FR)
réduit le drag fiscal.

Hypothèses documentées :
- Profils géographiques par indice dans _constantes.PONDERATION_GEO_PAR_INDICE
- Rendements dividendes par catégorie dans _constantes.RENDEMENT_DIVIDENDE_PAR_CATEGORIE
- Taux de retenue source depuis RetenuesSourceConfig (config/retenues_source.yaml)
- ACWI : 60% US / 28% Dev hors US / 12% EM (source: factsheets iShares jan 2025)
"""

from __future__ import annotations

import logging
import warnings

from src.audit.moteurs._constantes import (
    DOMICILES_ACCEPTABLES,
    PONDERATION_GEO_PAR_INDICE,
    REGION_VERS_PAYS_REPRESENTATIF,
    RENDEMENT_DIVIDENDE_PAR_CATEGORIE,
    SOUS_CLASSE_VERS_INDICE,
    TAUX_ACTUALISATION_DEFAUT,
    WITHHOLDING_SEUIL_BPS,
)
from src.audit.opportunite import LigneEtf, Opportunite, capitaliser_30_ans
from src.schemas import ETFEnrichi, RetenuesSourceConfig

logger = logging.getLogger(__name__)

_SOURCES = [
    "JP Morgan Withholding Tax Handbook 2024",
    "config/retenues_source.yaml — matrice S8.2a",
    "config/univers_etf.yaml — données S8.2a",
    "OCDE — Modèle de convention fiscale et base des traités bilatéraux",
]


def _drag_withholding(
    sous_classe: str | None,
    domicile_iso: str,
    matrice: dict[str, dict[str, float]],
    rendement_dividende: float,
    montant_eur: float,
) -> float:
    """Calcule le drag annuel en € dû aux retenues à la source.

    Formule :
        drag = montant × rendement_dividende × Σ(poids_région × taux_retenue[pays_rep][domicile])

    Args:
        sous_classe: sous_classe de l'ETF (ex: "Monde développé")
        domicile_iso: domicile ISO-2 de l'ETF (ex: "IE", "LU", "FR")
        matrice: matrice des retenues source (depuis RetenuesSourceConfig)
        rendement_dividende: rendement en dividendes estimé (décimal)
        montant_eur: montant investi €

    Returns:
        Drag annuel en € (toujours positif — c'est un coût).
    """
    indice = SOUS_CLASSE_VERS_INDICE.get(sous_classe or "", None)
    ponderations = PONDERATION_GEO_PAR_INDICE.get(indice or "", None)

    if ponderations is None:
        # Fallback: utiliser MSCI_WORLD comme défaut documenté
        logger.debug(
            "sous_classe '%s' non reconnue — fallback MSCI_WORLD pour withholding", sous_classe
        )
        ponderations = PONDERATION_GEO_PAR_INDICE["MSCI_WORLD"]

    taux_moyen = 0.0
    for region, poids in ponderations.items():
        pays_rep = REGION_VERS_PAYS_REPRESENTATIF.get(region)
        if pays_rep is None:
            logger.debug("Région '%s' sans pays représentatif — ignorée", region)
            continue
        taux = matrice.get(pays_rep, {}).get(domicile_iso, None)
        if taux is None:
            logger.debug(
                "matrice[%s][%s] absent — région %s ignorée dans calcul withholding",
                pays_rep,
                domicile_iso,
                region,
            )
            continue
        taux_moyen += poids * taux

    dividende_annuel = montant_eur * rendement_dividende
    return dividende_annuel * taux_moyen


def _rendement_dividende_pour(sous_classe: str | None) -> float:
    """Retourne le rendement dividende estimé pour une sous_classe."""
    indice = SOUS_CLASSE_VERS_INDICE.get(sous_classe or "", "_DEFAUT")
    return RENDEMENT_DIVIDENDE_PAR_CATEGORIE.get(
        indice, RENDEMENT_DIVIDENDE_PAR_CATEGORIE["_DEFAUT"]
    )


def detecter_opportunites_withholding(
    portefeuille_actuel: list[LigneEtf],
    univers: list[ETFEnrichi],
    matrice_retenues: RetenuesSourceConfig,
) -> list[Opportunite]:
    """Détecte les opportunités de réduction du drag fiscal sur dividendes.

    Pour chaque ETF actions :
    1. Estime le revenu dividendes annuel via RENDEMENT_DIVIDENDE_PAR_CATEGORIE.
    2. Calcule drag_actuel = Σ(poids_geo × taux_retenue[pays][domicile]) × dividende.
    3. Pour chaque alternative (même indice, domicile différent) : calcule drag_alternative.
    4. Si drag_actuel - drag_alternative > 3 bps × montant, crée Opportunite.

    Args:
        portefeuille_actuel: lignes ETF du client.
        univers: liste des ETFEnrichi depuis univers_etf.yaml.
        matrice_retenues: matrice des retenues source S8.2a.

    Returns:
        Liste d'Opportunite triée par gain_30ans_eur décroissant.
    """
    index_isin: dict[str, ETFEnrichi] = {etf.isin: etf for etf in univers}
    matrice = matrice_retenues.matrice
    opportunites: list[Opportunite] = []

    for ligne in portefeuille_actuel:
        etf_actuel = index_isin.get(ligne.isin)
        if etf_actuel is None:
            warnings.warn(
                f"ISIN {ligne.isin} absent de l'univers ETF — ligne ignorée",
                stacklevel=2,
            )
            continue

        # Filtre : ETF actions uniquement
        if etf_actuel.classe_actifs.lower() not in ("actions", "etf actions"):
            logger.debug(
                "ETF %s : classe_actifs '%s' → skip withholding",
                etf_actuel.ticker,
                etf_actuel.classe_actifs,
            )
            continue

        domicile_actuel = etf_actuel.domicile_iso or (
            etf_actuel.domicile[:2].upper() if etf_actuel.domicile else "IE"
        )
        rendement_div = _rendement_dividende_pour(etf_actuel.sous_classe)
        drag_actuel = _drag_withholding(
            etf_actuel.sous_classe,
            domicile_actuel,
            matrice,
            rendement_div,
            ligne.montant_eur,
        )
        drag_actuel_bps = drag_actuel / ligne.montant_eur * 10_000

        indice_actuel = SOUS_CLASSE_VERS_INDICE.get(etf_actuel.sous_classe or "")

        best_alt = None
        best_gain = 0.0

        for alt in univers:
            if alt.isin == etf_actuel.isin:
                continue
            if alt.classe_actifs.lower() not in ("actions", "etf actions"):
                continue
            indice_alt = SOUS_CLASSE_VERS_INDICE.get(alt.sous_classe or "")
            if indice_alt != indice_actuel or indice_actuel is None:
                continue

            domicile_alt = alt.domicile_iso or (alt.domicile[:2].upper() if alt.domicile else None)
            if domicile_alt is None or domicile_alt not in DOMICILES_ACCEPTABLES:
                continue
            if domicile_alt == domicile_actuel:
                continue  # même domicile — pas d'opportunité withholding

            drag_alt = _drag_withholding(
                alt.sous_classe,
                domicile_alt,
                matrice,
                rendement_div,
                ligne.montant_eur,
            )
            gain = drag_actuel - drag_alt
            if gain > best_gain:
                best_gain = gain
                best_alt = alt

        if best_alt is None:
            continue

        gain_bps = best_gain / ligne.montant_eur * 10_000
        if gain_bps < WITHHOLDING_SEUIL_BPS:
            continue

        domicile_alt_final = best_alt.domicile_iso or best_alt.domicile[:2].upper()
        drag_alt_bps = (drag_actuel - best_gain) / ligne.montant_eur * 10_000
        gain_30ans = capitaliser_30_ans(best_gain, TAUX_ACTUALISATION_DEFAUT)

        contraintes = [
            f"Domicile actuel {domicile_actuel} → proposé {domicile_alt_final}",
            "Vérifier éligibilité enveloppe pour l'ETF alternatif",
        ]
        if ligne.enveloppe == "AV":
            contraintes.append(
                "Switch fiscalement neutre en AV — vérifier disponibilité dans contrat"
            )

        note_ec = (
            f"Rendement dividende estimé {rendement_div * 100:.1f}% "
            f"(hypothèse par catégorie d'indice — à affiner avec données réelles). "
            f"Pondération géo par défaut PONDERATION_GEO_PAR_INDICE."
        )

        opp = Opportunite(
            id=f"etf.withholding.{etf_actuel.ticker}_domicile_{domicile_actuel}_vs_{domicile_alt_final}",
            levier="withholding_tax",
            titre=f"{etf_actuel.ticker} : changer domicile {domicile_actuel}→{domicile_alt_final} pour réduire drag fiscal dividendes",
            gain_annuel_bps=round(gain_bps, 2),
            gain_annuel_eur=round(best_gain, 2),
            gain_30ans_eur=round(gain_30ans, 0),
            montant_concerne_eur=ligne.montant_eur,
            avant={
                "ticker": etf_actuel.ticker,
                "isin": etf_actuel.isin,
                "domicile_iso": domicile_actuel,
                "drag_annuel_eur": round(drag_actuel, 2),
                "drag_bps": round(drag_actuel_bps, 2),
                "rendement_dividende_estime": rendement_div,
            },
            apres={
                "ticker": best_alt.ticker,
                "isin": best_alt.isin,
                "domicile_iso": domicile_alt_final,
                "drag_annuel_eur": round(drag_actuel - best_gain, 2),
                "drag_bps": round(drag_alt_bps, 2),
            },
            formule=(
                f"drag = montant × rendement_div × Σ(poids_geo × taux_traité) ; "
                f"drag_actuel({domicile_actuel}) = {drag_actuel:.0f}€/an ({drag_actuel_bps:.1f}bps) ; "
                f"drag_alt({domicile_alt_final}) = {drag_actuel - best_gain:.0f}€/an ({drag_alt_bps:.1f}bps) ; "
                f"économie = {best_gain:.0f}€/an"
            ),
            sources=_SOURCES,
            complexite="faible",
            delai_mise_en_oeuvre_jours=7,
            contraintes=contraintes,
            confiance="moyenne",  # toujours moyenne car estimations géographiques
            note_ec=note_ec,
        )
        opportunites.append(opp)

    opportunites.sort(key=lambda o: o.gain_30ans_eur, reverse=True)
    return opportunites
