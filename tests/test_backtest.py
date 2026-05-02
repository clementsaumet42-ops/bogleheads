"""Tests pour le système de backtest S9."""

from __future__ import annotations

import contextlib

import pytest

with contextlib.suppress(ImportError):
    import pandas as pd
    from src.backtest.donnees_historiques import aligner_series, charger_serie
    from src.backtest.fiscalite_backtest import (
        ConfigFiscalite,
        calculer_impot_dividendes_cto,
    )
    from src.backtest.frais import ConfigFrais, appliquer_ter_mensuel
    from src.backtest.metriques import (
        calculer_cagr,
        calculer_calmar,
        calculer_max_drawdown,
        calculer_sharpe,
        calculer_volatilite_annuelle,
    )
    from src.backtest.moteur_backtest import ResultatBacktest, backtester
    from src.backtest.portefeuilles_bogle import (
        BOGLE_2_FUNDS_70_30,
        PORTEFEUILLES_DISPONIBLES,
        PortefeuilleBogle,
    )

pytestmark = pytest.mark.skip(reason="Module archivé suite au pivot EC — voir archive/README.md")

# ─── Fixtures ────────────────────────────────────────────────────────────────

with contextlib.suppress(NameError):
    CONFIG_FRAIS_ZERO = ConfigFrais(
        ter_par_classe={},
        courtage_par_ordre_eur=0.0,
        spread_bps=0.0,
        frais_enveloppe_annuel_pct={},
    )

    CONFIG_FRAIS_REEL = ConfigFrais(
        ter_par_classe={"actions_monde_developpe": 0.002, "obligations_euro_agg": 0.001},
        courtage_par_ordre_eur=1.0,
        spread_bps=5.0,
        frais_enveloppe_annuel_pct={"PEA": 0.0, "AV": 0.006},
    )

    CONFIG_FISCAL_ZERO = ConfigFiscalite(
        pfu_taux=0.30,
        ps_taux=0.172,
        distribution_par_classe={},
        rebalancement_seuil_pct=0.05,
    )

    CONFIG_FISCAL_AVEC_DISTRIB = ConfigFiscalite(
        pfu_taux=0.30,
        ps_taux=0.172,
        distribution_par_classe={"obligations_euro_agg": 0.02, "cash_eur": 0.03},
        rebalancement_seuil_pct=0.05,
    )


# ─── Tests chargement données ────────────────────────────────────────────────


def test_charger_serie_csv_existe():
    """CSV présent → série chargée correctement."""
    serie = charger_serie("actions_monde_developpe")
    assert isinstance(serie, pd.Series)
    assert len(serie) > 0
    assert serie.name == "actions_monde_developpe"
    assert isinstance(serie.index, pd.DatetimeIndex)


def test_charger_serie_longueur_attendue():
    """264 mois de 2003-01 à 2024-12."""
    serie = charger_serie("actions_monde_developpe")
    assert len(serie) == 264


def test_charger_serie_cash_eur():
    serie = charger_serie("cash_eur")
    assert len(serie) == 264
    assert serie.name == "cash_eur"


def test_charger_serie_absente_leve_erreur():
    """CSV absent sans yfinance → FileNotFoundError."""
    with pytest.raises((FileNotFoundError, Exception)):
        charger_serie("classe_inexistante_xyz_abc")


def test_aligner_series_deux_series_identiques():
    """Deux séries identiques → DataFrame avec 2 colonnes."""
    s1 = charger_serie("actions_monde_developpe")
    s2 = charger_serie("obligations_euro_agg")
    df = aligner_series(s1, s2)
    assert isinstance(df, pd.DataFrame)
    assert df.shape[1] == 2
    assert len(df) > 0


def test_aligner_series_meme_longueur():
    """Séries de même longueur → pas de perte."""
    s1 = charger_serie("actions_monde_developpe")
    s2 = charger_serie("or")
    df = aligner_series(s1, s2)
    assert len(df) == 264


def test_aligner_series_une_seule():
    """Une seule série → DataFrame une colonne."""
    s1 = charger_serie("cash_eur")
    df = aligner_series(s1)
    assert df.shape[1] == 1


def test_aligner_series_vide_leve_erreur():
    with pytest.raises(ValueError, match="Au moins une série"):
        aligner_series()


