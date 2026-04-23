"""Helpers de formatage pour l'UI Streamlit — aucune logique métier."""

from __future__ import annotations


def format_euro(montant: float, decimales: int = 0) -> str:
    """Formate un montant en euros avec séparateur de milliers."""
    if decimales == 0:
        return f"{montant:,.0f} €".replace(",", "\u202f")
    return f"{montant:,.{decimales}f} €".replace(",", "\u202f")


def format_pct(valeur: float, decimales: int = 1) -> str:
    """Formate une valeur fractionnaire [0, 1] en pourcentage."""
    return f"{valeur * 100:.{decimales}f} %"


def format_kpi(label: str, valeur: str, delta: str | None = None) -> dict:
    """Retourne un dict prêt à passer à st.metric()."""
    result: dict = {"label": label, "value": valeur}
    if delta is not None:
        result["delta"] = delta
    return result


def format_ratio_sharpe(ratio: float) -> str:
    """Formate le ratio de Sharpe avec 2 décimales."""
    return f"{ratio:.2f}"
