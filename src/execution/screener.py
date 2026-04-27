"""Sprint S15 Lot A — Screener ETF assisté.

Pour chaque case d'allocation cible, propose le top N ETF avec scoring
multi-critères à partir du catalogue univers_etf.yaml.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ─── Pondérations par défaut ──────────────────────────────────────────────────

_POIDS_DEFAUT: dict[str, float] = {
    "ter": 0.30,
    "aum": 0.20,
    "tracking_diff": 0.15,
    "eligibilite": 0.20,
    "capi_dist": 0.10,
    "domicile_ue": 0.05,
}

# Seuil AUM minimum (M€) en dessous duquel l'ETF reçoit un malus fort
_AUM_SEUIL_MIN_M = 100.0
# Domiciles UE qui reçoivent le bonus domicile
_DOMICILES_UE = {"Irlande", "Luxembourg", "France", "Allemagne", "Belgique", "Pays-Bas"}
# Domiciles ISO considérés UE (champ domicile_iso)
_DOMICILES_UE_ISO = {"IE", "LU", "FR", "DE", "BE", "NL", "AT", "FI", "SE", "DK", "ES", "IT"}

# Correspondance enveloppe → champ eligibilite dans univers_etf.yaml
_ENVELOPPE_ELIGIBILITE: dict[str, str] = {
    "PEA": "PEA",
    "AV": "AV_UC",
    "PER": "PER",
    "CTO": "CTO_perso",
}


def _score_ter(ter: float | None) -> float:
    """Score TER : 1.0 pour TER=0, décroissant. Basé sur une échelle [0, 1%]."""
    if ter is None:
        return 0.5  # valeur neutre si données manquantes
    ter_clamp = max(0.0, min(ter, 0.01))  # plafonné à 1%
    return 1.0 - ter_clamp / 0.01


def _score_aum(aum_m_eur: float | None) -> float:
    """Score AUM : 0 si sous le seuil, croissant logarithmique au-delà."""
    if aum_m_eur is None:
        return 0.3  # valeur neutre si données manquantes
    if aum_m_eur < _AUM_SEUIL_MIN_M:
        return 0.0  # filtre dur : malus maximal sous 100M€
    # Bonus logarithmique : 1.0 pour 10 000M€, 0.5 pour 100M€
    import math

    return min(1.0, math.log10(aum_m_eur / _AUM_SEUIL_MIN_M) / math.log10(100))


def _score_tracking_diff(td: float | None) -> float:
    """Score tracking difference : plus négative (favorable) = meilleur score."""
    if td is None:
        return 0.5  # valeur neutre si données manquantes
    # TD est typiquement négatif (bon) ou légèrement positif (mauvais)
    # Référence : [-0.002, +0.002] → [1.0, 0.0]
    td_clamp = max(-0.002, min(td, 0.002))
    return 1.0 - (td_clamp + 0.002) / 0.004


def _score_eligibilite(
    etf: Any,
    enveloppe: str,
    contexte: dict,
) -> float:
    """
    Score éligibilité enveloppe.

    Filtre dur : retourne 0.0 si l'ETF n'est pas éligible à l'enveloppe.
    Pour AV : vérifie contrats_av_reference vs contrat fourni dans contexte.
    Pour PER : vérifie etfs_disponibles vs ISIN.
    """
    eligibilite = getattr(etf, "eligibilite", None)
    enveloppe_up = enveloppe.upper()

    # Champ eligibilite dans le catalogue
    champ = _ENVELOPPE_ELIGIBILITE.get(enveloppe_up)
    if champ and eligibilite is not None:
        eligible_flag = getattr(eligibilite, champ, False)
        if not eligible_flag:
            return 0.0  # filtre dur

    # PEA : exige domicile UE
    if enveloppe_up == "PEA":
        domicile = getattr(etf, "domicile", "") or ""
        domicile_iso = getattr(etf, "domicile_iso", "") or ""
        if domicile not in _DOMICILES_UE and domicile_iso not in _DOMICILES_UE_ISO:
            return 0.0  # filtre dur PEA

    # AV : vérifier référencement contrat
    if enveloppe_up == "AV":
        contrat_av_id = contexte.get("contrat_av")
        if contrat_av_id:
            contrats_ref = getattr(etf, "contrats_av_reference", []) or []
            if contrats_ref and contrat_av_id not in contrats_ref:
                return 0.0  # filtre dur AV : non référencé

    # PER : vérifier univers du teneur
    if enveloppe_up == "PER":
        teneur_per = contexte.get("teneur_per")
        if teneur_per is not None:
            etfs_dispo = getattr(teneur_per, "etfs_disponibles", None)
            isin = getattr(etf, "isin", None)
            if etfs_dispo is not None and isin and isin not in etfs_dispo:
                return 0.0  # filtre dur PER

    return 1.0


def _score_capi_dist(etf: Any, enveloppe: str) -> float:
    """
    Score capi vs dist selon la fiscalité de l'enveloppe.

    CTO : préférence capitalisant (pas de dividendes imposables chaque année).
    PEA / AV / PER : indifférent (enveloppe défiscalisée).
    """
    enveloppe_up = enveloppe.upper()
    capitalisant = getattr(etf, "capitalisant", None)

    if enveloppe_up == "CTO":
        if capitalisant is True:
            return 1.0
        if capitalisant is False:
            return 0.3
        return 0.5  # inconnu
    # PEA / AV / PER : indifférent
    return 0.7


def _score_domicile_ue(etf: Any) -> float:
    """Score domicile UE : bonus pour IE ou LU."""
    domicile = getattr(etf, "domicile", "") or ""
    domicile_iso = getattr(etf, "domicile_iso", "") or ""
    if domicile in _DOMICILES_UE or domicile_iso in _DOMICILES_UE_ISO:
        return 1.0
    return 0.0


def _extraire_aum(etf: Any) -> float | None:
    """Extrait l'AUM depuis les champs disponibles (volume_quotidien comme proxy)."""
    # Priorité : champ aum si présent (non défini dans les schémas actuels mais supporté)
    aum = getattr(etf, "aum_m_eur", None)
    if aum is not None:
        return float(aum)
    # Fallback : volume quotidien × 60 (approximation encours ~60j de volume)
    vol = getattr(etf, "volume_quotidien_m_eur", None)
    if vol is not None:
        return float(vol) * 60
    return None