def test_aligner_series_trou_trop_grand():
    """Trou > 3 mois → ValueError."""
    idx = pd.date_range("2003-01-31", periods=20, freq="ME")
    s1 = pd.Series([0.01] * 20, index=idx, name="s1")
    s2 = pd.Series([0.01] * 20, index=idx, name="s2")
    # Introduire un trou de 5 NaN dans s2
    s2.iloc[5:10] = None
    with pytest.raises(ValueError):
        aligner_series(s1, s2, fill_max_mois=3)


# ─── Tests portefeuilles Bogle ────────────────────────────────────────────────


def test_portefeuille_allocations_somme_1():
    for nom, pf in PORTEFEUILLES_DISPONIBLES.items():
        total = sum(pf.allocations.values())
        assert abs(total - 1.0) < 1e-6, f"{nom}: somme={total}"


def test_portefeuille_invalide_somme_mauvaise():
    with pytest.raises(ValueError, match="somme des allocations"):
        PortefeuilleBogle(
            nom="test",
            description="d",
            source="s",
            allocations={"a": 0.5, "b": 0.6},
        )


def test_portefeuille_invalide_poids_negatif():
    with pytest.raises(ValueError):
        PortefeuilleBogle(
            nom="test",
            description="d",
            source="s",
            allocations={"a": 1.2, "b": -0.2},
        )


def test_tous_portefeuilles_disponibles():
    assert len(PORTEFEUILLES_DISPONIBLES) == 5
    assert "BOGLE_2_FUNDS_70_30" in PORTEFEUILLES_DISPONIBLES


# ─── Tests métriques ─────────────────────────────────────────────────────────


def test_cagr_1pct_mensuel():
    """1% mensuel constant sur 1 an → CAGR ≈ 12.68%."""
    capital_initial = 100_000.0
    capital_final = capital_initial * (1.01**12)
    cagr = calculer_cagr(capital_initial, capital_final, 1.0)
    assert abs(cagr - 0.1268) < 0.001


def test_cagr_zero_returns():
    """0% mensuel → CAGR = 0%."""
    cagr = calculer_cagr(100_000, 100_000, 10.0)
    assert cagr == 0.0


def test_cagr_capital_initial_zero():
    assert calculer_cagr(0, 100_000, 10.0) == 0.0


def test_volatilite_constante_zero():
    """Série constante → volatilité ≈ 0 (erreur flottante tolérée)."""
    s = pd.Series([0.01] * 60)
    vol = calculer_volatilite_annuelle(s)
    assert vol < 1e-10


def test_volatilite_annualisee():
    """Volatilité annualisée = std mensuel * sqrt(12)."""
    import numpy as np

    s = pd.Series([0.01, -0.02, 0.03, -0.01, 0.02] * 12)
    vol = calculer_volatilite_annuelle(s)
    expected = float(s.std() * np.sqrt(12))
    assert abs(vol - expected) < 1e-10


def test_sharpe_series_positive():
    """Série à rendement moyen >> taux sans risque → Sharpe > 0."""
    import numpy as np

    rng = np.random.default_rng(7)
    s = pd.Series(rng.normal(0.05, 0.01, 60))
    sharpe = calculer_sharpe(s)
    assert sharpe > 0


def test_sharpe_serie_variable_positive():
    """Série positive variable → Sharpe > 0."""
    import numpy as np

    rng = np.random.default_rng(42)
    s = pd.Series(rng.normal(0.01, 0.03, 120))
    sharpe = calculer_sharpe(s)
    assert sharpe > 0


def test_max_drawdown_negatif():
    """Drawdown doit être négatif ou nul."""
    s = pd.Series([100, 110, 105, 90, 95, 100.0])
    mdd = calculer_max_drawdown(s)
    assert mdd <= 0.0


def test_max_drawdown_serie_croissante():
    """Série strictement croissante → drawdown = 0."""
    s = pd.Series([100, 101, 102, 103, 104.0])
    mdd = calculer_max_drawdown(s)
    assert mdd == 0.0


def test_calmar_zero_drawdown():
    assert calculer_calmar(0.07, 0.0) == 0.0


