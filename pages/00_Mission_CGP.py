"""Page 00 — Mission CGP : fil conducteur et checklist de mission."""

from __future__ import annotations

import io
import logging
from datetime import date
from pathlib import Path

import streamlit as st

from src.mission.checklist import ETAPES_CANONIQUES, PHASES
from src.mission.etat import (
    EtatEtape,
    EtatMission,
    charger_mission,
    creer_mission,
    lister_missions,
    sauvegarder_mission,
    supprimer_mission,
)
from src.mission.progress import calculer_progression

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Mission CGP", page_icon="🗂️", layout="wide")
st.title("🗂️ Mission CGP — Fil conducteur")
st.caption("Pilotez votre mission de bout en bout : de la prise en charge au suivi M+3.")

# ─── Section 1 — Sélecteur de mission ────────────────────────────────────────

st.subheader("1. Sélection de la mission")

missions = lister_missions()
mission_ids = [m.mission_id for m in missions]
labels = {m.mission_id: f"{m.nom_client} ({m.mission_id})" for m in missions}

col_sel, col_new, col_del = st.columns([4, 2, 1])

with col_sel:
    if mission_ids:
        selected_id = st.selectbox(
            "Mission active",
            options=mission_ids,
            format_func=lambda x: labels.get(x, x),
            index=mission_ids.index(st.session_state.get("mission_id", mission_ids[0]))
            if st.session_state.get("mission_id") in mission_ids
            else 0,
        )
        st.session_state["mission_id"] = selected_id
    else:
        st.info("Aucune mission — créez-en une avec le bouton ci-contre.")
        selected_id = None
        st.session_state["mission_id"] = None

with col_new:
    with st.popover("➕ Nouvelle mission"):
        nc = st.text_input("Nom du client", key="_new_nom_client")
        cgp = st.text_input("CGP", key="_new_cgp")
        if st.button("Créer", key="_btn_creer_mission"):
            if nc and cgp:
                nouvelle = creer_mission(nc, cgp)
                st.session_state["mission_id"] = nouvelle.mission_id
                st.success(f"Mission **{nouvelle.mission_id}** créée ✅")
                st.rerun()
            else:
                st.warning("Renseignez le nom du client et le CGP.")

with col_del:
    if selected_id and st.button("🗑️", key="_btn_del_mission", help="Supprimer la mission"):
        st.session_state["_confirm_delete"] = True

if st.session_state.get("_confirm_delete") and selected_id:
    st.warning(f"⚠️ Confirmer la suppression de **{selected_id}** ?")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Oui, supprimer", key="_btn_confirm_del"):
            supprimer_mission(selected_id)
            st.session_state["mission_id"] = None
            st.session_state["_confirm_delete"] = False
            st.success("Mission supprimée.")
            st.rerun()
    with c2:
        if st.button("Annuler", key="_btn_cancel_del"):
            st.session_state["_confirm_delete"] = False
            st.rerun()

# Si aucune mission sélectionnée, on s'arrête
if not st.session_state.get("mission_id"):
    st.stop()

# Chargement de la mission active
try:
    etat: EtatMission = charger_mission(st.session_state["mission_id"])
except FileNotFoundError:
    st.error("Mission introuvable.")
    st.stop()

progression = calculer_progression(etat)

# ─── Section 2 — En-tête mission active ───────────────────────────────────────

st.divider()
st.subheader("2. Mission active")

col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("Client", etat.nom_client)
col_b.metric("CGP", etat.cgp)
col_c.metric("Créée le", etat.date_creation.strftime("%d/%m/%Y"))
col_d.metric("Mise à jour", etat.date_derniere_maj.strftime("%d/%m/%Y"))

pct = progression["pct_global"]
pct_obl = progression["pct_obligatoire"]
st.progress(
    pct / 100, text=f"Avancement global : **{pct}%** — Étapes obligatoires : **{pct_obl}%**"
)

# Badge statut global
etapes_bloquees = progression["etapes_bloquees"]
rdv1_pct = progression["pct_par_rdv"].get("RDV1", 0)
rdv2_pct = progression["pct_par_rdv"].get("RDV2", 0)

