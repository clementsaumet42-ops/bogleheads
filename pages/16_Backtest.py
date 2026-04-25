"""Page Streamlit — Backtest Historique (Sprint S9)."""
from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Backtest Historique",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Backtest Historique — Portefeuilles Bogle")
st.markdown(
    "Simulation historique mensuelle des portefeuilles Boglehead sur données réelles EUR (2003–2024)."
)

# ─── Imports avec gestion erreur ─────────────────────────────────────────────

try:
    from src.backtest.comparaison import comparer_4_niveaux
    from src.backtest.portefeuilles_bogle import PORTEFEUILLES_DISPONIBLES
    from src.schemas import charger_et_valider

    _backtest_ok = True
except Exception as e:
    _backtest_ok = False
    st.error(f"Module backtest indisponible : {e}")

# ─── Sidebar paramètres ───────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Paramètres")

    if _backtest_ok:
        try:
            cfg = charger_et_valider("backtest.yaml")
            capital_defaut = int(cfg.backtest.capital_initial_eur)
            date_debut_defaut = cfg.backtest.date_debut
            date_fin_defaut = cfg.backtest.date_fin
        except Exception:
            capital_defaut = 100_000
            date_debut_defaut = "2003-01-31"
            date_fin_defaut = "2024-12-31"

        capital = st.number_input(
            "Capital initial (€)", min_value=1_000, max_value=10_000_000,
            value=capital_defaut, step=10_000,
        )
        date_debut = st.text_input("Date début (YYYY-MM-DD)", value=date_debut_defaut)
        date_fin = st.text_input("Date fin (YYYY-MM-DD)", value=date_fin_defaut)

        portefeuille_choisi = st.selectbox(
            "Portefeuille",
            list(PORTEFEUILLES_DISPONIBLES.keys()),
            format_func=lambda k: PORTEFEUILLES_DISPONIBLES[k].description[:60] + "…",
        )

        mode_affichage = st.radio(
            "Mode de comparaison",
            ["Tous les 4 modes", "Brut uniquement", "Net optimisé uniquement"],
        )

        lancer = st.button("🚀 Lancer le backtest", use_container_width=True)

# ─── Corps principal ──────────────────────────────────────────────────────────

if not _backtest_ok:
    st.info("Veuillez corriger les erreurs d'import pour utiliser le backtest.")
    st.stop()

if not lancer:
    st.info(
        "👈 Configurez les paramètres dans la barre latérale puis cliquez sur **Lancer le backtest**."
    )

    # Afficher la liste des portefeuilles disponibles
    st.subheader("Portefeuilles disponibles")
    for nom, pf in PORTEFEUILLES_DISPONIBLES.items():
        with st.expander(f"**{nom}**"):
            st.write(f"📝 {pf.description}")
            st.write(f"📚 Source : {pf.source}")
            alloc_data = {k: f"{v*100:.1f}%" for k, v in pf.allocations.items()}
            st.table(alloc_data)
    st.stop()

# ─── Exécution backtest ───────────────────────────────────────────────────────

portefeuille = PORTEFEUILLES_DISPONIBLES[portefeuille_choisi]

config_backtest = {
    "capital_initial_eur": capital,
    "date_debut": date_debut,
    "date_fin": date_fin,
    "frais": {},
    "fiscalite": {},
}

with st.spinner("Calcul en cours…"):
    try:
        rapport = comparer_4_niveaux(
            portefeuille=portefeuille,
            config_backtest=config_backtest,
        )
    except Exception as e:
        st.error(f"Erreur lors du backtest : {e}")
        st.stop()

# ─── Affichage résultats ──────────────────────────────────────────────────────

st.success(f"✅ Backtest terminé — **{portefeuille_choisi}**")

# Métriques clés en colonnes
modes_labels = {
    "brut": "📊 Brut",
    "net_frais": "💸 Net Frais",
    "net_fiscal_cto": "🏛️ Net Fiscal CTO",
    "net_optimise": "✨ Net Optimisé",
}

cols = st.columns(4)
for i, (mode, label) in enumerate(modes_labels.items()):
    res = rapport.resultats[mode]
    with cols[i]:
        st.metric(
            label=label,
            value=f"{res.capital_final:,.0f} €",
            delta=f"CAGR {res.cagr*100:.2f}%",
        )

st.divider()

# Tableau comparatif détaillé
st.subheader("📋 Tableau comparatif")
import pandas as pd

rows = []
for mode, res in rapport.resultats.items():
    rows.append(
        {
            "Mode": modes_labels.get(mode, mode),
            "Capital final (€)": f"{res.capital_final:,.0f}",
            "CAGR": f"{res.cagr*100:.2f}%",
            "Volatilité ann.": f"{res.volatilite_annuelle*100:.2f}%",
            "Sharpe": f"{res.sharpe:.2f}",
            "Max Drawdown": f"{res.max_drawdown*100:.2f}%",
            "Sortino": f"{res.sortino:.2f}",
            "Frais totaux (€)": f"{res.frais_totaux_eur:,.0f}",
            "Fiscalité (€)": f"{res.fiscalite_totale_eur:,.0f}",
        }
    )
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# Deltas
st.subheader("📉 Impact des frais et de la fiscalité")
col1, col2, col3 = st.columns(3)
col1.metric("Impact frais (bps/an)", f"{rapport.delta_frais_bps:.1f} bps")
col2.metric("Impact fiscal CTO (bps/an)", f"{rapport.delta_fiscal_bps:.1f} bps")
col3.metric("Gain optimisation fiscale (bps/an)", f"{rapport.delta_optimise_bps:.1f} bps")

# Graphique évolution du portefeuille
st.subheader("📈 Évolution de la valeur du portefeuille")
try:
    import plotly.graph_objects as go

    fig = go.Figure()
    couleurs = {
        "brut": "#1a4d8f",
        "net_frais": "#d4a017",
        "net_fiscal_cto": "#e05c4a",
        "net_optimise": "#2ecc71",
    }
    for mode, res in rapport.resultats.items():
        if res.serie_valeur_mensuelle:
            dates = [d for d, _ in res.serie_valeur_mensuelle]
            vals = [v for _, v in res.serie_valeur_mensuelle]
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=vals,
                    mode="lines",
                    name=modes_labels.get(mode, mode),
                    line=dict(color=couleurs.get(mode, "#333"), width=2),
                )
            )
    fig.update_layout(
        title=f"Backtest — {portefeuille_choisi}",
        xaxis_title="Date",
        yaxis_title="Valeur (€)",
        hovermode="x unified",
        height=450,
    )
    st.plotly_chart(fig, use_container_width=True)
except ImportError:
    st.info("Installer plotly pour afficher le graphique interactif.")

# Détail annuel
with st.expander("📅 Détail annuel (mode brut)"):
    brut_detail = rapport.resultats["brut"].detail_annuel
    if brut_detail:
        df_annuel = pd.DataFrame(brut_detail)
        df_annuel["rendement"] = df_annuel["rendement"].map(lambda x: f"{x*100:.2f}%")
        df_annuel["capital_debut"] = df_annuel["capital_debut"].map(lambda x: f"{x:,.0f} €")
        df_annuel["capital_fin"] = df_annuel["capital_fin"].map(lambda x: f"{x:,.0f} €")
        st.dataframe(df_annuel, use_container_width=True, hide_index=True)

st.caption(
    "⚠️ Les données utilisées sont synthétiques à des fins de démonstration. "
    "Les performances passées ne préjugent pas des performances futures. "
    "Cet outil ne constitue pas un conseil en investissement."
)
