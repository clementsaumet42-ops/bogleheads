"""Tests d'audit qualité univers ETF — Sprint S11-B (≥ 6 tests)."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from tools.audit_univers_etf import (  # noqa: E402
    auditer_etf,
    valider_isin,
)

# ─── Tests ISIN ──────────────────────────────────────────────────────────────


def test_isin_invalide_longueur():
    """L'audit détecte un ISIN de longueur incorrecte."""
    ok, msg = valider_isin("FR123")
    assert not ok
    assert "Longueur" in msg or "longueur" in msg or "12" in msg


def test_isin_invalide_format():
    """L'audit détecte un ISIN au format incorrect (chiffres en début)."""
    ok, msg = valider_isin("123456789012")
    assert not ok


def test_isin_invalide_checksum():
    """L'audit détecte un ISIN avec checksum Luhn incorrect."""
    # ISIN avec mauvais dernier chiffre (checksum modifié)
    ok_valid, _ = valider_isin("IE00B4L5Y983")  # IWDA — valide
    assert ok_valid
    ok_inv, msg_inv = valider_isin("IE00B4L5Y984")  # checksum modifié → invalide
    assert not ok_inv


def test_isin_valide():
    """Un ISIN valide (CW8, IWDA) passe la validation."""
    ok_cw8, _ = valider_isin("IE0031442068")  # CW8
    assert ok_cw8
    ok_iwda, _ = valider_isin("IE00B4L5Y983")  # IWDA
    assert ok_iwda


# ─── Tests audit ETF ─────────────────────────────────────────────────────────


def test_audit_detecte_ter_negatif():
    """L'audit détecte un TER négatif."""
    etf = {
        "ticker": "TEST",
        "isin": "IE00B4L5Y983",
        "nom": "Test ETF",
        "ter": -0.001,
        "classe_actifs": "Actions",
    }
    rapport = auditer_etf(etf, avec_net=False)
    ter_regle = next(r for r in rapport["regles"] if r["regle"] == "ter")
    assert ter_regle["statut"] == "fail"
    assert rapport["statut_global"] == "fail"


def test_audit_detecte_ter_aberrant():
    """L'audit détecte un TER > 5 %."""
    etf = {
        "ticker": "TEST",
        "isin": "IE00B4L5Y983",
        "nom": "Test ETF coûteux",
        "ter": 0.06,  # 6% > 5%
        "classe_actifs": "Actions",
    }
    rapport = auditer_etf(etf, avec_net=False)
    ter_regle = next(r for r in rapport["regles"] if r["regle"] == "ter")
    assert ter_regle["statut"] == "fail"


def test_audit_detecte_aum_nulle():
    """L'audit détecte une AUM nulle."""
    etf = {
        "ticker": "TEST",
        "isin": "IE00B4L5Y983",
        "nom": "Test ETF AUM nul",
        "ter": 0.002,
        "aum_mds_eur": 0.0,
        "classe_actifs": "Actions",
    }
    rapport = auditer_etf(etf, avec_net=False)
    aum_regle = next(r for r in rapport["regles"] if r["regle"] == "aum")
    assert aum_regle["statut"] == "fail"


def test_audit_etf_propre_donne_statut_ok():
    """Un ETF complet et propre obtient le statut 'ok' ou 'warn' (mais pas 'fail')."""
    etf = {
        "ticker": "IWDA",
        "isin": "IE00B4L5Y983",
        "nom": "iShares Core MSCI World UCITS ETF",
        "ter": 0.002,
        "aum_mds_eur": 50.0,
        "tracking_difference_3y": -0.001,
        "tracking_difference_5y": -0.001,
        "url_dic_kid": None,  # pas de vérif réseau dans les tests
        "derniere_verification": str(date.today()),
        "alternatives_ecartees": [{"ticker": "CW8", "raison": "swap"}],
        "classe_actifs": "Actions",
    }
    rapport = auditer_etf(etf, avec_net=False)
    assert rapport["statut_global"] in ("ok", "warn")
    assert rapport["statut_global"] != "fail"


def test_audit_isin_invalide_dans_univers():
    """L'audit détecte un ISIN invalide dans l'univers ETF."""
    etf = {
        "ticker": "BADISIN",
        "isin": "XX0000000000",  # format correct mais Luhn incorrect
        "nom": "ETF ISIN invalide",
        "ter": 0.002,
        "classe_actifs": "Actions",
    }
    rapport = auditer_etf(etf, avec_net=False)
    isin_regle = next(r for r in rapport["regles"] if r["regle"] == "isin")
    assert isin_regle["statut"] == "fail"