if etapes_bloquees:
    st.error(f"🔴 Bloqué — {len(etapes_bloquees)} étape(s) bloquée(s)")
elif rdv1_pct == 100 and rdv2_pct < 100:
    st.warning("🟡 En cours d'analyse — RDV1 prêt, RDV2 en préparation")
elif rdv1_pct < 100:
    st.info(f"🔵 En cours — RDV1 : {rdv1_pct}%")
else:
    st.success("🟢 Mission avancée — tous les RDV préparés")

# ─── Section 3 — Checklist visuelle ───────────────────────────────────────────

st.divider()
st.subheader("3. Checklist de mission")

STATUT_OPTIONS = [e.value for e in EtatEtape]
STATUT_LABELS = {e.value: f"{e.value} {e.name.replace('_', ' ').title()}" for e in EtatEtape}

changed = False

for phase in PHASES:
    etapes_phase = [e for e in ETAPES_CANONIQUES if e.phase == phase]
    if not etapes_phase:
        continue

    with st.expander(f"**Phase : {phase}**", expanded=True):
        for etape in etapes_phase:
            statut = etat.etapes.get(etape.cle, EtatEtape.NON_COMMENCE)
            est_bloque = etape in etapes_bloquees

            col_ico, col_titre, col_page, col_statut = st.columns([1, 5, 2, 2])

            with col_ico:
                st.markdown(f"## {statut.value}")

            with col_titre:
                badge = " 🔒" if est_bloque else (" ⭐" if etape.obligatoire else "")
                st.markdown(f"**{etape.titre}**{badge}")
                st.caption(etape.description)
                if etape.livrables:
                    st.caption("📎 " + " · ".join(etape.livrables))
                # Note libre
                note_key = f"_note_{etape.cle}"
                note = st.text_area(
                    "Notes",
                    value=etat.notes.get(etape.cle, ""),
                    key=note_key,
                    height=60,
                    label_visibility="collapsed",
                    placeholder="Notes libres...",
                )
                if note != etat.notes.get(etape.cle, ""):
                    etat.notes[etape.cle] = note
                    changed = True

            with col_page:
                if etape.page_streamlit:
                    page_path = Path("pages") / etape.page_streamlit
                    if page_path.exists():
                        st.page_link(str(page_path), label="→ Aller à la page")
                    else:
                        st.caption(f"📄 {etape.page_streamlit}")

            with col_statut:
                idx = STATUT_OPTIONS.index(statut.value)
                nouveau_val = st.selectbox(
                    "Statut",
                    options=STATUT_OPTIONS,
                    format_func=lambda v: STATUT_LABELS[v],
                    index=idx,
                    key=f"_statut_{etape.cle}",
                    label_visibility="collapsed",
                    disabled=est_bloque and statut == EtatEtape.NON_COMMENCE,
                )
                if nouveau_val != statut.value:
                    etat.etapes[etape.cle] = EtatEtape(nouveau_val)
                    changed = True

if changed:
    sauvegarder_mission(etat)
    st.rerun()

# ─── Section 4 — Vue Gantt simple ─────────────────────────────────────────────

st.divider()
st.subheader("4. Vue d'ensemble (ordre & dépendances)")

import pandas as pd  # noqa: E402

gantt_rows = []
for etape in ETAPES_CANONIQUES:
    statut = etat.etapes.get(etape.cle, EtatEtape.NON_COMMENCE)
    est_bloque = etape in etapes_bloquees
    gantt_rows.append(
        {
            "Phase": etape.phase,
            "Étape": etape.titre,
            "Statut": statut.value,
            "Obligatoire": "⭐" if etape.obligatoire else "",
            "Dépendances": ", ".join(etape.depends_on) if etape.depends_on else "—",
            "Bloqué": "🔒" if est_bloque else "",
            "RDV": etape.rdv or "—",
        }
    )

df_gantt = pd.DataFrame(gantt_rows)


