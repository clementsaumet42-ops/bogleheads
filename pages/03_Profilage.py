"""Page 03 — Profilage client MIF2 / Grable-Lytton."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
import yaml

from src.ui.theme import injecter_css

st.set_page_config(page_title="Profilage", page_icon="🏛️")
injecter_css()

st.title("Profilage Client")
st.caption("Questionnaire MIF2 + Grable-Lytton + Scénarios comportementaux")

_ROOT = Path(__file__).parent.parent

step = st.radio(
    "Étape", ["1. AMF", "2. Grable-Lytton", "3. Scénarios", "4. Synthèse"], horizontal=True
)

if step == "1. AMF":
    st.subheader("Connaissance & Expérience (Art. 325-3 RG AMF)")

    _amf_path = _ROOT / "config" / "questionnaire_amf.yaml"
    with open(_amf_path, encoding="utf-8") as _f:
        _amf_data = yaml.safe_load(_f)

    sections = _amf_data.get("sections", [])

    reponses_amf = {}
    for section in sections:
        st.markdown(f"**{section['titre']}**")
        for q in section["questions"]:
            qid = q["id"]
            texte = q["texte"]
            opts = q["options"]
            qtype = q.get("type", "binaire")

            if qtype == "binaire":
                val = st.checkbox(texte, key=f"amf_{qid}")
                reponses_amf[qid] = val
            else:
                sel = st.radio(texte, opts, key=f"amf_{qid}", horizontal=True)
                reponses_amf[qid] = sel

    if st.button("Calculer le niveau AMF"):
        from src.profilage.amf import ProfilAMF

        p = ProfilAMF(
            connait_actions=reponses_amf.get("q1", False),
            connait_obligations=reponses_amf.get("q2", False),
            connait_opcvm_etf=reponses_amf.get("q3", False),
            a_deja_investi=reponses_amf.get("q5", False),
            annees_experience={
                "Jamais": "jamais",
                "Moins de 2 ans": "moins_2",
                "2 à 5 ans": "2_a_5",
                "Plus de 5 ans": "plus_5",
            }.get(reponses_amf.get("q7", "Jamais"), "jamais"),
        )
        st.success(f"Niveau : **{p.niveau_connaissance_global()}**")

elif step == "2. Grable-Lytton":
    st.subheader("Questionnaire Grable & Lytton (1999)")

    _gl_path = _ROOT / "config" / "questionnaire_grable_lytton.yaml"
    with open(_gl_path, encoding="utf-8") as _f:
        _gl_data = yaml.safe_load(_f)

    nb_questions = _gl_data.get("nb_questions", 13)
    categories = _gl_data.get("categories", {})
    questions = _gl_data.get("questions", [])

    st.info(
        f"{nb_questions} questions, score de {_gl_data.get('score_min', 13)} à {_gl_data.get('score_max', 47)}."
    )

    reponses_prev = st.session_state.get("reponses_grable_lytton", {})
    reponses = {}

    for q in questions:
        qid = q["id"]
        texte = q["texte"]
        options = q["options"]
        option_labels = list(options.values())
        option_keys = list(options.keys())

        prev_key = reponses_prev.get(qid, option_keys[1])
        prev_idx = option_keys.index(prev_key) if prev_key in option_keys else 1

        sel = st.radio(f"**Q{qid}.** {texte}", option_labels, index=prev_idx, key=f"gl_{qid}")
        reponses[qid] = option_keys[option_labels.index(sel)]

    if st.button("Calculer le profil"):
        from src.profilage.grable_lytton import calculer_profil_grable_lytton

        st.session_state["reponses_grable_lytton"] = reponses
        p = calculer_profil_grable_lytton(reponses)
        st.success(f"Score brut : **{p.score_brut}** — Profil : **{p.categorie}**")

        st.markdown("**Seuils des profils :**")
        for cat, seuils in categories.items():
            marker = "← *votre profil*" if cat == p.categorie else ""
            st.write(f"- **{cat}** : {seuils['min']} – {seuils['max']}{marker}")

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
