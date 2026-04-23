"""Page 1 — Accueil : présentation de l'outil et KPIs."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
import yaml

st.title("🏦 Boglehead FR — Outil CGP Multi-Enveloppes")
st.markdown(
    """
Bienvenue dans l'outil **Boglehead FR** pour conseillers en gestion de patrimoine.

Construisez une stratégie d'investissement Boglehead complète pour vos clients :
allocation cible optimisée, asset location fiscale, projection Monte-Carlo et plan de rebalancement.
"""
)

# ─── KPIs ─────────────────────────────────────────────────────────────────────

_ROOT = Path(__file__).parent.parent


@st.cache_data(ttl=3600)
def _charger_kpis() -> tuple[int, int, int]:
    """Charge les KPIs de la page d'accueil depuis les fichiers YAML."""
    nb_profils = 0
    nb_enveloppes = 0
    nb_etfs = 0

    try:
        profils_path = _ROOT / "config" / "profils_clients.yaml"
        data = yaml.safe_load(profils_path.read_text(encoding="utf-8"))
        nb_profils = len(data.get("profils", []))
    except Exception:
        pass

    try:
        enveloppes_path = _ROOT / "config" / "enveloppes.yaml"
        data = yaml.safe_load(enveloppes_path.read_text(encoding="utf-8"))
        nb_enveloppes = len(data.get("enveloppes", []))
    except Exception:
        pass

    try:
        etfs_path = _ROOT / "config" / "univers_etf.yaml"
        data = yaml.safe_load(etfs_path.read_text(encoding="utf-8"))
        nb_etfs = len(data.get("univers_etf", []))
    except Exception:
        pass

    return nb_profils, nb_enveloppes, nb_etfs


nb_profils, nb_enveloppes, nb_etfs = _charger_kpis()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("👤 Profils types", nb_profils, help="Profils clients fictifs pré-configurés")
with col2:
    st.metric(
        "🏦 Enveloppes fiscales", nb_enveloppes, help="PEA, PER, AV, CTO, PEE, Contrat Cap IS"
    )
with col3:
    st.metric("📊 ETF disponibles", nb_etfs, help="ETF passifs Boglehead validés")

st.divider()

# ─── Présentation des modules ──────────────────────────────────────────────────

st.subheader("🗺️ Fonctionnalités de l'outil")

col_a, col_b = st.columns(2)
with col_a:
    st.markdown(
        """
**👤 Profil client**
Saisissez les caractéristiques de votre client (âge, patrimoine, TMI, enveloppes)
ou chargez un profil type YAML. Validation Pydantic en temps réel.

**🎯 Allocation cible**
Calcul de l'allocation optimale via Markowitz (scipy QP) calibré sur le profil de risque.
Ajustez les contraintes (exposition USA, marchés émergents) et recalculez en live.

**🏦 Asset Location**
Ventilation optimale des classes d'actifs par enveloppe fiscale (MILP PuLP).
Heatmap interactive et comparaison du coût annuel optimisé vs naïf.
"""
    )
with col_b:
    st.markdown(
        """
**📈 Projection Monte-Carlo**
Simulation de 10 000 trajectoires sur 5 à 40 ans avec votre allocation cible.
Fan chart P10/médiane/P90 et probabilité d'atteindre votre objectif patrimonial.

**🔄 Rebalancement**
Plan de rebalancement en 3 étapes fiscalement optimisé :
arbitrages gratuits → flux → ventes ordonnées.

**📥 Téléchargements**
Générez le rapport Excel complet (22 onglets) et le PDF client (13 pages)
directement depuis l'interface — aucune ligne de commande.
"""
    )

st.divider()

# ─── Call-to-action ───────────────────────────────────────────────────────────

st.subheader("🚀 Commencer")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.info(
        "👈 Utilisez la navigation à gauche ou cliquez ci-dessous "
        "pour charger votre premier profil client."
    )
    if st.button("👤 Charger un profil client", type="primary", use_container_width=True):
        st.switch_page("pages/2_👤_Profil.py")

st.divider()
st.caption(
    "⚠️ *Les profils et simulations fournis sont illustratifs et ne constituent pas "
    "un conseil en investissement personnalisé au sens de la directive MIF II.*"
)
