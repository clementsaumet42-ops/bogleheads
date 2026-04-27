"""Page 22 — Plan d'Exécution : screener ETF, ordres, déploiement, calendrier."""

from __future__ import annotations

import contextlib
import logging
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from src.ui.theme import injecter_css

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Plan d'Exécution", page_icon="🏛️", layout="wide")
injecter_css()

st.title("Plan d'Exécution — Du théorique au concret")
st.caption("Screener ETF · Ordres chiffrés · Déploiement DCA/lump · Calendrier de mise en œuvre")

ROOT = Path(__file__).parent.parent
CONFIG_DIR = ROOT / "config"

# ─── Chargement catalogue ──────────────────────────────────────────────────────


@st.cache_data(ttl=300)
def _charger_catalogue() -> dict:
    try:
        path = CONFIG_DIR / "univers_etf.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        logger.warning("Impossible de charger univers_etf.yaml : %s", e)
        return {}


@st.cache_data(ttl=300)
def _charger_brokers() -> dict:
    try:
        path = CONFIG_DIR / "brokers.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        logger.warning("Impossible de charger brokers.yaml : %s", e)
        return {}


catalogue = _charger_catalogue()
brokers_raw = _charger_brokers()

# ─── Lecture session state ────────────────────────────────────────────────────

profil_actif = st.session_state.get("profil_actif")

# ─── Section 1 : Récap allocation cible ──────────────────────────────────────

st.header("1. Récapitulatif allocation cible")

allocation_cible: dict = {}
if profil_actif is not None:
    with contextlib.suppress(Exception):
        from src.optimiseur_allocation import (
            calculer_allocation_cible,
            charger_config_optimiseur,
        )

        config_optim = charger_config_optimiseur()
        allocation_cible = calculer_allocation_cible(profil_actif, config_optim) or {}

