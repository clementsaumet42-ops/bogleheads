"""Tests Sprint S15 Lot A — Screener ETF assisté."""

from __future__ import annotations

from types import SimpleNamespace

from src.execution.screener import (
    _etf_correspond_case,
    _score_aum,
    _score_capi_dist,
    _score_domicile_ue,
    _score_eligibilite,
    _score_ter,
    _score_tracking_diff,
    screener_etf,
)

# ─── Fixtures ETF ─────────────────────────────────────────────────────────────


def _elig(**kwargs):
    defaults = {
        "PEA": False,
        "AV_UC": False,
        "PER": False,
        "CTO_perso": True,
        "CTO_IS": True,
        "Contrat_Cap_IS": False,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _etf(
    ticker="IWDA",
    isin="IE00B4L5Y983",
    nom="iShares MSCI World",
    ter=0.002,
    domicile="Irlande",
    domicile_iso="IE",
    capitalisant=True,
    sous_classe="Monde développé",
    classe_actifs="Actions",
    exposition_geo="Monde_dev",
    volume_quotidien_m_eur=45.0,
    tracking_difference_1y=-0.0005,
    contrats_av_reference=None,
    eligibilite=None,
):
    if eligibilite is None:
        eligibilite = _elig(PEA=False, AV_UC=True, PER=True)
    if contrats_av_reference is None:
        contrats_av_reference = []
    return SimpleNamespace(
        ticker=ticker,
        isin=isin,
        nom=nom,
        ter=ter,
        domicile=domicile,
        domicile_iso=domicile_iso,
        capitalisant=capitalisant,
        sous_classe=sous_classe,
        classe_actifs=classe_actifs,
        exposition_geo=exposition_geo,
        volume_quotidien_m_eur=volume_quotidien_m_eur,
        tracking_difference_1y=tracking_difference_1y,
        contrats_av_reference=contrats_av_reference,
        eligibilite=eligibilite,
    )


def _catalogue_minimal():
    """Catalogue minimal pour les tests (format dict brut)."""
    return {
        "univers_etf": [
            {
                "isin": "IE0031442068",
                "ticker": "CW8",
                "nom": "Amundi MSCI World PEA",
                "ter": 0.0038,
                "domicile": "Irlande",
                "domicile_iso": "IE",
                "capitalisant": True,
                "sous_classe": "Monde développé",
                "classe_actifs": "Actions",
                "exposition_geo": "Monde_dev",
                "volume_quotidien_m_eur": 15.0,
                "tracking_difference_1y": -0.0003,
                "contrats_av_reference": ["Linxea Spirit 2"],
                "eligibilite": {"PEA": True, "AV_UC": True, "PER": True, "CTO_perso": True},
            },
            {
                "isin": "IE00B4L5Y983",
                "ticker": "IWDA",
                "nom": "iShares Core MSCI World",
                "ter": 0.002,
                "domicile": "Irlande",
                "domicile_iso": "IE",
                "capitalisant": True,
                "sous_classe": "Monde développé",
                "classe_actifs": "Actions",
                "exposition_geo": "Monde_dev",
                "volume_quotidien_m_eur": 45.0,
                "tracking_difference_1y": -0.0005,
                "contrats_av_reference": ["Linxea Spirit 2"],
                "eligibilite": {"PEA": False, "AV_UC": True, "PER": True, "CTO_perso": True},
            },
            {
                "isin": "LU1681043599",
                "ticker": "LCWD",
                "nom": "Amundi MSCI World CTO",
                "ter": 0.0038,
                "domicile": "Luxembourg",
                "domicile_iso": "LU",
                "capitalisant": True,
                "sous_classe": "Monde développé",
                "classe_actifs": "Actions",
                "exposition_geo": "Monde_dev",
                "volume_quotidien_m_eur": 8.0,
                "tracking_difference_1y": None,
                "contrats_av_reference": [],
                "eligibilite": {"PEA": False, "AV_UC": True, "PER": True, "CTO_perso": True},
            },
        ]
    }


# ─── Tests scoring par critère ────────────────────────────────────────────────


class TestScoreTer:
    def test_ter_zero_score_un(self):
        assert _score_ter(0.0) == 1.0

    def test_ter_un_pct_score_zero(self):
        assert _score_ter(0.01) == 0.0

    def test_ter_normal(self):
        score = _score_ter(0.002)
        assert 0.7 < score < 0.9

    def test_ter_none_score_neutre(self):
        assert _score_ter(None) == 0.5


class TestScoreAum:
    def test_aum_sous_seuil_score_zero(self):
        assert _score_aum(50.0) == 0.0

    def test_aum_none_score_neutre(self):
        assert _score_aum(None) == 0.3

    def test_aum_grand_score_eleve(self):
        score = _score_aum(10000.0)
        assert score >= 0.9

    def test_aum_seuil_score_faible(self):
        score = _score_aum(100.0)
        assert score >= 0.0


class TestScoreTrackingDiff:
    def test_td_negatif_score_eleve(self):
        score = _score_tracking_diff(-0.002)
        assert score == 1.0

    def test_td_positif_score_faible(self):
        score = _score_tracking_diff(0.002)
        assert score == 0.0

    def test_td_none_score_neutre(self):
        assert _score_tracking_diff(None) == 0.5


class TestScoreEligibilite:
    def test_pea_refuse_non_ue(self):
        """PEA refuse un ETF hors UE (domicile US)."""
        etf = _etf(
            domicile="États-Unis",
            domicile_iso="US",
            eligibilite=_elig(PEA=True),
        )
        assert _score_eligibilite(etf, "PEA", {}) == 0.0

    def test_pea_accepte_ue(self):
        """PEA accepte un ETF domicilié en Irlande avec eligibilite PEA=True."""
        etf = _etf(
            domicile="Irlande",
            domicile_iso="IE",
            eligibilite=_elig(PEA=True),
        )
        assert _score_eligibilite(etf, "PEA", {}) == 1.0

    def test_pea_refuse_eligibilite_false(self):
        """PEA refuse un ETF avec eligibilite.PEA=False."""
        etf = _etf(
            domicile="Irlande",
            domicile_iso="IE",
            eligibilite=_elig(PEA=False),
        )
        assert _score_eligibilite(etf, "PEA", {}) == 0.0

    def test_av_refuse_hors_contrat(self):
        """AV refuse un ETF non référencé dans le contrat."""
        etf = _etf(
            contrats_av_reference=["Generali"],
            eligibilite=_elig(AV_UC=True),
        )
        contexte = {"contrat_av": "Linxea Spirit 2"}
        assert _score_eligibilite(etf, "AV", contexte) == 0.0

    def test_av_accepte_contrat_reference(self):
        """AV accepte un ETF référencé dans le contrat."""
        etf = _etf(
            contrats_av_reference=["Linxea Spirit 2"],
            eligibilite=_elig(AV_UC=True),
        )
        contexte = {"contrat_av": "Linxea Spirit 2"}
        assert _score_eligibilite(etf, "AV", contexte) == 1.0

    def test_cto_accepte_tous(self):
        """CTO accepte tout ETF avec CTO_perso=True."""
        etf = _etf(eligibilite=_elig(CTO_perso=True))
        assert _score_eligibilite(etf, "CTO", {}) == 1.0


class TestScoreCapiDist:
    def test_cto_prefere_capitalisant(self):
        etf = _etf(capitalisant=True)
        assert _score_capi_dist(etf, "CTO") == 1.0

    def test_cto_penalise_distribuant(self):
        etf = _etf(capitalisant=False)
        assert _score_capi_dist(etf, "CTO") < 1.0

    def test_pea_indifferent(self):
        etf_c = _etf(capitalisant=True)
        etf_d = _etf(capitalisant=False)
        # Pas de forte discrimination en PEA
        assert _score_capi_dist(etf_c, "PEA") == _score_capi_dist(etf_d, "PEA")


class TestScoreDomicileUE:
    def test_irlande_bonus(self):
        etf = _etf(domicile="Irlande", domicile_iso="IE")
        assert _score_domicile_ue(etf) == 1.0

    def test_luxembourg_bonus(self):
        etf = _etf(domicile="Luxembourg", domicile_iso="LU")
        assert _score_domicile_ue(etf) == 1.0

    def test_usa_pas_bonus(self):
        etf = _etf(domicile="États-Unis", domicile_iso="US")
        assert _score_domicile_ue(etf) == 0.0


# ─── Tests correspondance case ────────────────────────────────────────────────


class TestEtfCorrespondCase:
    def test_monde_dev_match(self):
        etf = _etf(sous_classe="Monde développé")
        assert _etf_correspond_case(etf, "actions_monde_dev") is True

    def test_emergents_match(self):
        etf = _etf(sous_classe="Pays émergents", exposition_geo="Emergents")
        assert _etf_correspond_case(etf, "actions_emergents") is True

    def test_no_match(self):
        etf = _etf(sous_classe="Monde développé")
        assert _etf_correspond_case(etf, "or") is False


# ─── Tests screener_etf ───────────────────────────────────────────────────────


class TestScreenerETF:
    def test_top3_retourne_au_plus_3(self):
        catalogue = _catalogue_minimal()
        result = screener_etf("actions_monde_dev", "CTO", {}, catalogue, top_n=3)
        assert len(result) <= 3

    def test_top1_retourne_1(self):
        catalogue = _catalogue_minimal()
        result = screener_etf("actions_monde_dev", "CTO", {}, catalogue, top_n=1)
        assert len(result) == 1

    def test_tri_par_score_decroissant(self):
        catalogue = _catalogue_minimal()
        result = screener_etf("actions_monde_dev", "CTO", {}, catalogue, top_n=3)
        scores = [r["score_global"] for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_pea_filtre_non_ue(self):
        """Le PEA ne retourne que des ETF domiciliés UE avec eligibilite PEA=True."""
        catalogue = {
            "univers_etf": [
                {
                    "isin": "US1234567890",
                    "ticker": "SPY",
                    "nom": "SPDR S&P 500 ETF",
                    "ter": 0.001,
                    "domicile": "États-Unis",
                    "domicile_iso": "US",
                    "capitalisant": True,
                    "sous_classe": "Monde développé",
                    "classe_actifs": "Actions",
                    "exposition_geo": "Monde_dev",
                    "volume_quotidien_m_eur": 500.0,
                    "tracking_difference_1y": 0.0,
                    "contrats_av_reference": [],
                    "eligibilite": {
                        "PEA": False,
                        "AV_UC": False,
                        "PER": True,
                        "CTO_perso": True,
                    },
                },
            ]
        }
        result = screener_etf("actions_monde_dev", "PEA", {}, catalogue, top_n=3)
        assert result == []

    def test_pea_garde_etf_ue_eligible(self):
        """PEA retourne l'ETF domicilié UE avec PEA=True."""
        catalogue = {
            "univers_etf": [
                {
                    "isin": "IE0031442068",
                    "ticker": "CW8",
                    "nom": "Amundi MSCI World PEA",
                    "ter": 0.0038,
                    "domicile": "Irlande",
                    "domicile_iso": "IE",
                    "capitalisant": True,
                    "sous_classe": "Monde développé",
                    "classe_actifs": "Actions",
                    "exposition_geo": "Monde_dev",
                    "volume_quotidien_m_eur": 15.0,
                    "tracking_difference_1y": -0.0003,
                    "contrats_av_reference": [],
                    "eligibilite": {"PEA": True, "AV_UC": True, "PER": True, "CTO_perso": True},
                },
            ]
        }
        result = screener_etf("actions_monde_dev", "PEA", {}, catalogue, top_n=3)
        assert len(result) == 1
        assert result[0]["ticker"] == "CW8"

    def test_resultat_contient_champs_requis(self):
        catalogue = _catalogue_minimal()
        result = screener_etf("actions_monde_dev", "CTO", {}, catalogue, top_n=1)
        assert len(result) == 1
        r = result[0]
        assert "isin" in r
        assert "ticker" in r
        assert "nom" in r
        assert "ter" in r
        assert "score_global" in r
        assert "score_detail" in r
        assert "commentaire" in r

    def test_catalogue_vide_retourne_liste_vide(self):
        result = screener_etf("actions_monde_dev", "CTO", {}, {}, top_n=3)
        assert result == []

    def test_poids_personnalises(self):
        """Les pondérations personnalisées influencent le classement."""
        catalogue = _catalogue_minimal()
        # Pondération forte sur TER
        poids_ter = {"ter": 1.0, "aum": 0.0, "tracking_diff": 0.0,
                     "eligibilite": 0.0, "capi_dist": 0.0, "domicile_ue": 0.0}
        result = screener_etf("actions_monde_dev", "CTO", {}, catalogue, top_n=3, poids=poids_ter)
        assert len(result) > 0
        # Doit contenir IWDA (TER 0.20%, le meilleur)
        tickers = [r["ticker"] for r in result]
        assert "IWDA" in tickers
        # IWDA doit être en premier
        assert result[0]["ticker"] == "IWDA"
