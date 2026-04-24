"""Page 6 — Rebalancement : plan 3 étapes (arbitrages gratuits → flux → ventes)."""

from __future__ import annotations

import streamlit as st

from src.ui.formatters import format_euro

st.title("🔄 Rebalancement")

# ─── Vérification du profil ───────────────────────────────────────────────────

profil = st.session_state.get("profil_actif")
if not profil:
    st.warning("⚠️ Aucun profil chargé. Veuillez d'abord configurer un profil client.")
    if st.button("👤 Aller au profil client"):
        st.switch_page("pages/02_Profil.py")
    st.stop()

nom = profil.get("nom", "—") if isinstance(profil, dict) else getattr(profil, "nom", "—")
st.markdown(f"**Profil actif :** {nom}")

profil_dict = dict(profil) if isinstance(profil, dict) else {}

# ─── Sélecteur d'approche ─────────────────────────────────────────────────────

st.subheader("⚙️ Approche de rebalancement")
approche = st.radio(
    "Méthode",
    ["🌊 Par flux (cash flow rebalancing)", "🔧 Optimal MILP (cascade fiscale)"],
    horizontal=True,
)

# ─── Paramètres communs ───────────────────────────────────────────────────────

col1, col2 = st.columns(2)
with col1:
    versement_mensuel = st.number_input(
        "Versement mensuel disponible (€)",
        min_value=0,
        value=int((profil_dict.get("capacite_epargne_annuelle", 12_000) or 12_000) // 12),
        step=100,
    )
with col2:
    bande_tolerance = st.slider(
        "Bande de tolérance (pp)",
        min_value=1,
        max_value=15,
        value=5,
        help="Écart en points de pourcentage déclenchant le rebalancement",
    )

# ─── Allocation cible depuis session ──────────────────────────────────────────

resultat_optim = st.session_state.get("resultat_optim")
allocation_cible: dict[str, float] = {}
if resultat_optim and resultat_optim.get("allocation_cible"):
    allocation_cible = resultat_optim["allocation_cible"]
else:
    alloc_boglehead = profil_dict.get("allocation_cible_bogleheads") or {}
    if isinstance(alloc_boglehead, dict):
        allocation_cible = {
            k: v for k, v in alloc_boglehead.items() if k != "commentaire" and isinstance(v, float)
        }

patrimoine = float(profil_dict.get("patrimoine_financier_total", 0) or 0)

# Allocation actuelle = allocation cible × patrimoine (simplification si pas de positions)
positions_detaillees = profil_dict.get("positions_detaillees") or []
if positions_detaillees:
    # Calculer l'allocation actuelle depuis les positions
    montants_par_classe: dict[str, float] = {}
    for pos in positions_detaillees:
        if isinstance(pos, dict):
            etf = pos.get("etf", "")
            montant = float(pos.get("montant_actuel", 0))
            montants_par_classe[etf] = montants_par_classe.get(etf, 0) + montant
    total_positions = sum(montants_par_classe.values())
    if total_positions > 0:
        allocation_actuelle = {k: v / total_positions for k, v in montants_par_classe.items()}
    else:
        allocation_actuelle = dict(allocation_cible)
else:
    # Pas de positions : allocation actuelle = allocation cible (pas de dérive)
    allocation_actuelle = dict(allocation_cible)

# ─── Calcul du plan ───────────────────────────────────────────────────────────

if patrimoine <= 0:
    st.info("ℹ️ Le patrimoine financier est à 0 — aucun rebalancement possible.")
    st.stop()

if approche.startswith("🌊"):
    # ── Approche par flux ─────────────────────────────────────────────────────
    st.subheader("🌊 Rebalancement par flux")
    st.markdown(
        "Le **cash flow rebalancing** réoriente les nouveaux versements vers les classes "
        "sous-pondérées, **sans vendre** les positions existantes. Aucune fiscalité déclenchée."
    )

    try:
        from src.rebalancement_flux import EtatPortefeuille, repartir_versement

        portef_kwargs = {
            k: v * patrimoine for k, v in allocation_actuelle.items() if k != "commentaire"
        }
        try:
            portefeuille = EtatPortefeuille(**portef_kwargs)
        except TypeError:
            portefeuille = EtatPortefeuille()

        cible_flux = {k: v for k, v in allocation_cible.items() if k != "commentaire"}
        rep = repartir_versement(portefeuille, cible_flux, float(versement_mensuel * 12))

        repartition = {k: v for k, v in rep.repartition.items() if v > 0}
        if repartition:
            import pandas as pd

            df_flux = pd.DataFrame(
                [
                    {
                        "Classe d'actifs": k,
                        "Montant versé (€)": format_euro(v),
                    }
                    for k, v in sorted(repartition.items(), key=lambda x: -x[1])
                ]
            )
            st.dataframe(df_flux, use_container_width=True, hide_index=True)
            st.metric("Total orienté", format_euro(sum(repartition.values())))
        else:
            st.success(
                "✅ Le portefeuille est dans les bandes de tolérance — pas de flux nécessaire."
            )

        if rep.recommandation:
            st.info(rep.recommandation)
    except Exception as exc:
        st.error(f"❌ Erreur lors du calcul par flux : {exc}")

else:
    # ── Approche MILP ─────────────────────────────────────────────────────────
    st.subheader("🔧 Plan de rebalancement optimal (cascade fiscale)")
    st.markdown(
        """
Le plan suit une **cascade fiscale en 3 étapes** ordonnées par coût fiscal croissant :

1. **Étape 1 — Gratuit** : arbitrages intra-enveloppe (PEA, PER, AV) sans fiscalité
2. **Étape 2 — Par flux** : orienter les versements vers les classes sous-pondérées
3. **Étape 3 — Ventes optimisées** : si nécessaire, ventes dans l'ordre fiscal optimal
"""
    )

    try:
        from src.rebalancement_optimal import (
            Position,
            etape1_arbitrages_gratuits,
            etape2_flux,
            etape3_ventes,
        )

        # Construire les positions depuis le profil
        positions = []
        for pos_raw in positions_detaillees:
            if isinstance(pos_raw, dict):
                try:
                    montant = float(pos_raw.get("montant_actuel", 0))
                    prm = float(pos_raw.get("prix_revient_moyen", 1) or 1)
                    quantite = montant / prm if prm > 0 else 1.0
                    pos = Position(
                        etf=pos_raw.get("etf", "ETF"),
                        enveloppe=pos_raw.get("enveloppe", "CTO_perso"),
                        quantite=quantite,
                        prix_revient_moyen=prm,
                        montant_actuel=montant,
                        date_ouverture_enveloppe=pos_raw.get("date_ouverture_enveloppe"),
                    )
                    positions.append(pos)
                except Exception:
                    pass

        # Étape 1
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            st.markdown("### Étape 1 — Arbitrages gratuits")
            arb = etape1_arbitrages_gratuits(
                positions=positions,
                allocation_actuelle=allocation_actuelle,
                allocation_cible=allocation_cible,
                patrimoine_total=patrimoine,
                bande_pp=bande_tolerance / 100,
            )
            if arb:
                for a in arb:
                    st.info(a.get("detail", str(a)))
                cout_e1 = sum(a.get("cout_fiscal", 0) for a in arb)
                st.metric("Coût fiscal étape 1", format_euro(cout_e1))
            else:
                st.success("✅ Aucun arbitrage gratuit nécessaire.")

        with col_e2:
            st.markdown("### Étape 2 — Par flux")
            flux = etape2_flux(
                allocation_actuelle=allocation_actuelle,
                allocation_cible=allocation_cible,
                patrimoine_total=patrimoine,
                versement_mensuel=float(versement_mensuel),
            )
            if flux:
                for f in flux:
                    st.info(f.get("detail", str(f)))
            else:
                st.success("✅ Aucun flux nécessaire.")

        # Étape 3
        st.markdown("### Étape 3 — Ventes optimisées (si nécessaire)")
        regime = profil_dict.get("regime_fiscal_detenteur", "IR")
        abattement = float(
            (profil_dict.get("abattements_utilises") or {}).get(
                "av_abattement_annuel_restant", 4600
            )
        )
        frais_courtage = float(profil_dict.get("frais_courtier_par_transaction", 0) or 0)

        if positions:
            ventes = etape3_ventes(
                positions=positions,
                allocation_actuelle=allocation_actuelle,
                allocation_cible=allocation_cible,
                patrimoine_total=patrimoine,
                regime_fiscal=regime,
                abattement_av_restant=abattement,
                frais_courtage=frais_courtage,
                bande_pp=bande_tolerance / 100,
            )
            if ventes:
                import pandas as pd

                df_ventes = pd.DataFrame(
                    [
                        {
                            "ETF": v.etf,
                            "Enveloppe": v.enveloppe,
                            "Montant (€)": format_euro(v.montant),
                            "PV réalisée (€)": format_euro(v.plus_value_realisee),
                            "Coût fiscal (€)": format_euro(v.cout_fiscal),
                            "Méthode": v.methode,
                        }
                        for v in ventes
                    ]
                )
                st.dataframe(df_ventes, use_container_width=True, hide_index=True)
                cout_total = sum(v.cout_fiscal + v.frais_courtage for v in ventes)
                st.metric("Coût fiscal total étape 3", format_euro(cout_total))
            else:
                st.success("✅ Aucune vente nécessaire.")
        else:
            st.info(
                "ℹ️ Aucune position détaillée dans le profil — "
                "l'étape 3 nécessite des positions avec prix de revient."
            )

    except Exception as exc:
        st.error(f"❌ Erreur lors du calcul du plan MILP : {exc}")

st.divider()
col1, col2 = st.columns(2)
with col1:
    if st.button("📈 ← Monte-Carlo", use_container_width=True):
        st.switch_page("pages/06_Monte_Carlo.py")
with col2:
    if st.button("📥 Téléchargements →", type="primary", use_container_width=True):
        st.switch_page("pages/08_Exports.py")
