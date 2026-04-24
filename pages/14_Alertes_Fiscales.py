"""
Alertes Fiscales — Boglehead FR
Détecte les pièges fiscaux et optimisations possibles
"""

import streamlit as st

from src.fiscalite.constantes import (
    AV_DUREE_8_ANS,
    PEA_DUREE_5_ANS,
    TAUX_PFU_TOTAL,
    TAUX_PS,
)
from src.fiscalite.cto_is import detecter_piege_mtm
from src.fiscalite.pea import verifier_plafond_pea

st.set_page_config(page_title="Alertes Fiscales", page_icon="⚠️", layout="wide")

st.title("⚠️ Alertes Fiscales")
st.markdown("Détectez les pièges fiscaux et optimisez votre stratégie d'investissement.")

# Section 1 : Mark-to-Market IS
st.header("🚨 Piège Mark-to-Market (MTM) pour sociétés IS")
st.markdown(
    """
Le Mark-to-Market (Art. 209-0 A CGI) impose les **plus-values latentes** chaque année
sur les OPCVM détenus à plus de 90% par des sociétés IS.
"""
)

with st.expander("Tester une position"):
    type_actif = st.selectbox(
        "Type d'actif", ["etf", "opcvm", "sicav", "fcp", "action", "obligation"]
    )
    regime_detenteur = st.selectbox("Régime fiscal détenteur", ["is", "ir"])
    valeur_marche = st.number_input("Valeur de marché (€)", value=110000, step=1000)
    prix_acquisition = st.number_input("Prix d'acquisition (€)", value=100000, step=1000)
    pourcent_detention_is = st.number_input("% détention par sociétés IS", value=95, step=1) / 100

    if st.button("Vérifier", key="mtm"):
        position = {
            "type_actif": type_actif,
            "valeur_marche": valeur_marche,
            "prix_acquisition": prix_acquisition,
            "pourcent_detention_is": pourcent_detention_is,
        }
        alerte = detecter_piege_mtm(position, regime_detenteur)

        if alerte:
            st.error(f"🚨 {alerte['alerte']}")
            st.write(f"**Plus-value latente** : {alerte['pv_latente']:,.0f} €")
            st.write(f"**IS dû annuellement** : {alerte['is_du_annuel']:,.0f} €")
            st.write(f"**Article** : {alerte['article']}")
            st.write(f"**Conséquence** : {alerte['consequence']}")
            st.info(f"💡 **Solution** : {alerte['solution']}")
        else:
            st.success("✅ Pas de MTM détecté sur cette position")


# Section 2 : PEA < 5 ans
st.header("⏰ Durée de détention PEA")
st.markdown(
    f"""
Avant {PEA_DUREE_5_ANS} ans, le PEA n'a **pas d'avantage fiscal** significatif vs CTO.
**Attendez 5 ans** pour bénéficier de l'exonération d'IR (seuls les PS {TAUX_PS:.1%} restent dus).
"""
)

with st.expander("Vérifier votre PEA"):
    date_ouverture_pea = st.date_input("Date d'ouverture du PEA")
    date_actuelle = st.date_input("Date actuelle")

    duree_pea = (date_actuelle - date_ouverture_pea).days / 365.25

    st.metric("Durée de détention", f"{duree_pea:.1f} ans")

    if duree_pea < PEA_DUREE_5_ANS:
        temps_restant = PEA_DUREE_5_ANS - duree_pea
        st.warning(
            f"⚠️ PEA < 5 ans : **pas d'avantage fiscal**. "
            f"Attendez encore **{temps_restant:.1f} ans** avant de retirer."
        )
        st.info(
            f"💰 Économie attendue après 5 ans : **12.8%** d'IR économisés (seuls les PS {TAUX_PS:.1%} restent dus)"
        )
    else:
        st.success(
            f"✅ PEA > 5 ans : **exonération d'IR**, seuls les PS {TAUX_PS:.1%} dus. Retraits libres !"
        )


