"""Page 18 — Assureurs AV : CRUD avec dry-run diff."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.catalogue.crud import diff_yaml, lire_yaml, sauvegarder_yaml

st.set_page_config(page_title="Assureurs AV", page_icon="🛡️")
st.title("🛡️ Assureurs AV — Gestion des contrats")

st.info(
    "Gérez les contrats d'assurance-vie référencés. Backup automatique avant chaque sauvegarde."
)

_FILENAME = "contrats_av.yaml"
_KEY_LIST = "contrats_av"


@st.cache_data(ttl=30)
def _charger() -> dict:
    try:
        return lire_yaml(_FILENAME)
    except Exception as exc:
        st.error(f"Erreur chargement : {exc}")
        return {_KEY_LIST: []}


data = _charger()
contrats: list[dict] = data.get(_KEY_LIST, [])

# ─── Tableau lecture ───────────────────────────────────────────────────────────

st.subheader(f"📊 {len(contrats)} contrats AV dans le catalogue")

if contrats:
    cols = [
        "id",
        "nom",
        "assureur",
        "frais_gestion_uc_pct",
        "frais_entree_pct",
        "nb_etf",
        "fonds_euros_disponible",
        "versement_minimum_eur",
    ]
    df = pd.DataFrame([{c: c_.get(c, "") for c in cols} for c_ in contrats])
    st.dataframe(df, use_container_width=True, height=250)

# ─── Formulaire ───────────────────────────────────────────────────────────────

st.subheader("➕ Ajouter / Modifier un contrat AV")

with st.form("form_av"):
    c_id = st.text_input("ID (slug, ex: linxea_spirit) *")
    c_nom = st.text_input("Nom *")
    assureur = st.text_input("Assureur *")
    distributeur = st.text_input("Distributeur")
    frais_uc = st.number_input(
        "Frais gestion UC (%)", min_value=0.0, max_value=5.0, step=0.001, format="%.3f"
    )
    frais_fe = st.number_input(
        "Frais gestion fonds euros (%)", min_value=0.0, max_value=5.0, step=0.001, format="%.3f"
    )
    frais_entree = st.number_input(
        "Frais d'entrée (%)", min_value=0.0, max_value=10.0, step=0.001, format="%.3f"
    )
    frais_arb = st.number_input(
        "Frais d'arbitrage (%)", min_value=0.0, max_value=5.0, step=0.001, format="%.3f"
    )
    nb_uc = st.number_input("Nombre total d'UC", min_value=0, step=1)
    nb_etf = st.number_input("Nombre d'ETF", min_value=0, step=1)
    fonds_euros = st.checkbox("Fonds euros disponible", value=True)
    rendement_fe = st.number_input(
        "Rendement fonds euros 2024 (%)", min_value=0.0, max_value=20.0, step=0.01, format="%.2f"
    )
    versement_min = st.number_input("Versement minimum (€)", min_value=0.0, step=10.0)
    annees = st.number_input("Années d'existence", min_value=0, step=1)
    sources = st.text_area("Sources (une par ligne, obligatoire)")

    submitted = st.form_submit_button("🔍 Prévisualiser le diff")

if submitted:
    if not c_id or not c_nom or not assureur or not sources.strip():
        st.warning("⚠️ ID, Nom, Assureur et au moins une source sont obligatoires.")
    else:
        nouveau_contrat: dict = {
            "id": c_id.strip().lower(),
            "nom": c_nom.strip(),
            "assureur": assureur.strip(),
            "distributeur": distributeur.strip() or assureur.strip(),
            "frais_gestion_uc_pct": float(frais_uc) / 100,
            "frais_gestion_fonds_euros_pct": float(frais_fe) / 100,
            "frais_entree_pct": float(frais_entree) / 100,
            "frais_arbitrage_pct": float(frais_arb) / 100,
            "nb_uc_total": int(nb_uc),
            "nb_etf": int(nb_etf),
            "fonds_euros_disponible": fonds_euros,
            "rendement_fonds_euros_2024": float(rendement_fe) / 100 if rendement_fe > 0 else None,
            "versement_minimum_eur": float(versement_min),
            "annees_existence": int(annees),
            "sources": [s.strip() for s in sources.splitlines() if s.strip()],
        }

        nouveau_data = dict(data)
        liste = list(contrats)
        idx = next((i for i, c in enumerate(liste) if c.get("id") == nouveau_contrat["id"]), None)
        if idx is not None:
            liste[idx] = nouveau_contrat
        else:
            liste.append(nouveau_contrat)
        nouveau_data[_KEY_LIST] = liste

        diff = diff_yaml(data, nouveau_data)
        st.subheader("🔍 Diff (dry-run)")
        if diff:
            st.code(diff, language="diff")
        else:
            st.info("Aucun changement détecté.")

        st.session_state["av_preview"] = nouveau_data

if "av_preview" in st.session_state and st.button("✅ Confirmer la sauvegarde"):
    try:
        sauvegarder_yaml(_FILENAME, st.session_state["av_preview"])
        st.success("✅ Contrats AV sauvegardés avec backup.")
        del st.session_state["av_preview"]
        st.cache_data.clear()
    except Exception as exc:
        st.error(f"❌ Erreur : {exc}")

# ─── Suppression ──────────────────────────────────────────────────────────────

st.subheader("🗑️ Supprimer un contrat AV")
if contrats:
    options = {f"{c.get('nom', '?')} ({c.get('id', '?')})": c.get("id") for c in contrats}
    choix = st.selectbox("Sélectionner le contrat à supprimer", list(options.keys()))
    if st.button("🗑️ Supprimer (avec backup)"):
        cid = options[choix]
        nouveau_data = dict(data)
        nouveau_data[_KEY_LIST] = [c for c in contrats if c.get("id") != cid]
        try:
            sauvegarder_yaml(_FILENAME, nouveau_data)
            st.success(f"✅ Contrat '{cid}' supprimé.")
            st.cache_data.clear()
        except Exception as exc:
            st.error(f"❌ Erreur : {exc}")
