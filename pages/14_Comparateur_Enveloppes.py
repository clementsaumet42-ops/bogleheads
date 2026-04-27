"""
Comparateur d'Enveloppes Fiscales — Boglehead FR
Compare PEA vs CTO vs AV vs PER sur un horizon donné
"""

import pandas as pd
import streamlit as st

from src.fiscalite import (
    avantage_pea_vs_cto,
    comparer_per_vs_cto,
)
from src.fiscalite.constantes import TAUX_PFU_TOTAL, TAUX_PS
from src.ui.theme import injecter_css

st.set_page_config(page_title="Comparateur Enveloppes", page_icon="🏛️", layout="wide")

injecter_css()

st.title("Comparateur d'Enveloppes Fiscales")
st.markdown(
    "Comparez la fiscalité de différentes enveloppes d'investissement sur un horizon donné."
)

# Paramètres
st.header("Paramètres de simulation")

col1, col2 = st.columns(2)

with col1:
    capital_initial = st.number_input("Capital initial (€)", value=100000, step=1000)
    rendement_annuel = (
        st.number_input("Rendement annuel (%)", value=6.0, step=0.1, min_value=0.0, max_value=20.0)
        / 100
    )
    horizon_ans = st.number_input("Horizon (années)", value=10, step=1, min_value=1, max_value=40)

with col2:
    tmi_actuel = st.selectbox(
        "TMI actuel", [0.0, 0.11, 0.30, 0.41, 0.45], index=2, key="tmi_actuel"
    )
    tmi_retraite = st.selectbox(
        "TMI à la retraite (pour PER)", [0.0, 0.11, 0.30, 0.41, 0.45], index=1, key="tmi_retraite"
    )
    duree_pea = st.number_input(
        "Durée détention PEA (années)", value=10, step=1, min_value=0, max_value=40
    )

# Calcul
if st.button("Comparer", type="primary"):
    # Calcul capital final et gains pour chaque enveloppe
    capital_final = capital_initial * ((1 + rendement_annuel) ** horizon_ans)
    gains = capital_final - capital_initial

    # CTO : référence (PFU 31.4%)
    impots_cto = gains * TAUX_PFU_TOTAL
    capital_net_cto = capital_final - impots_cto

    # PEA : dépend de la durée
    result_pea = avantage_pea_vs_cto(gains, duree_pea, tmi_actuel)
    capital_net_pea = capital_final - result_pea["impots_pea"]

    # AV : simplifié, assume >8 ans, < 150k, 7.5% IR + 18.6% PS
    taux_av = 0.075 + TAUX_PS  # 26.1%
    impots_av = gains * taux_av * 0.9  # Après abattement estimé
    capital_net_av = capital_final - impots_av

    # PER : avec déduction
    result_per = comparer_per_vs_cto(
        capital_initial, tmi_actuel, tmi_retraite, rendement_annuel, horizon_ans
    )
    capital_net_per = result_per["capital_per_net"]

    # Résultats
    st.success("Comparaison terminée")

    # Tableau comparatif
    st.subheader("Comparaison des enveloppes")

    df = pd.DataFrame(
        {
            "Enveloppe": ["CTO (PFU)", "PEA", "Assurance Vie", "PER"],
            "Capital final brut": [capital_final] * 4,
            "Impôts": [impots_cto, result_pea["impots_pea"], impots_av, 0],
            "Capital net": [
                capital_net_cto,
                capital_net_pea,
                capital_net_av,
                capital_net_per,
            ],
            "Taux effectif": [
                TAUX_PFU_TOTAL,
                result_pea["taux_effectif_pea"],
                taux_av * 0.9,
                (capital_final - capital_net_per) / gains if gains > 0 else 0,
            ],
            "Avantage vs CTO": [
                0,
                capital_net_pea - capital_net_cto,
                capital_net_av - capital_net_cto,
                capital_net_per - capital_net_cto,
            ],
        }
    )

    # Formater
    df["Capital final brut"] = df["Capital final brut"].apply(lambda x: f"{x:,.0f} €")
    df["Impôts"] = df["Impôts"].apply(lambda x: f"{x:,.0f} €")
    df["Capital net"] = df["Capital net"].apply(lambda x: f"{x:,.0f} €")
    df["Taux effectif"] = df["Taux effectif"].apply(lambda x: f"{x:.1%}")
    df["Avantage vs CTO"] = df["Avantage vs CTO"].apply(
        lambda x: f"+{x:,.0f} €" if x >= 0 else f"{x:,.0f} €"
    )

    st.dataframe(df, use_container_width=True, hide_index=True)

    # Graphique
    st.subheader("Visualisation")

    try:
        import plotly.graph_objects as go

        fig = go.Figure(
            data=[
                go.Bar(
                    name="Capital net",
                    x=["CTO", "PEA", "AV", "PER"],
                    y=[capital_net_cto, capital_net_pea, capital_net_av, capital_net_per],
                    marker_color=["#636EFA", "#EF553B", "#00CC96", "#AB63FA"],
                )
            ]
        )

        fig.update_layout(
            title="Capital net après impôts",
            xaxis_title="Enveloppe",
            yaxis_title="Capital net (€)",
            yaxis_tickformat=",",
            height=400,
        )

        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.info("Installer plotly pour visualiser le graphique : pip install plotly")

    # Insights
    st.subheader("Insights")

    # Meilleure enveloppe
    meilleure = df.loc[
        df["Capital net"]
        .str.replace("€", "")
        .str.replace(",", "")
        .str.replace("", "")
        .astype(float)
        .idxmax(),
        "Enveloppe",
    ]
    st.info(f"**Meilleure enveloppe** : {meilleure}")

    # PEA vs CTO
    if duree_pea >= 5:
        st.success(
            f"PEA > 5 ans : exonération IR, économie de **{result_pea['economie']:,.0f} €** vs CTO"
        )
    else:
        st.warning(
            f"PEA < 5 ans : pas d'avantage fiscal significatif vs CTO (durée actuelle : {duree_pea} ans)"
        )

    # PER
    if result_per["avantage_per"] > 0:
        st.success(
            f"PER avantageux : économie de **{result_per['avantage_per']:,.0f} €** vs CTO grâce à la déduction"
        )
    else:
        st.warning("PER moins avantageux si TMI retraite > TMI actuel")

# Footer
st.markdown("---")
st.caption(
    "Simulation simplifiée indicative. Hypothèses : AV >8 ans avec abattement, "
    "PER sortie en capital sur versements déduits. Consultez un CGP pour votre situation."
)
