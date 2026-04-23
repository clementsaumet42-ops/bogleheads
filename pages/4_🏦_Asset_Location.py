"""Page 4 — Asset Location : heatmap Plotly classes × enveloppes."""

from __future__ import annotations

import streamlit as st

from src.ui.charts import heatmap_asset_location
from src.ui.formatters import format_euro, format_pct

st.title("🏦 Asset Location")

# ─── Vérification du profil ───────────────────────────────────────────────────

profil = st.session_state.get("profil_actif")
if not profil:
    st.warning("⚠️ Aucun profil chargé. Veuillez d'abord configurer un profil client.")
    if st.button("👤 Aller au profil client"):
        st.switch_page("pages/2_👤_Profil.py")
    st.stop()

nom = profil.get("nom", "—") if isinstance(profil, dict) else getattr(profil, "nom", "—")
st.markdown(f"**Profil actif :** {nom}")

# ─── Calcul de l'optimisation complète ───────────────────────────────────────


@st.cache_data(ttl=3600)
def _optimiser(profil_dict: dict) -> dict:
    """Lance l'optimisation complète Mode A + Mode B."""
    from src.optimiseur_allocation import optimiser_portefeuille_complet

    return optimiser_portefeuille_complet(profil_dict)


profil_dict = dict(profil) if isinstance(profil, dict) else profil.model_dump(by_alias=True)

# Récupérer depuis session ou recalculer
if st.session_state.get("resultat_optim") and st.session_state["resultat_optim"].get(
    "resultat_mode_b"
):
    resultat_complet = st.session_state["resultat_optim"]
else:
    with st.spinner("⚙️ Optimisation asset location MILP en cours…"):
        try:
            resultat_complet = _optimiser(profil_dict)
            st.session_state["resultat_optim"] = resultat_complet
        except Exception as exc:
            st.error(f"❌ Erreur lors de l'optimisation : {exc}")
            st.stop()

res_a = resultat_complet.get("resultat_mode_a", {})
res_b = resultat_complet.get("resultat_mode_b", {})

# ─── KPIs comparaison coût ────────────────────────────────────────────────────

st.subheader("💰 Comparaison des coûts annuels")
col1, col2, col3 = st.columns(3)

cout_opt = res_b.get("cout_annuel_optimise", 0)
cout_naif = res_b.get("cout_annuel_naif", 0)
economie = res_b.get("economie_annuelle", 0)

with col1:
    st.metric(
        "Coût optimisé",
        format_euro(cout_opt),
        help="Coût annuel total (TER + frais gestion) avec l'asset location optimisée",
    )
with col2:
    st.metric(
        "Coût naïf (AV gestion pilotée)",
        format_euro(cout_naif),
        help="Coût annuel si tout était placé en AV gestion pilotée (~2,3% tout compris)",
    )
with col3:
    delta_pct = f"-{format_pct(economie / cout_naif)}" if cout_naif > 0 else None
    st.metric(
        "Économie annuelle",
        format_euro(economie),
        delta=delta_pct,
        delta_color="inverse",
        help="Économie réalisée grâce à l'optimisation de l'asset location",
    )

statut_b = res_b.get("statut", "—")
msg_b = res_b.get("message")
if statut_b:
    if statut_b == "optimal":
        st.success(f"✅ Statut : {statut_b}")
    else:
        st.info(f"ℹ️ Statut : {statut_b}" + (f" — {msg_b}" if msg_b else ""))

# ─── Heatmap ─────────────────────────────────────────────────────────────────

st.divider()
st.subheader("🗺️ Ventilation par classe × enveloppe")

ventilation = res_b.get("ventilation", [])
if ventilation:
    fig = heatmap_asset_location(ventilation)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Aucune ventilation calculée (enveloppes non configurées ou patrimoine nul).")

# ─── Tableau détaillé ─────────────────────────────────────────────────────────

if ventilation:
    st.subheader("📋 Tableau détaillé de la ventilation")
    import pandas as pd

    patrimoine = profil_dict.get("patrimoine_financier_total", 100_000) or 100_000
    df = pd.DataFrame(ventilation)
    if not df.empty:
        df["poids"] = df["montant"] / patrimoine
        df["Poids (%)"] = df["poids"].apply(format_pct)
        df["Montant (€)"] = df["montant"].apply(lambda x: format_euro(x))
        df = df[["classe", "enveloppe", "Poids (%)", "Montant (€)"]].rename(
            columns={"classe": "Classe d'actifs", "enveloppe": "Enveloppe"}
        )
        st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()
col1, col2 = st.columns(2)
with col1:
    if st.button("🎯 ← Allocation cible", use_container_width=True):
        st.switch_page("pages/3_🎯_Allocation.py")
with col2:
    if st.button("📈 Projection Monte-Carlo →", type="primary", use_container_width=True):
        st.switch_page("pages/5_📈_Monte_Carlo.py")