def test_ter_mensuel_reduit_valeur():
    """TER réduit la valeur. 0.2% annuel → ~99983.35€."""
    val = appliquer_ter_mensuel(100_000, 0.002)
    assert val < 100_000
    assert val > 99_980
    # Vérification mathématique : val = 100000 * (1 - ter) ^ (1/12)
    expected = 100_000 * (0.998 ** (1 / 12))
    assert abs(val - expected) < 0.01


# ─── Tests backtest principal ─────────────────────────────────────────────────


def _backtester_simple(mode: str = "brut") -> ResultatBacktest:
    return backtester(
        portefeuille=BOGLE_2_FUNDS_70_30,
        capital_initial_eur=100_000.0,
        date_debut="2003-01-31",
        date_fin="2024-12-31",
        config_frais=CONFIG_FRAIS_ZERO,
        config_fiscalite=CONFIG_FISCAL_ZERO,
        mode=mode,
    )


def test_backtest_brut_retourne_resultat():
    res = _backtester_simple("brut")
    assert isinstance(res, ResultatBacktest)
    assert res.portefeuille_nom == "BOGLE_2_FUNDS_70_30"
    assert res.capital_initial == 100_000.0
    assert res.capital_final > 0


def test_backtest_brut_serie_valeur_non_vide():
    res = _backtester_simple("brut")
    assert len(res.serie_valeur_mensuelle) > 0
    assert len(res.serie_valeur_mensuelle) == 264


def test_backtest_brut_cagr_positif():
    """Données positives → CAGR > 0."""
    res = _backtester_simple("brut")
    assert res.cagr > 0


def test_backtest_net_frais_inferieur_brut():
    """Net frais ≤ brut (frais réels)."""
    res_brut = backtester(
        portefeuille=BOGLE_2_FUNDS_70_30,
        capital_initial_eur=100_000.0,
        date_debut="2003-01-31",
        date_fin="2024-12-31",
        config_frais=CONFIG_FRAIS_REEL,
        config_fiscalite=CONFIG_FISCAL_ZERO,
        mode="brut",
    )
    res_net = backtester(
        portefeuille=BOGLE_2_FUNDS_70_30,
        capital_initial_eur=100_000.0,
        date_debut="2003-01-31",
        date_fin="2024-12-31",
        config_frais=CONFIG_FRAIS_REEL,
        config_fiscalite=CONFIG_FISCAL_ZERO,
        mode="net_frais",
    )
    assert res_net.capital_final <= res_brut.capital_final
    assert res_net.frais_totaux_eur > 0


def test_backtest_net_fiscal_inferieur_net_frais():
    """Fiscal CTO ≤ net frais (dividendes taxés)."""
    res_frais = backtester(
        portefeuille=BOGLE_2_FUNDS_70_30,
        capital_initial_eur=100_000.0,
        date_debut="2003-01-31",
        date_fin="2024-12-31",
        config_frais=CONFIG_FRAIS_REEL,
        config_fiscalite=CONFIG_FISCAL_AVEC_DISTRIB,
        mode="net_frais",
    )
    res_fiscal = backtester(
        portefeuille=BOGLE_2_FUNDS_70_30,
        capital_initial_eur=100_000.0,
        date_debut="2003-01-31",
        date_fin="2024-12-31",
        config_frais=CONFIG_FRAIS_REEL,
        config_fiscalite=CONFIG_FISCAL_AVEC_DISTRIB,
        mode="net_fiscal_cto",
    )
    assert res_fiscal.capital_final <= res_frais.capital_final


def test_backtest_net_optimise_superieur_net_fiscal():
    """Net optimisé ≥ net fiscal CTO (fiscalité réduite)."""
    res_fiscal = backtester(
        portefeuille=BOGLE_2_FUNDS_70_30,
        capital_initial_eur=100_000.0,
        date_debut="2003-01-31",
        date_fin="2024-12-31",
        config_frais=CONFIG_FRAIS_ZERO,
        config_fiscalite=CONFIG_FISCAL_AVEC_DISTRIB,
        mode="net_fiscal_cto",
    )
    res_optimise = backtester(
        portefeuille=BOGLE_2_FUNDS_70_30,
        capital_initial_eur=100_000.0,
        date_debut="2003-01-31",
        date_fin="2024-12-31",
        config_frais=CONFIG_FRAIS_ZERO,
        config_fiscalite=CONFIG_FISCAL_AVEC_DISTRIB,
        mode="net_optimise",
    )
    assert res_optimise.capital_final >= res_fiscal.capital_final


