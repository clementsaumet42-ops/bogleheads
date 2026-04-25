"""Page 5 — Projection Monte-Carlo : fan chart P10/médiane/P90."""

from __future__ import annotations

import streamlit as st

from src.ui.charts import fan_chart_mc
from src.ui.formatters import format_euro, format_pct

st.title("📈 Projection Monte-Carlo")

# ─── Vérification du profil ───────────────────────────────────────────────────

profil = st.session_state.get("profil_actif")
if not profil:
    st.warning("⚠️ Aucun profil chargé. Veuillez d'abord configurer un profil client.")
    if st.button("👤 Aller au profil client"):
        st.switch_page("pages/04_Profil.py")
    st.stop()

nom = profil.get("nom", "—") if isinstance(profil, dict) else getattr(profil, "nom", "—")
st.markdown(f"**Profil actif :** {nom}")

# ─── Paramètres de simulation ─────────────────────────────────────────────────

st.subheader("⚙️ Paramètres de simulation")
col1, col2, col3 = st.columns(3)

profil_dict = dict(profil) if isinstance(profil, dict) else {}
capital_defaut = int(profil_dict.get("patrimoine_financier_total", 100_000) or 100_000)
versement_defaut = int(profil_dict.get("capacite_epargne_annuelle", 12_000) or 12_000)
horizon_defaut = min(int(profil_dict.get("horizon_placement_ans", 20) or 20), 40)

with col1:
    capital = st.number_input(
        "Capital initial (€)",
        min_value=0,
        value=capital_defaut,
        step=10_000,
        help="Patrimoine financier de départ",
    )
    horizon = st.slider(
        "Horizon (ans)",
        min_value=5,
        max_value=40,
        value=horizon_defaut,
        step=1,
    )

with col2:
    versement_mensuel = st.number_input(
        "Versement mensuel (€)",
        min_value=0,
        value=versement_defaut // 12,
        step=100,
        help="Versement mensuel régulier (converti en versement annuel pour la simulation)",
    )
    objectif = st.number_input(
        "Objectif patrimonial (€)",
        min_value=0,
        value=int(capital_defaut * 2),
        step=50_000,
        help="Objectif de capital à atteindre (optionnel — 0 pour désactiver)",
    )

with col3:
    nb_simulations = st.select_slider(
        "Nombre de simulations",
        options=[1_000, 2_000, 5_000, 10_000],
        value=5_000,
    )

# ─── Allocation pour la simulation ────────────────────────────────────────────

resultat_optim = st.session_state.get("resultat_optim")
alloc_cible: dict[str, float] = {}
if resultat_optim and resultat_optim.get("allocation_cible"):
    alloc_cible = resultat_optim["allocation_cible"]
else:
    # Fallback : allocation Boglehead du profil
    alloc_boglehead = profil_dict.get("allocation_cible_bogleheads") or {}
    if isinstance(alloc_boglehead, dict):
        alloc_cible = {
            "actions_monde": alloc_boglehead.get("actions", 0.6),
            "obligations": alloc_boglehead.get("obligations", 0.3),
            "or_": alloc_boglehead.get("or", alloc_boglehead.get("or_", 0.05)),
            "monetaire": alloc_boglehead.get("liquidites", 0.05),
        }

# ─── Calcul Monte-Carlo ───────────────────────────────────────────────────────


