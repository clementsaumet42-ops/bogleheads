"""Page 20 — Best Provider : classement des providers par coût sur 10 ans."""

from __future__ import annotations

import contextlib
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from src.catalogue.best_provider import classer_providers
from src.schemas import AssuranceVieConfig, BrokersConfig, TeneursPERConfig, UniversETFWrapper
from src.ui.theme import injecter_css

st.set_page_config(page_title="Best Provider", page_icon="🏛️")
injecter_css()

st.title("Best Provider — Classement par coût sur 10 ans")

st.markdown(
    "Comparez les brokers, assureurs AV et teneurs PER sur votre allocation cible. "
    "Le classement est calculé sur un horizon de **10 ans** en tenant compte des frais de gestion, "
    "du TER des ETF, des frais de courtage et d'arbitrage."
)

_CONFIG_DIR = Path(__file__).parent.parent / "config"


@st.cache_data(ttl=300)
def _charger_config() -> dict:
    result: dict = {}
    for f in ["brokers.yaml", "contrats_av.yaml", "teneurs_per.yaml", "univers_etf.yaml"]:
        try:
            raw = yaml.safe_load((_CONFIG_DIR / f).read_text(encoding="utf-8"))
            result[f] = raw or {}
        except Exception:
            result[f] = {}
    return result


config = _charger_config()

# ─── Chargement des listes ─────────────────────────────────────────────────────

_brokers_list = []
_contrats_av_list = []
_teneurs_per_list = []
_univers_etf_list = []

with contextlib.suppress(Exception):
    _brokers_list = BrokersConfig.model_validate(config["brokers.yaml"]).brokers

with contextlib.suppress(Exception):
    _contrats_av_list = AssuranceVieConfig.model_validate(config["contrats_av.yaml"]).contrats_av

with contextlib.suppress(Exception):
    _teneurs_per_list = TeneursPERConfig.model_validate(config["teneurs_per.yaml"]).teneurs_per

with contextlib.suppress(Exception):
    _univers_etf_list = UniversETFWrapper.model_validate(config["univers_etf.yaml"]).univers_etf

# ─── Paramètres de simulation ─────────────────────────────────────────────────

st.subheader("Paramètres de simulation")

col1, col2, col3 = st.columns(3)
with col1:
    patrimoine = st.number_input(
        "Patrimoine financier total (€)",
        min_value=1000,
        max_value=10_000_000,
        value=100_000,
        step=5000,
    )
with col2:
    horizon = st.slider("Horizon (années)", min_value=3, max_value=30, value=10)
with col3:
    enveloppes_choisies = st.multiselect(
        "Enveloppes à analyser",
        options=["PEA", "CTO", "AV", "PER"],
        default=["PEA", "AV", "PER"],
    )

# Sélection d'ETF retenus
etf_options = {}
for etf in _univers_etf_list:
    ticker = getattr(etf, "ticker", "")
    isin = getattr(etf, "isin", "")
    nom = getattr(etf, "nom", "")
    if isin:
        etf_options[f"{ticker} — {nom} ({isin})"] = isin

etfs_selectionnes = st.multiselect(
    "ETF retenus dans la simulation",
    options=list(etf_options.keys()),
    default=list(etf_options.keys())[:3] if etf_options else [],
    help="Laissez vide pour utiliser le TER moyen par défaut (0,30%)",
)
etfs_retenus = [etf_options[e] for e in etfs_selectionnes]

# Allocation par enveloppe
st.subheader("Allocation cible par enveloppe")
allocation_cible: dict[str, float] = {}
if enveloppes_choisies:
    poids_defaut = 1.0 / len(enveloppes_choisies)
    cols_alloc = st.columns(len(enveloppes_choisies))
    total_poids = 0.0
    for i, env in enumerate(enveloppes_choisies):
        with cols_alloc[i]:
            poids = st.number_input(
                f"{env} (%)",
                min_value=0.0,
                max_value=100.0,
                value=round(poids_defaut * 100, 1),
                step=5.0,
                key=f"poids_{env}",
            )
            allocation_cible[env] = poids / 100.0
            total_poids += poids

    if abs(total_poids - 100.0) > 0.1:
        st.warning(f"Le total des pondérations ({total_poids:.1f}%) doit être égal à 100%.")

# ─── Calcul ───────────────────────────────────────────────────────────────────


class _ProfilSimple:
    """Profil fictif minimal pour classer_providers."""

    def __init__(self, patrimoine: float, enveloppes: list[str]):
        self.patrimoine_financier_total = patrimoine
        self.composition_actuelle = [_LigneSimple(e) for e in enveloppes]


class _LigneSimple:
    def __init__(self, enveloppe: str):
        self.enveloppe = enveloppe


if st.button("Calculer le classement") and enveloppes_choisies:
    profil_sim = _ProfilSimple(float(patrimoine), enveloppes_choisies)

    with st.spinner("Calcul en cours..."):
        resultats = classer_providers(
            profil=profil_sim,
            allocation_cible=allocation_cible,
            etfs_retenus=etfs_retenus,
            horizon_annees=int(horizon),
            brokers=_brokers_list,
            contrats_av=_contrats_av_list,
            teneurs_per=_teneurs_per_list,
            univers_etf=_univers_etf_list,
        )

    if not any(resultats.values()):
        st.warning("Aucun provider trouvé pour les enveloppes sélectionnées.")
    else:
        for enveloppe, candidats in resultats.items():
            if not candidats:
                continue

            st.subheader(f"{enveloppe} — {len(candidats)} provider(s)")

            rows = []
            for i, c in enumerate(candidats):
                medal = "" if i == 0 or i == 1 or i == 2 else f"#{i + 1}"
                rows.append(
                    {
                        "Rang": medal,
                        "Provider": c.provider_nom,
                        "Type": c.type_provider,
                        f"Coût total {horizon}y (€)": f"{c.cout_total_10y_eur:,.0f}",
                        "Score": f"{c.score:.0f}/100",
                        "TER eff. (%)": c.detail.get("ter_effectif_pct", "—"),
                        "Frais env. (%)": c.detail.get("frais_enveloppe_pct", "—"),
                        "Courtage (€)": f"{c.detail.get('courtage_estime_eur', 0):,.0f}",
                    }
                )

            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Graphique comparatif
            if len(candidats) > 1:
                chart_data = pd.DataFrame(
                    {
                        "Provider": [c.provider_nom for c in candidats],
                        f"Coût {horizon}y (€)": [c.cout_total_10y_eur for c in candidats],
                    }
                ).set_index("Provider")
                st.bar_chart(chart_data)

        # Résumé global
        st.subheader("Résumé — Meilleur provider par enveloppe")
        resume = []
        for enveloppe, candidats in resultats.items():
            if candidats:
                best = candidats[0]
                resume.append(
                    {
                        "Enveloppe": enveloppe,
                        "Meilleur provider": best.provider_nom,
                        f"Coût {horizon}y (€)": f"{best.cout_total_10y_eur:,.0f}",
                        "Score": "100/100",
                    }
                )
        if resume:
            st.dataframe(pd.DataFrame(resume), use_container_width=True, hide_index=True)

st.caption(
    "Simulation indicative sur la base des données disponibles. "
    "Les frais réels peuvent varier. Consultez les grilles tarifaires des providers avant toute décision."
)
