"""Page 19 — Teneurs PER : CRUD avec dry-run diff."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.catalogue.crud import diff_yaml, lire_yaml, sauvegarder_yaml
from src.ui.theme import injecter_css

st.set_page_config(page_title="Teneurs PER", page_icon="🏛️")
injecter_css()

st.title("Teneurs PER — Gestion")

st.info("Gérez les teneurs de compte PER référencés. Backup automatique avant chaque sauvegarde.")

_FILENAME = "teneurs_per.yaml"
_KEY_LIST = "teneurs_per"


@st.cache_data(ttl=30)
def _charger() -> dict:
    try:
        return lire_yaml(_FILENAME)
    except Exception as exc:
        st.error(f"Erreur chargement : {exc}")
        return {_KEY_LIST: []}


data = _charger()
teneurs: list[dict] = data.get(_KEY_LIST, [])

# ─── Tableau lecture ───────────────────────────────────────────────────────────

st.subheader(f"{len(teneurs)} teneurs PER dans le catalogue")

if teneurs:
    cols = [
        "id",
        "nom",
        "assureur",
        "frais_gestion_uc_pct",
        "frais_entree_pct",
        "nb_etf",
        "fonds_euros_disponible",
        "versement_minimum_eur",
        "gestion_libre",
    ]
    df = pd.DataFrame([{c: t.get(c, "") for c in cols} for t in teneurs])
    st.dataframe(df, use_container_width=True, height=250)

# ─── Formulaire ───────────────────────────────────────────────────────────────

st.subheader("Ajouter / Modifier un teneur PER")

with st.form("form_per"):
    t_id = st.text_input("ID (slug, ex: linxea_spirit_per) *")
    t_nom = st.text_input("Nom *")
    assureur = st.text_input("Assureur")
    distributeur = st.text_input("Distributeur")
    type_per = st.selectbox("Type PER", ["individuel", "collectif", "obligatoire"])
    frais_uc = st.number_input(
        "Frais gestion UC (%)", min_value=0.0, max_value=5.0, step=0.001, format="%.3f"
    )
    frais_fe = st.number_input(
        "Frais gestion fonds euros (%, 0=non applicable)",
        min_value=0.0,
        max_value=5.0,
        step=0.001,
        format="%.3f",
    )
    frais_entree = st.number_input(
        "Frais d'entrée (%)", min_value=0.0, max_value=10.0, step=0.001, format="%.3f"
    )
    frais_arb = st.number_input(
        "Frais d'arbitrage (%)", min_value=0.0, max_value=5.0, step=0.001, format="%.3f"
    )
    frais_versement = st.number_input(
        "Frais de versement (%)", min_value=0.0, max_value=10.0, step=0.001, format="%.3f"
    )
    nb_uc = st.number_input("Nombre total d'UC", min_value=0, step=1)
    nb_etf = st.number_input("Nombre d'ETF", min_value=0, step=1)
    fonds_euros = st.checkbox("Fonds euros disponible")
    rendement_fe = st.number_input(
        "Rendement fonds euros 2024 (%, 0=non applicable)",
        min_value=0.0,
        max_value=20.0,
        step=0.01,
        format="%.2f",
    )
    versement_min = st.number_input("Versement minimum (€)", min_value=0.0, step=10.0)
    gestion_libre = st.checkbox("Gestion libre", value=True)
    gestion_pilotee = st.checkbox("Gestion pilotée")
    annees = st.number_input("Années d'existence", min_value=0, step=1)
    sources = st.text_area("Sources (une par ligne)")

    submitted = st.form_submit_button("Prévisualiser le diff")

if submitted:
    if not t_id or not t_nom:
        st.warning("ID et Nom sont obligatoires.")
    else:
        nouveau_teneur: dict = {
            "id": t_id.strip().lower(),
            "nom": t_nom.strip(),
            "type_per": type_per,
            "assureur": assureur.strip() or None,
            "distributeur": distributeur.strip() or None,
            "frais_gestion_uc_pct": float(frais_uc) / 100,
            "frais_gestion_fonds_euros_pct": float(frais_fe) / 100 if frais_fe > 0 else None,
            "frais_entree_pct": float(frais_entree) / 100,
            "frais_arbitrage_pct": float(frais_arb) / 100,
            "frais_versement_pct": float(frais_versement) / 100,
            "nb_uc_total": int(nb_uc),
            "nb_etf": int(nb_etf),
            "fonds_euros_disponible": fonds_euros,
            "rendement_fonds_euros_2024": float(rendement_fe) / 100 if rendement_fe > 0 else None,
            "etfs_disponibles": None,
            "versement_minimum_eur": float(versement_min),
            "gestion_libre": gestion_libre,
            "gestion_pilotee": gestion_pilotee,
            "sortie_capital_possible": True,
            "sortie_rente_possible": True,
            "annees_existence": int(annees),
            "sources": [s.strip() for s in sources.splitlines() if s.strip()],
        }

        nouveau_data = dict(data)
        liste = list(teneurs)
        idx = next((i for i, t in enumerate(liste) if t.get("id") == nouveau_teneur["id"]), None)
        if idx is not None:
            liste[idx] = nouveau_teneur
        else:
            liste.append(nouveau_teneur)
        nouveau_data[_KEY_LIST] = liste

        diff = diff_yaml(data, nouveau_data)
        st.subheader("Diff (dry-run)")
        if diff:
            st.code(diff, language="diff")
        else:
            st.info("Aucun changement détecté.")

        st.session_state["per_preview"] = nouveau_data

if "per_preview" in st.session_state and st.button("Confirmer la sauvegarde"):
    try:
        sauvegarder_yaml(_FILENAME, st.session_state["per_preview"])
        st.success("Teneurs PER sauvegardés avec backup.")
        del st.session_state["per_preview"]
        st.cache_data.clear()
    except Exception as exc:
        st.error(f"Erreur : {exc}")

# ─── Suppression ──────────────────────────────────────────────────────────────

st.subheader("Supprimer un teneur PER")
if teneurs:
    options = {f"{t.get('nom', '?')} ({t.get('id', '?')})": t.get("id") for t in teneurs}
    choix = st.selectbox("Sélectionner le teneur à supprimer", list(options.keys()))
    if st.button("Supprimer (avec backup)"):
        tid = options[choix]
        nouveau_data = dict(data)
        nouveau_data[_KEY_LIST] = [t for t in teneurs if t.get("id") != tid]
        try:
            sauvegarder_yaml(_FILENAME, nouveau_data)
            st.success(f"Teneur PER '{tid}' supprimé.")
            st.cache_data.clear()
        except Exception as exc:
            st.error(f"Erreur : {exc}")
