"""Tests S8.2a — Couche données sourcée : ETF enrichi, contrats AV, brokers, retenues source."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.schemas import AssuranceVieConfig, BrokersConfig, RetenuesSourceConfig, charger_et_valider

# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def etfs():
    yaml_path = Path(__file__).parent.parent / "config" / "univers_etf.yaml"
    with open(yaml_path, encoding="utf-8") as f:
        return yaml.safe_load(f)["univers_etf"]


@pytest.fixture(scope="module")
def contrats_av_raw():
    yaml_path = Path(__file__).parent.parent / "config" / "contrats_av.yaml"
    with open(yaml_path, encoding="utf-8") as f:
        return yaml.safe_load(f)["contrats_av"]


@pytest.fixture(scope="module")
def brokers_raw():
    yaml_path = Path(__file__).parent.parent / "config" / "brokers.yaml"
    with open(yaml_path, encoding="utf-8") as f:
        return yaml.safe_load(f)["brokers"]


@pytest.fixture(scope="module")
def retenues_raw():
    yaml_path = Path(__file__).parent.parent / "config" / "retenues_source.yaml"
    with open(yaml_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ─── Tests ETF enrichi ───────────────────────────────────────────────────────


def test_univers_etf_charge_sans_erreur():
    """1. charger_et_valider doit charger univers_etf.yaml sans exception."""
    data = charger_et_valider("univers_etf.yaml")
    assert data is not None
    assert len(data.univers_etf) > 0


def test_chaque_etf_a_domicile_iso_valide(etfs):
    """2. domicile_iso ∈ {IE, LU, FR, DE, AT, ...} si présent (champ optionnel)."""
    domiciles_valides = {"IE", "LU", "FR", "DE", "AT", "BE", "NL", "SE", "DK", "FI"}
    violations = []
    for etf in etfs:
        domicile_iso = etf.get("domicile_iso")
        if domicile_iso is not None and domicile_iso not in domiciles_valides:
            violations.append(f"{etf.get('ticker')}: domicile_iso='{domicile_iso}' non reconnu")
    assert not violations, "domicile_iso invalides:\n" + "\n".join(violations)


def test_chaque_etf_a_3_alternatives_ecartees(etfs):
    """3. Si alternatives_ecartees est présent et non vide, doit avoir ≥ 3 entrées."""
    violations = []
    for etf in etfs:
        alt = etf.get("alternatives_ecartees")
        if alt is not None and len(alt) > 0 and len(alt) < 3:
            violations.append(
                f"{etf.get('ticker')}: {len(alt)} alternative(s) seulement (min 3 si renseigné)"
            )
    assert not violations, "\n".join(violations)


def test_tracking_difference_dans_fourchette(etfs):
    """4. TD 3y ∈ [-0.01, +0.005] si présent (au-delà = suspect)."""
    violations = []
    for etf in etfs:
        td3 = etf.get("tracking_difference_3y")
        if td3 is not None and not (-0.01 <= td3 <= 0.005):
            violations.append(
                f"{etf.get('ticker')}: tracking_difference_3y={td3} hors fourchette [-0.01, +0.005]"
            )
    assert not violations, "TD 3y suspects:\n" + "\n".join(violations)


# ─── Tests Contrats AV ───────────────────────────────────────────────────────


def test_contrats_av_charge_sans_erreur():
    """5. charger_et_valider("contrats_av.yaml") ne lève pas d'exception."""
    data = charger_et_valider("contrats_av.yaml")
    assert isinstance(data, AssuranceVieConfig)
    assert len(data.contrats_av) > 0


def test_contrats_av_min_15_entrees(contrats_av_raw):
    """6. Au moins 15 contrats AV dans le fichier."""
    assert len(contrats_av_raw) >= 15, (
        f"Seulement {len(contrats_av_raw)} contrats AV (minimum 15 requis)"
    )


def test_contrats_av_frais_uc_coherent(contrats_av_raw):
    """7. frais_gestion_uc_pct ∈ [0.003, 0.015] pour chaque contrat."""
    violations = []
    for contrat in contrats_av_raw:
        frais = contrat.get("frais_gestion_uc_pct")
        if frais is not None and not (0.003 <= frais <= 0.015):
            violations.append(
                f"{contrat.get('id')}: frais_gestion_uc_pct={frais} hors fourchette [0.003, 0.015]"
            )
    assert not violations, "\n".join(violations)


def test_contrats_av_sources_non_vides(contrats_av_raw):
    """8. Chaque contrat AV a ≥ 1 source listée."""
    violations = [
        c.get("id")
        for c in contrats_av_raw
        if not c.get("sources") or len(c.get("sources", [])) == 0
    ]
    assert not violations, f"Contrats sans source: {violations}"


