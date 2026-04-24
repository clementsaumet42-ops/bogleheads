"""Page 4 — Audit patrimonial : Chasse aux points de base.

Identification et quantification des économies activables sur le portefeuille actuel.
Orchestration des 5 moteurs S8.2b → rapport ranked par gain capitalisé 30 ans.
"""

from __future__ import annotations

import streamlit as st

from src.ui.cards import carte_kpi
from src.ui.explications import bloc_script_restitution, expander_explication
from src.ui.formatters import format_euro

# ─── Injection typographie premium ───────────────────────────────────────────

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Inter:wght@300;400;500&display=swap');
h1, h2, h3 { font-family: 'Cormorant Garamond', Georgia, serif !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ─── Section 1 — En-tête ──────────────────────────────────────────────────────

st.title("🔍 Audit patrimonial — Chasse aux points de base")
st.markdown("_Identification des économies activables sur votre portefeuille actuel_")

profil_raw = st.session_state.get("profil_actif")
if profil_raw:
    nom = (
        profil_raw.get("nom", "—")
        if isinstance(profil_raw, dict)
        else getattr(profil_raw, "nom", "—")
    )
    patrimoine = (
        profil_raw.get("patrimoine_financier_total", 0)
        if isinstance(profil_raw, dict)
        else getattr(profil_raw, "patrimoine_financier_total", 0)
    )
    tmi_val = (
        profil_raw.get("tmi", 0) if isinstance(profil_raw, dict) else getattr(profil_raw, "tmi", 0)
    )
    st.markdown(
        f"<div style='background:#F5F3EE;border:1px solid #B08D57;border-radius:6px;"
        f"padding:10px 16px;font-size:0.9rem;color:#1B3A5B;margin-bottom:16px;'>"
        f"👤 <strong>{nom}</strong> &nbsp;|&nbsp; "
        f"Patrimoine financier : <strong>{format_euro(float(patrimoine))}</strong> &nbsp;|&nbsp; "
        f"TMI : <strong>{tmi_val * 100:.0f} %</strong>"
        f"</div>",
        unsafe_allow_html=True,
    )

# ─── Intro pédagogique ────────────────────────────────────────────────────────

from src.pedagogie.audit import expliquer_concept_bps  # noqa: E402

expander_explication(expliquer_concept_bps(), icone="📐")

# ─── Chargement des référentiels ──────────────────────────────────────────────


@st.cache_data(ttl=600)
def _charger_referentiels() -> tuple:
    """Charge les référentiels une fois, avec cache 10 min."""
    from src.schemas import charger_et_valider

    contrats_config = charger_et_valider("contrats_av.yaml")
    brokers_config = charger_et_valider("brokers.yaml")
    retenues = charger_et_valider("retenues_source.yaml")
    univers_config = charger_et_valider("univers_etf.yaml")

    # Convertir les ETF du catalogue en ETFEnrichi
    from src.schemas import ETFEnrichi

    univers_enrichi = []
    for etf in univers_config.univers_etf:
        try:
            enr = ETFEnrichi.model_validate(etf.model_dump())
            univers_enrichi.append(enr)
        except Exception:
            pass

    return (
        contrats_config.contrats_av,
        brokers_config.brokers,
        retenues,
        univers_enrichi,
    )


# ─── Calcul ou récupération du rapport ───────────────────────────────────────


def _lancer_audit(profil_raw: dict | object) -> None:  # noqa: ANN001
    """Calcule le rapport d'audit et le stocke en session_state."""
    from src.audit.adapter import contexte_depuis_profil
    from src.audit.master import auditer_patrimoine
    from src.schemas import Profil

    contrats_av, brokers, retenues, univers_etf = _charger_referentiels()

    # Construire le Profil Pydantic
    profil = Profil.model_validate(profil_raw) if isinstance(profil_raw, dict) else profil_raw  # type: ignore[assignment]

    # Construire le contexte
    contexte, avertissements_adapter = contexte_depuis_profil(profil)

    # Lancer l'audit
    rapport = auditer_patrimoine(
        contexte=contexte,
        univers_etf=univers_etf,
        contrats_av_marche=contrats_av,
        brokers_marche=brokers,
        matrice_retenues=retenues,
    )

    # Fusionner les avertissements de l'adaptateur
    rapport = rapport.model_copy(
        update={"avertissements": avertissements_adapter + rapport.avertissements}
    )

    st.session_state["rapport_audit"] = rapport
    st.session_state["rapport_audit_profil_id"] = profil.id if hasattr(profil, "id") else None
    st.session_state["opportunites_a_activer"] = []


# Bouton de relance
col_btn, col_info = st.columns([1, 3])
with col_btn:
    if st.button("🔄 Lancer / relancer l'audit"):
        if profil_raw:
            with st.spinner("Analyse en cours…"):
                _lancer_audit(profil_raw)
        else:
            st.warning("⚠️ Aucun profil chargé — rendez-vous sur la page Profil.")

# Lancer automatiquement si profil présent et pas encore de rapport
if profil_raw and "rapport_audit" not in st.session_state:
    with st.spinner("Analyse en cours…"):
        _lancer_audit(profil_raw)

rapport = st.session_state.get("rapport_audit")

if rapport is None:
    st.info(
        "📋 Aucun rapport disponible. "
        "Chargez d'abord un profil client sur la page **Profil** puis revenez ici."
    )
    if st.button("👤 Aller au profil client"):
        st.switch_page("pages/02_Profil.py")
    st.stop()

# ─── Section 2 — KPIs ─────────────────────────────────────────────────────────

st.divider()
st.subheader("💶 Résumé des opportunités")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        carte_kpi(
            titre="💰 Gain activable / an",
            valeur=format_euro(rapport.gain_total_annuel_eur),
            contexte="Somme des économies annuelles identifiées",
        ),
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        carte_kpi(
            titre="📈 Gain capitalisé 30 ans",
            valeur=format_euro(rapport.gain_total_30ans_eur),
            contexte="À 4 %/an, hypothèses constantes",
            couleur_valeur="#2E5D4F",
        ),
        unsafe_allow_html=True,
    )

