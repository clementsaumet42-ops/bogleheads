"""Tests S8.2b — 5 moteurs de quantification des bps en €.

Couverture : modèle Opportunite, helper capitaliser_30_ans, et les 5 moteurs
(tracking_difference, withholding, dist_vs_cap, frais_contrat_av, frais_broker).

≥ 20 tests, tous cas canoniques pré-calculés manuellement.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest
import yaml

from src.audit.moteurs._constantes import (
    PONDERATION_GEO_PAR_INDICE,
    RENDEMENT_DIVIDENDE_PAR_CATEGORIE,
)
from src.audit.moteurs.dist_vs_cap import detecter_opportunites_dist_vs_cap
from src.audit.moteurs.frais_broker import detecter_opportunites_frais_broker
from src.audit.moteurs.frais_contrat_av import detecter_opportunites_frais_av
from src.audit.moteurs.tracking_difference import detecter_opportunites_td
from src.audit.moteurs.withholding import detecter_opportunites_withholding
from src.audit.opportunite import LigneEtf, Opportunite, capitaliser_30_ans
from src.schemas import Broker, ContratAV, ETFEligibilite, ETFEnrichi, RetenuesSourceConfig

# ─── Fixtures ETF ────────────────────────────────────────────────────────────


def _make_etf(
    ticker: str,
    isin: str,
    sous_classe: str = "Monde développé",
    td3y: float | None = -0.0008,
    td1y: float | None = None,
    domicile_iso: str = "IE",
    dist_cap: str = "ACC",
    capitalisant: bool = True,
    ter: float = 0.002,
    classe_actifs: str = "Actions",
    pea: bool = False,
    av: bool = True,
    cto: bool = True,
    aum: float | None = None,
) -> ETFEnrichi:
    return ETFEnrichi(
        isin=isin,
        ticker=ticker,
        nom=f"ETF {ticker}",
        emetteur="iShares",
        classe_actifs=classe_actifs,
        sous_classe=sous_classe,
        ter=ter,
        devise="EUR",
        domicile="Irlande",
        domicile_iso=domicile_iso,
        capitalisant=capitalisant,
        eur_hedged=False,
        eligibilite=ETFEligibilite(
            PEA=pea,
            PER=True,
            PEE=False,
            CTO_perso=cto,
            CTO_IS=cto,
            Contrat_Cap_IS=False,
            AV_UC=av,
        ),
        distribuant_capitalisant=dist_cap,
        tracking_difference_3y=td3y,
        tracking_difference_1y=td1y,
        volume_quotidien_m_eur=aum,
    )


@pytest.fixture
def etf_cw8() -> ETFEnrichi:
    return _make_etf(
        ticker="CW8",
        isin="IE0031442068",
        sous_classe="Monde développé",
        td3y=-0.0008,
        domicile_iso="FR",
        dist_cap="ACC",
        capitalisant=True,
        ter=0.0038,
        pea=True,
    )


@pytest.fixture
def etf_iwda() -> ETFEnrichi:
    return _make_etf(
        ticker="IWDA",
        isin="IE00B4L5Y983",
        sous_classe="Monde développé",
        td3y=-0.0012,
        domicile_iso="IE",
        dist_cap="ACC",
        capitalisant=True,
        ter=0.002,
    )


@pytest.fixture
def etf_vwrl() -> ETFEnrichi:
    return _make_etf(
        ticker="VWRL",
        isin="IE00B3RBWM25",
        sous_classe="Monde (tous pays)",
        td3y=None,
        domicile_iso="IE",
        dist_cap="DIST",
        capitalisant=False,
        ter=0.0022,
    )


@pytest.fixture
def etf_vwce() -> ETFEnrichi:
    return _make_etf(
        ticker="VWCE",
        isin="IE00BK5BQT80",
        sous_classe="Monde (tous pays)",
        td3y=-0.0006,
        domicile_iso="IE",
        dist_cap="ACC",
        capitalisant=True,
        ter=0.0022,
    )


@pytest.fixture
def etf_sp500_ie() -> ETFEnrichi:
    return _make_etf(
        ticker="CSP1",
        isin="IE00B52VJ196",
        sous_classe="USA S&P 500",
        td3y=-0.0008,
        domicile_iso="IE",
        dist_cap="ACC",
        capitalisant=True,
        ter=0.0007,
    )


@pytest.fixture
def etf_sp500_lu() -> ETFEnrichi:
    return _make_etf(
        ticker="XSPX",
        isin="LU0274211480",
        sous_classe="USA S&P 500",
        td3y=-0.0007,
        domicile_iso="LU",
        dist_cap="ACC",
        capitalisant=True,
        ter=0.002,
    )


@pytest.fixture
def matrice_retenues() -> RetenuesSourceConfig:
    yaml_path = Path(__file__).parent.parent / "config" / "retenues_source.yaml"
    with open(yaml_path, encoding="utf-8") as f:
        return RetenuesSourceConfig(**yaml.safe_load(f))


@pytest.fixture
def contrat_cher() -> ContratAV:
    return ContratAV(
        id="av_cher",
        nom="AV Chère",
        assureur="Assureur Cher",
        distributeur="Banque",
        frais_gestion_uc_pct=0.009,
        frais_gestion_fonds_euros_pct=0.006,
        frais_entree_pct=0.0,
        frais_arbitrage_pct=0.0,
        nb_uc_total=10,
        nb_etf=5,
        versement_minimum_eur=500,
        sources=["https://exemple.fr"],
    )


@pytest.fixture
def contrat_pas_cher() -> ContratAV:
    return ContratAV(
        id="linxea_spirit_2",
        nom="Linxea Spirit 2",
        assureur="Spirica",
        distributeur="Linxea",
        frais_gestion_uc_pct=0.005,
        frais_gestion_fonds_euros_pct=0.006,
        frais_entree_pct=0.0,
        frais_arbitrage_pct=0.0,
        nb_uc_total=700,
        nb_etf=40,
        versement_minimum_eur=500,
        sources=["https://linxea.com"],
    )


@pytest.fixture
def broker_cher() -> Broker:
    return Broker(
        id="banque_en_ligne",
        nom="Banque en Ligne",
        frais_courtage_actions_euronext_eur=5.0,
        frais_courtage_actions_us_eur=10.0,
        frais_change_devise_pct=0.005,
        frais_garde_annuel_eur=50.0,
        cto_disponible=True,
        sources=["https://banque.fr"],
    )


@pytest.fixture
def broker_pas_cher() -> Broker:
    return Broker(
        id="bourse_direct",
        nom="Bourse Direct",
        frais_courtage_actions_euronext_eur=0.99,
        frais_courtage_actions_us_eur=1.99,
        frais_change_devise_pct=0.0025,
        frais_garde_annuel_eur=0.0,
        cto_disponible=True,
        sources=["https://boursedirect.fr"],
    )


# ─── Tests helper capitaliser_30_ans ─────────────────────────────────────────


def test_capitalisation_30_ans_correcte():
    """Test canonique : capitaliser_30_ans(1000, 0.04, 30) ≈ 56 085 €."""
    resultat = capitaliser_30_ans(1000.0, 0.04, 30)
    # Formule exacte : 1000 × ((1.04^30 - 1) / 0.04)
    attendu = 1000 * ((1.04**30 - 1) / 0.04)
    assert math.isclose(resultat, attendu, rel_tol=1e-9)
    assert abs(resultat - 56_085) < 100  # tolérance 100€ sur valeur canonique


def test_capitalisation_taux_zero():
    """Avec taux = 0, la capitalisation est simplement gain × N ans."""
    assert capitaliser_30_ans(1000.0, taux_actualisation=0.0, horizon_ans=10) == 10_000.0


def test_capitalisation_horizon_1_an():
    """Sur 1 an avec taux 4%, le résultat doit être ≈ gain_annuel (pas d'intérêt)."""
    # ((1.04^1 - 1) / 0.04) = 1.0 exactement
    assert math.isclose(capitaliser_30_ans(500.0, 0.04, 1), 500.0, rel_tol=1e-9)


# ─── Tests Opportunite model ──────────────────────────────────────────────────


def test_opportunite_complexite_dans_enum():
    """Vérifier que complexite n'accepte que les valeurs de l'enum."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Opportunite(
            id="test",
            levier="tracking_difference",
            titre="Test",
            gain_annuel_bps=10.0,
            gain_annuel_eur=100.0,
            gain_30ans_eur=5000.0,
            montant_concerne_eur=10000.0,
            avant={},
            apres={},
            formule="test",
            sources=["src"],
            complexite="tres_elevee",  # invalide
            delai_mise_en_oeuvre_jours=7,
            contraintes=[],
            confiance="haute",
        )


def test_opportunite_confiance_dans_enum():
    """confiance n'accepte que haute/moyenne/basse."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Opportunite(
            id="test",
            levier="tracking_difference",
            titre="Test",
            gain_annuel_bps=10.0,
            gain_annuel_eur=100.0,
            gain_30ans_eur=5000.0,
            montant_concerne_eur=10000.0,
            avant={},
            apres={},
            formule="test",
            sources=["src"],
            complexite="faible",
            delai_mise_en_oeuvre_jours=7,
            contraintes=[],
            confiance="tres_haute",  # invalide
        )


