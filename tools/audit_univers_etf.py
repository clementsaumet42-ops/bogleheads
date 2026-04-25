#!/usr/bin/env python3
"""
Audit qualité de l'univers ETF — Sprint S11-B.

Usage :
    python tools/audit_univers_etf.py              # rapport stdout + JSON + MD
    python tools/audit_univers_etf.py --check      # exit 1 si ≥ 1 FAIL
    python tools/audit_univers_etf.py --no-net     # ignore les checks réseau

Le script vérifie pour chaque ETF de config/univers_etf.yaml :
  - ISIN valide (format + checksum Luhn)
  - TER présent et dans [0, 5 %]
  - AUM (aum_mds_eur) ≥ 0,05 si présent
  - Tracking difference présente (warn si absente)
  - URL DIC/KID HEAD HTTP (optionnel — skippé si offline ou --no-net)
  - derniere_verification < 365 jours (sinon "stale data")
  - alternatives_ecartees non vide pour classes principales

Produit :
  - Tableau coloré stdout
  - output/audit_univers_etf_YYYYMMDD.json
  - output/audit_univers_etf_YYYYMMDD.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
CONFIG_DIR = ROOT / "config"
OUTPUT_DIR = ROOT / "output"

# ─── Constantes ───────────────────────────────────────────────────────────────

CLASSES_PRINCIPALES = {"Actions"}
ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}\d$")
STALE_JOURS = 365

# Codes couleur ANSI
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


# ─── Validation ISIN (checksum Luhn) ─────────────────────────────────────────


def _isin_to_digits(isin: str) -> str:
    """Convertit un ISIN en chaîne de chiffres (lettres → position dans l'alphabet + 9)."""
    digits = ""
    for ch in isin:
        if ch.isdigit():
            digits += ch
        elif ch.isalpha():
            digits += str(ord(ch) - ord("A") + 10)
    return digits


def valider_isin(isin: str) -> tuple[bool, str]:
    """
    Valide le format et le checksum Luhn d'un ISIN.

    Returns (valide, message_erreur).
    """
    if not isin:
        return False, "ISIN absent"
    if len(isin) != 12:
        return False, f"Longueur invalide : {len(isin)} (attendu 12)"
    if not ISIN_RE.match(isin):
        return False, "Format invalide : ne correspond pas à ^[A-Z]{2}[A-Z0-9]{9}\\d$"

    # Luhn modifié ISIN
    digits = _isin_to_digits(isin)
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    if total % 10 != 0:
        return False, f"Checksum Luhn invalide (total={total})"
    return True, ""


# ─── Vérification HTTP (optionnelle) ─────────────────────────────────────────


def verifier_url_http(url: str, timeout: float = 5.0) -> tuple[str, str]:
    """
    Effectue un HEAD HTTP sur l'URL.

    Returns (statut, message) où statut ∈ {"ok", "warn", "fail", "skip"}.
    """
    if not url:
        return "warn", "URL DIC/KID absente"
    try:
        import urllib.request

        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "BogleheadsFR-AuditBot/1.0")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            if code == 200:
                return "ok", f"HTTP {code}"
            return "warn", f"HTTP {code} (non-200)"
    except Exception as exc:
        msg = str(exc)
        if "timeout" in msg.lower() or "unreachable" in msg.lower() or "connection" in msg.lower():
            return "skip", f"Réseau indisponible : {msg[:60]}"
        return "fail", f"Erreur HTTP : {msg[:80]}"


# ─── Audit d'un ETF ───────────────────────────────────────────────────────────


