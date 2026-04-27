"""Composants Streamlit réutilisables pour les explications pédagogiques.

Ces helpers sont non-intrusifs : ils s'ajoutent aux pages existantes sans
modifier la logique métier.

Palettes cabinet : navy #1B3A5B / ivoire #F5F3EE / serif (cohérence avec cards.py).
"""

from __future__ import annotations

from src.pedagogie.base import Explication


def expander_explication(explication: Explication, icone: str = "") -> None:
    """Affiche un st.expander avec titre court, contenu long et source en pied.

    Args:
        explication: Objet Explication à afficher.
        icone: Préfixe optionnel du titre (défaut : vide).
    """
    import streamlit as st

    label = f"{icone} {explication.titre}".strip() if icone else explication.titre
    with st.expander(label):
        st.markdown(explication.texte_long)

        if explication.formule:
            st.markdown(f"**Formule :** `{explication.formule}`")

        if explication.alternative_ecartee:
            st.markdown(
                f"<div style='"
                f"background:#FAF7F2;"
                f"border-left:3px solid #8B6F47;"
                f"padding:8px 12px;"
                f"border-radius:0 4px 4px 0;"
                f"font-size:0.9rem;"
                f"color:#5A5A5A;"
                f"margin-top:8px;"
                f"'>"
                f"<strong>Alternative écartée :</strong> {explication.alternative_ecartee}"
                f"</div>",
                unsafe_allow_html=True,
            )

        if explication.gain_eur is not None:
            gain_str = f"{explication.gain_eur:+,.0f} €"
            couleur = "#2D4A3E" if explication.gain_eur >= 0 else "#6B1E2C"
            st.markdown(
                f"<div style='"
                f"font-size:0.85rem;"
                f"color:{couleur};"
                f"margin-top:6px;"
                f"'>"
                f"<strong>Impact chiffré :</strong> {gain_str}"
                f"</div>",
                unsafe_allow_html=True,
            )

        if explication.source:
            st.markdown(badge_source(explication.source))


def bloc_script_restitution(
    script_texte: str,
    titre: str = "Ce que vous dites au client",
) -> None:
    """Encadré distinctif avec script type prêt à lire pour l'EC/CIF.

    Style : bordure bleu nuit, fond ivoire, typo serif cabinet.

    Args:
        script_texte: Texte du script (déjà rendu via rendre_script()).
        titre: Titre de l'encadré (défaut : "Ce que vous dites au client").
    """
    import html as html_module

    import streamlit as st

    texte_safe = html_module.escape(script_texte).replace("\n", "<br>")

    st.markdown(
        f"""
<div style="
    background: #F5F3EE;
    border: 2px solid #1B3A5B;
    border-radius: 8px;
    padding: 20px 24px;
    margin: 12px 0;
    box-shadow: 0 2px 8px rgba(27,58,91,0.10);
">
    <div style="
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: #1B3A5B;
        margin-bottom: 12px;
        border-bottom: 1px solid #1B3A5B33;
        padding-bottom: 6px;
    ">{titre}</div>
    <div style="
        font-family: 'Cormorant Garamond', Georgia, serif;
        font-size: 15px;
        line-height: 1.7;
        color: #2C2C2C;
    ">{texte_safe}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def tableau_alternatives(explications: list[Explication]) -> None:
    """Tableau 2 colonnes : Choix retenu | Alternative écartée, avec raison.

    Affiche uniquement les Explication ayant un champ alternative_ecartee renseigné.

    Args:
        explications: Liste d'Explication (filtrée automatiquement).
    """
    import streamlit as st

    with_alt = [e for e in explications if e.alternative_ecartee]

    if not with_alt:
        st.info("Aucune alternative écartée documentée pour cette section.")
        return

    import pandas as pd

    df = pd.DataFrame(
        [
            {
                "Choix retenu": e.titre,
                "Alternative écartée": e.alternative_ecartee or "—",
            }
            for e in with_alt
        ]
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Choix retenu": st.column_config.TextColumn(
                "Choix retenu",
                width="medium",
            ),
            "Alternative écartée": st.column_config.TextColumn(
                "Alternative écartée",
                width="large",
            ),
        },
    )


def badge_source(source: str) -> str:
    """Retourne un badge HTML 'Source : ...' pour fin de section.

    Args:
        source: Référence académique ou réglementaire.

    Returns:
        Chaîne HTML formatée.
    """
    return (
        f"<div style='"
        f"font-size:0.78rem;"
        f"color:#888;"
        f"margin-top:8px;"
        f"border-top:1px solid #E8E0D5;"
        f"padding-top:6px;"
        f"'><em>Source : {source}</em></div>"
    )
