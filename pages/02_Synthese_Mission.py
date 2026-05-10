"""Page 02 — Synthese mission.

Vue d'ensemble dense d'une mission unique, conçue pour deux usages :

1. **Travail EC** : ouvrir le matin, voir ou j'en suis, decider la
   prochaine action en 30 secondes.
2. **RDV client** : presentation a partager a l'ecran. Big numbers,
   trade-offs explicites, talking points pour structurer l'echange.

Cette page ne remplace pas Mission_EC (qui reste la checklist
d'avancement) : elle est l'angle "metier" qu'on ouvrirait avec le
client en face. Elle est lue, jamais saisie.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from src.mission.etat import EtatMission, charger_mission, lister_missions
from src.mission.parcours import (
    PHASES_PARCOURS,
    phase_courante,
    progression_par_phase,
)
from src.mission.progress import calculer_progression
from src.ui.parcours_widget import afficher_bandeau_parcours, afficher_carte_phase
from src.ui.theme import (
    ARDOISE,
    OR_VIEILLI,
    injecter_css,
)

st.set_page_config(page_title="Synthese mission", page_icon="📋", layout="wide")
injecter_css()


# ─── Selection de la mission ─────────────────────────────────────────────────


def _selectionner_mission() -> EtatMission | None:
    missions = lister_missions()
    if not missions:
        st.info("Aucune mission enregistree. Creez-en une depuis la page Mission EC.")
        st.page_link("pages/00_Mission_EC.py", label="Aller a Mission EC")
        return None

    mission_id_actif = st.session_state.get("mission_id")
    ids = [m.mission_id for m in missions]
    labels = {m.mission_id: f"{m.nom_client} ({m.mission_id})" for m in missions}
    idx = ids.index(mission_id_actif) if mission_id_actif in ids else 0
    selection = st.selectbox(
        "Mission",
        options=ids,
        format_func=lambda x: labels.get(x, x),
        index=idx,
    )
    st.session_state["mission_id"] = selection
    try:
        return charger_mission(selection)
    except FileNotFoundError:
        return None


etat = _selectionner_mission()
if etat is None:
    st.stop()


# ─── En-tete mission ─────────────────────────────────────────────────────────

phase = phase_courante(etat)
prog = calculer_progression(etat)
jours_inactif = (date.today() - etat.date_derniere_maj).days

st.title(etat.nom_client)
col_h1, col_h2, col_h3 = st.columns([2, 2, 1])
with col_h1:
    st.caption(
        f"Mission **{etat.mission_id}** — EC {etat.cgp} — creee le {etat.date_creation.isoformat()}"
    )
with col_h2:
    st.caption(
        f"Phase courante : **{phase.numero} — {phase.titre}** ({prog['pct_global']} % global)"
    )
with col_h3:
    couleur_maj = OR_VIEILLI if jours_inactif <= 30 else "#A65A4E"
    st.markdown(
        f'<div style="text-align:right;font-size:12px;color:{couleur_maj};">'
        f"Derniere MAJ : {etat.date_derniere_maj.isoformat()} "
        f"({jours_inactif} j)</div>",
        unsafe_allow_html=True,
    )


# ─── Bandeau parcours ────────────────────────────────────────────────────────

afficher_bandeau_parcours(etat, page_courante="02_Synthese_Mission.py")


# ─── KPIs patrimoine ─────────────────────────────────────────────────────────


def _kpis_patrimoine(etat: EtatMission) -> dict:
    """Agrege les KPIs lisibles depuis les imports_patrimoine."""
    imports = etat.imports_patrimoine or []
    total = 0.0
    par_type: dict[str, float] = {}
    nb_lignes = 0
    for imp in imports:
        valeur = (
            imp.get("valeur_totale")
            or imp.get("valorisation_totale")
            or imp.get("encours_total")
            or 0.0
        )
        total += float(valeur or 0)
        type_env = (imp.get("type_enveloppe") or imp.get("type") or "Autre").upper()
        par_type[type_env] = par_type.get(type_env, 0.0) + float(valeur or 0)
        positions = imp.get("positions") or imp.get("lignes") or []
        nb_lignes += len(positions)
    return {
        "total": total,
        "par_type": par_type,
        "nb_releves": len(imports),
        "nb_lignes": nb_lignes,
    }


kpis = _kpis_patrimoine(etat)
profil_actif = st.session_state.get("profil_actif") or {}
profil_valide = bool(profil_actif) and prog["pct_par_rdv"].get("RDV1", 0) > 50

st.subheader("Patrimoine et profil")

col_p1, col_p2, col_p3, col_p4 = st.columns(4)
with col_p1:
    st.metric(
        "Patrimoine importe",
        f"{kpis['total']:,.0f} €".replace(",", " "),
        delta=f"{kpis['nb_releves']} releve(s)",
    )
with col_p2:
    st.metric("Lignes detectees", kpis["nb_lignes"])
with col_p3:
    st.metric("Profil MIF II", "Valide" if profil_valide else "A completer")
with col_p4:
    st.metric("Etapes bloquees", len(prog.get("etapes_bloquees", [])))

if kpis["par_type"]:
    st.caption(
        "Repartition par enveloppe : "
        + " · ".join(
            f"**{k}** {v:,.0f} €".replace(",", " ")
            for k, v in sorted(kpis["par_type"].items(), key=lambda x: -x[1])
        )
    )


# ─── Talking points contextuels ──────────────────────────────────────────────

TALKING_POINTS_PAR_PHASE: dict[str, list[str]] = {
    "qualification": [
        "Confirmer avec le client la pertinence d'une mission CIF dediee.",
        "Annoncer le pricing indicatif (5 a 15 k€ HT) et la duree (4 semaines).",
        "Clarifier que cette mission est independante de la mission d'expertise comptable.",
    ],
    "onboarding": [
        "Saisir le foyer : situation familiale, revenus, regime matrimonial.",
        "Faire passer le questionnaire MIF II : connaissance, experience, "
        "tolerance au risque, capacite de perte, horizon, objectifs.",
        "Generer DER + lettre de mission, envoyer pour signature eIDAS.",
    ],
    "diagnostic": [
        "Importer les 3 a 8 derniers releves PDF (PEA, AV, CTO, PEE...).",
        "Valider chaque ligne ligne par ligne — jamais de merge silencieux.",
        "Presenter au client la friction fiscale ANNUELLE actuelle "
        "(en € et en bps) — c'est l'argument economique cle.",
        "Hierarchiser les alertes : concentration, frais courants, pieges "
        "MIF II, fonds bloques, retenues source UK.",
    ],
    "recommandations": [
        "Proposer une allocation cible Boglehead adaptee au profil "
        "(ex. 60/40 ou 70/30) avec coeur indiciel mondial.",
        "Justifier l'asset location MILP : pour chaque ETF, dans quelle "
        "enveloppe et pourquoi (defendabilite fiscale).",
        "Faire valider l'allocation par le client — toujours modifiable, jamais imposee.",
    ],
    "plan_action": [
        "Presenter la cascade trimestrielle : versements cibles sur les "
        "enveloppes sous-ponderees, en priorite.",
        "Chiffrer le COUT FISCAL EVITE vs un rebalancement naïf — c'est "
        "le ROI defendable a presenter au client.",
        "Lister les arbitrages eventuels en privilegiant les enveloppes "
        "sans friction (PEA antériorité, AV >8 ans, PEE débloqué).",
        "Remettre les ordres prets a passer (CSV ou copie-broker).",
    ],
    "livrables": [
        "Generer le ZIP horodate : PDF diagnostic, DER, LM, RAA, Excel, "
        "CSV ordres, journal de mission.",
        "Verifier la conformite CIF et la signature eIDAS de tous les documents reglementaires.",
        "Transmettre au client par canal securise et obtenir l'accuse de reception.",
    ],
    "suivi_annuel": [
        "Re-importer les releves a J+12 mois et comparer realise vs cible.",
        "Chiffrer la friction fiscale REELLEMENT evitee vs scenario naïf.",
        "Mettre a jour le DER si situation foyer ou objectifs ont evolue.",
        "Produire le nouveau plan 12 mois pour l'annee a venir.",
    ],
}


st.subheader(f"Que faire avec le client en phase {phase.numero}")
points = TALKING_POINTS_PAR_PHASE.get(phase.cle, [])
for i, point in enumerate(points, 1):
    st.markdown(
        f'<div style="display:flex;gap:8px;margin-bottom:6px;">'
        f'<span style="color:{OR_VIEILLI};font-weight:600;'
        f'min-width:20px;">{i}.</span>'
        f'<span style="color:{ARDOISE};">{point}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )


# ─── Cartes phases avec progression ──────────────────────────────────────────

st.subheader("Etat detaille du parcours")

progressions = progression_par_phase(etat)
col_left, col_right = st.columns(2)
phases_gauche = [p for p in PHASES_PARCOURS if p.numero in (1, 2, 3, 4)]
phases_droite = [p for p in PHASES_PARCOURS if p.numero in (5, 6, 7)]

with col_left:
    for ph in phases_gauche:
        afficher_carte_phase(ph, progressions.get(ph.numero, 0))
with col_right:
    for ph in phases_droite:
        afficher_carte_phase(ph, progressions.get(ph.numero, 0))


# ─── Pied : prochaine action ────────────────────────────────────────────────

st.divider()
prochaine_etape = prog.get("prochaine_etape")
col_pied_l, col_pied_r = st.columns([3, 1])
with col_pied_l:
    if prochaine_etape:
        st.markdown(
            f"**Prochaine action concrete** : {prochaine_etape.titre}  \n"
            f"_{prochaine_etape.description}_"
        )
    else:
        st.markdown("**Mission terminee** — passer en suivi annuel.")
with col_pied_r:
    if (
        prochaine_etape
        and prochaine_etape.page_streamlit
        and st.button("Y aller", use_container_width=True, key="_cta_pied")
    ):
        st.switch_page(f"pages/{prochaine_etape.page_streamlit}")