@st.cache_data(ttl=3600)
def _projeter(
    capital: float,
    versement_annuel: float,
    horizon: int,
    alloc: dict,
    nb_tirages: int,
    objectif_capital: float | None,
) -> dict:
    """Lance la simulation Monte-Carlo via src.projection."""
    from src.projection import AllocationClasses, ParametresProjection, simuler_monte_carlo

    alloc_obj = AllocationClasses(
        actions_monde=alloc.get("actions_monde", alloc.get("actions", 0.6)),
        actions_usa=alloc.get("actions_usa", 0.0),
        actions_europe=alloc.get("actions_europe", 0.0),
        actions_emergents=alloc.get("actions_em", alloc.get("actions_emergents", 0.0)),
        obligations=alloc.get("obligations", 0.2),
        monetaire=alloc.get("monetaire", 0.0),
        or_=alloc.get("or_matieres", alloc.get("or_", alloc.get("or", 0.05))),
        immobilier=alloc.get("reit", alloc.get("immobilier", 0.0)),
        matieres_premieres=alloc.get("matieres_premieres", 0.0),
    )
    params = ParametresProjection(
        capital_initial=capital,
        versement_annuel=versement_annuel,
        horizon_annees=horizon,
        allocation=alloc_obj,
        nb_tirages=nb_tirages,
        seed=42,
        objectif_capital=objectif_capital if objectif_capital and objectif_capital > 0 else None,
    )
    res = simuler_monte_carlo(params)
    return {
        "p10": res.capital_p10_par_annee.tolist(),
        "mediane": res.capital_median_par_annee.tolist(),
        "p90": res.capital_p90_par_annee.tolist(),
        "capital_final_percentiles": res.capital_final_percentiles,
        "probabilite_objectif": res.probabilite_objectif,
        "annee_mediane_atteinte": res.annee_mediane_atteinte_objectif,
    }


versement_annuel = versement_mensuel * 12
objectif_val = objectif if objectif and objectif > 0 else None

with st.spinner("⚙️ Simulation Monte-Carlo en cours…"):
    try:
        resultats_mc = _projeter(
            float(capital),
            float(versement_annuel),
            int(horizon),
            alloc_cible,
            nb_simulations,
            objectif_val,
        )
        st.session_state["resultat_mc"] = resultats_mc
    except Exception as exc:
        st.error(f"❌ Erreur lors de la simulation : {exc}")
        st.stop()

# ─── KPIs résultats ───────────────────────────────────────────────────────────

st.divider()
st.subheader("📊 Résultats de la simulation")

perc = resultats_mc["capital_final_percentiles"]
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Capital médian final", format_euro(perc.get(50, 0)))
with col2:
    st.metric("P10 (scénario bas)", format_euro(perc.get(10, 0)))
with col3:
    st.metric("P90 (scénario haut)", format_euro(perc.get(90, 0)))
with col4:
    prob = resultats_mc.get("probabilite_objectif")
    if prob is not None:
        st.metric(
            "Probabilité d'atteindre l'objectif",
            format_pct(prob),
            help=f"Probabilité d'atteindre {format_euro(objectif_val or 0)} sur {horizon} ans",
        )
    else:
        st.metric("Objectif", "Non défini", help="Saisissez un objectif patrimonial ci-dessus")

annee_med = resultats_mc.get("annee_mediane_atteinte")
if annee_med is not None:
    st.success(f"🎯 La médiane atteint l'objectif à **l'année {annee_med}**.")

# ─── Fan chart ────────────────────────────────────────────────────────────────

annees = list(range(horizon + 1))
fig = fan_chart_mc(
    annees=annees,
    p10=resultats_mc["p10"],
    mediane=resultats_mc["mediane"],
    p90=resultats_mc["p90"],
    objectif=objectif_val,
    titre=f"Projection Monte-Carlo — {nb_simulations:,} simulations, {horizon} ans",
)
st.plotly_chart(fig, use_container_width=True)

st.caption(
    "📌 *Simulation basée sur des rendements historiques calibrés. "
    "Les performances passées ne préjugent pas des performances futures.*"
)

st.divider()
col1, col2 = st.columns(2)
with col1:
    if st.button("🏦 ← Asset Location", use_container_width=True):
        st.switch_page("pages/07_Asset_Location.py")
with col2:
    if st.button("🔄 Rebalancement →", type="primary", use_container_width=True):
        st.switch_page("pages/09_Rebalancement.py")
