"""Palette et injection CSS du thème Private Banking."""

import streamlit as st

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
BLEU_NUIT = "#0B1929"
BLEU_PROFOND = "#16263F"
IVOIRE = "#F5F1EA"
BLANC_CASSE = "#FAF7F2"
OR_VIEILLI = "#8B6F47"
OR_CLAIR = "#B8946A"
ARDOISE = "#2C2C2C"
ARDOISE_CLAIRE = "#5A5A5A"
ROUGE_BORDEAUX = "#6B1E2C"
VERT_FORET = "#2D4A3E"

# ---------------------------------------------------------------------------
# CSS global
# ---------------------------------------------------------------------------
_CSS = """
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@300;400;500;600&display=swap');

:root {
    --bleu-nuit:      #0B1929;
    --bleu-profond:   #16263F;
    --ivoire:         #F5F1EA;
    --blanc-casse:    #FAF7F2;
    --or-vieilli:     #8B6F47;
    --or-clair:       #B8946A;
    --ardoise:        #2C2C2C;
    --ardoise-claire: #5A5A5A;
    --rouge-bordeaux: #6B1E2C;
    --vert-foret:     #2D4A3E;
}

/* ── Corps ──────────────────────────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 15px;
    color: var(--ardoise);
    line-height: 1.7;
    background-color: var(--ivoire);
}

/* ── En-têtes ────────────────────────────────────────────────────────────── */
h1, h2, h3, h4, h5, h6,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 {
    font-family: 'EB Garamond', Georgia, 'Times New Roman', serif;
    color: var(--bleu-nuit);
    letter-spacing: -0.02em;
    line-height: 1.25;
}

h1, [data-testid="stMarkdownContainer"] h1 { font-size: 2.25rem; font-weight: 700; }
h2, [data-testid="stMarkdownContainer"] h2 { font-size: 1.75rem; font-weight: 600; }
h3, [data-testid="stMarkdownContainer"] h3 { font-size: 1.35rem; font-weight: 600; }

/* ── Espacement sections ─────────────────────────────────────────────────── */
[data-testid="block-container"] > div > div {
    padding-top: 2rem;
}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: var(--ivoire) !important;
    border-right: 0.5px solid var(--or-vieilli);
}
[data-testid="stSidebar"] * {
    font-family: 'Inter', system-ui, sans-serif;
}
[data-testid="stSidebar"] hr {
    border-color: var(--or-vieilli);
    opacity: 0.4;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    font-size: 0.8rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ardoise-claire);
}

/* ── Boutons primaires ───────────────────────────────────────────────────── */
[data-testid="baseButton-primary"],
button[kind="primary"],
.stButton > button[kind="primary"] {
    background-color: var(--bleu-nuit) !important;
    color: var(--ivoire) !important;
    border: 1px solid var(--or-vieilli) !important;
    border-radius: 2px !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    padding: 0.5rem 1.5rem !important;
    transition: border-color 0.2s ease, background-color 0.2s ease !important;
}
[data-testid="baseButton-primary"]:hover,
button[kind="primary"]:hover,
.stButton > button[kind="primary"]:hover {
    background-color: var(--bleu-profond) !important;
    border-color: var(--or-clair) !important;
    color: var(--or-clair) !important;
}

/* ── Boutons secondaires ─────────────────────────────────────────────────── */
[data-testid="baseButton-secondary"],
button[kind="secondary"],
.stButton > button:not([kind="primary"]) {
    background-color: transparent !important;
    color: var(--ardoise) !important;
    border: 1px solid var(--ardoise-claire) !important;
    border-radius: 2px !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    padding: 0.5rem 1.5rem !important;
    transition: border-color 0.2s ease, color 0.2s ease !important;
}
[data-testid="baseButton-secondary"]:hover,
button[kind="secondary"]:hover,
.stButton > button:not([kind="primary"]):hover {
    border-color: var(--or-vieilli) !important;
    color: var(--or-vieilli) !important;
}

/* ── Tables ──────────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] table,
.stDataFrame table {
    font-family: 'Inter', system-ui, sans-serif;
    border-collapse: collapse;
    width: 100%;
}
[data-testid="stDataFrame"] thead th,
.stDataFrame thead th {
    background-color: var(--bleu-nuit) !important;
    color: var(--ivoire) !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    padding: 0.6rem 0.75rem !important;
    border-bottom: 0.5px solid var(--or-vieilli) !important;
}
[data-testid="stDataFrame"] tbody tr:nth-child(odd) td,
.stDataFrame tbody tr:nth-child(odd) td {
    background-color: var(--ivoire) !important;
}
[data-testid="stDataFrame"] tbody tr:nth-child(even) td,
.stDataFrame tbody tr:nth-child(even) td {
    background-color: var(--blanc-casse) !important;
}
[data-testid="stDataFrame"] tbody td,
.stDataFrame tbody td {
    padding: 0.5rem 0.75rem !important;
    border-bottom: 0.5px solid rgba(139, 111, 71, 0.2) !important;
    font-variant-numeric: tabular-nums !important;
}
[data-testid="stDataFrame"] tbody tr:hover td,
.stDataFrame tbody tr:hover td {
    background-color: rgba(139, 111, 71, 0.08) !important;
}

/* ── Métriques (st.metric) ───────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background-color: var(--blanc-casse);
    border: 0.5px solid rgba(139, 111, 71, 0.3);
    border-radius: 2px;
    padding: 1rem 1.25rem;
}
[data-testid="stMetricValue"] {
    font-family: 'EB Garamond', Georgia, serif !important;
    font-size: 2rem !important;
    font-weight: 700 !important;
    color: var(--bleu-nuit) !important;
    font-variant-numeric: tabular-nums !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'Inter', system-ui, sans-serif !important;
    font-size: 0.688rem !important;
    font-style: italic !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    color: var(--ardoise-claire) !important;
}
[data-testid="stMetricDelta"] {
    font-family: 'Inter', system-ui, sans-serif !important;
    font-size: 0.8rem !important;
}

/* ── Alertes ─────────────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
    background-color: var(--blanc-casse) !important;
    border: none !important;
    border-radius: 2px !important;
    padding: 0.75rem 1rem 0.75rem 1.25rem !important;
}
[data-testid="stAlert"][data-baseweb="notification"] {
    border-left: 4px solid var(--or-vieilli) !important;
}
div[data-testid="stAlert"] > div[role="alert"] {
    background-color: transparent !important;
}

/* ── Expanders ───────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 0.5px solid rgba(139, 111, 71, 0.3) !important;
    border-radius: 2px !important;
    background-color: var(--blanc-casse) !important;
}
[data-testid="stExpander"] summary {
    font-family: 'Inter', system-ui, sans-serif !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.04em !important;
    color: var(--ardoise) !important;
}

/* ── Inputs ──────────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] div,
[data-testid="stMultiSelect"] div {
    border-color: rgba(139, 111, 71, 0.4) !important;
    border-radius: 2px !important;
    background-color: var(--blanc-casse) !important;
    font-family: 'Inter', system-ui, sans-serif !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: var(--or-vieilli) !important;
    box-shadow: 0 0 0 1px var(--or-vieilli) !important;
}

/* ── Diviseurs ───────────────────────────────────────────────────────────── */
hr {
    border: none !important;
    border-top: 0.5px solid rgba(139, 111, 71, 0.35) !important;
    margin: 2rem 0 !important;
}
"""


def injecter_css() -> None:
    """Injecte le CSS global du thème Private Banking dans l'application Streamlit."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)
