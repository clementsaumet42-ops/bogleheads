"""Page 11 — Journal des dossiers clients (SQLite)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.ui.theme import injecter_css

st.set_page_config(page_title="Dossiers", page_icon="🏛️")
injecter_css()

st.title("Journal des Dossiers Clients")
st.caption("Audit SQLite + chiffrement Fernet (AES-256)")

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "journal_cif.db"

passphrase = st.text_input("Passphrase de déchiffrement", value="changeme", type="password")

if st.button("Voir les conseils enregistrés"):
    from src.cif.journal import JournalConseils

    journal = JournalConseils(DB_PATH, passphrase)
    conseils = journal.lire_conseils()
    if conseils:
        st.write(f"**{len(conseils)} conseil(s) enregistré(s)**")
        for c in conseils[:20]:
            st.write(f"- {c['date_heure']} | {c['client_id']} | {c['type_conseil']}")
    else:
        st.info("Aucun conseil enregistré.")

st.divider()
st.subheader("Ajouter un conseil test")
client_id = st.text_input("ID client", value="CLIENT_001")
type_conseil = st.text_input("Type de conseil", value="allocation")
if st.button("Enregistrer"):
    from src.cif.journal import JournalConseils

    journal = JournalConseils(DB_PATH, passphrase)
    cid = journal.ajouter_conseil(client_id, type_conseil, {"test": True})
    st.success(f"Conseil enregistré : {cid}")