def _etf_correspond_case(etf: Any, case_allocation: str) -> bool:
    """Vérifie si un ETF correspond à la case d'allocation demandée."""
    case = case_allocation.lower().strip()
    sous_classe = (getattr(etf, "sous_classe", "") or "").lower()
    classe_actifs = (getattr(etf, "classe_actifs", "") or "").lower()
    exposition_geo = (getattr(etf, "exposition_geo", "") or "").lower()

    # Table de correspondance case → mots-clés
    correspondances: dict[str, list[str]] = {
        "actions_monde_dev": ["monde développé", "monde_dev", "msci world", "msci world"],
        "actions_monde_dev_pea": ["monde développé", "monde_dev", "msci world"],
        "actions_monde": ["monde", "world", "all-world", "monde (tous pays)", "monde_acwi"],
        "actions_emergents": ["émergents", "emergents", "emerging"],
        "actions_usa": ["usa", "s&p 500", "sp500", "nasdaq", "us"],
        "actions_europe": ["europe", "euro stoxx", "stoxx europe"],
        "actions_france": ["france", "cac"],
        "obligations_monde": ["obligation", "bond", "aggregate", "gouvernement", "gouvern"],
        "obligations_eur": ["obligation", "bond", "eur", "europe"],
        "immobilier": ["immobilier", "reit", "real estate", "foncier"],
        "or": ["or", "gold", "precious metals"],
        "liquidites": ["monetaire", "monétaire", "money market", "cash"],
    }

    keywords = correspondances.get(case, [case.replace("_", " ")])
    text_to_check = f"{sous_classe} {classe_actifs} {exposition_geo}"
    return any(kw in text_to_check for kw in keywords)


