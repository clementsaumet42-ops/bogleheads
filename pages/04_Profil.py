"""Page 2 — Profil client : formulaire interactif avec validation Pydantic."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from src.ui.formatters import format_euro
from src.ui.parcours_widget import afficher_talking_points, injecter_bandeau_si_mission
from src.ui.theme import injecter_css

injecter_css()
injecter_bandeau_si_mission("04_Profil.py")

st.title("Profil client")

_ROOT = Path(__file__).parent.parent


# ─── Chargement des profils types ─────────────────────────────────────────────


@st.cache_data(ttl=3600)
def _charger_profils_yaml() -> list[dict]:
    """Charge les profils types depuis le YAML de configuration."""
    path = _ROOT / "config" / "profils_clients.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data.get("profils", [])


profils_yaml = _charger_profils_yaml()

# ─── Choix du mode ────────────────────────────────────────────────────────────

mode = st.radio(
    "Source du profil",
    ["Profil type YAML", "Profil custom"],
    horizontal=True,
)

if mode == "Profil type YAML":
    # ── Sélection d'un profil type ────────────────────────────────────────────
    noms = [f"Profil {p['id']} — {p['nom']}" for p in profils_yaml]
    choix = st.selectbox("Choisissez un profil type", noms)
    idx = noms.index(choix)
    profil_raw = profils_yaml[idx]

    st.subheader("Aperçu du profil sélectionné")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Âge", profil_raw.get("age", "—"))
        st.metric("TMI", f"{int(profil_raw.get('tmi', 0) * 100)} %")
    with col2:
        patrimoine = profil_raw.get("patrimoine_financier_total", 0) or 0
        st.metric("Patrimoine financier", format_euro(patrimoine))
        capacite = profil_raw.get("capacite_epargne_annuelle", 0) or 0
        st.metric("Épargne annuelle", format_euro(capacite))
    with col3:
        horizon = profil_raw.get("horizon_placement_ans", "—")
        st.metric("Horizon", f"{horizon} ans")
        aversion = profil_raw.get("profil_aversion_risque", "équilibré") or "équilibré"
        st.metric("Aversion au risque", aversion)

    alloc = profil_raw.get("allocation_cible_bogleheads", {})
    if alloc:
        st.markdown("**Allocation cible Boglehead :**")
        alloc_cols = st.columns(len(alloc))
        for i, (k, v) in enumerate(alloc.items()):
            if k != "commentaire" and isinstance(v, (int, float)):
                with alloc_cols[i]:
                    st.metric(k.capitalize(), f"{v * 100:.0f} %")

    if st.button("Charger ce profil", type="primary"):
        # Validation Pydantic
        try:
            from src.schemas import Profil

            profil_valide = Profil.model_validate(profil_raw)
            st.session_state["profil_actif"] = profil_valide.model_dump(by_alias=True)
            st.session_state["profil_source"] = "yaml"
            # Reset des caches de calcul
            st.session_state["resultat_optim"] = None
            st.session_state["resultat_mc"] = None
            st.session_state["pdf_bytes"] = None
            st.session_state["excel_bytes"] = None
            st.success(f"Profil **{profil_raw['nom']}** chargé avec succès !")
        except Exception as exc:
            st.error(f"Erreur de validation Pydantic : {exc}")

else:
    # ── Formulaire custom ─────────────────────────────────────────────────────
    st.subheader("Nouveau profil client")

    with st.form("profil_custom"):
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nom du client", value="Client Test")
            age = st.number_input("Âge", min_value=18, max_value=100, value=45)
            tmi_pct = st.selectbox("TMI (%)", [0, 11, 30, 41, 45], index=3)

        with col2:
            patrimoine = st.number_input(
                "Patrimoine financier (€)", min_value=0, value=200_000, step=10_000
            )
            capacite_epargne = st.number_input(
                "Capacité d'épargne annuelle (€)", min_value=0, value=12_000, step=1_000
            )
            horizon = st.number_input(
                "Horizon de placement (ans)", min_value=1, max_value=40, value=20
            )

        st.markdown("**Allocation cible Boglehead**")
        col3, col4, col5 = st.columns(3)
        with col3:
            actions_pct = st.slider("Actions (%)", 0, 100, 65)
            obligations_pct = st.slider("Obligations (%)", 0, 100, 20)
        with col4:
            immo_pct = st.slider("Immobilier coté (%)", 0, 100, 5)
            or_pct = st.slider("Or (%)", 0, 100, 5)
        with col5:
            liquidites_pct = st.slider("Liquidités (%)", 0, 100, 5)

        total_alloc = actions_pct + obligations_pct + immo_pct + or_pct + liquidites_pct
        if total_alloc != 100:
            st.warning(f"Total allocation : {total_alloc}% (doit être 100%)")

        aversion = st.selectbox(
            "Profil d'aversion au risque",
            ["defensif", "equilibre", "dynamique", "agressif"],
            index=1,
        )

        st.markdown("**Enveloppes disponibles**")
        col_env1, col_env2 = st.columns(2)
        with col_env1:
            pea_ouvert = st.checkbox("PEA", value=True)
            pea_encours = (
                st.number_input("Encours PEA (€)", min_value=0, value=50_000, step=5_000)
                if pea_ouvert
                else 0
            )
            per_ouvert = st.checkbox("PER", value=True)
            per_encours = (
                st.number_input("Encours PER (€)", min_value=0, value=20_000, step=5_000)
                if per_ouvert
                else 0
            )
        with col_env2:
            av_ouvert = st.checkbox("Assurance-vie", value=True)
            av_encours = (
                st.number_input("Encours AV (€)", min_value=0, value=80_000, step=5_000)
                if av_ouvert
                else 0
            )
            cto_ouvert = st.checkbox("CTO", value=True)
            cto_encours = (
                st.number_input("Encours CTO (€)", min_value=0, value=50_000, step=5_000)
                if cto_ouvert
                else 0
            )

        submitted = st.form_submit_button("Valider le profil", type="primary")

    if submitted:
        if total_alloc != 100:
            st.error("La somme des allocations doit être égale à 100%.")
        else:
            enveloppes: dict = {}
            if pea_ouvert:
                enveloppes["PEA"] = {
                    "plafond": 150_000,
                    "encours_actuel": pea_encours,
                    "ouvert": True,
                }
            if per_ouvert:
                enveloppes["PER"] = {"encours_actuel": per_encours, "ouvert": True}
            if av_ouvert:
                enveloppes["AV"] = {"encours_actuel": av_encours, "ouvert": True}
            if cto_ouvert:
                enveloppes["CTO_perso"] = {"encours_actuel": cto_encours, "ouvert": True}

            profil_dict = {
                "id": 99,
                "code": "PROFIL_CUSTOM",
                "nom": nom,
                "age": int(age),
                "tmi": tmi_pct / 100,
                "patrimoine_financier_total": float(patrimoine),
                "capacite_epargne_annuelle": float(capacite_epargne),
                "horizon_placement_ans": int(horizon),
                "profil_aversion_risque": aversion,
                "allocation_cible_bogleheads": {
                    "actions": actions_pct / 100,
                    "obligations": obligations_pct / 100,
                    "immobilier_cote": immo_pct / 100,
                    "or": or_pct / 100,
                    "liquidites": liquidites_pct / 100,
                },
                "enveloppes_disponibles": enveloppes,
                "contraintes_personnalisees": {},
            }

            try:
                from src.schemas import Profil

                profil_valide = Profil.model_validate(profil_dict)
                st.session_state["profil_actif"] = profil_valide.model_dump(by_alias=True)
                st.session_state["profil_source"] = "custom"
                st.session_state["resultat_optim"] = None
                st.session_state["resultat_mc"] = None
                st.session_state["pdf_bytes"] = None
                st.session_state["excel_bytes"] = None
                st.success(f"Profil **{nom}** validé et enregistré !")
            except Exception as exc:
                st.error(f"Erreur de validation : {exc}")

# ─── Affichage du profil actif en session ─────────────────────────────────────

if st.session_state.get("profil_actif"):
    st.divider()
    st.subheader("Profil actif en session")
    profil = st.session_state["profil_actif"]
    st.json(profil, expanded=False)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Calculer l'allocation", use_container_width=True):
            st.switch_page("pages/05_Allocation.py")
    with col2:
        if st.button("Projection Monte-Carlo", use_container_width=True):
            st.switch_page("pages/08_Monte_Carlo.py")

# ─── Composition patrimoniale existante ──────────────────────────────────────

st.divider()
with st.expander("Patrimoine financier déjà constitué", expanded=False):
    st.markdown("Saisissez ligne par ligne les supports déjà détenus (ETF, fonds, etc.)")

    @st.cache_data(ttl=3600)
    def _charger_univers() -> dict:
        path = _ROOT / "config" / "univers_etf.yaml"
        import yaml as _yaml

        data = _yaml.safe_load(path.read_text(encoding="utf-8"))
        return {e["isin"]: e for e in data.get("univers_etf", []) if e.get("isin")}

    _univers = _charger_univers()

    _comp_init = []
    if st.session_state.get("profil_actif"):
        _comp_init = st.session_state["profil_actif"].get("composition_actuelle", [])

    _df_init = (
        pd.DataFrame(
            _comp_init if _comp_init else [],
            columns=[
                "enveloppe",
                "etf_isin",
                "etf_ticker",
                "libelle_libre",
                "classe_actif",
                "montant_eur",
                "prix_revient_eur",
            ],
        )
        if _comp_init
        else pd.DataFrame(
            columns=[
                "enveloppe",
                "etf_isin",
                "etf_ticker",
                "libelle_libre",
                "classe_actif",
                "montant_eur",
                "prix_revient_eur",
            ]
        )
    )

    edited_df = st.data_editor(
        _df_init,
        column_config={
            "enveloppe": st.column_config.SelectboxColumn(
                "Enveloppe",
                options=["PEA", "PEA_PME", "PER", "AV", "CTO", "CTO_IS", "Contrat_Cap_IS"],
            ),
            "etf_isin": st.column_config.TextColumn("ISIN"),
            "etf_ticker": st.column_config.TextColumn("Ticker"),
            "libelle_libre": st.column_config.TextColumn("Libellé libre"),
            "classe_actif": st.column_config.TextColumn("Classe d'actif"),
            "montant_eur": st.column_config.NumberColumn("Montant (€)", format="%.2f"),
            "prix_revient_eur": st.column_config.NumberColumn("Prix de revient (€)", format="%.2f"),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="composition_editor",
    )

    isin_input = st.text_input("Lookup ISIN → Ticker / Classe", placeholder="ex: IE00B4L5Y983")
    if isin_input and isin_input in _univers:
        etf = _univers[isin_input]
        st.info(
            f"{etf['ticker']} — {etf['nom']} — {etf.get('sous_classe', etf.get('classe_actifs', '?'))}"
        )
    elif isin_input:
        st.warning("ISIN non trouvé dans l'univers ETF.")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Enregistrer la composition", use_container_width=True):
            records = edited_df.dropna(subset=["enveloppe", "classe_actif", "montant_eur"]).to_dict(
                "records"
            )
            composition = []
            for r in records:
                try:
                    from src.schemas import LigneExistante

                    ligne = LigneExistante(
                        enveloppe=str(r.get("enveloppe", "")),
                        etf_isin=r.get("etf_isin") or None,
                        etf_ticker=r.get("etf_ticker") or None,
                        libelle_libre=r.get("libelle_libre") or None,
                        classe_actif=str(r.get("classe_actif", "")),
                        montant_eur=float(r.get("montant_eur", 0)),
                        prix_revient_eur=float(r["prix_revient_eur"])
                        if r.get("prix_revient_eur")
                        else None,
                    )
                    composition.append(ligne.model_dump())
                except Exception:
                    pass

            if st.session_state.get("profil_actif"):
                st.session_state["profil_actif"]["composition_actuelle"] = composition
                st.success(f"{len(composition)} ligne(s) enregistrée(s) dans le profil actif.")
            else:
                st.warning("Chargez d'abord un profil avant d'enregistrer la composition.")
    with col_btn2:
        if st.button("Vider", use_container_width=True):
            if st.session_state.get("profil_actif"):
                st.session_state["profil_actif"]["composition_actuelle"] = []
            st.rerun()

# ─── Widget mission (non-invasif) ────────────────────────────────────────────

from src.mission.widgets import widget_mission_etape  # noqa: E402

widget_mission_etape("profil_saisi")


# ─── Talking points ──────────────────────────────────────────────────────
afficher_talking_points("04_Profil.py")
