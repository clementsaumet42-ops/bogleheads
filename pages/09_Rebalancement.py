"""Page 6 — Rebalancement : plan 3 étapes (arbitrages gratuits → flux → ventes) + utilité S11-C."""

from __future__ import annotations

import streamlit as st

from src.ui.formatters import format_euro

st.title("🔄 Rebalancement")

# ─── Vérification du profil ───────────────────────────────────────────────────

profil = st.session_state.get("profil_actif")
if not profil:
    st.warning("⚠️ Aucun profil chargé. Veuillez d'abord configurer un profil client.")
    if st.button("👤 Aller au profil client"):
        st.switch_page("pages/04_Profil.py")
    st.stop()

nom = profil.get("nom", "—") if isinstance(profil, dict) else getattr(profil, "nom", "—")
st.markdown(f"**Profil actif :** {nom}")

profil_dict = dict(profil) if isinstance(profil, dict) else {}

# ─── Panneau « Pourquoi rebalancer ? » (S11-C) ────────────────────────────────

with st.expander("🔍 Pourquoi rebalancer ? — Simulation drift naturel 12 mois", expanded=False):
    st.markdown(
        """
Simulation du **drift naturel de l'allocation** sur 12 mois, en supposant que chaque classe
d'actifs évolue selon ses rendements espérés sans action de votre part.
"""
    )

    # Récupérer allocation cible depuis session
    _ro = st.session_state.get("resultat_optim")
    _alloc_cible_drift: dict[str, float] = {}
    if _ro and _ro.get("allocation_cible"):
        _alloc_cible_drift = _ro["allocation_cible"]
    else:
        _ab = profil_dict.get("allocation_cible_bogleheads") or {}
        if isinstance(_ab, dict):
            _alloc_cible_drift = {
                k: v for k, v in _ab.items() if k != "commentaire" and isinstance(v, float)
            }

    if not _alloc_cible_drift:
        st.info("ℹ️ Allocation cible non disponible — calculez d'abord l'allocation (page 05).")
    else:
        try:
            from src.optimiseur_allocation import charger_config_optimiseur as _cfg_drift

            _cfg = _cfg_drift()
            _classes_actifs = _cfg.get("classes_actifs", {})

            # Mapping approx entre clés allocation et clés optimiseur
            _mu_map = {
                "actions": "actions_monde_acwi",
                "obligations": "obligations_euro",
                "immobilier_cote": "reit",
                "or": "or_matieres",
                "liquidites": "monetaire",
                "actions_monde_acwi": "actions_monde_acwi",
                "actions_usa": "actions_usa",
                "actions_dev_ex_usa": "actions_dev_ex_usa",
                "actions_em": "actions_em",
                "obligations_agg_monde": "obligations_agg_monde",
                "obligations_euro": "obligations_euro",
                "reit": "reit",
                "or_matieres": "or_matieres",
                "monetaire": "monetaire",
            }

            total_p = sum(_alloc_cible_drift.values())
            if total_p <= 0:
                raise ValueError("Allocation nulle")

            # Normaliser l'allocation actuelle
            _w0 = {k: v / total_p for k, v in _alloc_cible_drift.items()}

            # Simuler le drift sur 12 mois
            _w1_raw: dict[str, float] = {}
            for classe, w in _w0.items():
                cfg_key = _mu_map.get(classe, classe)
                mu = float(_classes_actifs.get(cfg_key, {}).get("rendement_attendu_annuel", 0.05))
                _w1_raw[classe] = w * (1 + mu)

            total_1 = sum(_w1_raw.values())
            _w1 = {k: v / total_1 for k, v in _w1_raw.items()}

            # Calcul de la dérive max
            derives = {k: abs(_w1.get(k, 0) - _w0.get(k, 0)) for k in _w0}
            derive_max = max(derives.values()) if derives else 0.0
            classe_max = max(derives, key=derives.get) if derives else "—"

            # Verdict
            if derive_max < 0.01:
                verdict = "💚 Pas d'urgence — drift naturel limité (< 1 pp)"
                couleur = "success"
            elif derive_max < 0.05:
                verdict = "🟡 Surveillance — rebalancer dans les prochains mois (1–5 pp)"
                couleur = "warning"
            else:
                verdict = "🔴 Rebalancement recommandé maintenant (≥ 5 pp)"
                couleur = "error"

            # Affichage
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.markdown("**Allocation aujourd'hui**")
                import pandas as pd

                df_now = pd.DataFrame(
                    [
                        {"Classe": k, "Poids": f"{v:.1%}"}
                        for k, v in sorted(_w0.items(), key=lambda x: -x[1])
                    ]
                )
                st.dataframe(df_now, use_container_width=True, hide_index=True)

            with col_d2:
                st.markdown("**Dans 12 mois sans action**")
                df_future = pd.DataFrame(
                    [
                        {
                            "Classe": k,
                            "Poids estimé": f"{_w1.get(k, 0):.1%}",
                            "Dérive (pp)": f"{(_w1.get(k, 0) - _w0.get(k, 0)) * 100:+.1f}",
                        }
                        for k, _ in sorted(_w0.items(), key=lambda x: -abs(_w1.get(x[0], 0) - x[1]))
                    ]
                )
                st.dataframe(df_future, use_container_width=True, hide_index=True)

            st.metric(
                f"Dérive max — classe '{classe_max}'",
                f"{derive_max:.1%} ({derive_max * 100:.1f} pp)",
            )

            if couleur == "success":
                st.success(verdict)
            elif couleur == "warning":
                st.warning(verdict)
            else:
                st.error(verdict)

            st.caption(
                "*Estimation indicative — hypothèses de rendements long terme de config/optimiseur.yaml. "
                "Les rendements réels à 12 mois peuvent différer significativement.*"
            )

        except Exception as exc:
            st.info(f"ℹ️ Simulation non disponible : {exc}")

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

