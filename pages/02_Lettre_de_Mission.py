"""Page 02 — Lettre de Mission CIF : DER et Lettre de Mission."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
import yaml

st.set_page_config(page_title="Lettre de Mission", page_icon="📋")
st.title("📋 Lettre de Mission CIF")
st.caption("Document d'Entrée en Relation & Lettre de Mission — Art. L.541-8-1 CMF")

ROOT = Path(__file__).parent.parent
config_path = ROOT / "config" / "cabinet_cif.yaml"

config = {}
if config_path.exists():
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

cab = config.get("cabinet", {})

st.subheader("Informations du cabinet")
nom = st.text_input("Nom du cabinet", value=cab.get("nom", ""))
prenom_ec = st.text_input("Prénom du conseiller", value=cab.get("prenom_ec", ""))
nom_ec = st.text_input("Nom du conseiller", value=cab.get("nom_ec", ""))
orias = st.text_input("N° ORIAS", value=cab.get("numero_orias", ""))

st.subheader("Informations client")
client_nom = st.text_input("Nom du client", value="Dupont")
client_prenom = st.text_input("Prénom du client", value="Jean")
client_email = st.text_input("Email du client", value="jean.dupont@exemple.fr")

col1, col2 = st.columns(2)

with col1:
    if st.button("📄 Générer le DER"):
        from src.cif.der import generer_der

        out = ROOT / "output" / "der_client.pdf"
        config_cabinet = {
            "cabinet": {
                "nom": nom,
                "nom_ec": nom_ec,
                "prenom_ec": prenom_ec,
                "numero_orias": orias,
                "adresse": "",
                "telephone": "",
                "email": "",
                "rc_pro_assureur": "",
                "rc_pro_numero": "",
                "mediateur_nom": "Médiateur de l'AMF",
                "mediateur_url": "https://www.amf-france.org",
            },
            "remuneration": {
                "mode": "honoraires",
                "mention_retrocessions": "Aucune rétrocession perçue",
            },
        }
        path = generer_der(config_cabinet, out)
        with open(path, "rb") as f:
            st.download_button(
                "⬇ Télécharger le DER", f, file_name="DER.pdf", mime="application/pdf"
            )
        st.success("DER généré avec succès.")

with col2:
    if st.button("📝 Générer la Lettre de Mission"):
        from src.cif.lettre_mission import generer_lettre_mission

        out = ROOT / "output" / "lettre_mission_client.pdf"
        config_cabinet = {
            "cabinet": {
                "nom": nom,
                "nom_ec": nom_ec,
                "prenom_ec": prenom_ec,
                "numero_orias": orias,
                "adresse": "",
                "email": "",
            },
            "remuneration": {
                "mode": "honoraires",
                "mention_retrocessions": "Aucune rétrocession perçue",
            },
            "tarifs": {
                "mission_initiale_forfait_eur": 3000,
                "suivi_annuel_forfait_eur": 1200,
                "taux_horaire_eur": 250,
            },
        }
        client_info = {
            "nom": client_nom,
            "prenom": client_prenom,
            "adresse": "",
            "email": client_email,
        }
        path = generer_lettre_mission(config_cabinet, client_info, out)
        with open(path, "rb") as f:
            st.download_button(
                "⬇ Télécharger la Lettre", f, file_name="lettre_mission.pdf", mime="application/pdf"
            )
        st.success("Lettre de mission générée avec succès.")

# ─── Aperçu HTML ──────────────────────────────────────────────────────────────

st.divider()
st.subheader("👁 Aperçu de la lettre de mission")

preview_html = f"""
<div style="font-family: Georgia, serif; max-width: 680px; margin: 0 auto;
            border: 1px solid #B08D57; border-radius: 8px; padding: 32px 40px;
            background: #FAFAF8; color: #1B3A5B;">
  <h2 style="text-align:center; font-size:1.4rem; border-bottom:2px solid #B08D57;
             padding-bottom:12px; margin-bottom:20px;">
    LETTRE DE MISSION — CONSEIL EN INVESTISSEMENTS FINANCIERS
  </h2>
  <p><strong>Cabinet :</strong> {nom or "—"}<br>
     <strong>Conseiller :</strong> {prenom_ec or ""} {nom_ec or ""}<br>
     <strong>N° ORIAS :</strong> {orias or "—"}
  </p>
  <hr style="border:none; border-top:1px solid #E0D8CC; margin:16px 0;">
  <p><strong>Client :</strong> {client_prenom} {client_nom}<br>
     <strong>Email :</strong> {client_email}
  </p>
  <hr style="border:none; border-top:1px solid #E0D8CC; margin:16px 0;">
  <p style="font-size:0.9rem; color:#555;">
    La présente lettre de mission est établie conformément aux articles L.541-1 et suivants
    du Code monétaire et financier. Elle définit les modalités de la relation entre le
    Conseiller en Investissements Financiers (CIF) et le client.
  </p>
  <p style="font-size:0.85rem; color:#888; margin-top:20px;">
    <em>Document généré par Boglehead FR — usage interne CIF uniquement.</em>
  </p>
</div>
"""

st.html(preview_html)

st.divider()
st.info("💡 Pour générer la version finale signable, utilisez la page dédiée à la conformité CIF.")
if st.button("📄 Générer la version finale signable →", type="secondary"):
    st.switch_page("pages/21_Conformite_CIF.py")