def test_backtest_zero_returns_capital_constant():
    """Série à 0% → capital final ≈ capital initial (brut, frais zéro)."""
    idx = pd.date_range("2010-01-31", periods=36, freq="ME")
    # Patch: on crée un CSV de zéros temporaire
    import csv

    from src.backtest.donnees_historiques import DATA_DIR

    zero_csv = DATA_DIR / "zero_test_tmp.csv"
    try:
        with open(zero_csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["date", "rendement_total_eur"])
            for d in idx:
                w.writerow([str(d.date()), 0.0])

        zero_pf2 = PortefeuilleBogle(
            nom="ZERO_TEST",
            description="test",
            source="test",
            allocations={"zero_test_tmp": 1.0},
        )
        res = backtester(
            portefeuille=zero_pf2,
            capital_initial_eur=100_000.0,
            date_debut="2010-01-31",
            date_fin="2012-12-31",
            config_frais=CONFIG_FRAIS_ZERO,
            config_fiscalite=CONFIG_FISCAL_ZERO,
            mode="brut",
        )
        assert abs(res.capital_final - 100_000.0) < 1.0
    finally:
        if zero_csv.exists():
            zero_csv.unlink()


def test_backtest_reproducible():
    """Deux runs identiques → résultats identiques."""
    r1 = _backtester_simple("brut")
    r2 = _backtester_simple("brut")
    assert r1.capital_final == r2.capital_final
    assert r1.cagr == r2.cagr


def test_backtest_detail_annuel_non_vide():
    res = _backtester_simple("brut")
    assert len(res.detail_annuel) > 0
    for d in res.detail_annuel:
        assert "annee" in d
        assert "capital_fin" in d


def test_tous_5_portefeuilles_fonctionnent():
    """Les 5 portefeuilles Bogle doivent tourner sans erreur."""
    for nom, pf in PORTEFEUILLES_DISPONIBLES.items():
        res = backtester(
            portefeuille=pf,
            capital_initial_eur=100_000.0,
            date_debut="2010-01-31",
            date_fin="2020-12-31",
            config_frais=CONFIG_FRAIS_ZERO,
            config_fiscalite=CONFIG_FISCAL_ZERO,
            mode="brut",
        )
        assert res.capital_final > 0, f"{nom}: capital_final <= 0"
        assert res.portefeuille_nom == nom


def test_backtest_max_drawdown_negatif_ou_nul():
    res = _backtester_simple("brut")
    assert res.max_drawdown <= 0.0


def test_backtest_frais_zero_no_frais():
    """Frais zéro → frais_totaux = 0."""
    res = backtester(
        portefeuille=BOGLE_2_FUNDS_70_30,
        capital_initial_eur=100_000.0,
        date_debut="2003-01-31",
        date_fin="2024-12-31",
        config_frais=CONFIG_FRAIS_ZERO,
        config_fiscalite=CONFIG_FISCAL_ZERO,
        mode="brut",
    )
    assert res.frais_totaux_eur == 0.0


def test_impot_dividendes_cto_calcul():
    """Test calcul impôt dividendes CTO."""
    config = ConfigFiscalite(
        pfu_taux=0.30,
        ps_taux=0.172,
        distribution_par_classe={"obligations_euro_agg": 0.02},
    )
    valeurs = {"obligations_euro_agg": 100_000.0}
    impot = calculer_impot_dividendes_cto(valeurs, config)
    # dividendes = 100000 * 0.02 = 2000; impôt = 2000 * 0.30 = 600
    assert abs(impot - 600.0) < 0.01


def test_schema_configbacktest_yaml():
    """backtest.yaml se charge et valide correctement."""
    from src.schemas import charger_et_valider

    config = charger_et_valider("backtest.yaml")
    assert config.backtest.capital_initial_eur == 100_000.0
    assert "BOGLE_2_FUNDS_70_30" in config.backtest.portefeuilles_actifs
