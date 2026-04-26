"""Page 16 — Catalogue ETF : CRUD avec dry-run diff et import CSV."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.catalogue.crud import diff_yaml, importer_csv, lire_yaml, sauvegarder_yaml

st.set_page_config(page_title="Catalogue ETF", page_icon="📋")
st.title("📋 Catalogue ETF — Gestion")

st.info(
    "Cette page permet d'ajouter, modifier ou supprimer des ETF dans le catalogue. "
    "Toutes les modifications sont sauvegardées avec un backup automatique."
)

_FILENAME = "univers_etf.yaml"
_KEY_LIST = "univers_etf"


@st.cache_data(ttl=30)
def _charger() -> dict:
    try:
        return lire_yaml(_FILENAME)
    except Exception as exc:
        st.error(f"Erreur chargement : {exc}")
        return {_KEY_LIST: []}


data = _charger()
etfs: list[dict] = data.get(_KEY_LIST, [])

# ─── Tableau lecture ───────────────────────────────────────────────────────────

st.subheader(f"📊 {len(etfs)} ETF dans le catalogue")

if etfs:
    cols_affich = ["isin", "ticker", "nom", "ter", "domicile_iso"]
    rows = []
    for e in etfs:
        rows.append({c: e.get(c, "") for c in cols_affich})
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, height=300)

# ─── Formulaire ajout / édition ───────────────────────────────────────────────

st.subheader("➕ Ajouter / Modifier un ETF")

with st.form("form_etf"):
    isin = st.text_input("ISIN *", max_chars=12)
    ticker = st.text_input("Ticker *", max_chars=20)
    nom = st.text_input("Nom *")
    ter = st.number_input(
        "TER (ex: 0.0020)", min_value=0.0, max_value=0.05, step=0.0001, format="%.4f"
    )
    domicile = st.selectbox("Domicile ISO", ["IE", "LU", "FR", "DE", "ES", "IT", "NL", "BE", "AT"])
    pea = st.checkbox("Éligible PEA")
    cto = st.checkbox("Éligible CTO", value=True)
    av_uc = st.checkbox("Éligible AV (UC)")
    per = st.checkbox("Éligible PER")
    sources = st.text_area("Sources (une par ligne)")

    submitted = st.form_submit_button("💾 Prévisualiser le diff (dry-run)")

if submitted:
    if not isin or not ticker or not nom:
        st.warning("⚠️ ISIN, Ticker et Nom sont obligatoires.")
    else:
        nouveau_etf: dict = {
            "isin": isin.strip().upper(),
            "ticker": ticker.strip().upper(),
            "nom": nom.strip(),
            "ter": float(ter),
            "domicile_iso": domicile,
            "eligibilite": {
                "PEA": pea,
                "CTO_perso": cto,
                "AV_UC": av_uc,
                "PER": per,
            },
            "sources": [s.strip() for s in sources.splitlines() if s.strip()],
        }

        # Vérifier si ISIN existe déjà
        nouveau_data = dict(data)
        liste = list(etfs)
        idx_existant = next(
            (i for i, e in enumerate(liste) if e.get("isin") == nouveau_etf["isin"]), None
        )
        if idx_existant is not None:
            liste[idx_existant] = nouveau_etf
            st.info(f"🔄 Modification de l'ETF existant {isin}")
        else:
            liste.append(nouveau_etf)
            st.success(f"✅ Ajout du nouvel ETF {ticker}")

        nouveau_data[_KEY_LIST] = liste
        diff = diff_yaml(data, nouveau_data)

        st.subheader("🔍 Diff (dry-run)")
        if diff:
            st.code(diff, language="diff")
        else:
            st.info("Aucun changement détecté.")

        st.session_state["etf_preview"] = nouveau_data

# Bouton de confirmation séparé
if "etf_preview" in st.session_state and st.button("✅ Confirmer la sauvegarde"):
    try:
        sauvegarder_yaml(_FILENAME, st.session_state["etf_preview"])
        st.success("✅ Catalogue ETF sauvegardé avec backup.")
        del st.session_state["etf_preview"]
        st.cache_data.clear()
    except Exception as exc:
        st.error(f"❌ Erreur sauvegarde : {exc}")

# ─── Import CSV ───────────────────────────────────────────────────────────────

st.subheader("📥 Import CSV")
st.markdown(
    "Format attendu : colonnes séparées par `;`, encodage UTF-8. Colonnes minimales : `isin;ticker;nom;ter`"
)

uploaded = st.file_uploader("Importer un fichier CSV", type=["csv"])
if uploaded is not None:
    try:
        rows_csv = importer_csv(
            uploaded.read(), colonnes_attendues=["isin", "ticker", "nom", "ter"]
        )
        st.success(f"✅ {len(rows_csv)} lignes importées depuis le CSV.")
        st.dataframe(pd.DataFrame(rows_csv), use_container_width=True)
        if st.button("💾 Intégrer au catalogue"):
            nouveau_data = dict(data)
            liste = list(etfs)
            for row in rows_csv:
                isin_csv = str(row.get("isin", "")).strip().upper()
                idx = next((i for i, e in enumerate(liste) if e.get("isin") == isin_csv), None)
                entry = {
                    "isin": isin_csv,
                    "ticker": str(row.get("ticker", "")).strip().upper(),
                    "nom": str(row.get("nom", "")).strip(),
                    "ter": float(row.get("ter", 0.003) or 0.003),
                }
                if idx is not None:
                    liste[idx] = entry
                else:
                    liste.append(entry)
            nouveau_data[_KEY_LIST] = liste
            sauvegarder_yaml(_FILENAME, nouveau_data)
            st.success("✅ Import CSV intégré au catalogue.")
            st.cache_data.clear()
    except Exception as exc:
        st.error(f"❌ Erreur import CSV : {exc}")

# ─── Suppression ──────────────────────────────────────────────────────────────

st.subheader("🗑️ Supprimer un ETF")
if etfs:
    options = {f"{e.get('ticker', '?')} — {e.get('isin', '?')}": e.get("isin") for e in etfs}
    choix = st.selectbox("Sélectionner l'ETF à supprimer", list(options.keys()))
    if st.button("🗑️ Supprimer (avec backup)"):
        isin_suppr = options[choix]
        nouveau_data = dict(data)
        nouveau_data[_KEY_LIST] = [e for e in etfs if e.get("isin") != isin_suppr]
        try:
            sauvegarder_yaml(_FILENAME, nouveau_data)
            st.success(f"✅ ETF {isin_suppr} supprimé. Backup créé.")
            st.cache_data.clear()
        except Exception as exc:
            st.error(f"❌ Erreur suppression : {exc}")
