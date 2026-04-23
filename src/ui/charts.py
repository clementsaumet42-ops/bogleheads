"""Graphiques Plotly réutilisables pour l'UI Streamlit — aucune logique métier."""

from __future__ import annotations

import plotly.graph_objects as go

_PRIMARY = "#1a4d8f"
_ACCENT = "#d4a017"
_SECONDARY = "#4a90d9"


def camembert_allocation(poids: dict[str, float], titre: str = "Allocation cible") -> go.Figure:
    """Camembert interactif de l'allocation cible par classe d'actifs."""
    labels = list(poids.keys())
    values = [v * 100 for v in poids.values()]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            texttemplate="%{label}<br>%{value:.1f}%",
            hovertemplate="%{label} : %{value:.1f}%<extra></extra>",
            marker_colors=[
                _PRIMARY,
                _ACCENT,
                _SECONDARY,
                "#6aab9c",
                "#e07b54",
                "#9b59b6",
                "#3498db",
                "#e74c3c",
            ],
        )
    )
    fig.update_layout(
        title=titre,
        showlegend=True,
        height=420,
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return fig


def fan_chart_mc(
    annees: list[int],
    p10: list[float],
    mediane: list[float],
    p90: list[float],
    objectif: float | None = None,
    titre: str = "Projection Monte-Carlo",
) -> go.Figure:
    """Fan chart P10 / médiane / P90 pour la projection Monte-Carlo."""
    fig = go.Figure()

    # Bande P10–P90
    fig.add_trace(
        go.Scatter(
            x=annees + annees[::-1],
            y=p90 + p10[::-1],
            fill="toself",
            fillcolor="rgba(26,77,143,0.15)",
            line={"color": "rgba(0,0,0,0)"},
            name="P10–P90",
            hoverinfo="skip",
        )
    )

    # P10
    fig.add_trace(
        go.Scatter(
            x=annees,
            y=p10,
            line={"color": _ACCENT, "dash": "dot", "width": 1.5},
            name="P10 (scénario bas)",
            hovertemplate="Année %{x} — P10 : %{y:,.0f} €<extra></extra>",
        )
    )

    # Médiane
    fig.add_trace(
        go.Scatter(
            x=annees,
            y=mediane,
            line={"color": _PRIMARY, "width": 2.5},
            name="Médiane",
            hovertemplate="Année %{x} — Médiane : %{y:,.0f} €<extra></extra>",
        )
    )

    # P90
    fig.add_trace(
        go.Scatter(
            x=annees,
            y=p90,
            line={"color": "#2ecc71", "dash": "dot", "width": 1.5},
            name="P90 (scénario haut)",
            hovertemplate="Année %{x} — P90 : %{y:,.0f} €<extra></extra>",
        )
    )

    # Objectif
    if objectif is not None and objectif > 0:
        fig.add_hline(
            y=objectif,
            line={"color": "#e74c3c", "dash": "dash", "width": 1.5},
            annotation_text=f"Objectif {objectif:,.0f} €",
            annotation_position="top left",
        )

    fig.update_layout(
        title=titre,
        xaxis_title="Années",
        yaxis_title="Capital (€)",
        height=480,
        hovermode="x unified",
        margin={"l": 60, "r": 20, "t": 60, "b": 50},
    )
    return fig


def heatmap_asset_location(
    ventilation: list[dict],
    titre: str = "Asset Location — classes × enveloppes",
) -> go.Figure:
    """Heatmap Plotly montrant la ventilation des classes d'actifs par enveloppe."""
    if not ventilation:
        fig = go.Figure()
        fig.update_layout(title="Aucune donnée de ventilation disponible")
        return fig

    # Construire la matrice
    classes = sorted({v["classe"] for v in ventilation})
    enveloppes = sorted({v["enveloppe"] for v in ventilation})

    matrix: list[list[float]] = []
    for cls in classes:
        row = []
        for env in enveloppes:
            val = next(
                (v["montant"] for v in ventilation if v["classe"] == cls and v["enveloppe"] == env),
                0.0,
            )
            row.append(val)
        matrix.append(row)

    text = [[f"{v:,.0f} €" if v > 0 else "" for v in row] for row in matrix]

    fig = go.Figure(
        go.Heatmap(
            z=matrix,
            x=enveloppes,
            y=classes,
            text=text,
            texttemplate="%{text}",
            colorscale=[[0, "#f5f7fa"], [0.5, _SECONDARY], [1.0, _PRIMARY]],
            showscale=True,
            hovertemplate="Classe : %{y}<br>Enveloppe : %{x}<br>Montant : %{z:,.0f} €<extra></extra>",
        )
    )
    fig.update_layout(
        title=titre,
        xaxis_title="Enveloppe",
        yaxis_title="Classe d'actifs",
        height=max(300, len(classes) * 50 + 100),
        margin={"l": 160, "r": 20, "t": 60, "b": 60},
    )
    return fig
