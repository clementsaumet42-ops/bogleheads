"""Composants UI réutilisables — Private Banking."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pandas as pd
import streamlit as st

from src.ui.theme import (
    ARDOISE,
    ARDOISE_CLAIRE,
    BLANC_CASSE,
    BLEU_NUIT,
    IVOIRE,
    OR_CLAIR,
    OR_VIEILLI,
    ROUGE_BORDEAUX,
)

_ASSETS = Path(__file__).parent.parent.parent / "assets"


def icone_lucide(nom: str, taille: int = 16, couleur: str = "var(--ardoise-claire)") -> str:
    """Charge un SVG Lucide depuis assets/icons/{nom}.svg et l'injecte inline."""
    svg_path = _ASSETS / "icons" / f"{nom}.svg"
    if not svg_path.exists():
        return ""
    svg = svg_path.read_text(encoding="utf-8")
    svg = svg.replace(
        "<svg ",
        f'<svg width="{taille}" height="{taille}" style="color:{couleur};vertical-align:middle;" ',
        1,
    )
    return svg


def monogramme_html(taille: int = 48) -> str:
    """Renvoie le SVG du monogramme cabinet dimensionné."""
    svg_path = _ASSETS / "monogramme.svg"
    if not svg_path.exists():
        return ""
    svg = svg_path.read_text(encoding="utf-8")
    svg = svg.replace('width="100"', f'width="{taille}"').replace(
        'height="100"', f'height="{taille}"'
    )
    return svg


