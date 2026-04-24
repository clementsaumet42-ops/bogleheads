"""
app.py — Point d'entrée Streamlit de la webapp Boglehead FR.

Lancement : streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

# ─── Configuration de la page ─────────────────────────────────────────────────

st.set_page_config(
    page_title="Boglehead FR — CGP Multi-Enveloppes",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Initialisation session_state ─────────────────────────────────────────────

_DEFAULTS: dict = {
    "profil_actif": None,
    "profil_source": None,
    "resultat_optim": None,
    "resultat_mc": None,
    "pdf_bytes": None,
    "excel_bytes": None,
}

for _key, _val in _DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _val

# ─── Navigation multi-pages ───────────────────────────────────────────────────

_pages = {
    "🏠 Accueil": "pages/01_Accueil.py",
    "👤 Profil client": "pages/02_Profil.py",
    "🎯 Allocation cible": "pages/03_Allocation.py",
    "🏦 Asset Location": "pages/04_Asset_Location.py",
    "📈 Projection Monte-Carlo": "pages/05_Monte_Carlo.py",
    "🔄 Rebalancement": "pages/06_Rebalancement.py",
    "📥 Téléchargements": "pages/07_Exports.py",
}

# ─── Sidebar commune ──────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🏦 Boglehead FR")

    profil = st.session_state.get("profil_actif")
    if profil:
        nom = profil.get("nom", "—") if isinstance(profil, dict) else getattr(profil, "nom", "—")
        st.success(f"**Profil actif :** {nom}")
    else:
        st.info("Aucun profil chargé")

    if st.button("🔄 Réinitialiser", use_container_width=True):
        for key in _DEFAULTS:
            st.session_state[key] = _DEFAULTS[key]
        st.rerun()

    st.divider()
    _root = Path(__file__).parent
    _pyproject = _root / "pyproject.toml"
    _version = "0.8.0"
    if _pyproject.exists():
        for line in _pyproject.read_text(encoding="utf-8").splitlines():
            if line.startswith("version"):
                _version = line.split("=")[1].strip().strip('"')
                break
    st.caption(f"v{_version} — Boglehead FR")

# ─── Page d'accueil inline (si aucune page sélectionnée) ─────────────────────

# Streamlit affiche automatiquement la page active via le dossier pages/.
# Ce fichier sert uniquement de point d'entrée et de sidebar commune.
# La vraie page d'accueil est pages/01_Accueil.py.

# Redirection vers la page d'accueil si l'utilisateur arrive sur app.py directement
# (comportement natif Streamlit : affiche la première page du dossier pages/)
