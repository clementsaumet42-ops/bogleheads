"""Page 7 — Téléchargements : génération Excel et PDF depuis l'UI."""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

st.title("📥 Téléchargements")

# ─── Vérification du profil ───────────────────────────────────────────────────

profil = st.session_state.get("profil_actif")

if not profil:
    st.warning("⚠️ Aucun profil chargé. Veuillez d'abord configurer un profil client.")
    if st.button("👤 Aller au profil client"):
        st.switch_page("pages/2_👤_Profil.py")
    st.stop()

nom = profil.get("nom", "—") if isinstance(profil, dict) else getattr(profil, "nom", "—")
st.markdown(f"**Profil actif :** {nom}")

st.info(
    "💡 Les fichiers sont générés à la volée depuis votre profil actif. "
    "Le premier clic génère le fichier (quelques secondes), "
    "les suivants le servent depuis le cache de session."
)

st.divider()

# ─── Génération Excel ─────────────────────────────────────────────────────────


def _generer_excel_bytes() -> bytes:
    """Génère le fichier Excel et retourne les bytes."""
    from src.excel.builder import generer_excel

    with tempfile.TemporaryDirectory() as tmp_dir:
        chemin = Path(tmp_dir) / "portefeuille_bogleheads.xlsx"
        generer_excel(str(chemin))
        return chemin.read_bytes()


col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Rapport Excel")
    st.markdown(
        """
Fichier Excel complet **22 onglets** :
- Paramètres client et fiscaux
- Univers ETF (70 ETF Boglehead)
- Allocation cible optimisée
- Asset location × enveloppes
- Projection Monte-Carlo
- Plan de rebalancement
- Reporting client
"""
    )

    if st.session_state.get("excel_bytes") is None:
        if st.button("⚙️ Générer le fichier Excel", type="primary", use_container_width=True):
            with st.spinner("Génération du rapport Excel en cours… (peut prendre ~30s)"):
                try:
                    st.session_state["excel_bytes"] = _generer_excel_bytes()
                    st.success("✅ Fichier Excel généré avec succès !")
                    st.rerun()
                except Exception as exc:
                    st.error(f"❌ Erreur lors de la génération Excel : {exc}")
    else:
        st.success("✅ Fichier Excel prêt au téléchargement.")
        st.download_button(
            label="⬇️ Télécharger le fichier Excel",
            data=st.session_state["excel_bytes"],
            file_name="portefeuille_bogleheads.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
        )
        if st.button("🔄 Régénérer Excel", use_container_width=True):
            st.session_state["excel_bytes"] = None
            st.rerun()

with col2:
    # ─── Génération PDF ───────────────────────────────────────────────────────
    st.subheader("📄 Rapport PDF client")
    st.markdown(
        """
Rapport PDF personnalisé **13 pages** :
- Couverture et synthèse exécutive
- Profil client et patrimoine actuel
- Philosophie Boglehead
- Allocation cible et asset location
- Univers ETF recommandé
- Projection Monte-Carlo
- Plan de rebalancement
- Fiscalité et transmission
- Suivi et mentions légales
"""
    )

    if st.session_state.get("pdf_bytes") is None:
        if st.button("⚙️ Générer le rapport PDF", type="primary", use_container_width=True):
            with st.spinner("Génération du PDF client en cours… (peut prendre ~30s)"):
                try:
                    from src.pdf_builder import charger_config_pdf, generer_pdf
                    from src.schemas import Profil

                    profil_obj = Profil.model_validate(profil)
                    config_pdf = charger_config_pdf()

                    with tempfile.TemporaryDirectory() as tmp_dir:
                        chemin_pdf = Path(tmp_dir) / f"boglehead_{nom.replace(' ', '_')}.pdf"
                        generer_pdf(profil_obj, config_pdf, chemin_pdf)
                        st.session_state["pdf_bytes"] = chemin_pdf.read_bytes()

                    st.success("✅ PDF généré avec succès !")
                    st.rerun()
                except Exception as exc:
                    st.error(f"❌ Erreur lors de la génération PDF : {exc}")
    else:
        st.success("✅ Rapport PDF prêt au téléchargement.")
        nom_fichier = f"boglehead_{nom.replace(' ', '_').replace('/', '_')}.pdf"
        st.download_button(
            label="⬇️ Télécharger le rapport PDF",
            data=st.session_state["pdf_bytes"],
            file_name=nom_fichier,
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )

        # Aperçu PDF inline via iframe base64
        try:
            import base64

            b64 = base64.b64encode(st.session_state["pdf_bytes"]).decode("utf-8")
            st.markdown("**Aperçu du PDF :**")
            pdf_display = (
                f'<iframe src="data:application/pdf;base64,{b64}" '
                'width="100%" height="500px" type="application/pdf">'
                "</iframe>"
            )
            st.markdown(pdf_display, unsafe_allow_html=True)
        except Exception:
            # Aperçu iframe optionnel — l'échec (navigateur sans plugin PDF,
            # taille base64 trop grande) ne doit pas bloquer le téléchargement.
            pass

        if st.button("🔄 Régénérer PDF", use_container_width=True):
            st.session_state["pdf_bytes"] = None
            st.rerun()

st.divider()
st.caption(
    "⚠️ *Les documents générés sont illustratifs et ne constituent pas un conseil "
    "en investissement personnalisé au sens de la directive MIF II.*"
)

if st.button("🔄 ← Rebalancement"):
    st.switch_page("pages/6_🔄_Rebalancement.py")