def _colorize_statut(val: str) -> str:
    colors_map = {
        EtatEtape.VALIDE.value: "background-color: #d4edda; color: #155724;",
        EtatEtape.EN_COURS.value: "background-color: #fff3cd; color: #856404;",
        EtatEtape.BLOQUE.value: "background-color: #f8d7da; color: #721c24;",
        EtatEtape.NON_COMMENCE.value: "background-color: #f8f9fa; color: #6c757d;",
        EtatEtape.SKIP.value: "background-color: #e2e3e5; color: #383d41;",
    }
    return colors_map.get(val, "")


styled = df_gantt.style.applymap(_colorize_statut, subset=["Statut"])
st.dataframe(styled, use_container_width=True, hide_index=True)

# ─── Section 5 — Alertes & blocages ───────────────────────────────────────────

st.divider()
st.subheader("5. Alertes & blocages")

alertes = progression["alertes"]
prochaine = progression["prochaine_etape"]

if alertes:
    for alerte in alertes:
        st.warning(alerte)
else:
    st.success("✅ Aucun blocage détecté.")

if prochaine:
    st.info(f"**Prochaine action recommandée :** {prochaine.titre} — {prochaine.description}")

# Métriques RDV
if progression["pct_par_rdv"]:
    cols_rdv = st.columns(len(progression["pct_par_rdv"]))
    for i, (rdv, pct_rdv) in enumerate(progression["pct_par_rdv"].items()):
        cols_rdv[i].metric(f"Avancement {rdv}", f"{pct_rdv}%")

# ─── Section 6 — Export PDF récap mission ─────────────────────────────────────

st.divider()
st.subheader("6. Export récap mission")


def _generer_pdf_recap(etat: EtatMission, prog: dict) -> bytes:
    """Génère un PDF 1 page de récapitulatif de mission via ReportLab."""
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    titre_style = ParagraphStyle(
        "TitreMission",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=6,
    )
    sub_style = ParagraphStyle(
        "SousTitre",
        parent=styles["Normal"],
        fontSize=11,
        spaceAfter=4,
    )
    normal = styles["Normal"]

    story = []
    story.append(Paragraph("Récapitulatif Mission CGP", titre_style))
    story.append(
        Paragraph(
            f"Client : <b>{etat.nom_client}</b> — CGP : {etat.cgp} "
            f"— Créée le {etat.date_creation.strftime('%d/%m/%Y')}",
            sub_style,
        )
    )
    story.append(
        Paragraph(
            f"Avancement global : <b>{prog['pct_global']}%</b> "
            f"— Étapes obligatoires : <b>{prog['pct_obligatoire']}%</b>",
            sub_style,
        )
    )
    story.append(Spacer(1, 0.5 * cm))

    # Tableau checklist
    data = [["Statut", "Étape", "Phase", "Obligatoire"]]
    for etape in ETAPES_CANONIQUES:
        statut = etat.etapes.get(etape.cle, EtatEtape.NON_COMMENCE)
        data.append(
            [
                statut.value,
                etape.titre,
                etape.phase,
                "Oui" if etape.obligatoire else "Non",
            ]
        )

    tbl = Table(data, colWidths=[1.5 * cm, 9 * cm, 3 * cm, 2.5 * cm])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#1B3A5B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [rl_colors.white, rl_colors.HexColor("#F5F5F5")],
                ),
                ("GRID", (0, 0), (-1, -1), 0.25, rl_colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(tbl)
    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            f"Généré le {date.today().strftime('%d/%m/%Y')} — Outil CGP Boglehead FR",
            normal,
        )
    )

    doc.build(story)
    return buf.getvalue()


if st.button("📄 Exporter récap mission (PDF 1 page)"):
    try:
        pdf_bytes = _generer_pdf_recap(etat, progression)
        st.download_button(
            label="⬇️ Télécharger le récap PDF",
            data=pdf_bytes,
            file_name=f"recap_mission_{etat.mission_id}.pdf",
            mime="application/pdf",
        )
    except Exception as exc:
        st.error(f"Erreur lors de la génération du PDF : {exc}")
        logger.exception("Erreur génération PDF récap")

