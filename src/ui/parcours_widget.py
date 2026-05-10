"""Bandeau de navigation parcours mission — composant reutilisable.

A injecter en haut de chaque page Streamlit liee a une mission. Affiche :
    - les 7 phases du parcours VISION en bandeau horizontal
    - la phase courante mise en avant
    - le pct de completion par phase
    - un CTA "prochaine action" cliquable

Aligne charte S19 : aucun emoji, palette Private Banking, Lucide via
src.ui.components.icone_lucide.
"""

from __future__ import annotations

import streamlit as st

from src.mission.etat import EtatMission, charger_mission
from src.mission.parcours import (
    PHASES_PARCOURS,
    PhaseParcours,
    phase_courante,
    phase_d_une_page,
    prochaine_page_recommandee,
    progression_par_phase,
    talking_points_pour_phase,
)
from src.ui.theme import (
    ARDOISE,
    ARDOISE_CLAIRE,
    BLANC_CASSE,
    IVOIRE,
    OR_VIEILLI,
    VERT_FORET,
)


def _couleur_phase(numero: int, phase_active_num: int, pct: int) -> tuple[str, str, str]:
    """Renvoie (background, border, text) selon le statut de la phase."""
    if pct >= 100:
        return (VERT_FORET, VERT_FORET, "#FFFFFF")
    if numero == phase_active_num:
        return (OR_VIEILLI, OR_VIEILLI, "#FFFFFF")
    if numero < phase_active_num:
        return (BLANC_CASSE, ARDOISE_CLAIRE, ARDOISE)
    return (IVOIRE, "#D8CFC0", ARDOISE_CLAIRE)


def afficher_bandeau_parcours(
    etat: EtatMission | None,
    page_courante: str | None = None,
) -> None:
    """Affiche le bandeau parcours en haut d'une page mission.

    Args:
        etat : etat de la mission active. Si None, le widget est silencieux
            (cas page d'accueil ou hors mission).
        page_courante : nom du fichier page (ex '05_Allocation.py') pour
            mettre en evidence la phase courante meme si l'etat est neuf.
    """
    if etat is None:
        return

    phase_active = phase_courante(etat)
    phase_active_num = phase_active.numero

    # Override : si on est sur une page connue, on met en evidence sa phase
    if page_courante:
        phase_page = phase_d_une_page(page_courante)
        if phase_page is not None:
            phase_active_num = phase_page.numero

    progressions = progression_par_phase(etat)

    # Construction des cellules HTML
    cellules = []
    for phase in PHASES_PARCOURS:
        pct = progressions.get(phase.numero, 0)
        bg, border, text_color = _couleur_phase(phase.numero, phase_active_num, pct)
        is_active = phase.numero == phase_active_num
        weight = "600" if is_active else "500"
        # Indicateur de progression (barre fine en bas)
        bar = (
            f'<div style="height:3px;background:rgba(255,255,255,0.4);'
            f'width:{pct}%;margin-top:6px;border-radius:2px;"></div>'
            if pct > 0
            else ""
        )
        cellule = f"""
<div style="
    flex:1 1 0;
    min-width:0;
    background:{bg};
    border:1px solid {border};
    border-radius:6px;
    padding:8px 10px;
    color:{text_color};
    font-family:Inter,system-ui,sans-serif;
    font-size:11px;
    font-weight:{weight};
    line-height:1.3;
    overflow:hidden;
    text-overflow:ellipsis;
">
    <div style="
        text-transform:uppercase;
        letter-spacing:1.2px;
        font-size:9px;
        opacity:0.85;
    ">Phase {phase.numero}</div>
    <div style="font-weight:{weight};margin-top:2px;">{phase.titre}</div>
    {bar}
</div>
"""
        cellules.append(cellule)

    sep = '<div style="width:6px;flex-shrink:0;"></div>'
    bandeau_html = (
        '<div style="display:flex;flex-direction:row;align-items:stretch;'
        f'margin:8px 0 18px 0;gap:0;">{sep.join(cellules)}</div>'
    )
    st.markdown(bandeau_html, unsafe_allow_html=True)

    # Ligne d'objectif et de CTA
    col_obj, col_cta = st.columns([3, 1])
    with col_obj:
        st.caption(
            f"**Phase {phase_active.numero} — {phase_active.titre}** : {phase_active.objectif}"
        )
    with col_cta:
        prochaine = prochaine_page_recommandee(etat)
        if prochaine and prochaine != page_courante:
            label_court = prochaine.replace(".py", "").replace("_", " ").lstrip("0123456789 ")
            if st.button(
                f"Aller : {label_court}",
                key=f"_cta_phase_{phase_active.numero}",
                use_container_width=True,
            ):
                st.switch_page(f"pages/{prochaine}")


