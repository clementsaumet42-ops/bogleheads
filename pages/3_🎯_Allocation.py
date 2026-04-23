"""Page 3 — Allocation cible : résultat Markowitz + sliders contraintes."""

from __future__ import annotations

import streamlit as st

from src.ui.charts import camembert_allocation
from src.ui.formatters import format_euro, format_pct, format_ratio_sharpe

st.title("🎯 Allocation cible")

# ─── Vérification du profil ───────────────────────────────────────────────────

profil = st.session_state.get("profil_actif")
if not profil:
    st.warning("⚠️ Aucun profil chargé. Veuillez d'abord configurer un profil client.")
    if st.button("👤 Aller au profil client"):
        st.switch_page("pages/2_👤_Profil.py")
    st.stop()

nom = profil.get("nom", "—") if isinstance(profil, dict) else getattr(profil, "nom", "—")
st.markdown(f"**Profil actif :** {nom}")

# ─── Sliders contraintes ──────────────────────────────────────────────────────

st.subheader("⚙️ Contraintes personnalisées")
col1, col2, col3 = st.columns(3)

with col1:
    contraintes_raw = profil.get("contraintes_personnalisees") or {}
    usa_max_defaut = contraintes_raw.get("exposition_usa_max") or 0.5
    usa_max = st.slider(
        "Exposition USA max (%)",
        min_value=0,
        max_value=100,
        value=int(usa_max_defaut * 100),
        step=5,
        help="Poids maximum alloué aux actions américaines",
    )

with col2:
    em_max_defaut = contraintes_raw.get("exposition_em_max") or 0.20
    em_max = st.slider(
        "Exposition marchés émergents max (%)",
        min_value=0,
        max_value=50,
        value=int(em_max_defaut * 100),
        step=5,
        help="Poids maximum alloué aux marchés émergents",
    )

with col3:
    aversion_options = ["defensif", "equilibre", "dynamique", "agressif"]
    aversion_actuel = profil.get("profil_aversion_risque") or "equilibre"
    aversion_idx = (
        aversion_options.index(aversion_actuel) if aversion_actuel in aversion_options else 1
    )
    aversion = st.selectbox(
        "Profil d'aversion au risque",
        aversion_options,
        index=aversion_idx,
        help="Profil de risque retenu pour l'optimisation Markowitz",
    )

# ─── Calcul de l'allocation ───────────────────────────────────────────────────


@st.cache_data(ttl=3600)
def _calculer_allocation(
    profil_aversion: str,
    usa_max_pct: int,
    em_max_pct: int,
    age: int | None,
) -> dict:
    """Calcule l'allocation optimale via Markowitz."""
    from src.optimiseur_allocation import charger_config_optimiseur, optimiser_allocation_mode_a

    config = charger_config_optimiseur()
    contraintes = {
        "exposition_usa_max": usa_max_pct / 100,
        "exposition_em_max": em_max_pct / 100,
    }
    return optimiser_allocation_mode_a(
        profil_aversion=profil_aversion,
        config=config,
        contraintes=contraintes,
        age=age,
    )


age = profil.get("age") if isinstance(profil, dict) else getattr(profil, "age", None)

with st.spinner("⚙️ Calcul Markowitz en cours…"):
    resultat = _calculer_allocation(aversion, usa_max, em_max, age)

# ─── KPIs ─────────────────────────────────────────────────────────────────────

st.divider()
st.subheader("📊 Résultats de l'optimisation")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(
        "Rendement attendu",
        format_pct(resultat["rendement_attendu"]),
        help="Rendement annuel attendu du portefeuille",
    )
with col2:
    st.metric(
        "Volatilité annuelle",
        format_pct(resultat["volatilite_attendue"]),
        help="Écart-type annuel du portefeuille",
    )
with col3:
    st.metric(
        "Ratio de Sharpe",
        format_ratio_sharpe(resultat["ratio_sharpe"]),
        help="Rendement excédentaire par unité de risque",
    )
with col4:
    statut = resultat.get("statut", "—")
    st.metric("Statut", statut, help="Statut de la résolution : optimal ou fallback")

if resultat.get("message"):
    st.info(f"ℹ️ {resultat['message']}")

# ─── Graphiques ───────────────────────────────────────────────────────────────

poids = resultat["poids"]
poids_filtres = {k: v for k, v in poids.items() if v > 0.001}

col_left, col_right = st.columns([1, 1])

with col_left:
    fig = camembert_allocation(poids_filtres, titre="Répartition par classe d'actifs")
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Tableau des poids")
    import pandas as pd

    patrimoine_profil = profil.get("patrimoine_financier_total", 100_000) or 100_000
    df = pd.DataFrame(
        [
            {
                "Classe d'actifs": k,
                "Poids": format_pct(v),
                "Montant estimé (€)": format_euro(v * patrimoine_profil),
            }
            for k, v in sorted(poids_filtres.items(), key=lambda x: -x[1])
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)

# ─── Sauvegarde en session ────────────────────────────────────────────────────

# Stocker le résultat pour les pages suivantes
if st.session_state.get("resultat_optim") is None or st.button("🔄 Recalculer et sauvegarder"):
    st.session_state["resultat_optim"] = resultat
    profil_copy = dict(profil) if isinstance(profil, dict) else profil
    if isinstance(profil_copy, dict):
        profil_copy["profil_aversion_risque"] = aversion
        profil_copy["contraintes_personnalisees"] = {
            "exposition_usa_max": usa_max / 100,
            "exposition_em_max": em_max / 100,
        }
        st.session_state["profil_actif"] = profil_copy
    st.success("✅ Résultat sauvegardé en session.")

st.divider()
if st.button("🏦 Optimiser l'asset location →", type="primary"):
    st.switch_page("pages/4_🏦_Asset_Location.py")
