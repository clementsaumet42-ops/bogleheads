"""Tests de validation — univers ETF Boglehead FR"""

from pathlib import Path

import pytest
import yaml


@pytest.fixture(scope="module")
def etfs():
    """Charge la liste des ETF depuis le fichier YAML."""
    yaml_path = Path(__file__).parent.parent / "config" / "univers_etf.yaml"
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["univers_etf"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _isin_checksum_valid(isin: str) -> bool:
    """
    Valide un ISIN via l'algorithme Luhn modifié (Modulus 10 / Double-Add-Double).
    https://en.wikipedia.org/wiki/International_Securities_Identification_Number
    """
    if len(isin) != 12:
        return False
    # 2 lettres pays + 9 alphanumériques + 1 chiffre de contrôle
    country = isin[:2]
    if not country.isalpha():
        return False
    body = isin[2:11]
    if not body.isalnum():
        return False
    check = isin[11]
    if not check.isdigit():
        return False

    # Convertir chaque caractère en chiffre (A=10 ... Z=35)
    digits = ""
    for ch in isin[:-1]:
        if ch.isdigit():
            digits += ch
        else:
            digits += str(ord(ch) - 55)

    # Luhn : doubler les chiffres en position paire (de droite, 0-indexé)
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d)
        if i % 2 == 0:  # position paire (droite) → doubler
            n *= 2
            if n > 9:
                n -= 9
        total += n

    expected_check = (10 - (total % 10)) % 10
    return expected_check == int(check)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_tous_les_isin_valides(etfs):
    """Vérifie que chaque ISIN respecte le format et le checksum Luhn."""
    invalids = []
    for etf in etfs:
        isin = etf.get("isin", "")
        if isin is None:
            continue  # ISIN non encore disponible — ignoré
        if isin == "ISIN_A_VERIFIER":
            invalids.append(f"{etf.get('ticker')}: ISIN_A_VERIFIER (littéral non corrigé)")
        elif not _isin_checksum_valid(isin):
            invalids.append(f"{etf.get('ticker')}: ISIN invalide '{isin}'")
    assert not invalids, "ISIN invalides détectés :\n" + "\n".join(invalids)


def test_unicite_isin(etfs):
    """Vérifie qu'il n'y a pas de doublons ISIN."""
    isins = [e["isin"] for e in etfs if e.get("isin") is not None]
    seen = set()
    duplicates = []
    for isin in isins:
        if isin in seen:
            duplicates.append(isin)
        seen.add(isin)
    assert not duplicates, f"ISIN dupliqués : {duplicates}"


def test_coherence_pea_classe_actifs(etfs):
    """
    Vérifie qu'aucun ETF de classe Obligations/Or/Matières premières/Immobilier
    n'est marqué PEA=True.
    """
    classes_non_pea = {"Obligations", "Or", "Matières premières", "Immobilier"}
    violations = []
    for etf in etfs:
        cls = etf.get("classe_actifs", "")
        if cls in classes_non_pea and etf.get("eligibilite", {}).get("PEA"):
            violations.append(f"{etf.get('ticker')} ({cls}): PEA=True interdit pour cette classe")
    assert not violations, "Violations PEA/classe_actifs :\n" + "\n".join(violations)


def test_coherence_pea_domicile(etfs):
    """
    Vérifie que tout ETF marqué PEA=True est domicilié dans l'UE/EEE
    (France, Irlande, Luxembourg, Allemagne, Pays-Bas, Suède, etc.).
    """
    ue_eee = {
        "France",
        "Irlande",
        "Luxembourg",
        "Allemagne",
        "Pays-Bas",
        "Suède",
        "Danemark",
        "Belgique",
        "Espagne",
        "Italie",
        "Finlande",
        "Autriche",
        "Portugal",
        "Pologne",
    }
    violations = []
    for etf in etfs:
        if etf.get("eligibilite", {}).get("PEA"):
            domicile = etf.get("domicile", "")
            if domicile not in ue_eee:
                violations.append(
                    f"{etf.get('ticker')}: PEA=True mais domicile hors UE/EEE '{domicile}'"
                )
    assert not violations, "Violations PEA/domicile :\n" + "\n".join(violations)


def test_dic_renseigne_ou_null(etfs):
    """
    Vérifie que chaque ETF possède un champ url_dic_kid (URL ou null explicite,
    pas absent du tout).
    """
    missing = [etf.get("ticker", "?") for etf in etfs if "url_dic_kid" not in etf]
    assert not missing, f"url_dic_kid absent pour : {missing}"


