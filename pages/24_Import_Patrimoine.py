"""Page 24 — Import Patrimoine depuis PDF — Sprint S20."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from src.ui.theme import injecter_css

st.set_page_config(page_title="Import Patrimoine PDF", layout="wide")
injecter_css()
st.title("Import Patrimoine depuis PDF")
st.caption(
    "Importez des relevés PDF pour alimenter le patrimoine de la mission active. "
    "Chaque ligne extraite doit être validée individuellement avant import."
)

# ─── Imports métier ──────────────────────────────────────────────────────────

try:
    from src.import_patrimoine.audit import enregistrer_import
    from src.import_patrimoine.extracteur import extraire_pdf
    from src.import_patrimoine.modele import ImportPDF, LignePatrimoine
    from src.mission.etat import charger_mission, lister_missions, sauvegarder_mission
except Exception as exc:
    st.error(f"Erreur de chargement des modules : {exc}")
    st.stop()

# ─── Sélection de la mission active ─────────────────────────────────────────

missions = lister_missions()
if not missions:
    st.warning("Aucune mission active. Créez une mission dans la page Missions avant d'importer.")
    st.stop()

mission_options = {f"{m.mission_id} — {m.nom_client}": m.mission_id for m in missions}
mission_label = st.selectbox("Mission active", list(mission_options.keys()), index=0)
mission_id = mission_options[mission_label]

try:
    mission = charger_mission(mission_id)
except Exception as exc:
    st.error(f"Impossible de charger la mission : {exc}")
    st.stop()

st.info(f"Mission : **{mission.nom_client}** | ID : `{mission_id}`")

# ─── Upload PDF ──────────────────────────────────────────────────────────────

st.divider()
st.subheader("1. Téléverser des relevés PDF")

fichiers = st.file_uploader(
    "Sélectionner un ou plusieurs relevés PDF",
    type=["pdf"],
    accept_multiple_files=True,
)

if not fichiers:
    st.info("Veuillez téléverser au moins un fichier PDF.")
    st.stop()

# ─── Extraction des lignes ───────────────────────────────────────────────────

st.divider()
st.subheader("2. Lignes extraites — Révision et validation")

if "lignes_extraites" not in st.session_state:
    st.session_state["lignes_extraites"] = []
if "resultats_extractions" not in st.session_state:
    st.session_state["resultats_extractions"] = {}

# Traitement des PDFs uploadés
for fichier in fichiers:
    nom = fichier.name
    contenu = fichier.read()
    pdf_hash = hashlib.sha256(contenu).hexdigest()

    if pdf_hash not in st.session_state["resultats_extractions"]:
        chemin_tmp = Path(f"output/.import_tmp_{pdf_hash[:8]}.pdf")
        chemin_tmp.parent.mkdir(parents=True, exist_ok=True)
        chemin_tmp.write_bytes(contenu)

        with st.spinner(f"Extraction de {nom}..."):
            try:
                resultat = extraire_pdf(chemin_tmp)
                st.session_state["resultats_extractions"][pdf_hash] = resultat
                for avert in resultat.avertissements:
                    st.warning(f"{nom} : {avert}")
            except Exception as exc:
                st.error(f"Erreur lors de l'extraction de {nom} : {exc}")
                continue
            finally:
                if chemin_tmp.exists():
                    chemin_tmp.unlink()

# Collecte toutes les lignes de tous les PDFs extraits
toutes_lignes: list[LignePatrimoine] = []
for resultat in st.session_state["resultats_extractions"].values():
    toutes_lignes.extend(resultat.lignes)

if not toutes_lignes:
    st.warning(
        "Aucune ligne extraite automatiquement. "
        "Vérifiez le format des PDF ou saisissez les données manuellement."
    )
    for res in st.session_state["resultats_extractions"].values():
        if res.texte_brut:
            with st.expander(f"Texte brut extrait — {res.pdf_nom}"):
                st.text(res.texte_brut[:3000])
    st.stop()

# ─── Tableau de révision ─────────────────────────────────────────────────────


def _statut_confiance(score: int) -> str:
    if score >= 80:
        return "Vert"
    elif score >= 50:
        return "Orange"
    return "Rouge"


lignes_df_data = []
for i, ligne in enumerate(toutes_lignes):
    lignes_df_data.append(
        {
            "_idx": i,
            "Valider": False,
            "Statut": _statut_confiance(ligne.confiance),
            "ISIN": ligne.isin or "",
            "Nom actif": ligne.nom_actif,
            "Quantite": ligne.quantite if ligne.quantite is not None else "",
            "Valorisation EUR": ligne.valorisation_eur,
            "Enveloppe": ligne.enveloppe,
            "Broker": ligne.broker_emetteur,
            "Contrat AV": ligne.contrat_av or "",
            "Type actif": ligne.type_actif,
            "Devise": ligne.devise,
            "Page": ligne.source_page,
            "Confiance": ligne.confiance,
        }
    )

df_lignes = pd.DataFrame(lignes_df_data)

# Colonnes affichées dans data_editor
cols_affichees = [
    "Valider",
    "Statut",
    "ISIN",
    "Nom actif",
    "Quantite",
    "Valorisation EUR",
    "Enveloppe",
    "Broker",
    "Contrat AV",
    "Type actif",
    "Devise",
    "Page",
    "Confiance",
]

st.markdown(
    f"**{len(toutes_lignes)} ligne(s) extraite(s)** — cochez 'Valider' pour chaque ligne "
    "à importer, puis cliquez sur le bouton d'import."
)

col_btn1, col_btn2, _ = st.columns([2, 2, 4])

with col_btn1:
    if st.button("Valider toutes les lignes vertes"):
        for i, row in df_lignes.iterrows():
            if row["Statut"] == "Vert":
                df_lignes.at[i, "Valider"] = True
        st.session_state["df_lignes_override"] = df_lignes.copy()
        st.rerun()

with col_btn2:
    if st.button("Valider toutes (avec confirmation)"):
        st.session_state["confirm_valider_tout"] = True

if st.session_state.get("confirm_valider_tout"):
    st.warning(
        "Confirmer la validation de TOUTES les lignes, y compris celles à confiance faible ?"
    )
    c1, c2 = st.columns(2)
    if c1.button("Oui, valider tout"):
        for i in df_lignes.index:
            df_lignes.at[i, "Valider"] = True
        st.session_state["df_lignes_override"] = df_lignes.copy()
        st.session_state["confirm_valider_tout"] = False
        st.rerun()
    if c2.button("Annuler"):
        st.session_state["confirm_valider_tout"] = False
        st.rerun()

# Utiliser l'override si présent
if "df_lignes_override" in st.session_state:
    df_edit_init = st.session_state["df_lignes_override"][cols_affichees]
else:
    df_edit_init = df_lignes[cols_affichees]

df_edite = st.data_editor(
    df_edit_init,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Valider": st.column_config.CheckboxColumn("Valider", default=False),
        "Statut": st.column_config.TextColumn("Statut"),
        "Confiance": st.column_config.ProgressColumn(
            "Confiance", min_value=0, max_value=100, format="%d"
        ),
        "Valorisation EUR": st.column_config.NumberColumn("Valorisation EUR", format="%.2f €"),
    },
    key="data_editor_lignes",
)

# ─── Résumé de la sélection ──────────────────────────────────────────────────

nb_validees = int(df_edite["Valider"].sum())
nb_total = len(df_edite)
toutes_traitees = nb_validees > 0

st.caption(
    f"{nb_validees} ligne(s) cochée(s) sur {nb_total}. "
    "Le bouton d'import sera actif dès qu'au moins une ligne est validée."
)

# ─── Import dans la mission ──────────────────────────────────────────────────

st.divider()
st.subheader("3. Importer dans la mission")

import_desactive = not toutes_traitees

if st.button(
    "Importer les lignes validées dans la mission",
    disabled=import_desactive,
    type="primary",
):
    lignes_a_importer: list[LignePatrimoine] = []
    lignes_rejetees: list[LignePatrimoine] = []

    valider_col = df_edite["Valider"].tolist()
    for i, ligne in enumerate(toutes_lignes):
        if i < len(valider_col) and valider_col[i]:
            lignes_a_importer.append(ligne)
        else:
            lignes_rejetees.append(ligne)

    # Grouper par PDF source
    pdfs_importes: dict[str, dict] = {}
    for res in st.session_state["resultats_extractions"].values():
        pdfs_importes[res.pdf_nom] = {
            "pdf_hash": res.pdf_hash,
            "emetteur": res.emetteur_detecte,
            "template": res.template_utilise,
        }

    for pdf_nom, meta in pdfs_importes.items():
        lignes_pdf_val = [lg for lg in lignes_a_importer if lg.source_pdf == pdf_nom]
        lignes_pdf_rej = [lg for lg in lignes_rejetees if lg.source_pdf == pdf_nom]

        import_pdf = ImportPDF(
            pdf_nom=pdf_nom,
            pdf_hash=meta["pdf_hash"],
            timestamp_import=datetime.now(timezone.utc).isoformat(),
            emetteur_detecte=meta["emetteur"],
            template_utilise=meta["template"],
            lignes_validees=lignes_pdf_val,
            lignes_rejetees=lignes_pdf_rej,
        )
        mission.ajouter_import(import_pdf)
        try:
            enregistrer_import(mission_id, import_pdf)
        except Exception as exc:
            st.warning(f"Audit non enregistré pour {pdf_nom} : {exc}")

    try:
        sauvegarder_mission(mission)
        st.success(
            f"{len(lignes_a_importer)} ligne(s) importée(s) dans la mission "
            f"**{mission.nom_client}**."
        )
        # Nettoyage de l'état pour permettre un nouvel import
        st.session_state.pop("lignes_extraites", None)
        st.session_state.pop("resultats_extractions", None)
        st.session_state.pop("df_lignes_override", None)
    except Exception as exc:
        st.error(f"Erreur lors de la sauvegarde de la mission : {exc}")

# ─── Historique des imports ──────────────────────────────────────────────────

st.divider()
st.subheader("Historique des imports pour cette mission")

if mission.imports_patrimoine:
    for imp in reversed(mission.imports_patrimoine):
        nb_val = len(imp.get("lignes_validees", []))
        nb_rej = len(imp.get("lignes_rejetees", []))
        ts = imp.get("timestamp_import", "")[:19].replace("T", " ")
        emetteur = imp.get("emetteur_detecte") or "Inconnu"
        with st.expander(
            f"{imp.get('pdf_nom', '?')} — {emetteur} — {ts} "
            f"({nb_val} validée(s), {nb_rej} rejetée(s))"
        ):
            if imp.get("lignes_validees"):
                st.markdown("**Lignes validées :**")
                rows_val = [
                    {
                        "ISIN": lg.get("isin") or "",
                        "Nom": lg.get("nom_actif", ""),
                        "Valorisation EUR": lg.get("valorisation_eur", 0),
                        "Enveloppe": lg.get("enveloppe", ""),
                        "Type": lg.get("type_actif", ""),
                        "Confiance": lg.get("confiance", 0),
                    }
                    for lg in imp["lignes_validees"]
                ]
                st.dataframe(pd.DataFrame(rows_val), use_container_width=True, hide_index=True)
else:
    st.info("Aucun import enregistré pour cette mission.")

# ─── Pied de page ────────────────────────────────────────────────────────────

st.divider()
st.caption(
    "Import patrimoine PDF — Sprint S20. "
    "Toutes les extractions sont 100% locales, aucun envoi de données vers des services tiers."
)