# ─── Section hypothèses & sources (S17) ──────────────────────────────────────

st.divider()
st.subheader("📚 Hypothèses & Sources")
st.caption("Registre des hypothèses actives — sources citées, versions, snapshots.")

with st.expander("Voir les hypothèses actives"):
    try:
        import pandas as pd

        from src.hypotheses.catalogue import lister_hypotheses_par_categorie

        par_cat = lister_hypotheses_par_categorie()
        lignes = []
        for _cat, hyps in sorted(par_cat.items()):
            for h in sorted(hyps, key=lambda x: x.cle):
                src = h.sources[0] if h.sources else None
                lignes.append(
                    {
                        "Clé": h.cle,
                        "Valeur": f"{h.valeur} {h.unite}",
                        "Catégorie": h.categorie,
                        "Source": src.organisme if src else "—",
                        "Confiance": h.confiance,
                        "Version": h.version,
                    }
                )
        st.dataframe(pd.DataFrame(lignes), use_container_width=True, hide_index=True)
        st.caption("Liste complète et sources détaillées → page 23 « Hypothèses ».")
    except Exception as exc:
        st.warning(f"Hypothèses non disponibles : {exc}")

# ─── Snapshots ───────────────────────────────────────────────────────────────

if "mission_id" in st.session_state and st.session_state["mission_id"]:
    _mid = st.session_state["mission_id"]
    col_snap1, col_snap2 = st.columns([3, 1])
    with col_snap1:
        st.markdown("**Snapshots d'hypothèses** — traçabilité en cas de contestation future.")
    with col_snap2:
        if st.button("📎 Figer un snapshot maintenant"):
            try:
                from src.hypotheses.snapshot import creer_snapshot, sauvegarder_snapshot

                snap = creer_snapshot(_mid)
                chemin = sauvegarder_snapshot(snap)
                st.success(f"✅ Snapshot figé : {chemin.name}")
                st.caption(f"Hash SHA-256 : `{snap.hash_integrite[:16]}…`")
            except Exception as exc:
                st.error(f"Erreur lors du snapshot : {exc}")

    try:
        from src.hypotheses.snapshot import lister_snapshots

        snaps = lister_snapshots(_mid)
        if snaps:
            st.markdown(f"**{len(snaps)} snapshot(s) disponible(s)** pour cette mission :")
            for s_path in reversed(snaps[-5:]):
                st.markdown(f"- `{s_path.name}`")
            # Bouton diff entre les 2 derniers snapshots
            if len(snaps) >= 2 and st.button("🔍 Comparer les 2 derniers snapshots"):
                try:
                    import json

                    from src.hypotheses.snapshot import SnapshotHypotheses
                    from src.hypotheses.versionnage import comparer_snapshots

                    snap_a = SnapshotHypotheses.from_dict(
                        json.loads(snaps[-2].read_text(encoding="utf-8"))
                    )
                    snap_b = SnapshotHypotheses.from_dict(
                        json.loads(snaps[-1].read_text(encoding="utf-8"))
                    )
                    diff = comparer_snapshots(snap_a, snap_b)
                    if diff["modifiees"]:
                        st.warning(f"⚠️ {len(diff['modifiees'])} hypothèse(s) modifiée(s) :")
                        for m in diff["modifiees"]:
                            st.markdown(f"  - `{m['cle']}` : {m['delta_valeur']}")
                    if diff["ajoutees"]:
                        st.info(
                            f"➕ {len(diff['ajoutees'])} ajoutée(s) : {[h.cle for h in diff['ajoutees']]}"
                        )
                    if diff["retirees"]:
                        st.info(
                            f"➖ {len(diff['retirees'])} retirée(s) : {[h.cle for h in diff['retirees']]}"
                        )
                    if not diff["modifiees"] and not diff["ajoutees"] and not diff["retirees"]:
                        st.success("✅ Aucun changement entre les deux snapshots.")
                except Exception as exc:
                    st.error(f"Erreur comparaison : {exc}")
        else:
            st.caption("Aucun snapshot enregistré pour cette mission.")
    except Exception:
        pass