def titre_page(titre: str, sous_titre: str | None = None, icone: str | None = None) -> None:
    """Titre éditorial : EB Garamond 36px, sous-titre italique gris ardoise."""
    icone_html = icone_lucide(icone, taille=32, couleur=OR_VIEILLI) if icone else ""
    sous_titre_html = (
        f'<p style="font-family:Inter,system-ui,sans-serif;font-size:1rem;'
        f"color:{ARDOISE_CLAIRE};font-style:italic;margin:0.25rem 0 0 0;"
        f'letter-spacing:0.02em;">{sous_titre}</p>'
        if sous_titre
        else ""
    )
    st.markdown(
        f"""
        <div style="margin-bottom:2rem;padding-bottom:1rem;
                    border-bottom:0.5px solid rgba(139,111,71,0.35);">
          <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.25rem;">
            {icone_html}
            <h1 style="font-family:'EB Garamond',Georgia,serif;font-size:2.25rem;
                       font-weight:700;color:{BLEU_NUIT};letter-spacing:-0.02em;
                       margin:0;line-height:1.2;">{titre}</h1>
          </div>
          {sous_titre_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(
    label: str, valeur: str, variation: str | None = None, tendance: str | None = None
) -> None:
    """Carte KPI : valeur en serif 32px, fond blanc cassé, bordure or fine."""
    tendance_color = (
        OR_VIEILLI
        if tendance == "hausse"
        else (ROUGE_BORDEAUX if tendance == "baisse" else ARDOISE_CLAIRE)
    )
    variation_html = (
        f'<div style="font-family:Inter,system-ui,sans-serif;font-size:0.8rem;'
        f'color:{tendance_color};margin-top:0.25rem;">{variation}</div>'
        if variation
        else ""
    )
    st.markdown(
        f"""
        <div style="background-color:{BLANC_CASSE};border:0.5px solid rgba(139,111,71,0.35);
                    border-radius:2px;padding:1rem 1.25rem;margin-bottom:1rem;">
          <div style="font-family:Inter,system-ui,sans-serif;font-size:0.688rem;
                      letter-spacing:0.08em;text-transform:uppercase;
                      color:{ARDOISE_CLAIRE};font-style:italic;margin-bottom:0.35rem;">
            {label}
          </div>
          <div style="font-family:'EB Garamond',Georgia,serif;font-size:2rem;
                      font-weight:700;color:{BLEU_NUIT};font-variant-numeric:tabular-nums;">
            {valeur}
          </div>
          {variation_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def tableau_elegant(df: pd.DataFrame, colonnes_chiffrees: list[str] | None = None) -> None:
    """st.dataframe stylé : alternance lignes, chiffres serif tabulaire, en-têtes lettre-espacement."""
    colonnes_chiffrees = colonnes_chiffrees or []

    def _styler(s: pd.Series) -> list[str]:
        return [
            f"font-variant-numeric:tabular-nums;font-family:'EB Garamond',Georgia,serif;"
            f"font-size:0.95rem;"
            if s.name in colonnes_chiffrees
            else "font-family:Inter,system-ui,sans-serif;font-size:0.875rem;"
            for _ in s
        ]

    styler = df.style.apply(_styler, axis=0)
    st.dataframe(styler, use_container_width=True)


def bouton_principal(label: str, key: str, icone_lucide_nom: str | None = None) -> bool:
    """Bouton bleu nuit primaire. Returns True if clicked."""
    icone_html = (
        icone_lucide(icone_lucide_nom, taille=14, couleur=IVOIRE) if icone_lucide_nom else ""
    )
    label_html = f"{icone_html} {label}".strip() if icone_html else label
    if icone_html:
        st.markdown(
            f"""
            <style>
            div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {{
                background-color:{BLEU_NUIT};color:{IVOIRE};
                border:1px solid {OR_VIEILLI};border-radius:2px;
                font-family:Inter,system-ui,sans-serif;font-size:0.85rem;
                letter-spacing:0.05em;text-transform:uppercase;padding:0.5rem 1.5rem;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
    return st.button(label_html, key=key, type="primary")


def bouton_secondaire(label: str, key: str, icone_lucide_nom: str | None = None) -> bool:
    """Bouton transparent bordure ardoise. Returns True if clicked."""
    icone_html = (
        icone_lucide(icone_lucide_nom, taille=14, couleur=ARDOISE) if icone_lucide_nom else ""
    )
    label_html = f"{icone_html} {label}".strip() if icone_html else label
    return st.button(label_html, key=key)


def panneau_avertissement(severity: str, titre: str, description: str) -> None:
    """Panneau avec filet gauche 4px coloré. severity: 'info', 'warning', 'danger'."""
    color_map = {
        "info": OR_VIEILLI,
        "warning": ARDOISE_CLAIRE,
        "danger": ROUGE_BORDEAUX,
    }
    couleur = color_map.get(severity, OR_VIEILLI)
    st.markdown(
        f"""
        <div style="background-color:{BLANC_CASSE};border-left:4px solid {couleur};
                    border-radius:0 2px 2px 0;padding:0.75rem 1rem;margin:0.5rem 0;">
          <div style="font-family:'EB Garamond',Georgia,serif;font-size:1rem;
                      font-weight:600;color:{BLEU_NUIT};margin-bottom:0.2rem;">
            {titre}
          </div>
          <div style="font-family:Inter,system-ui,sans-serif;font-size:0.875rem;
                      color:{ARDOISE};line-height:1.6;">
            {description}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(titre: str, contenu_callback: Callable, separateur_or: bool = True) -> None:
    """Section éditoriale avec filet or fin sous le titre."""
    sep = f"border-bottom:0.5px solid {OR_VIEILLI};" if separateur_or else ""
    st.markdown(
        f"""
        <div style="margin-bottom:0.5rem;padding-bottom:0.4rem;{sep}">
          <h2 style="font-family:'EB Garamond',Georgia,serif;font-size:1.5rem;
                     font-weight:600;color:{BLEU_NUIT};letter-spacing:-0.01em;
                     margin:0;line-height:1.3;">
            {titre}
          </h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
    contenu_callback()


def lettrine(texte: str, taille: int = 64) -> None:
    """Première lettre en serif gras de grande taille (pour pages éditoriales)."""
    if not texte:
        return
    premiere, reste = texte[0], texte[1:]
    st.markdown(
        f"""
        <p style="font-family:Inter,system-ui,sans-serif;font-size:1rem;
                  color:{ARDOISE};line-height:1.7;">
          <span style="font-family:'EB Garamond',Georgia,serif;font-size:{taille}px;
                       font-weight:700;color:{BLEU_NUIT};float:left;
                       line-height:0.8;margin-right:0.15em;margin-top:0.1em;">
            {premiere}
          </span>{reste}
        </p>
        """,
        unsafe_allow_html=True,
    )