def screener_etf(
    case_allocation: str,
    enveloppe: str,
    contexte: dict,
    catalogue: dict,
    top_n: int = 3,
    poids: dict[str, float] | None = None,
) -> list[dict]:
    """
    Propose les top_n ETF pour une case d'allocation et une enveloppe.

    Parameters
    ----------
    case_allocation : str
        Identifiant de la case d'allocation, ex "actions_monde_dev".
    enveloppe : str
        Enveloppe fiscale : "PEA" | "AV" | "PER" | "CTO".
    contexte : dict
        Informations contextuelles : broker, contrat_av (id), teneur_per (objet).
    catalogue : dict
        Contenu de univers_etf.yaml chargé ({"univers_etf": [...]}).
    top_n : int
        Nombre d'ETF à retourner (défaut 3).
    poids : dict | None
        Pondérations des critères (si None, utilise _POIDS_DEFAUT).

    Returns
    -------
    list[dict]
        Liste de top_n dicts triés par score décroissant, chacun contenant :
        isin, ticker, nom, ter, aum, domicile, eligible, score_global,
        score_detail, commentaire.
    """
    if poids is None:
        poids = _POIDS_DEFAUT

    # Normaliser les pondérations
    total_poids = sum(poids.values()) or 1.0
    poids_norm = {k: v / total_poids for k, v in poids.items()}

    # Charger les ETF depuis le catalogue
    etfs_raw = catalogue.get("univers_etf", [])
    if not etfs_raw:
        return []

    # Essayer de valider avec les schémas Pydantic
    etfs: list[Any] = []
    try:
        from src.schemas import UniversETFWrapper

        wrapper = UniversETFWrapper.model_validate(catalogue)
        etfs = list(wrapper.univers_etf)
    except Exception:
        # Fallback : utiliser les dicts bruts comme SimpleNamespace
        from types import SimpleNamespace

        for raw in etfs_raw:
            if isinstance(raw, dict):
                raw_copy = dict(raw)
                elig_raw = raw_copy.pop("eligibilite", {})
                elig_ns = SimpleNamespace(**elig_raw) if isinstance(elig_raw, dict) else elig_raw
                ns = SimpleNamespace(**raw_copy, eligibilite=elig_ns)
                etfs.append(ns)
            else:
                etfs.append(raw)

    scored: list[dict] = []

    for etf in etfs:
        # Filtre : case d'allocation
        if not _etf_correspond_case(etf, case_allocation):
            continue

        # Calcul des scores par critère
        s_ter = _score_ter(getattr(etf, "ter", None))
        aum = _extraire_aum(etf)
        s_aum = _score_aum(aum)
        td = getattr(etf, "tracking_difference_1y", None)
        s_td = _score_tracking_diff(td)
        s_elig = _score_eligibilite(etf, enveloppe, contexte)
        s_capi = _score_capi_dist(etf, enveloppe)
        s_dom = _score_domicile_ue(etf)

        # Si non éligible → exclure (filtre dur)
        if s_elig == 0.0:
            continue

        score_detail = {
            "ter": round(s_ter, 4),
            "aum": round(s_aum, 4),
            "tracking_diff": round(s_td, 4),
            "eligibilite": round(s_elig, 4),
            "capi_dist": round(s_capi, 4),
            "domicile_ue": round(s_dom, 4),
        }

        score_global = (
            poids_norm.get("ter", 0) * s_ter
            + poids_norm.get("aum", 0) * s_aum
            + poids_norm.get("tracking_diff", 0) * s_td
            + poids_norm.get("eligibilite", 0) * s_elig
            + poids_norm.get("capi_dist", 0) * s_capi
            + poids_norm.get("domicile_ue", 0) * s_dom
        )

        # Construction du commentaire automatique
        commentaire_parts = []
        ter_val = getattr(etf, "ter", None)
        if ter_val is not None:
            commentaire_parts.append(f"TER {ter_val:.2%}")
        if aum is not None:
            commentaire_parts.append(f"AUM ~{aum:.0f}M€")
        dom = getattr(etf, "domicile", "")
        if dom:
            commentaire_parts.append(f"Domicile {dom}")
        capi = getattr(etf, "capitalisant", None)
        if capi is not None:
            commentaire_parts.append("Capitalisant" if capi else "Distribuant")

        scored.append(
            {
                "isin": getattr(etf, "isin", None),
                "ticker": getattr(etf, "ticker", ""),
                "nom": getattr(etf, "nom", ""),
                "ter": getattr(etf, "ter", None),
                "aum": aum,
                "domicile": getattr(etf, "domicile", ""),
                "eligible": True,
                "score_global": round(score_global, 4),
                "score_detail": score_detail,
                "commentaire": " · ".join(commentaire_parts),
            }
        )

    # Tri par score décroissant
    scored.sort(key=lambda x: x["score_global"], reverse=True)

    return scored[:top_n]
