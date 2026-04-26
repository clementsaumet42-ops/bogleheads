"""Validation soft de cohérence catalogue à la saisie profil — S13 Lot A.

Ce module ne lève jamais d'exception. Toutes les incohérences sont des warnings/errors
SOFT (jamais bloquants, la sauvegarde reste toujours possible).
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Any, Literal

# Pays de domicile éligibles PEA (UCITS domicile)
_DOMICILES_PEA_OK = {"FR", "IE", "LU", "DE", "ES", "IT", "NL", "BE", "AT", "PT", "FI"}

# Mapping enveloppe label → champ eligibilite ETF
_ENVELOPPE_TO_ELIGIBILITE = {
    "PEA": "PEA",
    "PEA-PME": "PEA",  # même critère UCITS
    "CTO": "CTO_perso",
    "CTO_perso": "CTO_perso",
    "CTO_IS": "CTO_IS",
    "AV": "AV_UC",
    "AV_UC": "AV_UC",
    "PER": "PER",
    "PEE": "PEE",
}

# Mapping enveloppe → champ broker disponible
_ENVELOPPE_TO_BROKER_FIELD = {
    "PEA": "pea_disponible",
    "PEA-PME": "pea_pme_disponible",
    "CTO": "cto_disponible",
    "CTO_perso": "cto_disponible",
    "CTO_IS": "cto_disponible",
    "AV": "av_disponible",
    "AV_UC": "av_disponible",
    "PER": "per_disponible",
}


@dataclass
class IncoherenceLigne:
    """Une incohérence détectée sur une ligne de portefeuille."""

    ligne_idx: int
    severite: Literal["info", "warning", "error"]
    code: str  # "ETF_INCONNU", "ETF_INCOMPATIBLE_ENVELOPPE", "PROVIDER_PAS_ENVELOPPE", "PROVIDER_PAS_ETF"
    message: str  # message client-friendly
    suggestion: str | None = None  # suggestion d'action


def _trouver_etf(identifiant: str | None, univers_etf: list) -> Any | None:
    """Cherche un ETF par ISIN ou ticker (case-insensitive)."""
    if not identifiant:
        return None
    identifiant_norm = identifiant.strip().upper()
    for etf in univers_etf:
        isin = getattr(etf, "isin", None) or ""
        ticker = getattr(etf, "ticker", None) or ""
        if isin.upper() == identifiant_norm or ticker.upper() == identifiant_norm:
            return etf
    return None


def _trouver_broker(identifiant: str | None, brokers: list) -> Any | None:
    """Cherche un broker par id ou nom (case-insensitive)."""
    if not identifiant:
        return None
    identifiant_norm = identifiant.strip().lower()
    for broker in brokers:
        broker_id = getattr(broker, "id", None) or ""
        broker_nom = getattr(broker, "nom", None) or ""
        if broker_id.lower() == identifiant_norm or broker_nom.lower() == identifiant_norm:
            return broker
    return None


def _trouver_contrat_av(identifiant: str | None, contrats_av: list) -> Any | None:
    """Cherche un contrat AV par id ou nom (case-insensitive)."""
    if not identifiant:
        return None
    identifiant_norm = identifiant.strip().lower()
    for contrat in contrats_av:
        c_id = getattr(contrat, "id", None) or ""
        c_nom = getattr(contrat, "nom", None) or ""
        if c_id.lower() == identifiant_norm or c_nom.lower() == identifiant_norm:
            return contrat
    return None


def _trouver_teneur_per(identifiant: str | None, teneurs_per: list) -> Any | None:
    """Cherche un teneur PER par id ou nom (case-insensitive)."""
    if not identifiant:
        return None
    identifiant_norm = identifiant.strip().lower()
    for teneur in teneurs_per:
        t_id = getattr(teneur, "id", None) or ""
        t_nom = getattr(teneur, "nom", None) or ""
        if t_id.lower() == identifiant_norm or t_nom.lower() == identifiant_norm:
            return teneur
    return None


def verifier_coherence(
    profil: Any,
    univers_etf: list,
    brokers: list,
    contrats_av: list,
    teneurs_per: list,
) -> list[IncoherenceLigne]:
    """Vérifie la cohérence des lignes du profil vs le catalogue.

    Ne lève jamais d'exception. Retourne une liste d'incohérences (peut être vide).
    Ne modifie jamais le profil passé en paramètre.
    """
    incoherences: list[IncoherenceLigne] = []

    try:
        composition = list(getattr(profil, "composition_actuelle", None) or [])
    except Exception:
        return []

    for idx, ligne in enumerate(composition):
        with contextlib.suppress(Exception):
            _verifier_ligne(
                idx, ligne, univers_etf, brokers, contrats_av, teneurs_per, incoherences
            )

    return incoherences


def _verifier_ligne(
    idx: int,
    ligne: Any,
    univers_etf: list,
    brokers: list,
    contrats_av: list,
    teneurs_per: list,
    incoherences: list[IncoherenceLigne],
) -> None:
    """Vérifie les 4 checks pour une ligne. Ne lève jamais."""
    enveloppe = getattr(ligne, "enveloppe", None) or ""
    etf_isin = getattr(ligne, "etf_isin", None)
    etf_ticker = getattr(ligne, "etf_ticker", None)

    # Identifiant ETF (ISIN prioritaire, sinon ticker)
    etf_identifiant = etf_isin or etf_ticker

    # Check 1 — ETF connu dans le catalogue ?
    etf_obj = None
    if etf_identifiant:
        etf_obj = _trouver_etf(etf_identifiant, univers_etf)
        if etf_obj is None:
            ticker_display = etf_ticker or etf_isin
            incoherences.append(
                IncoherenceLigne(
                    ligne_idx=idx,
                    severite="warning",
                    code="ETF_INCONNU",
                    message=f"'{ticker_display}' non trouvé dans le catalogue ETF. Vérifiez l'ISIN/ticker ou ajoutez-le.",
                    suggestion="Ajoutez cet ETF via la page 'Catalogue ETF' (page 16).",
                )
            )

    # Check 2 — ETF compatible avec l'enveloppe ?
    if etf_obj is not None and enveloppe:
        eligibilite_field = _ENVELOPPE_TO_ELIGIBILITE.get(
            enveloppe.upper(), _ENVELOPPE_TO_ELIGIBILITE.get(enveloppe)
        )
        if eligibilite_field is not None:
            elig = getattr(etf_obj, "eligibilite", None)
            if elig is not None:
                elig_val = getattr(elig, eligibilite_field, False)
                if not elig_val:
                    ticker_display = getattr(etf_obj, "ticker", etf_identifiant)
                    domicile = getattr(etf_obj, "domicile_iso", None) or getattr(
                        etf_obj, "domicile", ""
                    )

                    # Suggestion d'ETF compatible
                    suggestion = None
                    if enveloppe.upper() in ("PEA", "PEA-PME"):
                        for e in univers_etf:
                            e_elig = getattr(e, "eligibilite", None)
                            if e_elig and getattr(e_elig, "PEA", False):
                                e_ticker = getattr(e, "ticker", "")
                                e_nom = getattr(e, "nom", "")
                                if e_ticker != ticker_display:
                                    suggestion = (
                                        f"Suggestion : {e_ticker} ({e_nom}) est éligible PEA."
                                    )
                                    break

                    incoherences.append(
                        IncoherenceLigne(
                            ligne_idx=idx,
                            severite="error",
                            code="ETF_INCOMPATIBLE_ENVELOPPE",
                            message=f"🔴 {ticker_display} (domicile : {domicile}) n'est pas éligible {enveloppe}.",
                            suggestion=suggestion,
                        )
                    )

    # Check 3 — Provider supporte cette enveloppe ?
    provider_id = (
        getattr(ligne, "broker", None)
        or getattr(ligne, "assureur", None)
        or getattr(ligne, "teneur", None)
        or getattr(ligne, "provider", None)
    )

    if provider_id and enveloppe:
        enveloppe_up = enveloppe.upper()
        broker_field = _ENVELOPPE_TO_BROKER_FIELD.get(
            enveloppe_up, _ENVELOPPE_TO_BROKER_FIELD.get(enveloppe)
        )

        provider_found = False
        provider_supports = True
        provider_nom = provider_id

        # Chercher dans brokers
        broker_obj = _trouver_broker(provider_id, brokers)
        if broker_obj is not None:
            provider_found = True
            provider_nom = getattr(broker_obj, "nom", provider_id)
            if broker_field:
                provider_supports = getattr(broker_obj, broker_field, True)

        # Si AV : chercher dans contrats_av
        if not provider_found and enveloppe_up in ("AV", "AV_UC"):
            contrat_obj = _trouver_contrat_av(provider_id, contrats_av)
            if contrat_obj is not None:
                provider_found = True
                provider_supports = True  # Si on trouve le contrat AV, il supporte AV

        # Si PER : chercher dans teneurs_per
        if not provider_found and enveloppe_up == "PER":
            teneur_obj = _trouver_teneur_per(provider_id, teneurs_per)
            if teneur_obj is not None:
                provider_found = True
                provider_supports = True  # Si on trouve le teneur PER, il supporte PER

        if provider_found and not provider_supports:
            incoherences.append(
                IncoherenceLigne(
                    ligne_idx=idx,
                    severite="warning",
                    code="PROVIDER_PAS_ENVELOPPE",
                    message=f"🟡 {provider_nom} ne propose pas l'enveloppe {enveloppe} en France.",
                    suggestion=f"Choisissez un autre provider proposant {enveloppe}.",
                )
            )

    # Check 4 — Provider propose cet ETF ?
    if etf_obj is not None and provider_id and enveloppe:
        etf_isin_val = getattr(etf_obj, "isin", None)

        # Broker avec liste etfs_disponibles renseignée ?
        broker_obj = _trouver_broker(provider_id, brokers)
        if broker_obj is not None:
            etfs_dispo = getattr(broker_obj, "etfs_disponibles", None)
            if etfs_dispo is not None and etf_isin_val and etf_isin_val not in etfs_dispo:
                broker_nom = getattr(broker_obj, "nom", provider_id)
                incoherences.append(
                    IncoherenceLigne(
                        ligne_idx=idx,
                        severite="warning",
                        code="PROVIDER_PAS_ETF",
                        message=f"🟡 {getattr(etf_obj, 'ticker', etf_isin_val)} non listé chez {broker_nom}.",
                        suggestion="Vérifiez la disponibilité de cet ETF chez ce broker ou choisissez un autre provider.",
                    )
                )

        # AV : vérifier contrats_av_reference
        enveloppe_up = enveloppe.upper()
        if enveloppe_up in ("AV", "AV_UC"):
            contrat_obj = _trouver_contrat_av(provider_id, contrats_av)
            if contrat_obj is not None:
                contrats_ref = getattr(etf_obj, "contrats_av_reference", []) or []
                contrat_nom = getattr(contrat_obj, "nom", provider_id)
                contrats_ref_norm = [c.strip().lower() for c in contrats_ref]
                if contrats_ref and contrat_nom.lower() not in contrats_ref_norm:
                    incoherences.append(
                        IncoherenceLigne(
                            ligne_idx=idx,
                            severite="warning",
                            code="PROVIDER_PAS_ETF",
                            message=f"🟡 {getattr(etf_obj, 'ticker', etf_isin_val)} n'est pas référencé dans {contrat_nom}.",
                            suggestion="Vérifiez la liste des UC disponibles dans votre contrat AV.",
                        )
                    )

        # Teneur PER : vérifier etfs_disponibles
        if enveloppe_up == "PER":
            teneur_obj = _trouver_teneur_per(provider_id, teneurs_per)
            if teneur_obj is not None:
                etfs_per = getattr(teneur_obj, "etfs_disponibles", None)
                if etfs_per is not None and etf_isin_val and etf_isin_val not in etfs_per:
                    teneur_nom = getattr(teneur_obj, "nom", provider_id)
                    incoherences.append(
                        IncoherenceLigne(
                            ligne_idx=idx,
                            severite="warning",
                            code="PROVIDER_PAS_ETF",
                            message=f"🟡 {getattr(etf_obj, 'ticker', etf_isin_val)} non listé dans le PER {teneur_nom}.",
                            suggestion="Consultez l'univers ETF de ce PER ou choisissez un autre teneur.",
                        )
                    )
