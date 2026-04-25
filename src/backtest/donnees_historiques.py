"""Chargement des séries historiques EUR pour le backtest."""
from __future__ import annotations

import logging
import warnings
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "historiques"

CLASSES_DISPONIBLES = [
    "actions_monde_developpe",
    "actions_emergents",
    "actions_europe",
    "actions_usa",
    "obligations_euro_agg",
    "obligations_euro_souveraines",
    "obligations_inflation_eur",
    "cash_eur",
    "or",
    "matieres_premieres",
]


def charger_serie(classe: str) -> pd.Series:
    """
    Charge la série historique mensuelle de rendements totaux EUR pour une classe d'actifs.
    Lit depuis data/historiques/<classe>.csv.
    Fallback: tente yfinance si CSV absent (avec warning).
    Retourne pd.Series avec index DatetimeIndex.
    """
    csv_path = DATA_DIR / f"{classe}.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path, parse_dates=["date"], index_col="date")
        serie = df["rendement_total_eur"].squeeze()
        serie.index = pd.to_datetime(serie.index)
        serie.name = classe
        return serie

    # Fallback yfinance
    warnings.warn(
        f"CSV absent pour '{classe}' ({csv_path}). Tentative yfinance (non-reproductible).",
        UserWarning,
        stacklevel=2,
    )
    try:
        return _charger_depuis_yfinance(classe)
    except Exception as exc:
        logger.warning("yfinance indisponible pour '%s': %s", classe, exc)
        raise FileNotFoundError(
            f"Données historiques introuvables pour '{classe}'. "
            f"CSV manquant: {csv_path}"
        ) from exc


def _charger_depuis_yfinance(classe: str) -> pd.Series:
    """Tentative de chargement via yfinance (fallback, non-reproductible)."""
    try:
        import yfinance as yf
    except ImportError as exc:
        raise ImportError("yfinance non installé. Installer avec: pip install yfinance") from exc

    _TICKERS_YFINANCE = {
        "actions_monde_developpe": "IWDA.AS",
        "actions_emergents": "IEMM.AS",
        "actions_europe": "MEUD.PA",
        "actions_usa": "CSPX.L",
        "obligations_euro_agg": "IEAG.AS",
        "obligations_euro_souveraines": "IBGM.AS",
        "obligations_inflation_eur": "IBCI.AS",
        "cash_eur": None,
        "or": "SGLD.L",
        "matieres_premieres": "LYTR.PA",
    }
    ticker = _TICKERS_YFINANCE.get(classe)
    if ticker is None:
        raise ValueError(f"Pas de ticker yfinance pour '{classe}'")

    raw = yf.download(ticker, period="max", interval="1mo", auto_adjust=True, progress=False)
    if raw.empty:
        raise ValueError(f"yfinance a retourné des données vides pour {ticker}")

    prices = raw["Close"].squeeze()
    returns = prices.pct_change().dropna()
    returns.name = classe
    return returns


def aligner_series(*series: pd.Series, fill_max_mois: int = 3) -> pd.DataFrame:
    """
    Aligne plusieurs séries sur leur index commun.
    - Remplit les NaN par forward-fill max fill_max_mois mois
    - Raise ValueError si trou > fill_max_mois mois consécutifs après fill

    Returns DataFrame avec une colonne par série.
    """
    if not series:
        raise ValueError("Au moins une série requise")

    df = pd.concat(list(series), axis=1)

    # Vérifier les trous avant remplissage
    for col in df.columns:
        col_series = df[col]
        null_streak = 0
        for val in col_series:
            if pd.isna(val):
                null_streak += 1
                if null_streak > fill_max_mois:
                    raise ValueError(
                        f"Trou > {fill_max_mois} mois consécutifs dans la série '{col}'"
                    )
            else:
                null_streak = 0

    # Forward-fill puis drop NaN restants
    df = df.ffill(limit=fill_max_mois).dropna()

    if df.empty:
        raise ValueError("Aucune date commune entre les séries après alignement")

    return df