# ─── Bilan coût/bénéfice (S11-C) ─────────────────────────────────────────────

with st.expander("💰 Bilan coût / bénéfice du rebalancement", expanded=False):
    st.markdown(
        """
Estimation indicative de la rentabilité du rebalancement comparé à l'inaction.

> *⚠️ Calcul approximatif — ne tient pas compte de l'évolution réelle des marchés.*
"""
    )

    try:
        # Coût total (étapes MILP si disponibles)
        frais_courtage_total = float(profil_dict.get("frais_courtier_par_transaction", 5.0) or 5.0)
        # Estimation coût fiscal (ordre de grandeur)
        cout_total_estime = frais_courtage_total * 2  # 2 transactions estimées par défaut

        # Bénéfice estimé : réduction du tracking-error
        # dérive_max × volatilité relative × 0.5 × patrimoine
        patrimoine_cb = float(profil_dict.get("patrimoine_financier_total", 0) or 0)

        # Calcul de la dérive actuelle vs cible
        _ro2 = st.session_state.get("resultat_optim")
        _alloc_c: dict[str, float] = {}
        if _ro2 and _ro2.get("allocation_cible"):
            _alloc_c = _ro2["allocation_cible"]
        else:
            _ab2 = profil_dict.get("allocation_cible_bogleheads") or {}
            if isinstance(_ab2, dict):
                _alloc_c = {
                    k: v for k, v in _ab2.items() if k != "commentaire" and isinstance(v, float)
                }

        _pos2 = profil_dict.get("positions_detaillees") or []
        _alloc_act2: dict[str, float] = {}
        if _pos2:
            _mont2: dict[str, float] = {}
            for p2 in _pos2:
                if isinstance(p2, dict):
                    _mont2[p2.get("etf", "?")] = _mont2.get(p2.get("etf", "?"), 0) + float(
                        p2.get("montant_actuel", 0)
                    )
            _tot2 = sum(_mont2.values())
            if _tot2 > 0:
                _alloc_act2 = {k: v / _tot2 for k, v in _mont2.items()}

        if _alloc_c and _alloc_act2:
            derive_rms = (
                sum(
                    ((_alloc_act2.get(k, 0) - v) ** 2)
                    for k, v in _alloc_c.items()
                    if k != "commentaire"
                )
                ** 0.5
            )
        elif _alloc_c:
            # Utiliser la dérive théorique 12 mois comme proxy
            derive_rms = 0.03  # 3 pp estimation conservatrice
        else:
            derive_rms = 0.0

        # Bénéfice = réduction tracking-error × volatilité standard (15%) × 0.5 × patrimoine
        vol_std = 0.15
        benefice_estime = derive_rms * vol_std * 0.5 * patrimoine_cb

        # Ratio
        if cout_total_estime > 0 and benefice_estime > 0:
            ratio = cout_total_estime / benefice_estime
        else:
            ratio = None

        col_cb1, col_cb2, col_cb3 = st.columns(3)
        with col_cb1:
            st.metric(
                "Coût estimé total",
                format_euro(cout_total_estime),
                help="Frais de courtage estimés (2 transactions par défaut)",
            )
        with col_cb2:
            st.metric(
                "Bénéfice estimé",
                format_euro(benefice_estime),
                help="Réduction tracking-error × volatilité × patrimoine (proxy indicatif)",
            )
        with col_cb3:
            if ratio is not None:
                st.metric("Ratio coût/bénéfice", f"{ratio:.2f}")
            else:
                st.metric("Ratio coût/bénéfice", "N/D")

        if ratio is not None:
            if ratio < 1:
                st.success(f"✅ Rebalancement rentable — ratio {ratio:.2f} < 1 (bénéfice > coût)")
            else:
                st.warning(
                    f"⚠️ Coût supérieur au bénéfice attendu (ratio {ratio:.2f} ≥ 1) — "
                    "envisager d'attendre ou d'utiliser uniquement les flux entrants"
                )
        else:
            st.info("ℹ️ Patrimoine non renseigné — configurez le profil pour obtenir l'estimation.")

        st.caption(
            "*Estimation indicative — ne tient pas compte de l'évolution réelle des marchés. "
            "Dérive calculée sur l'allocation actuelle saisie. Coût fiscal non inclus dans cette estimation simplifiée.*"
        )

    except Exception as exc:
        st.info(f"ℹ️ Bilan non disponible : {exc}")

col1, col2 = st.columns(2)
with col1:
    if st.button("📈 ← Monte-Carlo", use_container_width=True):
        st.switch_page("pages/08_Monte_Carlo.py")
with col2:
    if st.button("📥 Téléchargements →", type="primary", use_container_width=True):
        st.switch_page("pages/11_Exports.py")