with col3:
    nb_opp = len(rapport.opportunites)
    st.markdown(
        carte_kpi(
            titre="🎯 Opportunités identifiées",
            valeur=str(nb_opp),
            contexte=f"dont {rapport.nb_opportunites_haute_confiance} haute confiance",
        ),
        unsafe_allow_html=True,
    )

# ─── Section 3 — Répartition par levier ──────────────────────────────────────

st.divider()
st.subheader("📊 Répartition par levier")

levier_labels = {
    "tracking_difference": "Tracking Difference",
    "withholding_tax": "Withholding Tax",
    "dist_vs_cap": "Distribuant → Capitalisant",
    "frais_contrat_av": "Frais contrat AV",
    "frais_broker": "Frais broker",
}

synthese_sorted = sorted(
    rapport.synthese_par_levier.items(),
    key=lambda kv: kv[1].get("gain_annuel_eur", 0),
    reverse=True,
)

if any(v.get("gain_annuel_eur", 0) > 0 for _, v in synthese_sorted):
    import pandas as pd

    rows = []
    for levier, data in synthese_sorted:
        gain_ann = data.get("gain_annuel_eur", 0.0)
        gain_30 = data.get("gain_30ans_eur", 0.0)
        nb = data.get("nb", 0)
        label = levier_labels.get(levier, levier)
        if gain_ann > 0:
            rows.append(
                {
                    "Levier": label,
                    "Nb opp.": nb,
                    "Gain annuel": format_euro(gain_ann),
                    "Gain 30 ans": format_euro(gain_30),
                }
            )
        else:
            rows.append(
                {
                    "Levier": label,
                    "Nb opp.": 0,
                    "Gain annuel": "✅ Optimal",
                    "Gain 30 ans": "—",
                }
            )

    df_synthese = pd.DataFrame(rows)
    st.dataframe(df_synthese, hide_index=True, use_container_width=True)
else:
    st.success(
        "✅ Pas d'optimisation identifiée — votre portefeuille est déjà optimal sur tous les leviers."
    )

# ─── Section 4 — Liste détaillée des opportunités ────────────────────────────

st.divider()
st.subheader("🔎 Opportunités détaillées")

if not rapport.opportunites:
    st.success(
        "✅ Aucune opportunité identifiée : votre portefeuille est déjà optimal "
        "sur les 5 leviers analysés. Bravo !"
    )
