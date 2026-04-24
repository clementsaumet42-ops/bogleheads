"""Page 3 — Allocation cible : résultat Markowitz + sliders contraintes."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
import yaml

from src.ui.cards import badge_statut, carte_kpi
from src.ui.charts import camembert_allocation
from src.ui.formatters import format_euro, format_pct, format_ratio_sharpe

# ─── Injection typographie premium ───────────────────────────────────────────

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Inter:wght@300;400;500&display=swap');
h1, h2, h3 { font-family: 'Cormorant Garamond', Georgia, serif !important; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("🎯 Allocation cible")

# ─── Vérification du profil ───────────────────────────────────────────────────

profil = st.session_state.get("profil_actif")
if not profil:
    st.warning("⚠️ Aucun profil chargé. Veuillez d'abord configurer un profil client.")
    if st.button("👤 Aller au profil client"):
        st.switch_page("pages/02_Profil.py")
    st.stop()

nom = profil.get("nom", "—") if isinstance(profil, dict) else getattr(profil, "nom", "—")
st.markdown(f"**Profil actif :** {nom}")

# ─── Toggle mode allocation ───────────────────────────────────────────────────

st.subheader("⚙️ Mode allocation")
mode_label = st.radio(
    "Mode allocation",
    options=["Simple (ACWI monde)", "Granulaire (US / Dev ex-US / EM)"],
    index=0,
    horizontal=True,
    help="Simple = 1 ligne monde MSCI ACWI capi-pondérée | Granulaire = 3 lignes régionales",
    label_visibility="collapsed",
)
mode = "simple" if mode_label == "Simple (ACWI monde)" else "granulaire"

# ─── Sliders contraintes ──────────────────────────────────────────────────────

st.subheader("⚙️ Contraintes personnalisées")
contraintes_raw = profil.get("contraintes_personnalisees") or {}

if mode == "granulaire":
    col1, col2, col3 = st.columns(3)
    with col1:
        usa_max_defaut = contraintes_raw.get("exposition_usa_max") or 0.5
        usa_max = st.slider(
            "Exposition USA max (%)",
            min_value=0,
            max_value=100,
            value=int(usa_max_defaut * 100),
            step=5,
            help="Poids maximum alloué aux actions américaines (mode granulaire uniquement)",
        )
    with col2:
        em_max_defaut = contraintes_raw.get("exposition_em_max") or 0.20
        em_max = st.slider(
            "Exposition marchés émergents max (%)",
            min_value=0,
            max_value=50,
            value=int(em_max_defaut * 100),
            step=5,
            help="Poids maximum alloué aux marchés émergents (mode granulaire uniquement)",
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
else:
    # Mode simple : pas de sliders USA/EM
    usa_max = 100  # non pertinent en mode simple
    em_max = 50  # non pertinent en mode simple
    col1, col2 = st.columns([1, 2])
    with col1:
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
    with col2:
        st.info(
            "ⓘ En mode Simple (ACWI), les contraintes régionales USA/EM ne sont pas applicables. "
            "L'allocation est dominée par un ETF monde unique capi-pondéré.",
            icon=None,
        )

# ─── Calcul de l'allocation ───────────────────────────────────────────────────


@st.cache_data(ttl=3600)
def _calculer_allocation(
    profil_aversion: str,
    usa_max_pct: int,
    em_max_pct: int,
    age: int | None,
    mode: str,
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
        mode=mode,
    )


age = profil.get("age") if isinstance(profil, dict) else getattr(profil, "age", None)

with st.spinner("⚙️ Calcul Markowitz en cours…"):
    resultat = _calculer_allocation(aversion, usa_max, em_max, age, mode)

poids = resultat["poids"]
statut = resultat.get("statut", "—")

# ─── Health Check ─────────────────────────────────────────────────────────────

st.divider()

from src.optimiseur_allocation import CLASSES_ACTIONS  # noqa: E402
from src.optimiseur_allocation import charger_config_optimiseur as _charger_cfg  # noqa: E402

_config_cached = _charger_cfg()
profil_ar = _config_cached.get("profils_aversion_risque", {}).get(aversion, {})
from src.ui.health_check import afficher_health_check  # noqa: E402

afficher_health_check(poids, profil_ar, statut, mode)

# ─── KPIs premium ─────────────────────────────────────────────────────────────

st.divider()
st.subheader("📊 Résultats de l'optimisation")

rendement_val = resultat["rendement_attendu"]
volatilite_val = resultat["volatilite_attendue"]
sharpe_val = resultat["ratio_sharpe"]

# Calcul du contexte comparatif
ref_av_pilotee = 0.045  # rendement net moyen AV gestion pilotée ~4.5%
ecart_rendt = rendement_val - ref_av_pilotee
ecart_vol_cac = 0.22  # volatilité historique CAC40
contexte_sharpe = (
    "Excellent (> 0,5)"
    if sharpe_val > 0.5
    else "Bon (> 0,3)"
    if sharpe_val > 0.3
    else "Satisfaisant (< 0,3)"
)

col1, col2, col3, col4 = st.columns(4)
with col1:
    ecart_str = f"+{ecart_rendt:.1%}" if ecart_rendt > 0 else f"{ecart_rendt:.1%}"
    st.markdown(
        carte_kpi(
            titre="Rendement attendu",
            valeur=format_pct(rendement_val),
            unite="par an",
            contexte=f"AV gestion pilotée : ~4,5 % — vous êtes {ecart_str}",
        ),
        unsafe_allow_html=True,
    )
with col2:
    ecart_vol = volatilite_val - ecart_vol_cac
    vol_ctx = f"CAC40 : ~22 % — {'–' if ecart_vol < 0 else '+'}{abs(ecart_vol):.1%}"
    st.markdown(
        carte_kpi(
            titre="Volatilité annuelle",
            valeur=format_pct(volatilite_val),
            unite="écart-type",
            contexte=vol_ctx,
            couleur_valeur="#2E5D4F",
        ),
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        carte_kpi(
            titre="Ratio de Sharpe",
            valeur=format_ratio_sharpe(sharpe_val),
            unite="rendement / risque",
            contexte=f"Évaluation : {contexte_sharpe}",
            couleur_valeur="#1B3A5B",
        ),
        unsafe_allow_html=True,
    )
with col4:
    st.markdown(
        badge_statut(statut),
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='margin-top:8px;font-size:0.85rem;color:#666;'>Résolution : {statut}</div>",
        unsafe_allow_html=True,
    )

if resultat.get("message"):
    st.info(f"ℹ️ {resultat['message']}")

# ─── Graphiques ───────────────────────────────────────────────────────────────

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

# ─── Comparatif AV gestion pilotée ────────────────────────────────────────────

st.divider()
st.subheader("📊 Comparaison avec l'AV gestion pilotée")

try:
    import plotly.graph_objects as go

    horizon = 20
    ter_av_pilotee = 0.023  # ~2.3% tout compris (UC + gestion)
    ter_conseille = sum(
        poids.get(c, 0.0)
        * _config_cached["classes_actifs"].get(c, {}).get("frais_ter_moyen", 0.001)
        for c in poids
    )
    rendement_net_av = ref_av_pilotee
    rendement_net_conseil = rendement_val - ter_conseille

    patrimoine = float(patrimoine_profil)
    capital_av = patrimoine * (1 + rendement_net_av) ** horizon
    capital_conseil = patrimoine * (1 + rendement_net_conseil) ** horizon
    gain_supplementaire = capital_conseil - capital_av

    fig_comp = go.Figure(
        go.Bar(
            x=["AV gestion pilotée", "Allocation recommandée"],
            y=[capital_av, capital_conseil],
            marker_color=["#A65A4E", "#2E5D4F"],
            text=[f"{capital_av:,.0f} €", f"{capital_conseil:,.0f} €"],
            textposition="outside",
            textfont={"size": 12},
        )
    )
    fig_comp.update_layout(
        title=f"Capital estimé sur {horizon} ans — patrimoine initial : {patrimoine:,.0f} €",
        yaxis_title="Capital (€)",
        height=380,
        margin={"l": 40, "r": 20, "t": 60, "b": 40},
        annotations=[
            {
                "x": 1,
                "y": capital_conseil * 0.5,
                "text": f"<b>+{gain_supplementaire:,.0f} €</b><br>gain supplémentaire",
                "showarrow": False,
                "font": {"color": "#B08D57", "size": 14},
            }
        ],
    )
    st.plotly_chart(fig_comp, use_container_width=True)
    st.caption(
        f"*AV gestion pilotée : rendement net supposé 4,5 %, TER ~2,3 %. "
        f"Allocation recommandée : TER estimé {ter_conseille:.2%}. "
        f"Projections illustratives — performances passées ne préjugent pas du futur.*"
    )
except Exception:
    pass

# ─── Expander "Pourquoi cette allocation ?" ────────────────────────────────────

with st.expander("💡 Pourquoi cette allocation ?"):
    profil_descriptions = {
        "defensif": "protection du capital, horizon court terme, faible tolérance au risque",
        "equilibre": "compromis rendement/risque, horizon moyen terme",
        "dynamique": "croissance long terme, tolérance au risque élevée",
        "agressif": "maximisation du rendement long terme, horizon > 15 ans",
    }
    st.markdown(f"**Profil retenu :** {aversion} — *{profil_descriptions.get(aversion, '')}*")

    total_actions = sum(poids.get(c, 0.0) for c in CLASSES_ACTIONS)
    st.markdown(f"**Exposition actions :** {total_actions:.1%} du portefeuille")

    if mode == "simple":
        st.markdown(
            """