# ─── Tests rapport JSON ───────────────────────────────────────────────────────


def test_audit_produit_json_valide(tmp_path):
    """Le mode audit produit un fichier JSON valide."""

    import tools.audit_univers_etf as audit_mod

    # Patcher OUTPUT_DIR vers tmp_path
    orig_dir = audit_mod.OUTPUT_DIR
    audit_mod.OUTPUT_DIR = tmp_path
    try:
        audit_mod.main(["--no-net"])
    finally:
        audit_mod.OUTPUT_DIR = orig_dir

    json_files = list(tmp_path.glob("audit_univers_etf_*.json"))
    assert len(json_files) >= 1, "Aucun fichier JSON généré"

    with open(json_files[0], encoding="utf-8") as fh:
        data = json.load(fh)
    assert "nb_etf" in data
    assert "rapports" in data
    assert isinstance(data["rapports"], list)
    assert data["nb_etf"] > 0


# ─── Tests mode --check ───────────────────────────────────────────────────────


def test_check_mode_exit_0_sur_univers_propre(tmp_path, monkeypatch):
    """Le mode --check retourne exit 0 si tous les ETFs sont propres."""
    import tools.audit_univers_etf as audit_mod

    # Créer un YAML minimal propre
    yaml_content = """univers_etf:
- isin: IE00B4L5Y983
  ticker: IWDA
  nom: iShares Core MSCI World UCITS ETF
  emetteur: iShares
  classe_actifs: Actions
  ter: 0.002
  aum_mds_eur: 50.0
  tracking_difference_3y: -0.001
  derniere_verification: '{today}'
  alternatives_ecartees:
    - ticker: CW8
      raison: swap
""".replace("{today}", str(date.today()))

    yaml_path = tmp_path / "univers_etf.yaml"
    yaml_path.write_text(yaml_content, encoding="utf-8")

    orig_dir = audit_mod.OUTPUT_DIR
    audit_mod.OUTPUT_DIR = tmp_path
    try:
        code = audit_mod.main(["--check", "--no-net", "--config", str(yaml_path)])
    finally:
        audit_mod.OUTPUT_DIR = orig_dir

    assert code == 0, f"Exit code attendu 0 (propre), obtenu {code}"


def test_check_mode_exit_1_sur_univers_cassé(tmp_path):
    """Le mode --check retourne exit 1 si ≥ 1 FAIL détecté."""
    import tools.audit_univers_etf as audit_mod

    yaml_content = """univers_etf:
- isin: INVALIDE12345
  ticker: BAD
  nom: ETF cassé
  emetteur: Test
  classe_actifs: Actions
  ter: -0.01
"""
    yaml_path = tmp_path / "univers_etf_bad.yaml"
    yaml_path.write_text(yaml_content, encoding="utf-8")

    orig_dir = audit_mod.OUTPUT_DIR
    audit_mod.OUTPUT_DIR = tmp_path
    try:
        code = audit_mod.main(["--check", "--no-net", "--config", str(yaml_path)])
    finally:
        audit_mod.OUTPUT_DIR = orig_dir

    assert code == 1, f"Exit code attendu 1 (fail), obtenu {code}"


# ─── Tests champ derniere_verification ───────────────────────────────────────


def test_derniere_verification_deserialise_correctement():
    """Le champ derniere_verification est désérialisé correctement comme date."""
    from src.schemas import ETF

    etf_data = {
        "ticker": "TEST",
        "nom": "Test ETF",
        "emetteur": "Test",
        "classe_actifs": "Actions",
        "ter": 0.002,
        "devise": "EUR",
        "domicile": "Irlande",
        "capitalisant": True,
        "eur_hedged": False,
        "derniere_verification": "2025-04-25",
    }
    etf = ETF.model_validate(etf_data)
    assert etf.derniere_verification == date(2025, 4, 25)
    assert isinstance(etf.derniere_verification, date)


def test_audit_status_defaut_non_verifie():
    """Le statut d'audit par défaut est 'non_verifie'."""
    from src.schemas import ETF

    etf_data = {
        "ticker": "TEST",
        "nom": "Test ETF",
        "emetteur": "Test",
        "classe_actifs": "Actions",
        "ter": 0.002,
        "devise": "EUR",
        "domicile": "Irlande",
        "capitalisant": True,
        "eur_hedged": False,
    }
    etf = ETF.model_validate(etf_data)
    assert etf.audit_status == "non_verifie"
