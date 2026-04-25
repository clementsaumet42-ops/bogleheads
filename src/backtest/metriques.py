"""Métriques de performance pour le backtest."""
from __future__ import annotations

import numpy as np
import pandas as pd


def calculer_cagr(capital_initial: float, capital_final: float, n_annees: float) -> float:
    """Compound Annual Growth Rate."""
    if capital_initial <= 0 or n_annees <= 0:
        return 0.0
    return (capital_final / capital_initial) ** (1.0 / n_annees) - 1.0


def calculer_volatilite_annuelle(rendements_mensuels: pd.Series) -> float:
    """Volatilité annualisée à partir de rendements mensuels."""
    if len(rendements_mensuels) < 2:
        return 0.0
    return float(rendements_mensuels.std() * np.sqrt(12))


def calculer_sharpe(rendements_mensuels: pd.Series, rf_annuel: float = 0.02) -> float:
    """Ratio de Sharpe annualisé."""
    vol = calculer_volatilite_annuelle(rendements_mensuels)
    if vol == 0:
        return 0.0
    rf_mensuel = (1 + rf_annuel) ** (1 / 12) - 1
    excess = rendements_mensuels - rf_mensuel
    return float(excess.mean() * 12 / vol)


def calculer_max_drawdown(serie_valeur: pd.Series) -> float:
    """Maximum drawdown (valeur négative ou nulle)."""
    if serie_valeur.empty:
        return 0.0
    cummax = serie_valeur.cummax()
    drawdown = (serie_valeur - cummax) / cummax
    return float(drawdown.min())


def calculer_sortino(rendements_mensuels: pd.Series, rf_annuel: float = 0.02) -> float:
    """Ratio de Sortino annualisé."""
    rf_mensuel = (1 + rf_annuel) ** (1 / 12) - 1
    excess = rendements_mensuels - rf_mensuel
    downside = excess[excess < 0]
    if len(downside) < 2:
        return 0.0
    downside_std = float(downside.std() * np.sqrt(12))
    if downside_std == 0:
        return 0.0
    return float(excess.mean() * 12 / downside_std)


def calculer_calmar(cagr: float, max_drawdown: float) -> float:
    """Ratio de Calmar."""
    if max_drawdown == 0:
        return 0.0
    return cagr / abs(max_drawdown)