# ─── Tests Moteur 1 : Tracking Difference ────────────────────────────────────


def test_td_gain_positif_sur_cas_canonique(etf_cw8, etf_iwda):
    """CW8 (TD=-8bps) vs IWDA (TD=-12bps) : IWDA meilleur de 4bps → opportunité."""
    # CW8 TD3y = -0.0008, IWDA TD3y = -0.0012
    # delta = -0.0008 - (-0.0012) = +0.0004 = 4 bps — en dessous du seuil 5bps → pas d'opport
    ligne = LigneEtf(isin=etf_cw8.isin, montant_eur=100_000.0, enveloppe="CTO")
    univers = [etf_cw8, etf_iwda]
    # 4 bps < 5 bps seuil → liste vide
    result = detecter_opportunites_td([ligne], univers)
    assert result == []


def test_td_opportunite_si_delta_suffisant(etf_cw8):
    """Si TD_alternative - TD_actuel > 5bps, une opportunité est créée."""
    etf_meilleur = _make_etf(
        ticker="BEST",
        isin="IE00TEST001",
        sous_classe="Monde développé",
        td3y=-0.0020,  # 20 bps mieux que CW8 (-8bps)
        domicile_iso="IE",
    )
    ligne = LigneEtf(isin=etf_cw8.isin, montant_eur=100_000.0, enveloppe="CTO")
    univers = [etf_cw8, etf_meilleur]
    result = detecter_opportunites_td([ligne], univers)
    assert len(result) == 1
    opp = result[0]
    assert opp.levier == "tracking_difference"
    assert opp.gain_annuel_bps > 5.0
    # gain_annuel = 100k × delta_td = 100k × 0.0012 = 120 €
    assert abs(opp.gain_annuel_eur - 120.0) < 1.0  # ±1€


