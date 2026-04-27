"""
Simulateur Fiscal — Boglehead FR
Calcule la fiscalité d'une opération avec cascade détaillée
"""

import streamlit as st

from src.fiscalite import (
    calculer_fiscalite_operation,
)
from src.ui.theme import injecter_css

st.set_page_config(page_title="Simulateur Fiscal", page_icon="🏛️", layout="wide")

injecter_css()

st.title("Simulateur Fiscal")
st.markdown("Calculez la fiscalité détaillée de vos opérations d'investissement.")

# Sidebar : profil contribuable
st.sidebar.header("Profil fiscal")
situation = st.sidebar.selectbox("Situation familiale", ["celibataire", "couple"])
rfr = st.sidebar.number_input("RFR (Revenu Fiscal de Référence)", value=50000, step=1000)
tmi = st.sidebar.selectbox(
    "TMI (Taux Marginal d'Imposition)", [0.0, 0.11, 0.30, 0.41, 0.45], index=2
)

profil = {"situation": situation, "rfr": rfr, "tmi": tmi}

# Main : simulation
st.header("Simulation")

type_operation = st.selectbox(
    "Type d'opération",
    [
        "Cession CTO (PFU)",
        "Retrait PEA",
        "Rachat Assurance Vie",
        "Sortie PER",
    ],
)

montant_brut = st.number_input("Montant brut de l'opération (€)", value=10000, step=100)
gains = st.number_input("Part de plus-value / gains (€)", value=5000, step=100)

# Paramètres spécifiques
if type_operation == "Retrait PEA":
    duree_detention = st.number_input("Durée de détention (années)", value=6.0, step=0.1)
    cas_force_majeure = st.checkbox("Cas de force majeure (invalidité, décès, etc.)")

    operation = {
        "type": "retrait_pea",
        "montant_brut": montant_brut,
        "gains": gains,
        "duree_detention": duree_detention,
        "type_pea": "pea",
        "cas_force_majeure": cas_force_majeure,
    }

elif type_operation == "Cession CTO (PFU)":
    option_bareme = st.checkbox("Option barème IR (au lieu du PFU)")

    operation = {
        "type": "cession_cto",
        "montant_brut": montant_brut,
        "gains": gains,
        "option_bareme": option_bareme,
        "type_revenu": "pv",
    }

else:
    # Simulation simple PFU pour autres cas
    operation = {
        "type": "cession_cto",
        "montant_brut": gains,
        "gains": gains,
        "option_bareme": False,
    }

# Calcul
if st.button("Calculer", type="primary"):
    try:
        result = calculer_fiscalite_operation(operation, profil)

        # Affichage résultat
        st.success("Calcul terminé")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Montant brut", f"{result.montant_brut:,.0f} €")
        with col2:
            st.metric("Impôts totaux", f"{result.total_impots:,.0f} €")
        with col3:
            st.metric("Montant net", f"{result.montant_net:,.0f} €")
        with col4:
            st.metric("Taux effectif", f"{result.taux_effectif:.1%}")

        # Cascade détaillée
        st.subheader("Cascade fiscale détaillée")
        if result.cascade:
            import pandas as pd

            df = pd.DataFrame(
                [
                    {
                        "Libellé": ligne.libelle,
                        "Montant": f"{ligne.montant:,.2f} €",
                        "Formule": ligne.formule,
                        "Source": ligne.source,
                    }
                    for ligne in result.cascade
                ]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)

        # Articles cités
        if result.articles_cites:
            st.subheader("Articles de loi cités")
            for article in result.articles_cites:
                if article:
                    st.caption(f"• {article}")

        # Avertissements
        if result.avertissements:
            st.subheader("Avertissements")
            for avert in result.avertissements:
                st.warning(avert)

    except Exception as e:
        st.error(f"Erreur lors du calcul : {e}")
        st.exception(e)

# Footer
st.markdown("---")
st.caption("Simulation indicative. Consultez un expert-comptable pour votre situation personnelle.")
