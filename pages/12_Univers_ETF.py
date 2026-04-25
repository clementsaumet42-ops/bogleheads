"""Page 12 — Univers ETF : visibilité éligibilité enveloppes + filtres + export CSV (S11-B)."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

st.title("📚 Univers ETF — Éligibilité enveloppes")
st.markdown(
    "*Consultez et filtrez les ETF de l'univers Boglehead FR par enveloppe fiscale, "
    "classe d'actifs, TER et AUM.*"
)

# ─── Chargement des données ───────────────────────────────────────────────────

_ETF_YAML = Path(__file__).parent.parent / "config" / "univers_etf.yaml"


@st.cache_data(ttl=3600)
def _charger_etfs() -> list[dict]:
    try:
        raw = yaml.safe_load(_ETF_YAML.read_text(encoding="utf-8"))
        return raw.get("univers_etf", [])
    except Exception as exc:
        st.error(f"❌ Erreur chargement univers_etf.yaml : {exc}")
        return []


etfs_raw = _charger_etfs()

if not etfs_raw:
    st.warning("⚠️ Aucun ETF chargé.")
    st.stop()


def _badge_verification(dv_str: str | None) -> str:
    """Retourne un badge coloré selon l'ancienneté de la vérification."""
    if dv_str is None:
        return "🔴 Non vérifié"
    try:
        dv = date.fromisoformat(str(dv_str)) if not isinstance(dv_str, date) else dv_str
        age = (date.today() - dv).days
        if age <= 180:
            return f"🟢 {dv} ({age}j)"
        elif age <= 365:
            return f"🟡 {dv} ({age}j)"
        else:
            return f"🔴 {dv} ({age}j)"
    except Exception:
        return f"⚪ {dv_str}"


def _bool_icon(val: bool | None) -> str:
    if val is True:
        return "✅"
    if val is False:
        return "❌"
    return "⚠️"


# ─── Construction du DataFrame ───────────────────────────────────────────────

rows = []
for etf in etfs_raw:
    elig = etf.get("eligibilite") or {}
    if isinstance(elig, dict):
        pea = elig.get("PEA", False)
        av = elig.get("AV_UC", False)
        per = elig.get("PER", False)
        cto = elig.get("CTO_perso", False)
    else:
        pea = av = per = cto = False

    # Tracking difference
    td3y = etf.get("tracking_difference_3y")
    td5y = etf.get("tracking_difference_5y")

    # AUM (peut être dans aum_mds_eur)
    aum = etf.get("aum_mds_eur")

    dv = etf.get("derniere_verification") or etf.get("date_verification_dic")
    audit_st = etf.get("audit_status", "non_verifie")

    rows.append(
        {
            "ISIN": etf.get("isin", "—") or "—",
            "Ticker": etf.get("ticker", "—"),
            "Nom": etf.get("nom", "—"),
            "Émetteur": etf.get("emetteur", "—"),
            "Classe": etf.get("classe_actifs", "—"),
            "Sous-classe": etf.get("sous_classe", "—") or "—",
            "TER": etf.get("ter"),
            "AUM (Mds€)": aum,
            "Domicile": etf.get("domicile", "—"),
            "Réplication": etf.get("methode_replication", "—") or "—",
            "Acc/Dist": "ACC" if etf.get("capitalisant") else "DIST",
            "TD 3y": td3y,
            "PEA": pea,
            "AV": av,
            "PER": per,
            "CTO": cto,
            "DICI": etf.get("url_dic_kid"),
            "Vérifié": dv,
            "_pea_raw": pea,
            "_av_raw": av,
            "_per_raw": per,
            "_cto_raw": cto,
            "_audit_status": audit_st,
        }
    )

df_all = pd.DataFrame(rows)

# ─── Carte synthèse ──────────────────────────────────────────────────────────

nb_total = len(df_all)
today = date.today()
six_mois = timedelta(days=180)


def _recent(dv: object) -> bool:
    if dv is None or (isinstance(dv, float) and pd.isna(dv)):
        return False
    try:
        dv_d = date.fromisoformat(str(dv)) if not isinstance(dv, date) else dv
        return (today - dv_d).days <= 180
    except Exception:
        return False


nb_verifies = sum(1 for dv in df_all["Vérifié"] if _recent(dv))
nb_dici = sum(1 for d in df_all["DICI"] if d and not (isinstance(d, float) and pd.isna(d)))
aum_values = [
    v for v in df_all["AUM (Mds€)"] if v is not None and not (isinstance(v, float) and pd.isna(v))
]
aum_total = sum(float(v) for v in aum_values) if aum_values else 0.0

col_s1, col_s2, col_s3, col_s4 = st.columns(4)
with col_s1:
    st.metric("ETF dans l'univers", nb_total)
with col_s2:
    st.metric("Vérifiés < 6 mois", nb_verifies)
with col_s3:
    st.metric("Avec URL DICI", nb_dici)
with col_s4:
    st.metric("AUM cumulé", f"{aum_total:.1f} Mds€" if aum_total > 0 else "N/D")

st.divider()

# ─── Filtres ─────────────────────────────────────────────────────────────────

st.subheader("🔍 Filtres")

col_f1, col_f2 = st.columns(2)