def auditer_etf(etf: dict, avec_net: bool = True) -> dict:
    """
    Audite un ETF et retourne un rapport avec statut par règle.

    Returns dict avec clés :
        ticker, isin, nom, statut_global ("ok" / "warn" / "fail"),
        regles (liste de dict {regle, statut, message}).
    """
    regles: list[dict] = []
    ticker = etf.get("ticker", "?")
    isin = str(etf.get("isin", "") or "")
    nom = etf.get("nom", "—")

    def _r(regle: str, statut: str, message: str) -> None:
        regles.append({"regle": regle, "statut": statut, "message": message})

    # ── ISIN ─────────────────────────────────────────────────────────────────
    if not isin:
        _r("isin", "warn", "ISIN absent (null)")
    else:
        ok, msg = valider_isin(isin)
        if ok:
            _r("isin", "ok", f"ISIN {isin} valide")
        else:
            _r("isin", "fail", f"ISIN invalide : {msg}")

    # ── TER ──────────────────────────────────────────────────────────────────
    ter = etf.get("ter")
    if ter is None:
        _r("ter", "fail", "TER absent")
    else:
        ter = float(ter)
        if ter < 0:
            _r("ter", "fail", f"TER négatif : {ter:.4f}")
        elif ter > 0.05:
            _r("ter", "fail", f"TER aberrant (> 5%) : {ter:.4f}")
        else:
            _r("ter", "ok", f"TER = {ter:.2%}")

    # ── AUM ──────────────────────────────────────────────────────────────────
    aum = etf.get("aum_mds_eur")
    if aum is None:
        _r("aum", "warn", "AUM (aum_mds_eur) absent — à compléter")
    else:
        aum = float(aum)
        if aum <= 0:
            _r("aum", "fail", f"AUM nul ou négatif : {aum}")
        elif aum < 0.05:
            _r("aum", "warn", f"ETF illiquide : AUM = {aum:.3f} Mds€ (< 0,05)")
        else:
            _r("aum", "ok", f"AUM = {aum:.2f} Mds€")

    # ── Tracking difference ──────────────────────────────────────────────────
    td3y = etf.get("tracking_difference_3y")
    td5y = etf.get("tracking_difference_5y")
    if td3y is None and td5y is None:
        _r("tracking_difference", "warn", "TD 3y et 5y absents — à compléter")
    else:
        _r("tracking_difference", "ok", f"TD 3y={td3y}, TD 5y={td5y}")

    # ── URL DIC/KID (réseau optionnel) ────────────────────────────────────────
    url_dic = etf.get("url_dic_kid")
    if avec_net and url_dic:
        statut_url, msg_url = verifier_url_http(url_dic)
        if statut_url == "skip":
            _r("url_dic_kid", "warn", f"Vérification réseau ignorée : {msg_url}")
        else:
            _r("url_dic_kid", statut_url, msg_url)
    elif url_dic:
        _r("url_dic_kid", "ok", f"URL présente (non vérifiée réseau) : {url_dic[:60]}")
    else:
        _r("url_dic_kid", "warn", "URL DIC/KID absente (null)")

    # ── Dernière vérification ─────────────────────────────────────────────────
    dv = etf.get("derniere_verification")
    if dv is None:
        _r("derniere_verification", "warn", "Jamais vérifié (derniere_verification absent)")
    else:
        try:
            dv_date = dv if isinstance(dv, date) else date.fromisoformat(str(dv))
            age_jours = (date.today() - dv_date).days
            if age_jours > STALE_JOURS:
                _r(
                    "derniere_verification",
                    "warn",
                    f"Données stale : {dv_date} ({age_jours} jours > {STALE_JOURS}j)",
                )
            else:
                _r("derniere_verification", "ok", f"Vérifié le {dv_date} ({age_jours}j)")
        except ValueError:
            _r("derniere_verification", "fail", f"Format de date invalide : {dv}")

    # ── Alternatives écartées (classes principales) ──────────────────────────
    classe = etf.get("classe_actifs", "")
    alts = etf.get("alternatives_ecartees", []) or []
    if classe in CLASSES_PRINCIPALES and not alts:
        _r(
            "alternatives_ecartees",
            "warn",
            f"Classe '{classe}' sans alternatives_ecartees documentées",
        )
    else:
        _r("alternatives_ecartees", "ok", f"{len(alts)} alternative(s) documentée(s)")

    # ── Statut global ─────────────────────────────────────────────────────────
    statuts = [r["statut"] for r in regles if r["statut"] != "skip"]
    if "fail" in statuts:
        statut_global = "fail"
    elif "warn" in statuts:
        statut_global = "warn"
    else:
        statut_global = "ok"

    return {
        "ticker": ticker,
        "isin": isin,
        "nom": nom,
        "statut_global": statut_global,
        "regles": regles,
    }


# ─── Rapport ──────────────────────────────────────────────────────────────────


def _couleur(statut: str) -> str:
    return {
        "ok": GREEN,
        "warn": YELLOW,
        "fail": RED,
        "skip": "",
    }.get(statut, "")


def _icone(statut: str) -> str:
    return {"ok": "✅", "warn": "⚠️ ", "fail": "❌", "skip": "🔵"}.get(statut, "?")


