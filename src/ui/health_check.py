"""Composant health check pour les pages de calcul."""

from __future__ import annotations


def afficher_health_check(
    poids: dict[str, float],
    profil_ar: dict,
    statut_optimiseur: str,
    mode: str = "simple",
) -> None:
    """Affiche un bandeau de vérification de l'allocation."""
    import streamlit as st

    from src.optimiseur_allocation import CLASSES_ACTIONS

    total = sum(poids.values())
    total_pct = total * 100

    actions_min = float(profil_ar.get("actions_min", 0.0))
    actions_max = float(profil_ar.get("actions_max", 1.0))
    total_actions = sum(poids.get(c, 0.0) for c in CLASSES_ACTIONS)

    somme_ok = abs(total - 1.0) < 1e-4
    contraintes_ok = (actions_min - 1e-4) <= total_actions <= (actions_max + 1e-4)
    optimiseur_optimal = statut_optimiseur == "optimal"

    with st.container(border=True):
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("**Vérification allocation**")
        with col2:
            if somme_ok:
                st.markdown(
                    f"<span style='color:#2D4A3E'>OK</span> Somme allocation = {total_pct:.1f} %",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<span style='color:#6B1E2C'>Attention</span> Somme = {total_pct:.1f} % ≠ 100 %",
                    unsafe_allow_html=True,
                )

            if contraintes_ok:
                st.markdown(
                    f"<span style='color:#2D4A3E'>OK</span> Contraintes profil respectées "
                    f"(actions ∈ [{actions_min:.0%}, {actions_max:.0%}])",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<span style='color:#6B1E2C'>Attention</span> Contraintes profil non respectées "
                    f"(actions = {total_actions:.1%}, attendu [{actions_min:.0%}, {actions_max:.0%}])",
                    unsafe_allow_html=True,
                )

            if optimiseur_optimal:
                st.markdown(
                    "<span style='color:#2D4A3E'>OK</span> Optimiseur : résolution optimale (scipy SLSQP)",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<span style='color:#6B1E2C'>Note</span> Optimiseur : fallback heuristique",
                    unsafe_allow_html=True,
                )

            mode_label = (
                "ACWI — 1 ligne monde pondérée par capitalisation"
                if mode == "simple"
                else "Granulaire — US / Dev ex-US / EM"
            )
            st.markdown(
                f"<span style='color:#0B1929'>Info</span> Mode {mode_label}",
                unsafe_allow_html=True,
            )