with col_f1:
    st.markdown("**Enveloppes éligibles (intersection)**")
    filtre_pea = st.checkbox("PEA", value=False)
    filtre_av = st.checkbox("AV (Assurance-Vie)", value=False)
    filtre_per = st.checkbox("PER", value=False)
    filtre_cto = st.checkbox("CTO", value=False)

with col_f2:
    # Filtre classe d'actifs
    classes_dispo = sorted(df_all["Classe"].dropna().unique().tolist())
    classes_selectionnees = st.multiselect(
        "Classe d'actifs",
        options=classes_dispo,
        default=[],
        help="Laisser vide = toutes les classes",
    )

col_f3, col_f4 = st.columns(2)

with col_f3:
    ter_max_pct = st.slider(
        "TER maximum (%)",
        min_value=0.0,
        max_value=1.0,
        value=1.0,
        step=0.05,
        format="%.2f%%",
        help="Filtre sur le Total Expense Ratio",
    )

with col_f4:
    aum_min = st.slider(
        "AUM minimum (Mds€)",
        min_value=0.0,
        max_value=10.0,
        value=0.0,
        step=0.1,
        help="Filtre sur les actifs sous gestion. 0 = pas de filtre.",
    )

# ─── Application des filtres ─────────────────────────────────────────────────

df_filtree = df_all.copy()

# Filtres enveloppes (intersection)
if filtre_pea:
    df_filtree = df_filtree[df_filtree["_pea_raw"] == True]  # noqa: E712
if filtre_av:
    df_filtree = df_filtree[df_filtree["_av_raw"] == True]  # noqa: E712
if filtre_per:
    df_filtree = df_filtree[df_filtree["_per_raw"] == True]  # noqa: E712
if filtre_cto:
    df_filtree = df_filtree[df_filtree["_cto_raw"] == True]  # noqa: E712

# Filtre classe
if classes_selectionnees:
    df_filtree = df_filtree[df_filtree["Classe"].isin(classes_selectionnees)]

# Filtre TER
ter_max = ter_max_pct / 100.0
df_filtree = df_filtree[df_filtree["TER"].isna() | (df_filtree["TER"] <= ter_max)]

# Filtre AUM
if aum_min > 0:
    df_filtree = df_filtree[
        df_filtree["AUM (Mds€)"].notna() & (df_filtree["AUM (Mds€)"] >= aum_min)
    ]

st.markdown(f"**{len(df_filtree)} ETF affiché(s)** sur {nb_total} total")

# ─── Tableau résultats ────────────────────────────────────────────────────────

if df_filtree.empty:
    st.info("Aucun ETF ne correspond aux filtres sélectionnés.")
else:
    # Colonnes d'affichage
    df_display = df_filtree[
        [
            "ISIN",
            "Ticker",
            "Nom",
            "Émetteur",
            "TER",
            "AUM (Mds€)",
            "Domicile",
            "Réplication",
            "Acc/Dist",
            "TD 3y",
            "PEA",
            "AV",
            "PER",
            "CTO",
            "DICI",
            "Vérifié",
        ]
    ].copy()

    # Formatter les colonnes booléennes avec icônes
    for col_env in ["PEA", "AV", "PER", "CTO"]:
        df_display[col_env] = df_display[col_env].apply(lambda v: _bool_icon(v))

    # TER en %
    df_display["TER"] = df_display["TER"].apply(
        lambda v: (
            f"{float(v):.2%}"
            if v is not None and not (isinstance(v, float) and pd.isna(v))
            else "—"
        )
    )

    # AUM formaté
    df_display["AUM (Mds€)"] = df_display["AUM (Mds€)"].apply(
        lambda v: (
            f"{float(v):.2f}"
            if v is not None and not (isinstance(v, float) and pd.isna(v))
            else "—"
        )
    )

    # TD 3y formaté
    df_display["TD 3y"] = df_display["TD 3y"].apply(
        lambda v: (
            f"{float(v):.2%}"
            if v is not None and not (isinstance(v, float) and pd.isna(v))
            else "—"
        )
    )

    # DICI : lien cliquable
    df_display["DICI"] = df_display["DICI"].apply(
        lambda v: f"[🔗 DICI]({v})" if v and not (isinstance(v, float) and pd.isna(v)) else "—"
    )

    # Badge vérification
    df_display["Vérifié"] = df_display["Vérifié"].apply(
        lambda v: _badge_verification(
            str(v) if v and not (isinstance(v, float) and pd.isna(v)) else None
        )
    )

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # ─── Export CSV ──────────────────────────────────────────────────────────

    csv_data = df_display.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button(
        label="📥 Export CSV",
        data=csv_data.encode("utf-8-sig"),
        file_name=f"univers_etf_filtre_{date.today()}.csv",
        mime="text/csv",
        help="Télécharger le tableau filtré en CSV (séparateur ;)",
    )

# ─── Navigation ──────────────────────────────────────────────────────────────

st.divider()
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("🎯 Allocation cible", use_container_width=True):
        st.switch_page("pages/05_Allocation.py")
with col_nav2:
    if st.button("🏦 Asset Location →", type="primary", use_container_width=True):
        st.switch_page("pages/07_Asset_Location.py")