# Section 3 : Plafonds PEA/PEA-PME
st.header("📏 Plafonds PEA et PEA-PME")
st.markdown(
    """
**Plafonds de versements** :
- PEA : 150 000 €
- PEA-PME : 225 000 €
- Cumul PEA + PEA-PME : 225 000 €
"""
)

with st.expander("Vérifier vos plafonds"):
    versements_pea = st.number_input("Versements PEA (€)", value=100000, step=1000)
    versements_pea_pme = st.number_input("Versements PEA-PME (€)", value=50000, step=1000)

    result = verifier_plafond_pea(versements_pea, versements_pea_pme)

    if result["respect_plafond"]:
        st.success("✅ Plafonds respectés")
    else:
        st.error("🚨 Plafonds dépassés !")
        if result["depassement_pea"] > 0:
            st.write(f"**Dépassement PEA** : {result['depassement_pea']:,.0f} €")
        if result["depassement_pea_pme"] > 0:
            st.write(f"**Dépassement PEA-PME** : {result['depassement_pea_pme']:,.0f} €")
        if result["depassement_cumul"] > 0:
            st.write(f"**Dépassement cumul** : {result['depassement_cumul']:,.0f} €")


# Section 4 : AV < 8 ans
st.header("🕐 Durée de détention Assurance Vie")
st.markdown(
    f"""
Avant {AV_DUREE_8_ANS} ans, l'assurance vie n'offre **pas d'abattement annuel** (4 600 € / 9 200 €).
**Attendez 8 ans** pour optimiser la fiscalité de vos rachats.
"""
)

with st.expander("Vérifier votre contrat AV"):
    date_ouverture_av = st.date_input("Date d'ouverture du contrat", key="av")
    date_actuelle_av = st.date_input("Date actuelle", key="av_date")

    duree_av = (date_actuelle_av - date_ouverture_av).days / 365.25

    st.metric("Durée de détention", f"{duree_av:.1f} ans")

    if duree_av < AV_DUREE_8_ANS:
        temps_restant_av = AV_DUREE_8_ANS - duree_av
        st.warning(
            f"⚠️ AV < 8 ans : **pas d'abattement**. "
            f"Attendez encore **{temps_restant_av:.1f} ans** pour bénéficier de l'abattement."
        )
    else:
        st.success(
            "✅ AV > 8 ans : **abattement annuel** de 4 600 € (célibataire) ou 9 200 € (couple) !"
        )


# Section 5 : Option barème IR
st.header("🎯 Option barème IR vs PFU")
st.markdown(
    f"""
L'option pour le barème IR est **irrévocable** pour l'année fiscale et s'applique à
**TOUS** les revenus du capital de l'année.

**PFU** : {TAUX_PFU_TOTAL:.1%} (12.8% IR + 18.6% PS)
**Barème IR** : TMI + 18.6% PS (avec abattement 40% sur dividendes)
"""
)

st.info(
    "💡 **Règle générale** : Option barème intéressante si TMI ≤ 11% "
    "(ou si beaucoup de dividendes avec abattement 40%)"
)


# Section 6 : Contrat cap IS vs CTO IS
st.header("💼 Société IS : Contrat cap vs CTO")
st.markdown(
    """
Pour une société IS, le **contrat de capitalisation** (Art. 238 septies E CGI)
est souvent plus avantageux que le CTO avec MTM.

**Base taxable contrat cap** : 105% × TME × capital (ex: 3.15% du capital si TME 3%)
**MTM CTO** : Imposition des PV latentes chaque année
"""
)

st.success(
    "💡 **Recommandation** : Privilégier le contrat de capitalisation IS "
    "si rendement attendu > TME (ce qui est généralement le cas)"
)


# Footer
st.markdown("---")
st.caption(
    "⚠️ Alertes indicatives basées sur la réglementation 2026. "
    "Consultez un expert-comptable pour votre situation spécifique."
)