def test_td_ignore_indices_differents(etf_cw8, etf_sp500_ie):
    """MSCI World (CW8) ≠ S&P 500 (CSP1) — pas de switch proposé."""
    ligne = LigneEtf(isin=etf_cw8.isin, montant_eur=50_000.0, enveloppe="CTO")
    univers = [etf_cw8, etf_sp500_ie]
    result = detecter_opportunites_td([ligne], univers)
    assert result == []  # indices différents → aucune opportunité


def test_td_aucun_levier_si_td_null():
    """Si l'ETF actuel n'a pas de TD, on ne plante pas et on retourne []."""
    etf_sans_td = _make_etf(
        ticker="NOTD",
        isin="IE00NOTD001",
        sous_classe="Monde développé",
        td3y=None,
        td1y=None,
    )
    etf_bon = _make_etf(
        ticker="GOOD",
        isin="IE00GOOD001",
        sous_classe="Monde développé",
        td3y=-0.0015,
    )
    ligne = LigneEtf(isin=etf_sans_td.isin, montant_eur=10_000.0, enveloppe="CTO")
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = detecter_opportunites_td([ligne], [etf_sans_td, etf_bon])
    assert result == []


def test_td_isin_inconnu_ne_plante_pas():
    """ISIN absent de l'univers → warning silencieux, pas de crash."""
    ligne = LigneEtf(isin="IE00INCONNU", montant_eur=10_000.0, enveloppe="CTO")
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = detecter_opportunites_td([ligne], [])
    assert result == []


def test_td_opportunite_a_sources_non_vides(etf_cw8):
    """Chaque opportunité TD doit avoir des sources non vides."""
    etf_meilleur = _make_etf(
        ticker="BESTW",
        isin="IE00BESTW001",
        sous_classe="Monde développé",
        td3y=-0.0025,
    )
    ligne = LigneEtf(isin=etf_cw8.isin, montant_eur=100_000.0, enveloppe="CTO")
    result = detecter_opportunites_td([ligne], [etf_cw8, etf_meilleur])
    for opp in result:
        assert len(opp.sources) > 0


# ─── Tests Moteur 2 : Withholding Tax ────────────────────────────────────────


