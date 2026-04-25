"""Script de génération des backtests et export résultats."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))  # noqa: E402

from src.backtest.comparaison import comparer_4_niveaux  # noqa: E402
from src.backtest.portefeuilles_bogle import PORTEFEUILLES_DISPONIBLES  # noqa: E402
from src.schemas import charger_et_valider  # noqa: E402


def main() -> None:
    print("=" * 60)
    print("  Backtest Bogleheads FR — Sprint S9")
    print("=" * 60)

    # Charger la configuration
    try:
        cfg = charger_et_valider("backtest.yaml")
    except Exception as e:
        print(f"❌ Impossible de charger backtest.yaml : {e}")
        sys.exit(1)

    params = cfg.backtest
    config_backtest = {
        "capital_initial_eur": params.capital_initial_eur,
        "date_debut": params.date_debut,
        "date_fin": params.date_fin,
        "frais": params.frais.model_dump(),
        "fiscalite": params.fiscalite.model_dump(),
    }

    portefeuilles_actifs = params.portefeuilles_actifs or list(PORTEFEUILLES_DISPONIBLES.keys())

    output_dir = ROOT / "output" / "backtest"
    output_dir.mkdir(parents=True, exist_ok=True)

    resultats_globaux = {}

    for nom_pf in portefeuilles_actifs:
        if nom_pf not in PORTEFEUILLES_DISPONIBLES:
            print(f"  ⚠️  Portefeuille inconnu : {nom_pf}, ignoré.")
            continue

        pf = PORTEFEUILLES_DISPONIBLES[nom_pf]
        print(f"\n  ▶ {nom_pf}")

        try:
            rapport = comparer_4_niveaux(
                portefeuille=pf,
                config_backtest=config_backtest,
                generer_graphique=True,
                dossier_sortie=str(output_dir),
            )
        except Exception as e:
            print(f"    ❌ Erreur : {e}")
            continue

        # Afficher résumé
        for mode, res in rapport.resultats.items():
            print(
                f"    [{mode:18s}] Capital final: {res.capital_final:>12,.0f} € "
                f"| CAGR: {res.cagr * 100:5.2f}% "
                f"| Sharpe: {res.sharpe:5.2f} "
                f"| MDD: {res.max_drawdown * 100:6.2f}%"
            )
        print(
            f"    Delta frais: {rapport.delta_frais_bps:.1f} bps | "
            f"Delta fiscal: {rapport.delta_fiscal_bps:.1f} bps | "
            f"Gain optim: {rapport.delta_optimise_bps:.1f} bps"
        )
        if rapport.chemin_png:
            print(f"    📊 Graphique : {rapport.chemin_png}")

        resultats_globaux[nom_pf] = rapport.model_dump(exclude={"resultats"})

    # Sauvegarder le résumé JSON
    json_path = output_dir / "backtest_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(resultats_globaux, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n✅ Résumé JSON : {json_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
