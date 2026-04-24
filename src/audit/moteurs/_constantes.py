"""Constantes des moteurs d'audit S8.2b.

Toutes les hypothèses chiffrées (rendements dividendes, pondérations géographiques,
taux d'actualisation) sont documentées avec source et date.
"""

# ─── Pondération géographique par indice ─────────────────────────────────────
# Source: factsheets émetteurs (iShares, Amundi, Vanguard), mise à jour janvier 2025
# Clés: "US" = actions américaines, "DEV_HORS_US" = développés hors US, "EM" = émergents
PONDERATION_GEO_PAR_INDICE: dict[str, dict[str, float]] = {
    "MSCI_ACWI": {"US": 0.60, "DEV_HORS_US": 0.28, "EM": 0.12},
    "MSCI_WORLD": {"US": 0.71, "DEV_HORS_US": 0.29},
    "FTSE_ALL_WORLD": {"US": 0.62, "DEV_HORS_US": 0.27, "EM": 0.11},
    "STOXX_600": {"DEV_HORS_US": 1.00},
    "MSCI_EM": {"EM": 1.00},
    "SP500": {"US": 1.00},
    "NASDAQ_100": {"US": 1.00},
    "MSCI_EUROPE": {"DEV_HORS_US": 1.00},
    "MSCI_JAPAN": {"DEV_HORS_US": 1.00},
}

# ─── Rendement dividende par catégorie ───────────────────────────────────────
# Source: Bloomberg / iShares factsheets 2024, Vanguard VWRL factsheet 2024
# Exprimé en décimal (0.018 = 1.8%/an)
RENDEMENT_DIVIDENDE_PAR_CATEGORIE: dict[str, float] = {
    "MSCI_ACWI": 0.018,
    "MSCI_WORLD": 0.018,
    "MSCI_EM": 0.022,
    "STOXX_600": 0.030,
    "SP500": 0.015,
    "NASDAQ_100": 0.008,
    "MSCI_EUROPE": 0.030,
    "FTSE_ALL_WORLD": 0.018,
    "MSCI_JAPAN": 0.020,
    # Défaut si catégorie inconnue
    "_DEFAUT": 0.018,
}

# ─── Mapping sous_classe → indice de référence ───────────────────────────────
# Permet de faire la correspondance depuis les données YAML vers les constantes ci-dessus
SOUS_CLASSE_VERS_INDICE: dict[str, str] = {
    "Monde développé": "MSCI_WORLD",
    "Monde (tous pays)": "MSCI_ACWI",
    "USA S&P 500": "SP500",
    "USA Nasdaq-100": "NASDAQ_100",
    "Europe Stoxx 600": "STOXX_600",
    "Émergents MSCI EM": "MSCI_EM",
    "Europe EMU": "MSCI_EUROPE",
    "Zone Euro EMU": "MSCI_EUROPE",
    "Japon": "MSCI_JAPAN",
    "Monde FTSE": "FTSE_ALL_WORLD",
}

# ─── Groupes d'indices « équivalents » pour le moteur TD ─────────────────────
# Deux ETF sont comparables si leur indice appartient au même groupe.
# IMPORTANT : MSCI_WORLD ≠ MSCI_ACWI (World exclut les émergents) — pas de confusion.
GROUPES_INDICES_EQUIVALENTS: list[frozenset[str]] = [
    frozenset({"MSCI_WORLD"}),
    frozenset({"MSCI_ACWI", "FTSE_ALL_WORLD"}),  # ACWI ≈ FTSE All-World (note de confiance)
    frozenset({"SP500"}),
    frozenset({"NASDAQ_100"}),
    frozenset({"STOXX_600", "MSCI_EUROPE"}),
    frozenset({"MSCI_EM"}),
    frozenset({"MSCI_JAPAN"}),
]

# ─── AUM minimum pour considérer un ETF « liquide » ──────────────────────────
# Source: règle de gestion Boglehead FR — cf. justETF.com best practices 2024
AUM_MINIMUM_M_EUR: float = 500.0  # millions €

# ─── Seuil TD minimum pour recommander un switch ─────────────────────────────
# En dessous de 5 bps, le gain est trop marginal vs coût de la complexité
TD_SEUIL_BPSPAR_AN: float = 5.0  # bps/an

# ─── Seuil withholding minimum pour recommander un switch ────────────────────
WITHHOLDING_SEUIL_BPS: float = 3.0  # bps/an

# ─── Taux PFU France 2026 ─────────────────────────────────────────────────────
# Source: art. 200 A CGI — PFU 30% = 12.8% IR + 17.2% PS
PFU_TAUX: float = 0.30
PS_TAUX: float = 0.172  # prélèvements sociaux

# ─── Taux d'actualisation par défaut ─────────────────────────────────────────
# Source: pratique conseil en gestion de patrimoine FR — taux OAT 30 ans ≈ 3.5% + prime risque
TAUX_ACTUALISATION_DEFAUT: float = 0.04  # 4%/an

# ─── Rendement total hypothétique ─────────────────────────────────────────────
# Source: Dimson-Marsh-Staunton 2024 (Credit Suisse Global Investment Returns Yearbook),
# rendement réel actions mondiales 1900-2023 ≈ 5%/an, nominal avec inflation 2% ≈ 7%/an
RENDEMENT_TOTAL_ACTIONS: float = 0.07  # 7%/an nominal hypothétique

# ─── Frais AV — seuil pour candidature ───────────────────────────────────────
# Un contrat est candidat si ses frais UC sont inférieurs de ≥ 30 bps au contrat actuel
SEUIL_DIFF_FRAIS_AV: float = 0.003  # 30 bps

# ─── Frais broker — seuil pour recommandation ────────────────────────────────
# On recommande une alternative broker si le gain annuel > 50 €
SEUIL_GAIN_BROKER_EUR: float = 50.0

# ─── Domiciles ETF acceptables ────────────────────────────────────────────────
# Source: règle de gestion Boglehead FR — IE et LU sont les domiciles standard UCITS
DOMICILES_ACCEPTABLES: frozenset[str] = frozenset({"IE", "LU", "FR"})

# ─── Matrice retenues source par région pour calcul withholding ──────────────
# Correspondance région (dans PONDERATION_GEO) → pays représentatif dans matrice retenues
# Source: matrice retenues_source.yaml S8.2a
REGION_VERS_PAYS_REPRESENTATIF: dict[str, str] = {
    "US": "US",  # 15% pour IE/LU
    "DEV_HORS_US": "DE",  # 15% pour IE/LU — représentant pays développés hors US
    "EM": "CN",  # 10% pour IE/LU — représentant émergents
}