def injecter_bandeau_si_mission(page_courante: str) -> None:
    """Wrapper pratique : charge la mission active depuis session_state et
    affiche le bandeau parcours. Silencieux si aucune mission active.

    A appeler en haut de toute page metier juste apres `injecter_css()` :

        from src.ui.parcours_widget import injecter_bandeau_si_mission
        injecter_bandeau_si_mission("05_Allocation.py")
    """
    mission_id = st.session_state.get("mission_id")
    if not mission_id:
        return
    try:
        etat = charger_mission(mission_id)
    except FileNotFoundError:
        return
    afficher_bandeau_parcours(etat, page_courante=page_courante)


def afficher_talking_points(page_courante: str | None = None) -> None:
    """Affiche un expander 'Que dire au client en phase X' au bas d'une page.

    Lit la mission active dans session_state. Silencieux si aucune mission.
    Utilise la cle de phase de la page courante si fournie, sinon la phase
    courante de la mission.
    """
    mission_id = st.session_state.get("mission_id")
    if not mission_id:
        return
    try:
        etat = charger_mission(mission_id)
    except FileNotFoundError:
        return

    phase = None
    if page_courante:
        phase = phase_d_une_page(page_courante)
    if phase is None:
        phase = phase_courante(etat)

    points = talking_points_pour_phase(phase.cle)
    if not points:
        return

    with st.expander(
        f"Que dire au client en phase {phase.numero} — {phase.titre}",
        expanded=False,
    ):
        for i, point in enumerate(points, 1):
            st.markdown(
                f'<div style="display:flex;gap:8px;margin-bottom:6px;">'
                f'<span style="color:{OR_VIEILLI};font-weight:600;'
                f'min-width:20px;">{i}.</span>'
                f'<span style="color:{ARDOISE};">{point}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )


def afficher_carte_phase(phase: PhaseParcours, pct: int) -> None:
    """Carte detaillee d'une phase (pour la synthese mission)."""
    bg = "#FFFFFF"
    statut_label = "Termine" if pct >= 100 else f"{pct} %"
    border_color = VERT_FORET if pct >= 100 else OR_VIEILLI if pct > 0 else "#E8E0D5"
    html = f"""
<div style="
    background:{bg};
    border-left:4px solid {border_color};
    border-top:1px solid #E8E0D5;
    border-right:1px solid #E8E0D5;
    border-bottom:1px solid #E8E0D5;
    border-radius:6px;
    padding:14px 16px;
    margin-bottom:8px;
">
    <div style="
        display:flex;justify-content:space-between;align-items:baseline;
        margin-bottom:4px;
    ">
        <div style="font-family:'EB Garamond',serif;font-size:18px;color:{ARDOISE};">
            Phase {phase.numero} — {phase.titre}
        </div>
        <div style="
            font-size:12px;font-weight:600;
            color:{border_color if pct > 0 else ARDOISE_CLAIRE};
        ">
            {statut_label}
        </div>
    </div>
    <div style="font-size:13px;color:{ARDOISE_CLAIRE};font-style:italic;margin-bottom:6px;">
        {phase.sous_titre} · {phase.duree_indicative}
    </div>
    <div style="font-size:13px;color:{ARDOISE};line-height:1.5;">
        {phase.objectif}
    </div>
    <div style="
        margin-top:8px;font-size:12px;color:{ARDOISE_CLAIRE};
        border-top:1px solid #F0EBE3;padding-top:6px;
    ">
        Livrable : {phase.livrable_principal}
    </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)
