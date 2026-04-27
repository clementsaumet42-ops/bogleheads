"""Page 10 — Note de Recommandation Personnalisée (17 pages)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.ui.theme import injecter_css

st.set_page_config(page_title="NRP", page_icon="🏛️")
injecter_css()

st.title("Note de Recommandation Personnalisée")
st.caption("Génère un PDF 17 pages avec profil 3 prismes + capital humain")

ROOT = Path(__file__).parent.parent

st.subheader("Données de profilage")
aversion = st.selectbox(
    "Profil de risque déclaré",
    ["tres_faible", "faible", "moyenne", "elevee", "tres_elevee"],
    index=2,
)
revenus = st.number_input("Revenus nets annuels (€)", value=60000, step=5000)
annees = st.slider("Années avant retraite", 0, 40, 20)

if st.button("Générer le PDF 17 pages"):
    from src.pdf_builder import charger_config_pdf, generer_pdf
    from src.profilage.capital_humain import CapitalHumain
    from src.profilage.synthese import synthetiser_profil
    from src.schemas import charger_et_valider

    profils = charger_et_valider("profils_clients.yaml")
    profil = profils.profils[0]
    config_pdf = charger_config_pdf()
    pc = synthetiser_profil(aversion)
    ch = CapitalHumain(revenus_nets_annuels=revenus, annees_restantes=annees)
    out = ROOT / "output" / "nrp_17pages.pdf"
    res = generer_pdf(profil, config_pdf, out, profil_consolide=pc, capital_humain_data=ch)
    st.success(f"PDF généré : {res.nb_pages} pages — {res.taille_octets // 1024} Ko")
    with open(out, "rb") as f:
        st.download_button("Télécharger la NRP", f, file_name="NRP.pdf", mime="application/pdf")
