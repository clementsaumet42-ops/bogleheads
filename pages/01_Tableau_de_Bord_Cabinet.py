"""Page 01 — Tableau de bord cabinet.

Vue d'ensemble multi-missions destinee a l'EC qui pilote 10-30 dossiers
patrimoniaux par an.

Repond au manque UX critique : aujourd'hui une instance Sextant ne montre
qu'UNE mission a la fois (page 00_Mission_EC). Le cabinet ne voit pas son
portefeuille de missions, ne peut pas prioriser, ne mesure pas son flux.

Affiche :
- KPIs cabinet : nb missions actives, repartition par phase, prochaines actions
- Tableau missions : nom, progression, prochaine etape, derniere MAJ
- Filtres : phase, statut
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from src.mission.checklist import PHASES
from src.mission.etat import EtatMission, lister_missions
from src.mission.progress import calculer_progression
from src.ui.theme import injecter_css

st.set_page_config(page_title="Tableau de bord cabinet", page_icon="📊", layout="wide")
injecter_css()

# ─── En-tete ──────────────────────────────────────────────────────────────────

st.title("Tableau de bord cabinet")
st.caption("Pilotage multi-missions — vue d'ensemble du portefeuille de dossiers")

missions = lister_missions()

if not missions:
    st.info(
        "Aucune mission enregistree. Creez une premiere mission depuis la page "
        "Mission EC pour la voir apparaitre ici."
    )
    st.page_link("pages/00_Mission_EC.py", label="Aller a la page Mission EC")
    st.stop()


# ─── Calcul agrege ────────────────────────────────────────────────────────────


def _statut_mission(progression: dict) -> str:
    """Statut synthetique d'une mission selon son avancement."""
    pct = progression["pct_global"]
    if pct >= 100:
        return "Terminee"
    if pct >= 75:
        return "Livrables"
    if pct >= 40:
        return "Analyse"
    return "Demarrage"


def _phase_courante(etat: EtatMission, progression: dict) -> str:
    """Phase de la prochaine etape a traiter."""
    prochaine = progression.get("prochaine_etape")
    if prochaine is None:
        return "Suivi"
    return prochaine.phase


def _jours_depuis_maj(etat: EtatMission) -> int:
    return (date.today() - etat.date_derniere_maj).days


def _est_inactive(etat: EtatMission, seuil_jours: int = 30) -> bool:
    return _jours_depuis_maj(etat) > seuil_jours


# Construit le DataFrame
lignes = []
for m in missions:
    prog = calculer_progression(m)
    prochaine = prog.get("prochaine_etape")
    lignes.append(
        {
            "Mission": m.nom_client,
            "ID": m.mission_id,
            "EC": m.cgp,
            "Phase": _phase_courante(m, prog),
            "Statut": _statut_mission(prog),
            "Progression": prog["pct_global"],
            "Pct obligatoires": prog["pct_obligatoire"],
            "Prochaine etape": prochaine.titre if prochaine else "Mission terminee",
            "Derniere MAJ": m.date_derniere_maj,
            "Jours inactivite": _jours_depuis_maj(m),
            "Inactive": _est_inactive(m),
            "Alertes": len(prog.get("alertes", [])),
            "Bloquees": len(prog.get("etapes_bloquees", [])),
        }
    )

df = pd.DataFrame(lignes)

# ─── KPIs cabinet ────────────────────────────────────────────────────────────

st.subheader("Indicateurs cabinet")

col1, col2, col3, col4 = st.columns(4)
nb_total = len(df)
nb_actives = (df["Statut"] != "Terminee").sum()
nb_inactives = df["Inactive"].sum()
nb_bloquees = (df["Bloquees"] > 0).sum()

with col1:
    st.metric("Missions actives", f"{nb_actives}", delta=f"{nb_total} au total")
with col2:
    st.metric("A relancer (>30j)", f"{int(nb_inactives)}")
with col3:
    st.metric("Avec etapes bloquees", f"{int(nb_bloquees)}")
with col4:
    pct_moyen = round(df["Progression"].mean()) if not df.empty else 0
    st.metric("Progression moyenne", f"{pct_moyen} %")

# ─── Repartition par phase ───────────────────────────────────────────────────

st.subheader("Repartition des missions par phase")