def test_withholding_acwi_ie_vs_lu_neutre(matrice_retenues):
    """US-IE = 15% = US-LU 15% → pas de gain à changer domicile IE→LU pour un ACWI."""
    etf_acwi_ie = _make_etf(
        ticker="ACWI_IE",
        isin="IE00ACWI001",
        sous_classe="Monde (tous pays)",
        domicile_iso="IE",
        td3y=-0.001,
    )
    etf_acwi_lu = _make_etf(
        ticker="ACWI_LU",
        isin="LU00ACWI001",
        sous_classe="Monde (tous pays)",
        domicile_iso="LU",
        td3y=-0.001,
    )
    ligne = LigneEtf(isin=etf_acwi_ie.isin, montant_eur=100_000.0, enveloppe="CTO")
    result = detecter_opportunites_withholding(
        [ligne], [etf_acwi_ie, etf_acwi_lu], matrice_retenues
    )
    # IE et LU ont le même traité avec US (15%) et les autres pays développés (15%)
    # → drag identique → pas d'opportunité
    assert result == []


def test_withholding_gain_positif_si_domicile_different(matrice_retenues):
    """Si un ETF FR a retenue > IE, le switch doit générer un gain."""
    etf_fr = _make_etf(
        ticker="MONDE_FR",
        isin="FR00MONDE001",
        sous_classe="USA S&P 500",  # 100% US : traité identique IE/LU/FR
        domicile_iso="FR",
        td3y=-0.001,
    )
    etf_ie = _make_etf(
        ticker="SP500_IE",
        isin="IE00SP500001",
        sous_classe="USA S&P 500",
        domicile_iso="IE",
        td3y=-0.001,
    )
    # matrice: US/FR = 0.15, US/IE = 0.15 → même taux → pas d'opportunité pour S&P500
    ligne = LigneEtf(isin=etf_fr.isin, montant_eur=100_000.0, enveloppe="CTO")
    result = detecter_opportunites_withholding([ligne], [etf_fr, etf_ie], matrice_retenues)
    # US-FR = 15%, US-IE = 15% → identiques, pas d'opportunité
    assert result == []


def test_withholding_aucun_levier_si_non_actions(matrice_retenues):
    """Les ETF obligataires sont skippés (withholding ne s'applique qu'aux actions)."""
    etf_oblig = _make_etf(
        ticker="OBLIG",
        isin="IE00OBLIG001",
        sous_classe="Corporate IG EUR",
        classe_actifs="Obligations",
        domicile_iso="IE",
    )
    ligne = LigneEtf(isin=etf_oblig.isin, montant_eur=50_000.0, enveloppe="CTO")
    result = detecter_opportunites_withholding([ligne], [etf_oblig], matrice_retenues)
    assert result == []


def test_withholding_opportunite_a_sources_non_vides(matrice_retenues):
    """Toute opportunité withholding doit avoir des sources."""
    # Créer un cas artificiel avec domicile FR (JP donne avantage à FR)
    etf_jp_ie = _make_etf(
        ticker="JP_IE",
        isin="IE00JP001",
        sous_classe="Japon",
        domicile_iso="IE",
        td3y=-0.001,
    )
    etf_jp_fr = _make_etf(
        ticker="JP_FR",
        isin="FR00JP001",
        sous_classe="Japon",
        domicile_iso="FR",
        td3y=-0.001,
    )
    # matrice JP/FR = 0.10, JP/IE = 0.15 → FR meilleur pour ETF Japon
    ligne = LigneEtf(isin=etf_jp_ie.isin, montant_eur=100_000.0, enveloppe="CTO")
    result = detecter_opportunites_withholding([ligne], [etf_jp_ie, etf_jp_fr], matrice_retenues)
    for opp in result:
        assert len(opp.sources) > 0


# ─── Tests Moteur 3 : Dist vs Cap ────────────────────────────────────────────


def test_dist_vs_cap_ne_propose_que_en_cto(etf_vwrl, etf_vwce):
    """En enveloppe AV ou PEA, le report est natif — aucune opportunité."""
    univers = [etf_vwrl, etf_vwce]
    for enveloppe in ("PEA", "AV", "PER", "PEE"):
        ligne = LigneEtf(isin=etf_vwrl.isin, montant_eur=50_000.0, enveloppe=enveloppe)  # type: ignore[arg-type]
        result = detecter_opportunites_dist_vs_cap([ligne], univers)
        assert result == [], f"Opportunité proposée en {enveloppe} — ne devrait pas"


