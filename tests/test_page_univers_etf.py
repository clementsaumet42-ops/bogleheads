"""Tests de la page 12_Univers_ETF.py — Sprint S11-B (≥ 4 tests)."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent


# ─── Tests de la logique de la page (sans Streamlit UI) ──────────────────────


def _badge_verification(dv_str: str | date | None) -> str:
    """Reproduit la logique de badge de la page."""
    if dv_str is None:
        return "🔴 Non vérifié"
    try:
        dv = date.fromisoformat(str(dv_str)) if not isinstance(dv_str, date) else dv_str
        age = (date.today() - dv).days
        if age <= 180:
            return f"🟢 {dv} ({age}j)"
        elif age <= 365:
            return f"🟡 {dv} ({age}j)"
        else:
            return f"🔴 {dv} ({age}j)"
    except Exception:
        return f"⚪ {dv_str}"


def test_badge_verification_recent():
    """Badge vert pour une vérification récente (< 180 jours)."""
    recent = date.today() - timedelta(days=30)
    badge = _badge_verification(recent)
    assert badge.startswith("🟢")


def test_badge_verification_ancien():
    """Badge rouge pour une vérification ancienne (> 365 jours)."""
    vieux = date.today() - timedelta(days=400)
    badge = _badge_verification(vieux)
    assert badge.startswith("🔴")


def test_badge_verification_absent():
    """Badge rouge pour une vérification absente."""
    badge = _badge_verification(None)
    assert badge == "🔴 Non vérifié"


def test_badge_verification_intermediaire():
    """Badge orange pour une vérification intermédiaire (181-365 jours)."""
    inter = date.today() - timedelta(days=200)
    badge = _badge_verification(inter)
    assert badge.startswith("🟡")


# ─── Tests de la page compilable (import) ───────────────────────────────────


def test_page_univers_etf_compilable():
    """La page 12_Univers_ETF.py se compile sans erreur de syntaxe."""
    page_path = ROOT / "pages" / "12_Univers_ETF.py"
    assert page_path.exists(), "La page 12_Univers_ETF.py n'existe pas."

    with open(page_path, encoding="utf-8") as fh:
        source = fh.read()
    compile(source, str(page_path), "exec")  # lève SyntaxError si invalide


# ─── Tests de filtrage logique ────────────────────────────────────────────────


def test_filtre_pea_reduit_nombre_etf():
    """Le filtre PEA réduit le nombre d'ETF affichés (sanity check)."""
    import yaml

    config_path = ROOT / "config" / "univers_etf.yaml"
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    etfs = raw.get("univers_etf", [])

    nb_total = len(etfs)
    nb_pea = sum(1 for e in etfs if (e.get("eligibilite") or {}).get("PEA", False) is True)
    # Il doit y avoir des ETFs non-PEA dans l'univers
    assert nb_pea < nb_total, (
        f"Tous les ETFs ({nb_total}) seraient éligibles PEA — filtre non pertinent."
    )
    assert nb_pea > 0, "Aucun ETF éligible PEA trouvé dans l'univers."


def test_intersection_pea_av_sous_ensemble_coherent():
    """L'intersection PEA + AV produit un sous-ensemble ≤ PEA seul."""
    import yaml

    config_path = ROOT / "config" / "univers_etf.yaml"
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    etfs = raw.get("univers_etf", [])

    def _pea(e: dict) -> bool:
        return (e.get("eligibilite") or {}).get("PEA", False) is True

    def _av(e: dict) -> bool:
        return (e.get("eligibilite") or {}).get("AV_UC", False) is True

    nb_pea = sum(1 for e in etfs if _pea(e))
    nb_pea_et_av = sum(1 for e in etfs if _pea(e) and _av(e))

    assert nb_pea_et_av <= nb_pea, (
        f"L'intersection PEA+AV ({nb_pea_et_av}) est plus grande que PEA seul ({nb_pea})."
    )


def test_univers_etf_contient_etfs_verifies():
    """Au moins quelques ETFs phares ont un champ derniere_verification renseigné."""
    import yaml

    config_path = ROOT / "config" / "univers_etf.yaml"
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    etfs = raw.get("univers_etf", [])

    nb_verifies = sum(1 for e in etfs if e.get("derniere_verification") is not None)
    assert nb_verifies >= 5, f"Attendu ≥ 5 ETFs avec derniere_verification, trouvé {nb_verifies}."