repartition = df.groupby("Phase").size().reset_index(name="Nombre")
# Ordonner selon PHASES canoniques
ordre = {p: i for i, p in enumerate(PHASES)}
repartition["_ordre"] = repartition["Phase"].map(lambda p: ordre.get(p, 99))
repartition = repartition.sort_values("_ordre").drop("_ordre", axis=1)

cols = st.columns(max(1, len(repartition)))
for i, (_, row) in enumerate(repartition.iterrows()):
    with cols[i]:
        st.metric(row["Phase"], int(row["Nombre"]))


# ─── Filtres + tableau ───────────────────────────────────────────────────────

st.subheader("Liste des missions")

col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
with col_f1:
    phases_options = ["Toutes"] + PHASES
    phase_filtre = st.selectbox("Filtrer par phase", phases_options, index=0)
with col_f2:
    statuts = ["Tous", "Demarrage", "Analyse", "Livrables", "Terminee"]
    statut_filtre = st.selectbox("Filtrer par statut", statuts, index=0)
with col_f3:
    inactivite_filtre = st.checkbox("A relancer uniquement (inactives > 30j)", value=False)

df_filtre = df.copy()
if phase_filtre != "Toutes":
    df_filtre = df_filtre[df_filtre["Phase"] == phase_filtre]
if statut_filtre != "Tous":
    df_filtre = df_filtre[df_filtre["Statut"] == statut_filtre]
if inactivite_filtre:
    df_filtre = df_filtre[df_filtre["Inactive"]]

if df_filtre.empty:
    st.info("Aucune mission ne correspond aux filtres.")
else:
    # Affichage tableau enrichi
    df_aff = df_filtre[
        [
            "Mission",
            "EC",
            "Phase",
            "Statut",
            "Progression",
            "Prochaine etape",
            "Derniere MAJ",
            "Jours inactivite",
            "Bloquees",
            "Alertes",
        ]
    ].copy()
    df_aff["Derniere MAJ"] = df_aff["Derniere MAJ"].apply(lambda d: d.isoformat())
    st.dataframe(
        df_aff,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Progression": st.column_config.ProgressColumn(
                "Progression",
                min_value=0,
                max_value=100,
                format="%d %%",
            ),
            "Bloquees": st.column_config.NumberColumn(
                "Bloquees",
                help="Nombre d'etapes bloquees par dependances non validees",
            ),
            "Alertes": st.column_config.NumberColumn(
                "Alertes",
                help="Alertes actives sur la mission",
            ),
        },
    )

# ─── Actions prioritaires ────────────────────────────────────────────────────

st.subheader("Actions prioritaires (top 5)")

# Priorite : missions inactives + missions avec etapes bloquees
priorites = df.copy()
priorites["score_priorite"] = (
    priorites["Inactive"].astype(int) * 5
    + priorites["Bloquees"] * 3
    + priorites["Alertes"] * 2
    + (100 - priorites["Progression"]) * 0.05
)
priorites = priorites.sort_values("score_priorite", ascending=False).head(5)

if priorites.empty:
    st.info("Aucune action prioritaire identifiee.")
else:
    for _, row in priorites.iterrows():
        col_l, col_r = st.columns([4, 1])
        with col_l:
            raison = []
            if row["Inactive"]:
                raison.append(f"inactive depuis {int(row['Jours inactivite'])} jours")
            if row["Bloquees"] > 0:
                raison.append(f"{int(row['Bloquees'])} etape(s) bloquee(s)")
            if row["Alertes"] > 0:
                raison.append(f"{int(row['Alertes'])} alerte(s)")
            if not raison:
                raison.append(f"progression {int(row['Progression'])} %")
            st.markdown(
                f"**{row['Mission']}** — {row['Prochaine etape']}  \n_{' · '.join(raison)}_"
            )
        with col_r:
            if st.button("Ouvrir", key=f"_open_{row['ID']}"):
                st.session_state["mission_id"] = row["ID"]
                st.switch_page("pages/00_Mission_EC.py")


# ─── Pied de page : export ───────────────────────────────────────────────────

st.divider()

col_ex1, col_ex2 = st.columns(2)
with col_ex1:
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Telecharger le tableau (CSV)",
        data=csv_bytes,
        file_name=f"tableau_bord_cabinet_{date.today().isoformat()}.csv",
        mime="text/csv",
    )
with col_ex2:
    st.caption(f"Genere le {date.today().isoformat()} — {nb_total} mission(s) — Sextant")
