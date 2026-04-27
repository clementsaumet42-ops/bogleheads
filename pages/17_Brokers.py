"""Page 17 — Brokers : CRUD avec dry-run diff."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.catalogue.crud import diff_yaml, lire_yaml, sauvegarder_yaml
from src.ui.theme import injecter_css

st.set_page_config(page_title="Brokers", page_icon="🏛️")
injecter_css()

st.title("Brokers — Gestion")

st.info("Gérez la liste des brokers disponibles. Backup automatique avant chaque sauvegarde.")

_FILENAME = "brokers.yaml"
_KEY_LIST = "brokers"


@st.cache_data(ttl=30)
def _charger() -> dict:
    try:
        return lire_yaml(_FILENAME)
    except Exception as exc:
        st.error(f"Erreur chargement : {exc}")
        return {_KEY_LIST: []}


data = _charger()
brokers: list[dict] = data.get(_KEY_LIST, [])

# ─── Tableau lecture ───────────────────────────────────────────────────────────

st.subheader(f"{len(brokers)} brokers dans le catalogue")

if brokers:
    cols = [
        "id",
        "nom",
        "pea_disponible",
        "cto_disponible",
        "per_disponible",
        "av_disponible",
        "frais_garde_annuel_eur",
    ]
    df = pd.DataFrame([{c: b.get(c, "") for c in cols} for b in brokers])
    st.dataframe(df, use_container_width=True, height=250)

# ─── Formulaire ───────────────────────────────────────────────────────────────

st.subheader("Ajouter / Modifier un broker")

with st.form("form_broker"):
    b_id = st.text_input("ID (slug, ex: degiro) *")
    b_nom = st.text_input("Nom *")
    pea = st.checkbox("PEA disponible")
    pea_pme = st.checkbox("PEA-PME disponible")
    cto = st.checkbox("CTO disponible", value=True)
    per = st.checkbox("PER disponible")
    av = st.checkbox("AV disponible")
    frais_garde = st.number_input("Frais de garde annuel (€)", min_value=0.0, step=0.01)
    frais_inact = st.number_input("Frais d'inactivité annuel (€)", min_value=0.0, step=0.01)
    courtage_eur = st.number_input(
        "Courtage Euronext (€/ordre, 0=non applicable)", min_value=0.0, step=0.01
    )
    annees = st.number_input("Années d'existence", min_value=0, step=1)
    sources = st.text_area("Sources (une par ligne)")

    submitted = st.form_submit_button("Prévisualiser le diff")

if submitted:
    if not b_id or not b_nom:
        st.warning("ID et Nom sont obligatoires.")
    else:
        nouveau_broker: dict = {
            "id": b_id.strip().lower(),
            "nom": b_nom.strip(),
            "pea_disponible": pea,
            "pea_pme_disponible": pea_pme,
            "cto_disponible": cto,
            "per_disponible": per,
            "av_disponible": av,
            "frais_garde_annuel_eur": float(frais_garde),
            "frais_inactivite_annuel_eur": float(frais_inact),
            "frais_courtage_actions_euronext_eur": float(courtage_eur)
            if courtage_eur > 0
            else None,
            "annees_existence": int(annees),
            "sources": [s.strip() for s in sources.splitlines() if s.strip()],
        }

        nouveau_data = dict(data)
        liste = list(brokers)
        idx = next((i for i, b in enumerate(liste) if b.get("id") == nouveau_broker["id"]), None)
        if idx is not None:
            liste[idx] = nouveau_broker
        else:
            liste.append(nouveau_broker)
        nouveau_data[_KEY_LIST] = liste

        diff = diff_yaml(data, nouveau_data)
        st.subheader("Diff (dry-run)")
        if diff:
            st.code(diff, language="diff")
        else:
            st.info("Aucun changement détecté.")

        st.session_state["broker_preview"] = nouveau_data

if "broker_preview" in st.session_state and st.button("Confirmer la sauvegarde"):
    try:
        sauvegarder_yaml(_FILENAME, st.session_state["broker_preview"])
        st.success("Brokers sauvegardés avec backup.")
        del st.session_state["broker_preview"]
        st.cache_data.clear()
    except Exception as exc:
        st.error(f"Erreur : {exc}")

# ─── Suppression ──────────────────────────────────────────────────────────────

st.subheader("Supprimer un broker")
if brokers:
    options = {f"{b.get('nom', '?')} ({b.get('id', '?')})": b.get("id") for b in brokers}
    choix = st.selectbox("Sélectionner le broker à supprimer", list(options.keys()))
    if st.button("Supprimer (avec backup)"):
        bid = options[choix]
        nouveau_data = dict(data)
        nouveau_data[_KEY_LIST] = [b for b in brokers if b.get("id") != bid]
        try:
            sauvegarder_yaml(_FILENAME, nouveau_data)
            st.success(f"Broker '{bid}' supprimé.")
            st.cache_data.clear()
        except Exception as exc:
            st.error(f"Erreur : {exc}")