def afficher_rapport_stdout(rapports: list[dict]) -> None:
    """Affiche un tableau coloré dans le terminal."""
    nb_ok = sum(1 for r in rapports if r["statut_global"] == "ok")
    nb_warn = sum(1 for r in rapports if r["statut_global"] == "warn")
    nb_fail = sum(1 for r in rapports if r["statut_global"] == "fail")

    print(f"\n{BOLD}=== Audit Univers ETF — {date.today()} ==={RESET}")
    print(
        f"Total : {len(rapports)} ETF  |  {GREEN}✅ OK : {nb_ok}{RESET}  |  {YELLOW}⚠️  WARN : {nb_warn}{RESET}  |  {RED}❌ FAIL : {nb_fail}{RESET}\n"
    )

    col_w = max((len(r["ticker"]) for r in rapports), default=6) + 2
    nom_w = 40

    header = f"{'Ticker':<{col_w}} {'Statut':<8} {'Nom':<{nom_w}} Problèmes"
    print(f"{BOLD}{header}{RESET}")
    print("-" * (col_w + 8 + nom_w + 30))

    for r in rapports:
        statut = r["statut_global"]
        c = _couleur(statut)
        icone = _icone(statut)
        problemes = [
            f"{reg['regle']}:{reg['message'][:40]}"
            for reg in r["regles"]
            if reg["statut"] in ("warn", "fail")
        ]
        ligne = f"{r['ticker']:<{col_w}} {c}{icone} {statut:<6}{RESET} {r['nom'][:nom_w]:<{nom_w}}"
        if problemes:
            ligne += "  " + " | ".join(problemes[:2])
        print(ligne)

    print()


def generer_rapport_md(rapports: list[dict], date_str: str) -> str:
    """Génère un rapport Markdown."""
    nb_ok = sum(1 for r in rapports if r["statut_global"] == "ok")
    nb_warn = sum(1 for r in rapports if r["statut_global"] == "warn")
    nb_fail = sum(1 for r in rapports if r["statut_global"] == "fail")

    lines = [
        f"# Audit Univers ETF — {date_str}",
        "",
        f"**Total :** {len(rapports)} ETF | **✅ OK :** {nb_ok} | **⚠️ WARN :** {nb_warn} | **❌ FAIL :** {nb_fail}",
        "",
        "| Ticker | ISIN | Statut | Problèmes |",
        "|--------|------|--------|-----------|",
    ]
    for r in rapports:
        icone = _icone(r["statut_global"])
        probs = [
            f"`{reg['regle']}` : {reg['message'][:60]}"
            for reg in r["regles"]
            if reg["statut"] in ("warn", "fail")
        ]
        prob_str = "<br>".join(probs) if probs else "—"
        lines.append(f"| {r['ticker']} | {r['isin']} | {icone} {r['statut_global']} | {prob_str} |")

    lines.extend(["", "---", f"*Généré le {date_str} par `tools/audit_univers_etf.py`*"])
    return "\n".join(lines)


# ─── Point d'entrée ───────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit qualité univers ETF Boglehead FR")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Mode CI : exit 1 si ≥ 1 FAIL",
    )
    parser.add_argument(
        "--no-net",
        action="store_true",
        help="Désactive les vérifications HTTP (URLs DIC/KID)",
    )
    parser.add_argument(
        "--config",
        default=str(CONFIG_DIR / "univers_etf.yaml"),
        help="Chemin vers univers_etf.yaml",
    )
    args = parser.parse_args(argv)

    avec_net = not args.no_net

    # Chargement
    config_path = Path(args.config)
    with open(config_path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    etfs = raw.get("univers_etf", [])
    if not etfs:
        print("⚠️  Aucun ETF trouvé dans le fichier de configuration.", file=sys.stderr)
        return 1

    # Audit
    rapports = [auditer_etf(etf, avec_net=avec_net) for etf in etfs]

    # Affichage stdout
    afficher_rapport_stdout(rapports)

    # Écriture JSON
    date_str = date.today().strftime("%Y%m%d")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    json_path = OUTPUT_DIR / f"audit_univers_etf_{date_str}.json"
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "date": date_str,
                "nb_etf": len(rapports),
                "nb_ok": sum(1 for r in rapports if r["statut_global"] == "ok"),
                "nb_warn": sum(1 for r in rapports if r["statut_global"] == "warn"),
                "nb_fail": sum(1 for r in rapports if r["statut_global"] == "fail"),
                "rapports": rapports,
            },
            fh,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    print(f"📄 Rapport JSON : {json_path}")

    # Écriture Markdown
    md_path = OUTPUT_DIR / f"audit_univers_etf_{date_str}.md"
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(generer_rapport_md(rapports, date_str))
    print(f"📝 Rapport Markdown : {md_path}")

    # Mode --check : exit 1 si FAIL
    nb_fail = sum(1 for r in rapports if r["statut_global"] == "fail")
    if args.check and nb_fail > 0:
        print(f"\n{RED}❌ --check mode : {nb_fail} ETF(s) en FAIL → exit 1{RESET}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