# ─── Tests Brokers ───────────────────────────────────────────────────────────


def test_brokers_charge_sans_erreur():
    """9. charger_et_valider("brokers.yaml") ne lève pas d'exception."""
    data = charger_et_valider("brokers.yaml")
    assert isinstance(data, BrokersConfig)
    assert len(data.brokers) > 0


def test_brokers_min_10_entrees(brokers_raw):
    """10. Au moins 10 brokers dans le fichier."""
    assert len(brokers_raw) >= 10, f"Seulement {len(brokers_raw)} brokers (minimum 10 requis)"


def test_brokers_eligibilite_coherent(brokers_raw):
    """11. Cohérence PEA et AV — un PSI broker ne peut pas proposer directement AV (sauf partenariat explicite)."""
    # Règle: si av_disponible=True, le broker est en réalité un assureur/distributeur
    # Les PSI purs (Bourse Direct, DEGIRO, IBKR, Trade Republic) ne doivent pas avoir av=True
    psi_purs = {"bourse_direct", "degiro", "interactive_brokers", "trade_republic"}
    violations = []
    for broker in brokers_raw:
        bid = broker.get("id")
        if bid in psi_purs and broker.get("av_disponible"):
            violations.append(f"{bid}: PSI pur avec av_disponible=True — incohérent")
    assert not violations, "\n".join(violations)


# ─── Tests Retenues Source ───────────────────────────────────────────────────


def test_retenues_source_charge_sans_erreur():
    """12. charger_et_valider("retenues_source.yaml") ne lève pas d'exception."""
    data = charger_et_valider("retenues_source.yaml")
    assert isinstance(data, RetenuesSourceConfig)


def test_retenues_source_matrice_complete(retenues_raw):
    """13. Au moins 12 pays émetteurs développés × 3 domiciles dans la matrice."""
    matrice = retenues_raw.get("matrice", {})
    pays_developpes_requis = {
        "US",
        "UK",
        "DE",
        "CH",
        "JP",
        "FR",
        "AU",
        "CA",
        "NL",
        "IT",
        "ES",
        "SE",
    }
    domiciles_requis = {"IE", "LU", "FR"}
    manquants = []
    for pays in pays_developpes_requis:
        if pays not in matrice:
            manquants.append(f"Pays '{pays}' absent de la matrice")
        else:
            for domicile in domiciles_requis:
                if domicile not in matrice[pays]:
                    manquants.append(f"matrice[{pays}][{domicile}] absent")
    assert not manquants, "Matrice incomplète:\n" + "\n".join(manquants)


def test_retenues_source_taux_dans_bornes(retenues_raw):
    """14. Tous les taux de retenue source ∈ [0, 0.35]."""
    matrice = retenues_raw.get("matrice", {})
    violations = []
    for pays, domiciles in matrice.items():
        for domicile, taux in domiciles.items():
            if taux is not None and not (0.0 <= taux <= 0.35):
                violations.append(f"matrice[{pays}][{domicile}]={taux} hors bornes [0, 0.35]")
    assert not violations, "\n".join(violations)


def test_retenues_source_cas_us_ie_est_15pct(retenues_raw):
    """15. Sanity check du traité emblématique US-IE = 15%."""
    matrice = retenues_raw.get("matrice", {})
    taux_us_ie = matrice.get("US", {}).get("IE")
    assert taux_us_ie is not None, "matrice[US][IE] absent"
    assert taux_us_ie == 0.15, f"Traité US-IE doit être 0.15 (15%), obtenu {taux_us_ie}"


def test_loader_echoue_proprement_sur_source_manquante():
    """16. Si un contrat AV n'a pas de sources, le validator Pydantic doit échouer."""
    from pydantic import ValidationError

    from src.schemas import ContratAV

    with pytest.raises(ValidationError, match="au moins une source obligatoire"):
        ContratAV(
            id="test_sans_source",
            nom="Test",
            assureur="Test",
            distributeur="Test",
            frais_gestion_uc_pct=0.005,
            frais_gestion_fonds_euros_pct=0.006,
            frais_entree_pct=0.0,
            frais_arbitrage_pct=0.0,
            nb_uc_total=100,
            versement_minimum_eur=500,
            sources=[],  # liste vide → doit échouer
        )


def test_retenues_source_emetteurs_emergents_presents(retenues_raw):
    """17. Les 6 pays émergents requis doivent être présents dans la matrice."""
    matrice = retenues_raw.get("matrice", {})
    emergents_requis = {"CN", "HK", "KR", "IN", "BR", "TW"}
    manquants = [p for p in emergents_requis if p not in matrice]
    assert not manquants, f"Pays émergents manquants dans la matrice: {manquants}"
