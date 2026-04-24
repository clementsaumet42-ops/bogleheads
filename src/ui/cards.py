"""Cartes KPI premium pour l'UI Streamlit."""

from __future__ import annotations


def carte_kpi(
    titre: str,
    valeur: str,
    unite: str = "",
    contexte: str = "",
    couleur_valeur: str = "#B08D57",
) -> str:
    """Génère une carte KPI en HTML/CSS."""
    return f"""
<div style="
    background: #FFFFFF;
    border: 1px solid #E8E0D5;
    border-radius: 8px;
    padding: 20px 16px;
    box-shadow: 0 2px 8px rgba(27,58,91,0.08);
    min-height: 140px;
">
    <div style="
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: #666666;
        margin-bottom: 12px;
    ">{titre}</div>
    <div style="
        font-size: 36px;
        font-weight: 700;
        color: {couleur_valeur};
        font-family: Georgia, serif;
        line-height: 1.1;
    ">{valeur}</div>
    <div style="
        font-size: 13px;
        color: #888888;
        margin-top: 4px;
    ">{unite}</div>
    {f'<div style="font-size:12px;color:#555555;margin-top:10px;border-top:1px solid #F0EBE3;padding-top:8px;">{contexte}</div>' if contexte else ""}
</div>
"""


def badge_statut(statut: str) -> str:
    """Badge coloré pour le statut de l'optimiseur."""
    if statut == "optimal":
        bg, color, label = "#E8F5E9", "#2E5D4F", "✓ Optimal"
    elif statut == "fallback":
        bg, color, label = "#FFF3E0", "#A65A4E", "⚠ Fallback"
    else:
        bg, color, label = "#E3F2FD", "#1B3A5B", f"ⓘ {statut}"
    return f"""
<div style="
    display:inline-block;
    background:{bg};
    color:{color};
    border:1px solid {color}33;
    border-radius:20px;
    padding:4px 14px;
    font-size:13px;
    font-weight:600;
">
    {label}
</div>
"""
