"""Page 21 — Conformité CIF : DER, Lettre de Mission, Rapport d'Adéquation."""

from __future__ import annotations

import logging
from pathlib import Path

import streamlit as st
import yaml

from src.ui.theme import injecter_css

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Conformité CIF", page_icon="🏛️", layout="wide")
injecter_css()

st.title("Conformité CIF — Documents réglementaires")
st.caption(
    "DER · Lettre de Mission · Rapport d'Adéquation MIF II — "
    "Art. L.541-1 CMF / Art. 325-3 & 325-5 RG AMF / Art. 25(6) MIF II"
)

ROOT = Path(__file__).parent.parent
OUTPUT_DIR = ROOT / "output"
ARCHIVE_DIR = ROOT / "output" / "clients"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ─── Chargement configs ────────────────────────────────────────────────────────


def _load_yaml(path: Path) -> dict:
    if path.exists():
        try:
            return yaml.safe_load(path.open(encoding="utf-8")) or {}
        except Exception as e:
            logger.warning("Impossible de charger %s : %s", path, e)
    return {}


cabinet_raw = _load_yaml(ROOT / "config" / "cabinet_cif.yaml")
if not cabinet_raw:
    cabinet_raw = _load_yaml(ROOT / "config" / "pdf_cabinet.yaml")

conformite_raw = _load_yaml(ROOT / "config" / "conformite.yaml")

profil_raw = st.session_state.get("profil_actif")

# Try to validate with schemas
cabinet = None
conformite = None
try:
    from src.schemas import ConformiteConfig

    if conformite_raw:
        conformite = ConformiteConfig.model_validate(conformite_raw)
except Exception:
    conformite = conformite_raw or None

try:
    from src.schemas import CabinetConfig

    if cabinet_raw:
        cabinet = CabinetConfig.model_validate(cabinet_raw)
except Exception:
    cabinet = cabinet_raw or None

# Derive client nom for display
client_nom_display = "—"
profil_id_display = 0
if profil_raw is not None:
    try:
        client_nom_display = (
            profil_raw.get("nom", "—")
            if isinstance(profil_raw, dict)
            else getattr(profil_raw, "nom", "—")
        ) or "—"
        profil_id_display = (
            profil_raw.get("id", 0)
            if isinstance(profil_raw, dict)
            else getattr(profil_raw, "id", 0)
        ) or 0
    except Exception:
        pass


# ─── Avertissement si pas de profil ───────────────────────────────────────────

if profil_raw is None:
    st.warning(
        "Aucun profil client actif. Chargez un profil via la page **Profilage** "
        "ou **Dossiers** pour activer la génération des documents."
    )

# ─── Tabs principaux ──────────────────────────────────────────────────────────

tab_dash, tab_der, tab_lm, tab_ra, tab_archives = st.tabs(
    [
        "Dashboard",
        "DER",
        "Lettre de Mission",
        "Rapport d'Adéquation",
        "Archives",
    ]
)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 0 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

