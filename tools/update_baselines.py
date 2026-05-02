#!/usr/bin/env python3
"""Régénère les expected_outputs.json pour les missions de test.

Usage:
    python tools/update_baselines.py                    # toutes les missions
    python tools/update_baselines.py mission_cadre_sup_ir  # une seule mission

ATTENTION: Après régénération, réviser manuellement les valeurs fiscales
avant de committer (voir docs/fiabilisation.md §3).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
MISSIONS_DIR = ROOT / "tests" / "missions"


def build_expected_outputs(inputs_path: Path) -> dict:
    """Calcule les expected_outputs pour un fichier inputs.yaml donné."""
    with open(inputs_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    profil_data = data["profil"]

    from src.allocation.asset_location_milp import calculer_allocation_cible
    from src.audit.alertes import detecter_alertes
    from src.fiscalite.constantes import (
        IS_TAUX_NORMAL,
        IS_TAUX_REDUIT,
        PEA_PLAFOND_VERSEMENTS,
        TAUX_PFU_TOTAL,
        TAUX_PS,
    )
    from src.fiscalite.pea import verifier_plafond_pea
    from src.fiscalite.per import calculer_plafond_deduction_per
    from src.schemas import AllocationCible, Profil

    alloc_data = profil_data.get("allocation_cible_bogleheads", {})
    alloc = AllocationCible(
        actions=alloc_data.get("actions", 0.6),
        obligations=alloc_data.get("obligations", 0.3),
        liquidites=alloc_data.get("liquidites", 0.1),
    )
    profil_data["allocation_cible_bogleheads"] = alloc
    profil = Profil(**profil_data)

    alertes = detecter_alertes(profil)
    alloc_cible = calculer_allocation_cible(profil, None)

    # PEA plafond check
    enveloppes = profil.enveloppes_disponibles or {}
    pea_versements = 0.0
    if "PEA" in enveloppes:
        pea_info = enveloppes["PEA"]
        if isinstance(pea_info, dict):
            pea_versements = float(
                pea_info.get("versements_cumules", pea_info.get("encours_actuel", 0))
            )
    pea_result = verifier_plafond_pea(pea_versements)
    pea_plafond_atteint = pea_result["respect_plafond"] and pea_versements >= PEA_PLAFOND_VERSEMENTS

    # PER deduction
    rfr = float(profil.rfr_annuel or 0)
    per_ded = calculer_plafond_deduction_per(rfr)

    profil_map = {
        "defensif": "defensif_40_60",
        "equilibre": "equilibre_60_40",
        "dynamique": "dynamique_75_25",
        "agressif": "agressif_85_15",
    }
    profil_aversion = profil.profil_aversion_risque or "equilibre"
    profil_mif2 = profil_map.get(profil_aversion, profil_aversion)

    regime_is = profil.regime_fiscal_detenteur == "IS"

    return {
        "alertes_codes": [a.code for a in alertes],
        "nb_alertes_min": max(1, len(alertes)),
        "allocation_cible": alloc_cible,
        "allocation_tolerance": 1e-6,
        "profil_mif2": profil_mif2,
        "pea_plafond_atteint": pea_plafond_atteint,
        "per_deduction_max_eur": per_ded,
        "fiscal": {
            "taux_pfu_total": TAUX_PFU_TOTAL,
            "taux_ps": TAUX_PS,
            "regime_is": regime_is,
            "is_taux_normal": IS_TAUX_NORMAL,
            "is_taux_reduit": IS_TAUX_REDUIT,
        },
    }


def update_mission(mission_dir: Path) -> None:
    inputs_path = mission_dir / "inputs.yaml"
    if not inputs_path.exists():
        print(f"SKIP {mission_dir.name}: no inputs.yaml")
        return

    print(f"Processing {mission_dir.name}...")
    try:
        outputs = build_expected_outputs(inputs_path)
        out_path = mission_dir / "expected_outputs.json"
        out_path.write_text(
            json.dumps(outputs, ensure_ascii=False, indent=2, default=float),
            encoding="utf-8",
        )
        print(f"  ✅ Régénéré: {out_path}")
    except Exception as exc:
        print(f"  ❌ Erreur: {exc}", file=sys.stderr)
        raise


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else ""

    if target:
        mission_dir = MISSIONS_DIR / target
        if not mission_dir.exists():
            print(f"Mission introuvable: {mission_dir}", file=sys.stderr)
            sys.exit(1)
        update_mission(mission_dir)
    else:
        missions = [
            d for d in MISSIONS_DIR.iterdir() if d.is_dir() and not d.name.startswith("_")
        ]
        if not missions:
            print("Aucune mission trouvée dans tests/missions/", file=sys.stderr)
            sys.exit(1)
        for m in sorted(missions):
            update_mission(m)

    print("\n⚠️  Réviser manuellement les valeurs fiscales avant commit !")
    print("   Voir docs/fiabilisation.md §3 pour la checklist.")


if __name__ == "__main__":
    main()
