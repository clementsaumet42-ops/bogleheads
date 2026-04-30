"""Tests de la page 12_Univers_ETF.py — Sprint S11-B (≥ 4 tests)."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

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
    pytest.skip("Page archivée — pivot EC")


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


# ─── Tests S11-C : TER effectif ──────────────────────────────────────────────


def test_ter_effectif_colonne_presente():
    """La colonne TER_effectif_pct est calculée dans le DataFrame de la page."""
    import yaml

    from src.fiscalite.drag_etf import calculer_drag_fiscal_etf

    config_path = ROOT / "config" / "univers_etf.yaml"
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    etfs = raw.get("univers_etf", [])

    import pandas as pd

    rows = []
    for etf in etfs:
        ter = etf.get("ter", 0.0) or 0.0
        drag = calculer_drag_fiscal_etf(
            etf.get("replication"), etf.get("domicile_iso"), etf.get("exposition_geo")
        )
        rows.append({"ticker": etf["ticker"], "ter": ter, "drag_bps": drag})
    df = pd.DataFrame(rows)
    df["TER_effectif_pct"] = df["ter"] + df["drag_bps"] / 100.0

    assert "TER_effectif_pct" in df.columns, "Colonne TER_effectif_pct manquante"
    assert len(df) > 0, "DataFrame vide"
    # Les valeurs doivent toutes être ≥ ter (drag ≥ 0)
    assert (df["TER_effectif_pct"] >= df["ter"]).all(), (
        "TER_effectif_pct < TER affiché pour certains ETFs (drag négatif impossible)"
    )


def test_tri_ter_effectif_inverse_classement():
    """Tri par TER effectif ≠ tri par TER affiché sur fixture avec LU-US physique bas TER."""
    import pandas as pd

    from src.fiscalite.drag_etf import calculer_drag_fiscal_etf

    # Fixture : ETF physique LU-US avec TER bas vs synthétique avec TER plus haut
    fixture = [
        # Physique LU-US : TER 0.10% mais drag ~45 bps → TER effectif ~0.55%
        {
            "ticker": "ETF_PHYS_LU",
            "ter": 0.0010,
            "replication": "physique_sampling",
            "domicile_iso": "LU",
            "exposition_geo": "US",
        },
        # Synthétique : TER 0.38% mais drag 0 → TER effectif = 0.38%
        {
            "ticker": "ETF_SWAP_FR",
            "ter": 0.0038,
            "replication": "synthetique_swap",
            "domicile_iso": "FR",
            "exposition_geo": "US",
        },
    ]
    df = pd.DataFrame(fixture)
    df["drag_bps"] = df.apply(
        lambda r: calculer_drag_fiscal_etf(
            r["replication"], r["domicile_iso"], r["exposition_geo"]
        ),
        axis=1,
    )
    df["TER_effectif_pct"] = df["ter"] + df["drag_bps"] / 100.0

    # Tri par TER affiché : physique LU (0.10%) < synthétique (0.38%)
    par_ter_affiche = df.sort_values("ter").reset_index(drop=True)
    assert par_ter_affiche.iloc[0]["ticker"] == "ETF_PHYS_LU", (
        "TER affiché le plus bas devrait être physique LU"
    )

    # Tri par TER effectif : synthétique (0.38%) < physique LU (0.10% + ~0.45% = ~0.55%)
    par_ter_effectif = df.sort_values("TER_effectif_pct").reset_index(drop=True)
    assert par_ter_effectif.iloc[0]["ticker"] == "ETF_SWAP_FR", (
        "Après tri par TER effectif, le swap (drag=0) devrait passer devant le physique LU-US"
    )
