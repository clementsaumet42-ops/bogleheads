"""Page 09 — Profilage client MIF2 / Grable-Lytton."""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Profilage", page_icon="🎯")
st.title("🎯 Profilage Client")
st.caption("Questionnaire MIF2 + Grable-Lytton + Scénarios comportementaux")

step = st.radio(
    "Étape", ["1. AMF", "2. Grable-Lytton", "3. Scénarios", "4. Synthèse"], horizontal=True
)

if step == "1. AMF":
    st.subheader("Connaissance & Expérience (Art. 325-3 RG AMF)")
    actions = st.checkbox("Connaissez-vous les actions cotées ?")
    obligations = st.checkbox("Connaissez-vous les obligations ?")
    etf = st.checkbox("Connaissez-vous les OPCVM/ETF ?")
    investi = st.checkbox("Avez-vous déjà investi en bourse ?")
    exp = st.selectbox("Années d'expérience", ["jamais", "moins_2", "2_a_5", "plus_5"])
    if st.button("Calculer le niveau AMF"):
        from src.profilage.amf import ProfilAMF

        p = ProfilAMF(
            connait_actions=actions,
            connait_obligations=obligations,
            connait_opcvm_etf=etf,
            a_deja_investi=investi,
            annees_experience=exp,
        )
        st.success(f"Niveau : **{p.niveau_connaissance_global()}**")

elif step == "2. Grable-Lytton":
    st.subheader("Questionnaire Grable & Lytton (1999)")
    st.info("13 questions, score 1 à 4 par question.")
    reponses = {}
    for i in range(1, 14):
        reponses[i] = st.slider(f"Question {i}", 1, 4, 2)
    if st.button("Calculer le profil"):
        from src.profilage.grable_lytton import calculer_profil_grable_lytton

        p = calculer_profil_grable_lytton(reponses)
        st.success(f"Score : {p.score_brut} — Profil : **{p.categorie}**")

elif step == "3. Scénarios":
    st.subheader("Scénarios comportementaux")
    from src.profilage.scenarios_prospect import calculer_score_scenarios, generer_scenarios

    scenarios = generer_scenarios()
    choix = {}
    for sc in scenarios:
        opts = {c.texte: c.id for c in sc.choix}
        sel = st.radio(f"**{sc.titre}** — {sc.contexte}", list(opts.keys()), key=sc.id)
        choix[sc.id] = opts[sel]
    if st.button("Calculer le score"):
        score = calculer_score_scenarios(choix)
        st.success(f"Score comportemental moyen : **{score:.2f}** (de -2 à +2)")

elif step == "4. Synthèse":
    st.subheader("Synthèse du profil consolidé")
    aversion = st.selectbox(
        "Profil déclaré", ["tres_faible", "faible", "moyenne", "elevee", "tres_elevee"], index=2
    )
    if st.button("Générer la synthèse"):
        from src.profilage.synthese import synthetiser_profil

        pc = synthetiser_profil(aversion)
        st.success(f"Recommandation : **{pc.recommandation_allocation}**")
        st.write(f"Cohérence : {pc.delta_confiance}")