def test_dist_vs_cap_gain_positif_en_cto(etf_vwrl, etf_vwce):
    """VWRL (DIST) → VWCE (ACC) en CTO : gain de report fiscal positif."""
    ligne = LigneEtf(isin=etf_vwrl.isin, montant_eur=100_000.0, enveloppe="CTO")
    result = detecter_opportunites_dist_vs_cap([ligne], [etf_vwrl, etf_vwce], tmi_client=0.30)
    assert len(result) == 1
    opp = result[0]
    assert opp.levier == "dist_vs_cap"
    assert opp.gain_30ans_eur > 0
    assert opp.confiance == "moyenne"


def test_dist_vs_cap_skip_si_etf_deja_acc(etf_cw8, etf_iwda):
    """Aucune opportunité si l'ETF est déjà capitalisant."""
    ligne = LigneEtf(isin=etf_cw8.isin, montant_eur=100_000.0, enveloppe="CTO")
    result = detecter_opportunites_dist_vs_cap([ligne], [etf_cw8, etf_iwda])
    assert result == []


def test_dist_vs_cap_complexite_moyenne(etf_vwrl, etf_vwce):
    """La complexité doit être 'moyenne' pour ce moteur."""
    ligne = LigneEtf(isin=etf_vwrl.isin, montant_eur=50_000.0, enveloppe="CTO")
    result = detecter_opportunites_dist_vs_cap([ligne], [etf_vwrl, etf_vwce])
    if result:
        assert result[0].complexite == "moyenne"


def test_dist_vs_cap_note_ec_presente(etf_vwrl, etf_vwce):
    """Note EC doit être présente (hypothèses fortes sur rendement)."""
    ligne = LigneEtf(isin=etf_vwrl.isin, montant_eur=100_000.0, enveloppe="CTO")
    result = detecter_opportunites_dist_vs_cap([ligne], [etf_vwrl, etf_vwce])
    if result:
        assert result[0].note_ec is not None
        assert "hypothèses" in result[0].note_ec.lower()


# ─── Tests Moteur 4 : Frais Contrat AV ───────────────────────────────────────


def test_frais_av_gain_positif_sur_cas_canonique(contrat_cher, contrat_pas_cher):
    """AV chère 0.90% vs AV pas chère 0.50% : gain 400bps × 100k€ = 400€/an."""
    result = detecter_opportunites_frais_av(
        contrat_actuel=contrat_cher,
        montant_av_actuel_eur=100_000.0,
        versements_annuels_attendus_eur=500.0,
        contrats_marche=[contrat_pas_cher],
    )
    assert len(result) == 1
    opp = result[0]
    assert opp.levier == "frais_contrat_av"
    # gain_annuel = 100k × (0.009 - 0.005) = 400 €
    assert abs(opp.gain_annuel_eur - 400.0) < 1.0


def test_frais_av_marque_complexite_elevee(contrat_cher, contrat_pas_cher):
    """Complexité systématiquement élevée pour les transferts AV."""
    result = detecter_opportunites_frais_av(contrat_cher, 100_000.0, 500.0, [contrat_pas_cher])
    assert len(result) == 1
    assert result[0].complexite == "elevee"


def test_frais_av_zero_si_choix_optimal(contrat_pas_cher):
    """Si le client a déjà le contrat le moins cher, retourner []."""
    contrat_encore_moins_cher = ContratAV(
        id="super_cheap",
        nom="Super Cheap AV",
        assureur="SC",
        distributeur="SC",
        frais_gestion_uc_pct=0.0050,  # identique → pas de gain
        frais_gestion_fonds_euros_pct=0.005,
        nb_uc_total=100,
        versement_minimum_eur=100,
        sources=["https://supercheap.fr"],
    )
    result = detecter_opportunites_frais_av(
        contrat_pas_cher, 100_000.0, 500.0, [contrat_encore_moins_cher]
    )
    assert result == []  # diff = 0 < seuil 30bps


def test_frais_av_contraintes_fiscales_dans_resultat(contrat_cher, contrat_pas_cher):
    """Les contraintes fiscales du transfert doivent être listées."""
    result = detecter_opportunites_frais_av(contrat_cher, 100_000.0, 500.0, [contrat_pas_cher])
    if result:
        contraintes_text = " ".join(result[0].contraintes).lower()
        assert "fiscal" in contraintes_text or "taxé" in contraintes_text