with tab_dash:
    st.subheader(f"Statut conformité — Client : {client_nom_display}")

    try:
        from src.conformite.archivage import lister_documents_client

        docs = lister_documents_client(profil_id_display, ARCHIVE_DIR)
    except Exception:
        docs = []

    types_presents = {d.type_doc for d in docs}
    types_signes = {d.type_doc for d in docs if d.signe}

    col1, col2, col3 = st.columns(3)
    with col1:
        if "DER" in types_signes:
            st.success("DER — Signé")
        elif "DER" in types_presents:
            st.warning("DER — Généré, non signé")
        else:
            st.error("DER — Non généré")
    with col2:
        if "LETTRE_MISSION" in types_signes:
            st.success("Lettre de Mission — Signée")
        elif "LETTRE_MISSION" in types_presents:
            st.warning("Lettre de Mission — Générée, non signée")
        else:
            st.error("Lettre de Mission — Non générée")
    with col3:
        if "RAPPORT_ADEQUATION" in types_signes:
            st.success("Rapport d'Adéquation — Signé")
        elif "RAPPORT_ADEQUATION" in types_presents:
            st.warning("Rapport d'Adéquation — Généré, non signé")
        else:
            st.error("Rapport d'Adéquation — Non généré")

    if docs:
        st.markdown(f"**{len(docs)} document(s) archivé(s)** pour ce client.")
    else:
        st.info("Aucun document archivé pour ce client.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DER
# ══════════════════════════════════════════════════════════════════════════════

with tab_der:
    st.subheader("Document d'Entrée en Relation — Art. 325-5 RG AMF")

    if profil_raw is None:
        st.warning("Chargez un profil client pour générer le DER.")
    else:
        if st.button("Générer le DER", type="primary", key="btn_gen_der"):
            try:
                from src.conformite.der import generer_der

                out_path = OUTPUT_DIR / f"der_{profil_id_display}.pdf"
                doc = generer_der(profil_raw, cabinet_raw or {}, conformite_raw or {}, out_path)
                st.session_state["der_doc"] = doc
                st.success(f"DER généré — SHA256 : `{doc.sha256[:16]}…`")
                with open(out_path, "rb") as f:
                    st.download_button(
                        "Télécharger le DER",
                        f,
                        file_name=f"DER_{client_nom_display}_{doc.date_generation[:10]}.pdf",
                        mime="application/pdf",
                    )
            except Exception as e:
                st.error(f"Erreur lors de la génération du DER : {e}")

        der_doc = st.session_state.get("der_doc")
        if der_doc is not None:
            st.divider()
            st.subheader("Signature eIDAS simple")
            nom_sig = st.text_input(
                "Nom du signataire", value=client_nom_display, key="der_nom_sig"
            )
            email_sig = st.text_input("Email du signataire", value="", key="der_email_sig")
            consentement = st.checkbox(
                "Je certifie avoir lu et accepté le Document d'Entrée en Relation (signature électronique simple eIDAS)",
                key="der_consent",
            )
            if st.button("Signer le DER", key="btn_sign_der"):
                if not consentement:
                    st.error("Cochez la case de consentement pour signer.")
                elif not email_sig:
                    st.error("Saisissez l'email du signataire.")
                else:
                    try:
                        from src.conformite.archivage import archiver_document
                        from src.conformite.signature import signer_document

                        preuve = signer_document(der_doc, nom_sig, email_sig, consentement)
                        archiver_document(der_doc, preuve, ARCHIVE_DIR)
                        st.success(
                            f"DER signé et archivé — Hash signature : `{preuve.hash_signature[:16]}…`"
                        )
                    except Exception as e:
                        st.error(f"Erreur lors de la signature : {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — LETTRE DE MISSION
# ══════════════════════════════════════════════════════════════════════════════

with tab_lm:
    st.subheader("Lettre de Mission CIF — Art. 325-3 RG AMF")

    if profil_raw is None:
        st.warning("Chargez un profil client pour générer la Lettre de Mission.")
    else:
        with st.form("form_lm"):
            st.markdown("**Paramètres de la mission**")
            col_a, col_b = st.columns(2)
            with col_a:
                lm_objet = st.text_input(
                    "Objet de la mission", value="Conseil en investissements financiers global"
                )
                lm_honoraires = st.number_input(
                    "Honoraires (€)", min_value=0.0, value=3000.0, step=100.0
                )
                lm_modalite = st.selectbox("Modalité", ["forfait", "horaire", "pct_actifs"])
            with col_b:
                lm_perimetre = st.multiselect(
                    "Périmètre",
                    [
                        "audit",
                        "allocation",
                        "fiscalite",
                        "suivi_annuel",
                        "PEA",
                        "assurance-vie",
                        "PER",
                        "CTO",
                    ],
                    default=["audit", "allocation"],
                )
                lm_duree = st.number_input("Durée (mois)", min_value=1, value=12)
                lm_date_debut = st.date_input("Date de début")

            submitted = st.form_submit_button("Générer la Lettre de Mission", type="primary")

        if submitted:
            try:
                from src.conformite.lettre_mission import generer_lettre_mission

                parametres = {
                    "objet": lm_objet,
                    "perimetre": lm_perimetre,
                    "honoraires_eur": lm_honoraires,
                    "honoraires_modalite": lm_modalite,
                    "duree_mois": lm_duree,
                    "date_debut": str(lm_date_debut),
                }
                out_path = OUTPUT_DIR / f"lettre_mission_{profil_id_display}.pdf"
                doc = generer_lettre_mission(
                    profil_raw, cabinet_raw or {}, conformite_raw or {}, parametres, out_path
                )
                st.session_state["lm_doc"] = doc
                st.success(f"Lettre de Mission générée — SHA256 : `{doc.sha256[:16]}…`")
                with open(out_path, "rb") as f:
                    st.download_button(
                        "Télécharger la Lettre de Mission",
                        f,
                        file_name=f"LM_{client_nom_display}_{doc.date_generation[:10]}.pdf",
                        mime="application/pdf",
                    )
            except Exception as e:
                st.error(f"Erreur : {e}")

        lm_doc = st.session_state.get("lm_doc")
        if lm_doc is not None:
            st.divider()
            st.subheader("Signature eIDAS simple")
            lm_nom_sig = st.text_input(
                "Nom du signataire", value=client_nom_display, key="lm_nom_sig"
            )
            lm_email_sig = st.text_input("Email du signataire", value="", key="lm_email_sig")
            lm_consent = st.checkbox(
                "Je certifie avoir lu et accepté la Lettre de Mission (signature électronique simple eIDAS)",
                key="lm_consent",
            )
            if st.button("Signer la Lettre de Mission", key="btn_sign_lm"):
                if not lm_consent:
                    st.error("Cochez la case de consentement pour signer.")
                elif not lm_email_sig:
                    st.error("Saisissez l'email du signataire.")
                else:
                    try:
                        from src.conformite.archivage import archiver_document
                        from src.conformite.signature import signer_document

                        preuve = signer_document(lm_doc, lm_nom_sig, lm_email_sig, lm_consent)
                        archiver_document(lm_doc, preuve, ARCHIVE_DIR)
                        st.success(
                            f"Lettre de Mission signée et archivée — `{preuve.hash_signature[:16]}…`"
                        )
                    except Exception as e:
                        st.error(f"Erreur lors de la signature : {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — RAPPORT D'ADÉQUATION
# ══════════════════════════════════════════════════════════════════════════════

with tab_ra:
    st.subheader("Rapport d'Adéquation — Art. 25(6) MIF II")

    if profil_raw is None:
        st.warning("Chargez un profil client pour générer le Rapport d'Adéquation.")
    else:
        allocation_cible = st.session_state.get("allocation_cible") or {}
        etfs_retenus = st.session_state.get("etfs_retenus") or []

        if not allocation_cible:
            st.info(
                "ℹ Aucune allocation cible en session. "
                "Générez une allocation via la page **Allocation** pour pré-remplir ce rapport."
            )

        if st.button("Générer le Rapport d'Adéquation", type="primary", key="btn_gen_ra"):
            try:
                from src.conformite.rapport_adequation import generer_rapport_adequation

                out_path = OUTPUT_DIR / f"rapport_adequation_{profil_id_display}.pdf"
                doc = generer_rapport_adequation(
                    profil_raw,
                    cabinet_raw or {},
                    conformite_raw or {},
                    allocation_cible,
                    etfs_retenus,
                    out_path,
                )
                st.session_state["ra_doc"] = doc
                st.success(f"Rapport d'Adéquation généré — SHA256 : `{doc.sha256[:16]}…`")
                with open(out_path, "rb") as f:
                    st.download_button(
                        "Télécharger le Rapport d'Adéquation",
                        f,
                        file_name=f"RA_{client_nom_display}_{doc.date_generation[:10]}.pdf",
                        mime="application/pdf",
                    )
            except Exception as e:
                st.error(f"Erreur : {e}")

        ra_doc = st.session_state.get("ra_doc")
        if ra_doc is not None:
            st.divider()
            st.subheader("Signature eIDAS simple")
            ra_nom_sig = st.text_input(
                "Nom du signataire", value=client_nom_display, key="ra_nom_sig"
            )
            ra_email_sig = st.text_input("Email du signataire", value="", key="ra_email_sig")
            ra_consent = st.checkbox(
                "Je certifie avoir lu et accepté le Rapport d'Adéquation (signature électronique simple eIDAS)",
                key="ra_consent",
            )
            if st.button("Signer le Rapport d'Adéquation", key="btn_sign_ra"):
                if not ra_consent:
                    st.error("Cochez la case de consentement pour signer.")
                elif not ra_email_sig:
                    st.error("Saisissez l'email du signataire.")
                else:
                    try:
                        from src.conformite.archivage import archiver_document
                        from src.conformite.signature import signer_document

                        preuve = signer_document(ra_doc, ra_nom_sig, ra_email_sig, ra_consent)
                        archiver_document(ra_doc, preuve, ARCHIVE_DIR)
                        st.success(f"Rapport signé et archivé — `{preuve.hash_signature[:16]}…`")
                    except Exception as e:
                        st.error(f"Erreur lors de la signature : {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — ARCHIVES
# ══════════════════════════════════════════════════════════════════════════════

with tab_archives:
    st.subheader("Archives des documents conformité")

    try:
        from src.conformite.archivage import lister_documents_client, verifier_integrite_dossier

        docs_arch = lister_documents_client(profil_id_display, ARCHIVE_DIR)
        if not docs_arch:
            st.info("Aucun document archivé pour ce client.")
        else:
            import pandas as pd

            rows = []
            for d in docs_arch:
                rows.append(
                    {
                        "Type": d.type_doc,
                        "Client": d.client_nom,
                        "Date génération": d.date_generation[:19],
                        "Signé": "" if d.signe else "",
                        "Date signature": (d.date_signature or "")[:19],
                        "Version": d.version_template,
                        "SHA256": d.sha256[:16] + "…",
                    }
                )
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

            if st.button("Vérifier l'intégrité des PDFs", key="btn_verify"):
                resultats = verifier_integrite_dossier(profil_id_display, ARCHIVE_DIR)
                if not resultats:
                    st.warning("Aucun fichier à vérifier.")
                else:
                    ok = sum(1 for v in resultats.values() if v)
                    ko = sum(1 for v in resultats.values() if not v)
                    if ko == 0:
                        st.success(f"Intégrité vérifiée — {ok} fichier(s) intact(s).")
                    else:
                        st.error(f"{ko} fichier(s) altéré(s) / manquant(s) sur {ok + ko}.")
                    for chemin, valide in resultats.items():
                        icon = "" if valide else ""
                        st.text(f"{icon} {chemin}")
    except Exception as e:
        st.error(f"Erreur lors de la lecture des archives : {e}")
