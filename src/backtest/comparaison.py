"""Comparaison multi-modes des backtests Bogle."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from .fiscalite_backtest import ConfigFiscalite
from .frais import ConfigFrais
from .moteur_backtest import ResultatBacktest, backtester
from .portefeuilles_bogle import PortefeuilleBogle


class RapportComparatif(BaseModel):
    portefeuille_nom: str
    resultats: dict[str, ResultatBacktest]
    delta_frais_bps: float
    delta_fiscal_bps: float
    delta_optimise_bps: float
    chemin_png: str | None = None


def comparer_4_niveaux(
    portefeuille: PortefeuilleBogle,
    config_backtest: dict,
    profil_pour_optim: Any | None = None,
    generer_graphique: bool = False,
    dossier_sortie: str | None = None,
) -> RapportComparatif:
    """Lance les 4 modes de backtest et produit un rapport comparatif."""
    capital = config_backtest.get("capital_initial_eur", 100_000.0)
    date_debut = config_backtest.get("date_debut", "2003-01-31")
    date_fin = config_backtest.get("date_fin", "2024-12-31")

    config_frais = ConfigFrais(**config_backtest.get("frais", {}))
    config_fiscalite = ConfigFiscalite(**config_backtest.get("fiscalite", {}))

    modes = ["brut", "net_frais", "net_fiscal_cto", "net_optimise"]
    resultats: dict[str, ResultatBacktest] = {}

    for mode in modes:
        resultats[mode] = backtester(
            portefeuille=portefeuille,
            capital_initial_eur=capital,
            date_debut=date_debut,
            date_fin=date_fin,
            config_frais=config_frais,
            config_fiscalite=config_fiscalite,
            mode=mode,
            profil_pour_optim=profil_pour_optim if mode == "net_optimise" else None,
        )

    cagr_brut = resultats["brut"].cagr
    cagr_net_frais = resultats["net_frais"].cagr
    cagr_net_fiscal = resultats["net_fiscal_cto"].cagr
    cagr_optimise = resultats["net_optimise"].cagr

    delta_frais_bps = (cagr_brut - cagr_net_frais) * 10_000
    delta_fiscal_bps = (cagr_net_frais - cagr_net_fiscal) * 10_000
    delta_optimise_bps = (cagr_optimise - cagr_net_fiscal) * 10_000

    chemin_png: str | None = None
    if generer_graphique and dossier_sortie:
        chemin_png = _generer_graphique(portefeuille.nom, resultats, dossier_sortie)

    return RapportComparatif(
        portefeuille_nom=portefeuille.nom,
        resultats=resultats,
        delta_frais_bps=delta_frais_bps,
        delta_fiscal_bps=delta_fiscal_bps,
        delta_optimise_bps=delta_optimise_bps,
        chemin_png=chemin_png,
    )


def _generer_graphique(
    nom: str,
    resultats: dict[str, ResultatBacktest],
    dossier_sortie: str,
) -> str | None:
    """Génère un graphique comparatif des 4 modes."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        from pathlib import Path

        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(12, 6))
        couleurs = {
            "brut": "#1a4d8f",
            "net_frais": "#d4a017",
            "net_fiscal_cto": "#e05c4a",
            "net_optimise": "#2ecc71",
        }
        labels = {
            "brut": "Brut",
            "net_frais": "Net frais",
            "net_fiscal_cto": "Net fiscal CTO",
            "net_optimise": "Net optimisé",
        }

        for mode, res in resultats.items():
            if res.serie_valeur_mensuelle:
                dates = [d for d, _ in res.serie_valeur_mensuelle]
                vals = [v for _, v in res.serie_valeur_mensuelle]
                ax.plot(
                    dates[::6],
                    vals[::6],
                    label=labels[mode],
                    color=couleurs[mode],
                    linewidth=1.5,
                )

        ax.set_title(f"Backtest — {nom}")
        ax.set_xlabel("Date")
        ax.set_ylabel("Valeur du portefeuille (€)")
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        output_path = Path(dossier_sortie) / f"backtest_{nom}.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(output_path), dpi=120)
        plt.close(fig)
        return str(output_path)
    except Exception:
        return None