else:
    from src.pedagogie.audit import expliquer_opportunite

    if "opportunites_a_activer" not in st.session_state:
        st.session_state["opportunites_a_activer"] = []

    complexite_couleurs = {
        "faible": ("🟢", "#2E5D4F"),
        "moyenne": ("🟡", "#A65A00"),
        "elevee": ("🔴", "#A65A4E"),
    }
    confiance_couleurs = {
        "haute": ("✅", "#2E5D4F"),
        "moyenne": ("⚠️", "#A65A00"),
        "basse": ("❓", "#888888"),
    }

    for i, opp in enumerate(rapport.opportunites):
        titre_expander = (
            f"{'🥇' if i == 0 else '🎯'} {opp.titre} — "
            f"**{format_euro(opp.gain_annuel_eur)}/an** "
            f"({format_euro(opp.gain_30ans_eur)} sur 30 ans)"
        )
        with st.expander(titre_expander):
            # Avant / Après
            col_av, col_ap = st.columns(2)
            with col_av:
                st.markdown("**Situation actuelle**")
                for k, v in opp.avant.items():
                    st.markdown(f"- `{k}` : {v}")
            with col_ap:
                st.markdown("**Situation cible**")
                for k, v in opp.apres.items():
                    st.markdown(f"- `{k}` : {v}")

            st.markdown(f"**Formule :** `{opp.formule}`")

            # Badges complexité et confiance
            cplx_icone, cplx_couleur = complexite_couleurs.get(opp.complexite, ("⚪", "#888888"))
            conf_icone, conf_couleur = confiance_couleurs.get(opp.confiance, ("❓", "#888888"))
            st.markdown(
                f"<span style='background:#F5F3EE;border:1px solid #E8E0D5;"
                f"border-radius:4px;padding:3px 8px;font-size:0.82rem;color:{cplx_couleur};'>"
                f"{cplx_icone} Complexité : {opp.complexite}</span> &nbsp;"
                f"<span style='background:#F5F3EE;border:1px solid #E8E0D5;"
                f"border-radius:4px;padding:3px 8px;font-size:0.82rem;color:{conf_couleur};'>"
                f"{conf_icone} Confiance : {opp.confiance}</span> &nbsp;"
                f"<span style='background:#F5F3EE;border:1px solid #E8E0D5;"
                f"border-radius:4px;padding:3px 8px;font-size:0.82rem;color:#1B3A5B;'>"
                f"⏱ Délai : {opp.delai_mise_en_oeuvre_jours} j</span>",
                unsafe_allow_html=True,
            )

            # Contraintes
            if opp.contraintes:
                st.markdown("**Contraintes :**")
                for c in opp.contraintes:
                    st.markdown(f"- {c}")

            # Sources
            if opp.sources:
                sources_html = " &nbsp;|&nbsp; ".join(f"<em>{s}</em>" for s in opp.sources)
                st.markdown(
                    f"<div style='font-size:0.78rem;color:#888;margin-top:6px;"
                    f"border-top:1px solid #E8E0D5;padding-top:6px;'>"
                    f"📚 {sources_html}</div>",
                    unsafe_allow_html=True,
                )

            # Note EC
            if opp.note_ec:
                st.markdown(
                    f"<div style='background:#FFF8F0;border-left:3px solid #B08D57;"
                    f"padding:8px 12px;border-radius:4px;font-size:0.9rem;color:#555;"
                    f"margin-top:8px;'>⚠️ <strong>Note EC :</strong> {opp.note_ec}</div>",
                    unsafe_allow_html=True,
                )

            # Script de restitution
            script = expliquer_opportunite(opp)
            bloc_script_restitution(script)

            # Bouton "à activer"
            deja_coche = opp.id in st.session_state.get("opportunites_a_activer", [])
            label_btn = "✅ Marquée à activer" if deja_coche else "☑️ Marquer comme à activer"
            if st.button(label_btn, key=f"activer_{opp.id}"):
                a_activer = st.session_state.get("opportunites_a_activer", [])
                if opp.id in a_activer:
                    a_activer.remove(opp.id)
                else:
                    a_activer.append(opp.id)
                st.session_state["opportunites_a_activer"] = a_activer
                st.rerun()

# ─── Section 5 — Plan d'action EC ────────────────────────────────────────────

st.divider()
st.subheader("📋 Plan d'action")

ids_a_activer = st.session_state.get("opportunites_a_activer", [])
opps_a_activer = [o for o in rapport.opportunites if o.id in ids_a_activer]

if not opps_a_activer:
    st.info(
        "ℹ️ Aucune opportunité marquée à activer pour l'instant. "
        "Cochez les opportunités ci-dessus pour construire le plan d'action."
    )
else:
    import pandas as pd

    plan_rows = []
    for rang, opp in enumerate(
        sorted(opps_a_activer, key=lambda o: o.gain_30ans_eur, reverse=True), start=1
    ):
        plan_rows.append(
            {
                "Priorité": rang,
                "Opportunité": opp.titre,
                "Gain /an": format_euro(opp.gain_annuel_eur),
                "Gain 30 ans": format_euro(opp.gain_30ans_eur),
                "Délai": f"{opp.delai_mise_en_oeuvre_jours} j",
                "Complexité": opp.complexite,
            }
        )

    st.dataframe(pd.DataFrame(plan_rows), hide_index=True, use_container_width=True)

    if st.button("📄 Export plan d'action"):
        st.info(
            "📄 Export PDF/Excel à venir en S8.2d — "
            "la fonctionnalité d'export sera branchée sur le générateur de PDF NRP."
        )

# ─── Section 6 — Hypothèses & avertissements ─────────────────────────────────

st.divider()
with st.expander("⚙️ Hypothèses & avertissements", expanded=False):
    st.markdown("### Hypothèses utilisées")

    hyp = rapport.hypotheses_utilisees
    hyp_rows = [{"Paramètre": k, "Valeur": str(v)} for k, v in hyp.items()]
    if hyp_rows:
        import pandas as pd

        st.dataframe(pd.DataFrame(hyp_rows), hide_index=True, use_container_width=True)

    if rapport.avertissements:
        st.markdown("### ⚠️ Avertissements")
        for avert in rapport.avertissements:
            st.warning(avert)

    st.markdown(
        "<div style='font-size:0.78rem;color:#888;margin-top:12px;"
        "border-top:1px solid #E8E0D5;padding-top:8px;'>"
        "⚖️ <em>Économies modélisées à hypothèses constantes. "
        "Ne constitue pas un conseil personnalisé au sens de la directive MIF II "
        "sans signature du plan d'action par l'EC et le client.</em></div>",
        unsafe_allow_html=True,
    )