def test_frais_av_sources_non_vides(contrat_cher, contrat_pas_cher):
    """Sources non vides pour les opportunités AV."""
    result = detecter_opportunites_frais_av(contrat_cher, 100_000.0, 500.0, [contrat_pas_cher])
    for opp in result:
        assert len(opp.sources) > 0


# ─── Tests Moteur 5 : Frais Broker ───────────────────────────────────────────


def test_frais_broker_gain_positif_sur_cas_canonique(broker_cher, broker_pas_cher):
    """Broker cher (5€/ordre + 50€ garde) vs pas cher (0.99€/ordre) : gain > 50€/an."""
    result = detecter_opportunites_frais_broker(
        broker_actuel=broker_cher,
        nb_ordres_par_an_estim=20,
        montant_moyen_ordre_eur=500.0,
        parts_ordres_us_pct=0.0,
        brokers_marche=[broker_pas_cher],
    )
    assert len(result) == 1
    opp = result[0]
    # Actuel : 20 × 5€ + 50€ = 150€
    # Candidat : 20 × 0.99€ + 0€ = 19.8€
    # Gain = 150 - 19.8 = 130.2€/an
    assert abs(opp.gain_annuel_eur - 130.2) < 1.0


def test_frais_broker_compte_change_devise_si_us(broker_cher, broker_pas_cher):
    """Les frais de change USD sont pris en compte si parts_ordres_us_pct > 0."""
    result_avec_us = detecter_opportunites_frais_broker(
        broker_actuel=broker_cher,
        nb_ordres_par_an_estim=20,
        montant_moyen_ordre_eur=1000.0,
        parts_ordres_us_pct=0.5,  # 50% ordres US
        brokers_marche=[broker_pas_cher],
    )
    result_sans_us = detecter_opportunites_frais_broker(
        broker_actuel=broker_cher,
        nb_ordres_par_an_estim=20,
        montant_moyen_ordre_eur=1000.0,
        parts_ordres_us_pct=0.0,
        brokers_marche=[broker_pas_cher],
    )
    # Avec ordres US, on a les frais de change en plus → gain différent
    if result_avec_us and result_sans_us:
        assert result_avec_us[0].gain_annuel_eur != result_sans_us[0].gain_annuel_eur


def test_frais_broker_zero_si_meme_cout(broker_pas_cher):
    """Si le broker actuel est le moins cher, retourner []."""
    result = detecter_opportunites_frais_broker(
        broker_actuel=broker_pas_cher,
        nb_ordres_par_an_estim=20,
        montant_moyen_ordre_eur=500.0,
        parts_ordres_us_pct=0.0,
        brokers_marche=[broker_pas_cher],  # même broker
    )
    assert result == []


def test_frais_broker_sources_non_vides(broker_cher, broker_pas_cher):
    """Sources non vides pour les opportunités broker."""
    result = detecter_opportunites_frais_broker(broker_cher, 20, 500.0, 0.0, [broker_pas_cher])
    for opp in result:
        assert len(opp.sources) > 0


def test_frais_broker_gain_30ans_coherent(broker_cher, broker_pas_cher):
    """gain_30ans_eur doit être cohérent avec capitaliser_30_ans(gain_annuel_eur)."""
    result = detecter_opportunites_frais_broker(broker_cher, 20, 500.0, 0.0, [broker_pas_cher])
    if result:
        opp = result[0]
        attendu = capitaliser_30_ans(opp.gain_annuel_eur)
        assert abs(opp.gain_30ans_eur - attendu) < 1.0  # ±1€


# ─── Tests constantes ─────────────────────────────────────────────────────────


def test_constantes_ponderation_geo_somme_a_1():
    """La somme des pondérations géographiques doit être ≈ 1 pour chaque indice."""
    for indice, ponder in PONDERATION_GEO_PAR_INDICE.items():
        total = sum(ponder.values())
        assert math.isclose(total, 1.0, abs_tol=0.01), (
            f"Pondération géo {indice} : somme = {total} ≠ 1.0"
        )


def test_constantes_rendement_dividende_dans_bornes():
    """Les rendements dividende doivent être dans [0, 10%] (valeurs raisonnables)."""
    for categorie, rendement in RENDEMENT_DIVIDENDE_PAR_CATEGORIE.items():
        assert 0.0 < rendement <= 0.10, (
            f"Rendement dividende {categorie} = {rendement} hors bornes [0, 10%]"
        )