def test_schema_minimum(etfs):
    """Vérifie que tous les champs obligatoires sont présents pour chaque ETF."""
    champs_obligatoires = [
        "isin",
        "ticker",
        "nom",
        "emetteur",
        "classe_actifs",
        "ter",
        "devise",
        "domicile",
        "capitalisant",
        "eligibilite",
        "methode_replication",
        "url_dic_kid",
        "date_verification_dic",
        "contrats_av_reference",
        "frais_entree_typique_pct",
    ]
    eligibilite_champs = ["PEA", "PER", "PEE", "CTO_perso", "CTO_IS", "Contrat_Cap_IS", "AV_UC"]

    missing = []
    for etf in etfs:
        ticker = etf.get("ticker", "?")
        for champ in champs_obligatoires:
            if champ not in etf:
                missing.append(f"{ticker}: champ '{champ}' manquant")
        for champ in eligibilite_champs:
            if champ not in etf.get("eligibilite", {}):
                missing.append(f"{ticker}: eligibilite.{champ} manquant")

    assert not missing, "Champs manquants :\n" + "\n".join(missing[:20])


def test_methode_replication_valeurs_valides(etfs):
    """Vérifie que methode_replication est l'une des valeurs autorisées."""
    valeurs_valides = {
        "physique",
        "synthetique_swap",
        "synthetique_swap_unfunded",
        "physique_optimisee",
    }
    invalids = []
    for etf in etfs:
        m = etf.get("methode_replication", "")
        if m not in valeurs_valides:
            invalids.append(f"{etf.get('ticker')}: methode_replication='{m}'")
    assert not invalids, "Valeurs invalides :\n" + "\n".join(invalids)


def test_ter_positif(etfs):
    """Vérifie que le TER est un nombre non négatif."""
    invalids = []
    for etf in etfs:
        ter = etf.get("ter")
        if ter is None or ter < 0:
            invalids.append(f"{etf.get('ticker')}: TER={ter}")
    assert not invalids, f"TER invalides : {invalids}"


def test_contrats_av_reference_est_liste(etfs):
    """Vérifie que contrats_av_reference est une liste (vide ou non)."""
    invalids = [
        etf.get("ticker") for etf in etfs if not isinstance(etf.get("contrats_av_reference"), list)
    ]
    assert not invalids, f"contrats_av_reference n'est pas une liste pour : {invalids}"


def test_av_uc_coherence_avec_contrats(etfs):
    """
    Vérifie que si AV_UC=False, la liste contrats_av_reference est vide
    (on ne peut pas lister des contrats si l'ETF n'est pas éligible AV).
    """
    violations = []
    for etf in etfs:
        av_uc = etf.get("eligibilite", {}).get("AV_UC", False)
        contrats = etf.get("contrats_av_reference", [])
        if not av_uc and contrats:
            violations.append(
                f"{etf.get('ticker')}: AV_UC=False mais contrats_av_reference non vide"
            )
    assert not violations, "\n".join(violations)


def test_isin_lu0378818131_present(etfs):
    """Vérifie que l'ETF Xtrackers MSCI World 1C (LU0378818131) est dans l'univers."""
    isins = [e["isin"] for e in etfs]
    assert "LU0378818131" in isins, "LU0378818131 (Xtrackers MSCI World 1C) absent de l'univers"


def test_moteur_charge_univers(etfs):
    """
    Vérifie que le chargement via enveloppes.py ne lève pas d'exception
    avec le YAML enrichi et que verifier_eligibilite_etf fonctionne pour les nouveaux champs.
    """
    from src.enveloppes import verifier_eligibilite_etf

    for etf in etfs[:5]:  # Test sur les 5 premiers
        # Champs existants
        _ = verifier_eligibilite_etf(etf, "PEA")
        _ = verifier_eligibilite_etf(etf, "PER")
        # Nouveau champ
        _ = verifier_eligibilite_etf(etf, "AV_UC")
        # Champ inexistant → doit retourner False sans exception
        result = verifier_eligibilite_etf(etf, "ENVELOPPE_INCONNUE")
        assert result is False


def test_frais_entree_positif_ou_nul(etfs):
    """Vérifie que frais_entree_typique_pct >= 0."""
    invalids = [etf.get("ticker") for etf in etfs if etf.get("frais_entree_typique_pct", 0) < 0]
    assert not invalids, f"Frais d'entrée négatifs : {invalids}"