if allocation_cible:
    st.dataframe(
        pd.DataFrame(
            [{"Classe": k, "Allocation": f"{v:.1%}"} for k, v in allocation_cible.items()]
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info(
        "Aucune allocation cible disponible. "
        "Chargez un profil client depuis la page **Profilage** ou **Allocation**."
    )

# ─── Section 2 : Screener ETF ─────────────────────────────────────────────────

st.header("2. Screener ETF assisté — Lot A")

# Cases d'allocation disponibles dans le catalogue
CASES_ALLOCATION = [
    ("Actions Monde Développé", "actions_monde_dev"),
    ("Actions Monde (tous pays)", "actions_monde"),
    ("Actions Émergents", "actions_emergents"),
    ("Actions USA S&P 500", "actions_usa"),
    ("Actions Europe", "actions_europe"),
    ("Obligations Monde", "obligations_monde"),
    ("Or / Matières premières", "or"),
    ("Liquidités / Monétaire", "liquidites"),
]

ENVELOPPES = ["PEA", "AV", "PER", "CTO"]

col_screen1, col_screen2, col_screen3 = st.columns(3)
with col_screen1:
    case_label = st.selectbox(
        "Case d'allocation",
        [c[0] for c in CASES_ALLOCATION],
        key="screener_case",
    )
    case_id = next(c[1] for c in CASES_ALLOCATION if c[0] == case_label)

with col_screen2:
    enveloppe_screen = st.selectbox(
        "Enveloppe fiscale",
        ENVELOPPES,
        key="screener_enveloppe",
    )

with col_screen3:
    top_n = st.slider("Top N ETF", min_value=1, max_value=5, value=3, key="screener_top_n")

contrat_av_input = ""
if enveloppe_screen == "AV":
    contrat_av_input = st.text_input(
        "Contrat AV (nom, ex: Linxea Spirit 2)",
        key="screener_contrat_av",
        placeholder="Linxea Spirit 2",
    )

if st.button("Lancer le screener", key="btn_screener"):
    if not catalogue:
        st.warning("Catalogue ETF non disponible.")
    else:
        try:
            from src.execution.screener import screener_etf

            contexte_screen: dict = {}
            if contrat_av_input:
                contexte_screen["contrat_av"] = contrat_av_input

            with st.spinner("Calcul des scores ETF…"):
                resultats = screener_etf(
                    case_allocation=case_id,
                    enveloppe=enveloppe_screen,
                    contexte=contexte_screen,
                    catalogue=catalogue,
                    top_n=top_n,
                )

            if not resultats:
                st.warning(
                    f"Aucun ETF éligible trouvé pour la case **{case_label}** "
                    f"en enveloppe **{enveloppe_screen}**. "
                    f"Vérifiez le catalogue ou les contraintes d'éligibilité."
                )
            else:
                st.success(f"Top {len(resultats)} ETF pour {case_label} ({enveloppe_screen})")

                rows = []
                for i, r in enumerate(resultats):
                    rows.append(
                        {
                            "Rang": i + 1,
                            "Ticker": r.get("ticker", ""),
                            "ISIN": r.get("isin", ""),
                            "Nom": r.get("nom", ""),
                            "TER": f"{r['ter']:.2%}" if r.get("ter") is not None else "—",
                            "AUM (M€)": f"{r['aum']:.0f}" if r.get("aum") is not None else "—",
                            "Domicile": r.get("domicile", ""),
                            "Score": f"{r['score_global']:.2f}",
                            "Commentaire": r.get("commentaire", ""),
                        }
                    )
                df_screen = pd.DataFrame(rows)
                st.dataframe(df_screen, use_container_width=True, hide_index=True)

                # Afficher le détail scoring
                with st.expander("Détail scoring par critère"):
                    detail_rows = []
                    for r in resultats:
                        detail = r.get("score_detail", {})
                        detail_rows.append(
                            {
                                "Ticker": r["ticker"],
                                "TER (30%)": f"{detail.get('ter', 0):.2f}",
                                "AUM (20%)": f"{detail.get('aum', 0):.2f}",
                                "Track.Diff (15%)": f"{detail.get('tracking_diff', 0):.2f}",
                                "Éligibilité (20%)": f"{detail.get('eligibilite', 0):.2f}",
                                "Capi/Dist (10%)": f"{detail.get('capi_dist', 0):.2f}",
                                "Domicile UE (5%)": f"{detail.get('domicile_ue', 0):.2f}",
                                "Score global": f"{r['score_global']:.2f}",
                            }
                        )
                    st.dataframe(
                        pd.DataFrame(detail_rows), use_container_width=True, hide_index=True
                    )

                # Sauvegarde dans session state pour utilisation dans les ordres
                st.session_state["screener_resultats"] = {
                    f"{case_id}_{enveloppe_screen}": resultats
                }

        except Exception as exc:
            st.error(f"Erreur lors du screener : {exc}")
            logger.exception("Erreur screener")

# ─── Section 3 : Ordres ──────────────────────────────────────────────────────

st.header("3. Plan d'exécution chiffré — Lot B")

st.info("Saisissez l'allocation finale et les prix de référence pour générer les ordres.")

with st.expander("Saisir l'allocation finale et les prix", expanded=False):
    col_ord1, col_ord2 = st.columns(2)

    with col_ord1:
        st.subheader("Allocation finale ({enveloppe: {isin: montant}})")
        alloc_json = st.text_area(
            "Allocation finale (JSON)",
            value='{"PEA": {"IE0031442068": 30000}, "CTO": {"IE00B4L5Y983": 20000}}',
            height=120,
            key="ordres_alloc",
        )

    with col_ord2:
        st.subheader("Prix de référence ({isin: prix})")
        prix_json = st.text_area(
            "Prix de référence (JSON)",
            value='{"IE0031442068": 350.0, "IE00B4L5Y983": 85.0}',
            height=120,
            key="ordres_prix",
        )

    tolerance_prix = (
        st.slider(
            "Tolérance prix limité (%)",
            min_value=0.5,
            max_value=5.0,
            value=2.0,
            step=0.5,
            key="ordres_tolerance",
        )
        / 100
    )

    if st.button("Générer les ordres", key="btn_ordres"):
        try:
            import json

            from src.execution.ordres import export_ordres_csv, generer_ordres

            alloc_finale = json.loads(alloc_json)
            prix_ref = json.loads(prix_json)

            # Contexte : brokers depuis brokers.yaml
            contexte_ordres: dict = {}
            with contextlib.suppress(Exception):
                from src.schemas import BrokersConfig

                brokers_list = BrokersConfig.model_validate(brokers_raw).brokers
                # Mapper le premier broker disponible à chaque enveloppe
                brokers_par_env: dict = {}
                for env in alloc_finale:
                    env_up = env.upper()
                    for b in brokers_list:
                        if env_up == "PEA" and getattr(b, "pea_disponible", False):
                            brokers_par_env.setdefault("PEA", b)
                        elif env_up == "CTO" and getattr(b, "cto_disponible", False):
                            brokers_par_env.setdefault("CTO", b)
                        elif env_up == "AV" and getattr(b, "av_disponible", False):
                            brokers_par_env.setdefault("AV", b)
                        elif env_up == "PER" and getattr(b, "per_disponible", False):
                            brokers_par_env.setdefault("PER", b)
                contexte_ordres["brokers"] = brokers_par_env

            with st.spinner("Calcul des ordres…"):
                plan_ordres = generer_ordres(
                    alloc_finale, prix_ref, contexte_ordres, tolerance_prix
                )

            st.session_state["plan_ordres"] = plan_ordres
            st.success(
                f"{len(plan_ordres['ordres'])} ordre(s) générés — "
                f"Frais totaux : {plan_ordres['frais_total']:,.2f} €"
            )

        except Exception as exc:
            st.error(f"Erreur lors de la génération des ordres : {exc}")
            logger.exception("Erreur ordres")

# Affichage plan ordres si disponible
plan_ordres = st.session_state.get("plan_ordres")
if plan_ordres and plan_ordres.get("ordres"):
    st.subheader("Tableau des ordres")
    ordres_df = pd.DataFrame(plan_ordres["ordres"])
    st.dataframe(ordres_df, use_container_width=True, hide_index=True)

    col_reliq, col_frais = st.columns(2)
    with col_reliq:
        st.metric("Frais totaux estimés", f"{plan_ordres['frais_total']:,.2f} €")
    with col_frais:
        if plan_ordres.get("reliquats"):
            reliq_str = " | ".join(
                f"{env}: {rel:,.2f} €" for env, rel in plan_ordres["reliquats"].items()
            )
            st.info(f"Reliquats cash : {reliq_str}")

    # Export CSV
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        from src.execution.ordres import export_ordres_csv

        csv_content = export_ordres_csv(plan_ordres)
        st.download_button(
            label="Télécharger CSV",
            data=csv_content.encode("utf-8"),
            file_name=f"ordres_{date.today().isoformat()}.csv",
            mime="text/csv",
            key="dl_ordres_csv",
        )

# ─── Section 4 : Plan de déploiement ─────────────────────────────────────────

st.header("4. Plan de déploiement — Lot C")

col_dep1, col_dep2, col_dep3 = st.columns(3)

with col_dep1:
    capital_total = st.number_input(
        "Capital total à investir (€)",
        min_value=0.0,
        value=100_000.0,
        step=5_000.0,
        format="%.0f",
        key="dep_capital",
    )

with col_dep2:
    profil_risque = st.selectbox(
        "Profil de risque",
        ["prudent", "équilibré", "dynamique", "agressif"],
        index=1,
        key="dep_profil",
    )

with col_dep3:
    horizon_ans = st.slider("Horizon (années)", 1, 30, 15, key="dep_horizon")

col_dep4, col_dep5, col_dep6 = st.columns(3)
with col_dep4:
    age_client = st.number_input("Âge", min_value=18, max_value=80, value=40, key="dep_age")

with col_dep5:
    rfr_client = st.number_input(
        "RFR annuel (€)", min_value=0.0, value=60_000.0, step=5_000.0, format="%.0f", key="dep_rfr"
    )

with col_dep6:
    enveloppes_dep = st.multiselect(
        "Enveloppes disponibles",
        ["PEA", "AV", "PER", "CTO"],
        default=["PEA", "CTO"],
        key="dep_enveloppes",
    )

col_ovrd1, col_ovrd2 = st.columns(2)
with col_ovrd1:
    mode_override = st.selectbox(
        "Mode override (optionnel)",
        ["— auto —", "lump_sum", "DCA", "hybride"],
        key="dep_mode_override",
    )

with col_ovrd2:
    duree_override = st.number_input(
        "Durée DCA override (mois, 0 = auto)",
        min_value=0,
        max_value=24,
        value=0,
        key="dep_duree_override",
    )

if st.button("Calculer le plan de déploiement", key="btn_deploiement"):
    if not enveloppes_dep:
        st.warning("Veuillez sélectionner au moins une enveloppe.")
    else:
        try:
            from src.execution.deploiement import plan_deploiement

            mode_ov = None if mode_override == "— auto —" else mode_override
            duree_ov = duree_override if duree_override > 0 else None

            with st.spinner("Calcul du plan de déploiement…"):
                plan_dep = plan_deploiement(
                    capital_total=capital_total,
                    profil=profil_risque,
                    horizon_annees=horizon_ans,
                    age=int(age_client),
                    rfr=rfr_client,
                    enveloppes_disponibles=enveloppes_dep,
                    duree_mois_override=duree_ov,
                    mode_override=mode_ov,
                )

            st.session_state["plan_deploiement"] = plan_dep
            st.success(
                f"Mode **{plan_dep['mode']}** — "
                f"Durée : {plan_dep['duree_mois']} mois — "
                f"Séquence : {' → '.join(plan_dep['sequence_enveloppes'])}"
            )

        except Exception as exc:
            st.error(f"Erreur lors du calcul du plan : {exc}")
            logger.exception("Erreur déploiement")

# Affichage plan déploiement si disponible
plan_dep = st.session_state.get("plan_deploiement")
if plan_dep:
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.metric("Mode de déploiement", plan_dep["mode"])
    with col_info2:
        st.metric(
            "Durée DCA",
            f"{plan_dep['duree_mois']} mois" if plan_dep["duree_mois"] > 0 else "Immédiat",
        )

    st.subheader("Séquence d'enveloppes")
    seq = plan_dep.get("sequence_enveloppes", [])
    if seq:
        st.write("→ ".join(f"**{e}**" for e in seq))

    tranches = plan_dep.get("tranches", [])
    if tranches:
        st.subheader("Tranches d'investissement")
        df_tranches = pd.DataFrame(tranches)
        df_tranches = df_tranches.rename(
            columns={
                "mois": "Mois",
                "enveloppe": "Enveloppe",
                "montant_eur": "Montant (€)",
                "justification": "Justification",
            }
        )
        if "Montant (€)" in df_tranches.columns:
            df_tranches["Montant (€)"] = df_tranches["Montant (€)"].map("{:,.2f}".format)
        st.dataframe(df_tranches, use_container_width=True, hide_index=True)

# ─── Section 5 : Calendrier ──────────────────────────────────────────────────

st.header("5. Calendrier de mise en œuvre — Lot D")

date_debut_cal = st.date_input(
    "Date de démarrage",
    value=date.today(),
    key="cal_date_debut",
)

if st.button("Générer le calendrier", key="btn_calendrier"):
    plan_dep_cal = st.session_state.get("plan_deploiement")
    if plan_dep_cal is None:
        st.warning(
            "Calculez d'abord le plan de déploiement (section 4) avant de générer le calendrier."
        )
    else:
        try:
            from src.execution.calendrier import generer_calendrier

            with st.spinner("Génération du calendrier…"):
                calendrier = generer_calendrier(plan_dep_cal, date_debut_cal)

            st.session_state["calendrier"] = calendrier
            st.success(f"{len(calendrier)} étapes générées")

        except Exception as exc:
            st.error(f"Erreur lors de la génération du calendrier : {exc}")
            logger.exception("Erreur calendrier")

# Affichage calendrier si disponible
calendrier = st.session_state.get("calendrier")
if calendrier:
    # Icônes par type
    _icons = {"admin": "", "virement": "", "ordre": "", "controle": ""}

    df_cal = pd.DataFrame(
        [
            {
                "N°": e["ordre"],
                "Type": f"{_icons.get(e['type'], '')} {e['type']}",
                "Date début": e["date_debut"].strftime("%d/%m/%Y")
                if isinstance(e["date_debut"], date)
                else str(e["date_debut"]),
                "Date fin": e["date_fin"].strftime("%d/%m/%Y")
                if isinstance(e["date_fin"], date)
                else str(e["date_fin"]),
                "Enveloppe": e.get("enveloppe") or "—",
                "Titre": e["titre"],
                "Dépend de": ", ".join(str(d) for d in e["depends_on"]) if e["depends_on"] else "—",
            }
            for e in calendrier
        ]
    )
    st.dataframe(df_cal, use_container_width=True, hide_index=True)

    # Export CSV du calendrier
    csv_cal = df_cal.to_csv(index=False, encoding="utf-8")
    st.download_button(
        label="Télécharger le calendrier CSV",
        data=csv_cal.encode("utf-8"),
        file_name=f"calendrier_{date.today().isoformat()}.csv",
        mime="text/csv",
        key="dl_calendrier_csv",
    )

    # Checkboxes de suivi persistées dans session state
    st.subheader("Suivi des étapes")
    if "etapes_validees" not in st.session_state:
        st.session_state["etapes_validees"] = {}

    for etape in calendrier:
        etape_id = str(etape["ordre"])
        est_valide = st.session_state["etapes_validees"].get(etape_id, False)
        checked = st.checkbox(
            f"{_icons.get(etape['type'], '')} **{etape['titre']}** "
            f"({etape['date_debut']} → {etape['date_fin']})",
            value=est_valide,
            key=f"cal_check_{etape_id}",
        )
        if checked != est_valide:
            st.session_state["etapes_validees"][etape_id] = checked

    nb_valides = sum(1 for v in st.session_state.get("etapes_validees", {}).values() if v)
    nb_total = len(calendrier)
    if nb_total > 0:
        st.progress(nb_valides / nb_total, text=f"{nb_valides}/{nb_total} étapes validées")

# ─── Widget mission (non-invasif) ────────────────────────────────────────────

from src.mission.widgets import widget_mission_etape  # noqa: E402

widget_mission_etape("plan_execution")
