"""Widget réutilisable pour la mise à jour d'étapes mission depuis n'importe quelle page."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def widget_mission_etape(cle_etape: str, label: str | None = None) -> None:
    """Affiche un widget compact pour marquer une étape de mission.

    Usage en bas d'une page Streamlit existante :

        from src.mission.widgets import widget_mission_etape
        widget_mission_etape("allocation_cible")

    Si aucune mission n'est active en session_state, le widget est silencieux.
    """
    try:
        import streamlit as st

        from src.mission.checklist import ETAPES_PAR_CLE
        from src.mission.etat import EtatEtape, charger_mission, sauvegarder_mission

        mission_id = st.session_state.get("mission_id")
        if not mission_id:
            return

        etape = ETAPES_PAR_CLE.get(cle_etape)
        if etape is None:
            return

        titre = label or etape.titre

        try:
            etat = charger_mission(mission_id)
        except FileNotFoundError:
            return

        statut_actuel = etat.etapes.get(cle_etape, EtatEtape.NON_COMMENCE)

        with st.expander(f"📋 Mission : {etat.nom_client}", expanded=False):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Étape :** {titre}")
                st.caption(f"Statut actuel : {statut_actuel.value} {statut_actuel.name}")
            with col2:
                options = [e.value for e in EtatEtape]
                idx = options.index(statut_actuel.value)
                nouveau = st.selectbox(
                    "Statut",
                    options=options,
                    index=idx,
                    key=f"_widget_mission_{cle_etape}",
                    label_visibility="collapsed",
                )
                if nouveau != statut_actuel.value:
                    etat.etapes[cle_etape] = EtatEtape(nouveau)
                    sauvegarder_mission(etat)
                    st.success(f"✅ Étape « {titre} » mise à jour.")
                    st.rerun()

    except Exception as exc:
        logger.debug("widget_mission_etape non disponible : %s", exc)
