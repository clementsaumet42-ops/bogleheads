"""Page 1 — Accueil premium : cabinet patrimonial Boglehead."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
import yaml

# ─── Injection typographie premium ───────────────────────────────────────────

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Inter:wght@300;400;500&display=swap');
h1, h2, h3 { font-family: 'Cormorant Garamond', Georgia, serif !important; }
p, div, span, label { font-family: 'Inter', sans-serif !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ─── Hero section ─────────────────────────────────────────────────────────────

st.markdown(
    """
<div style="text-align:center; padding: 40px 20px 20px 20px;">
    <h1 style="font-size:2.8rem; color:#1B3A5B; margin-bottom:8px;">
        Conseil patrimonial Boglehead
    </h1>
    <p style="font-size:1.15rem; color:#555555; font-style:italic; margin-bottom:24px;">
        Le conseil patrimonial Boglehead, adossé à l'expertise de votre cabinet.
    </p>
</div>
""",
    unsafe_allow_html=True,
)

# ─── Trois cartes services ─────────────────────────────────────────────────────

col1, col2, col3 = st.columns(3)

_carte_css = """
background: #F5F3EE;
border: 1px solid #B08D57;
border-radius: 10px;
padding: 28px 22px;
min-height: 170px;
"""

with col1:
    st.markdown(
        f"""
<div style="{_carte_css}">
    <div style="font-size:1.2rem; font-weight:600; color:#1B3A5B; font-family:'Cormorant Garamond',serif;">
        1. Profil client
    </div>
    <p style="color:#444444; margin-top:10px; font-size:0.9rem;">
        Saisissez les caractéristiques de votre client : âge, patrimoine, fiscalité,
        enveloppes disponibles. Validation Pydantic en temps réel.
    </p>
</div>
""",
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""
<div style="{_carte_css}">
    <div style="font-size:1.2rem; font-weight:600; color:#1B3A5B; font-family:'Cormorant Garamond',serif;">
        2. Allocation optimale
    </div>
    <p style="color:#444444; margin-top:10px; font-size:0.9rem;">
        Calcul Markowitz via ACWI 1 ligne ou granulaire US/Dev ex-US/EM.
        Invariants validés : somme = 100 %, aucune pondération > 100 %.
    </p>
</div>
""",
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""
<div style="{_carte_css}">
    <div style="font-size:1.2rem; font-weight:600; color:#1B3A5B; font-family:'Cormorant Garamond',serif;">
        3. Livrable conseil
    </div>
    <p style="color:#444444; margin-top:10px; font-size:0.9rem;">
        Rapport PDF client 13 pages, Excel 22 onglets, projection Monte-Carlo
        et plan de rebalancement fiscalement optimisé.
    </p>
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
st.divider()

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

# ─── Call-to-action ───────────────────────────────────────────────────────────

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.info(
        "👈 Utilisez la navigation à gauche ou cliquez ci-dessous "
        "pour charger votre premier profil client."
    )
    if st.button("👤 Charger un profil client", type="primary", use_container_width=True):
        st.switch_page("pages/02_Profil.py")

st.divider()
st.caption(
    "⚠️ *Les informations contenues dans cet outil sont à titre indicatif uniquement "
    "et ne constituent pas un conseil en investissement personnalisé au sens de la directive MIF II. "
    "Consultez toujours un conseiller qualifié avant toute décision d'investissement.*"
)