**Pourquoi le mode ACWI (Simple) ?**
Une seule ligne monde — **MSCI ACWI / FTSE All-World** — réplique la capitalisation boursière mondiale
(~60 % US, ~28 % pays développés ex-US, ~12 % marchés émergents).
C'est l'approche recommandée par Vanguard et les Bogleheads orthodoxes :
*"Don't try to outguess the market's collective wisdom"*.
"""
        )
    else:
        st.markdown(
            """
**Pourquoi le mode Granulaire ?**
Décomposer l'exposition mondiale en 3 lignes (US / Dev ex-US / EM) permet d'appliquer des
contraintes régionales personnalisées (ex. réduction de l'exposition US ou des marchés émergents)
selon le profil ou les contraintes de l'investisseur.
"""
        )

    if age is not None:
        obligations_min_age = max(0.0, (age - 10) / 100.0)
        st.markdown(
            f"**Cohérence avec l'âge ({age} ans) :** la règle Boglehead suggère ~{obligations_min_age:.0%} "
            f"d'obligations (règle (âge − 10) / 100). "
            f"Cette contrainte de glide-path a été {'appliquée' if obligations_min_age > 0 else 'non active'} "
            f"dans l'optimisation."
        )

    actions_min_p = float(profil_ar.get("actions_min", 0.0))
    actions_max_p = float(profil_ar.get("actions_max", 1.0))
    st.markdown(
        f"**Contraintes actives :** bornes actions ∈ [{actions_min_p:.0%}, {actions_max_p:.0%}] "
        f"→ allocation actions = {total_actions:.1%}"
    )

# ─── Expander Hypothèses de calcul ─────────────────────────────────────────────

_ROOT_CFG = Path(__file__).parent.parent / "config" / "optimiseur.yaml"


@st.cache_data(ttl=86400)
def _charger_hypotheses() -> dict:
    try:
        data = yaml.safe_load(_ROOT_CFG.read_text(encoding="utf-8"))
        return data.get("hypotheses_meta", {})
    except Exception:
        return {}


with st.expander("ℹ️ Hypothèses de calcul et sources"):
    meta = _charger_hypotheses()
    if meta:
        st.markdown(f"**Base :** {meta.get('base', '—')}")
        st.markdown(
            f"**Inflation attendue :** {meta.get('inflation_attendue', 0.02):.1%} "
            f"(zone Euro long terme BCE)"
        )
        st.markdown(
            f"**Devise de référence :** {meta.get('devise_reference', 'EUR')} "
            f"| **Juridiction :** {meta.get('juridiction', 'France')}"
        )
        st.markdown(f"**Date de mise à jour :** {meta.get('date_maj', '—')}")
        sources = meta.get("sources", [])
        if sources:
            st.markdown("**Sources :**")
            for src in sources:
                st.markdown(f"- {src}")
        avert = meta.get("avertissement", "")
        if avert:
            st.warning(f"⚠️ {avert.strip()}")
    else:
        st.info("Métadonnées non disponibles.")

# ─── Explication pédagogique (S8.1 — preuve bout-en-bout) ────────────────────

st.divider()
st.subheader("🎓 Comprendre cette allocation")

try:
    from src.pedagogie import expliquer_allocation
    from src.pedagogie.scripts import rendre_script
    from src.ui.explications import bloc_script_restitution, expander_explication

    nom_client = nom if isinstance(nom, str) else "Client"
    contexte_ped = {
        "nom_client": nom_client,
        "profil": aversion,
        "patrimoine_total": str(patrimoine_profil),
    }

    explications_alloc = expliquer_allocation(
        poids=poids,
        profil=aversion,
        mode=mode,
        contexte=contexte_ped,
    )

    if explications_alloc:
        expander_explication(explications_alloc[0])

    # Script de restitution — première explication disponible selon le mode
    try:
        if mode == "simple":
            poids_acwi = poids.get("actions_monde", poids.get("actions", 0.0))
            script_cle = "allocation.mode_simple_acwi"
            script_vars = {
                "poids_acwi": poids_acwi,
                "ter": sum(
                    poids.get(c, 0.0)
                    * _config_cached["classes_actifs"].get(c, {}).get("frais_ter_moyen", 0.001)
                    for c in poids
                ),
                "profil_final": aversion,
            }
        else:
            poids_oblig = poids.get("obligations_monde", poids.get("obligations", 0.0))
            script_cle = "allocation.obligations"
            script_vars = {
                "poids_obligations": poids_oblig,
                "profil_final": aversion,
            }

        script_rendu = rendre_script(script_cle, script_vars)
        bloc_script_restitution(script_rendu)
    except Exception:
        pass

except Exception:
    pass

# ─── Sauvegarde en session ────────────────────────────────────────────────────

st.divider()
if st.session_state.get("resultat_optim") is None or st.button("🔄 Recalculer et sauvegarder"):
    st.session_state["resultat_optim"] = resultat
    profil_copy = dict(profil) if isinstance(profil, dict) else profil
    if isinstance(profil_copy, dict):
        profil_copy["profil_aversion_risque"] = aversion
        profil_copy["contraintes_personnalisees"] = {
            "exposition_usa_max": usa_max / 100,
            "exposition_em_max": em_max / 100,
        }
        profil_copy["mode_allocation"] = mode
        st.session_state["profil_actif"] = profil_copy
    st.success("✅ Résultat sauvegardé en session.")

if st.button("🏦 Optimiser l'asset location →", type="primary"):
    st.switch_page("pages/04_Asset_Location.py")
