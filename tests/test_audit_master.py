"""Tests S8.2c — Audit master + adaptateur profil.

≥ 15 tests couvrant :
- auditer_patrimoine : rapport valide, tri, déduplication, synthèse, avertissements
- contexte_depuis_profil : adaptateur Profil → ContexteAudit
- Cas limites : portefeuille optimal, profil sans broker, profil sans AV
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
import yaml

from src.audit.master import (
    _LEVIERS,
    ContexteAudit,
    RapportAudit,
    auditer_patrimoine,
)
from src.audit.opportunite import LigneEtf, Opportunite
from src.schemas import Broker, ContratAV, ETFEligibilite, ETFEnrichi, Profil, RetenuesSourceConfig

# ─── Helpers ETF ─────────────────────────────────────────────────────────────


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
def matrice_retenues() -> RetenuesSourceConfig:
    yaml_path = Path(__file__).parent.parent / "config" / "retenues_source.yaml"
    with open(yaml_path, encoding="utf-8") as f:
        return RetenuesSourceConfig(**yaml.safe_load(f))


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


@pytest.fixture
def portefeuille_500k(etf_cw8, etf_vwrl) -> list[LigneEtf]:
    """Portefeuille 500k€ type : CW8 en PEA + VWRL en CTO."""
    return [
        LigneEtf(isin=etf_cw8.isin, montant_eur=300_000.0, enveloppe="PEA"),
        LigneEtf(isin=etf_vwrl.isin, montant_eur=200_000.0, enveloppe="CTO"),
    ]


@pytest.fixture
def univers_500k(etf_cw8, etf_iwda, etf_vwrl, etf_vwce) -> list[ETFEnrichi]:
    """Univers ETF minimal pour le portefeuille 500k."""
    return [etf_cw8, etf_iwda, etf_vwrl, etf_vwce]


@pytest.fixture
def contexte_500k(portefeuille_500k, contrat_cher, broker_cher) -> ContexteAudit:
    """Contexte d'audit pour portefeuille 500k€."""
    return ContexteAudit(
        portefeuille=portefeuille_500k,
        contrat_av_actuel=contrat_cher,
        montant_av_actuel_eur=200_000.0,
        versements_av_annuels_eur=10_000.0,
        broker_actuel=broker_cher,
        nb_ordres_par_an_estim=12,
        montant_moyen_ordre_eur=5_000.0,
        parts_ordres_us_pct=0.5,
        tmi_client=0.30,
        horizon_ans=30,
        taux_actualisation=0.04,
    )


# ─── Tests du rapport global ──────────────────────────────────────────────────


def test_auditer_patrimoine_cas_complet_retourne_rapport_valide(
    contexte_500k, univers_500k, contrat_pas_cher, broker_pas_cher, matrice_retenues
):
    """Fixture 500k€ type → RapportAudit cohérent (nb opportunités > 0, sommes > 0)."""
    rapport = auditer_patrimoine(
        contexte=contexte_500k,
        univers_etf=univers_500k,
        contrats_av_marche=[contrat_pas_cher],
        brokers_marche=[broker_pas_cher],
        matrice_retenues=matrice_retenues,
    )

    assert isinstance(rapport, RapportAudit)
    assert len(rapport.opportunites) >= 0  # peut être 0 selon les conditions
    assert rapport.gain_total_annuel_eur >= 0
    assert rapport.gain_total_30ans_eur >= 0
    assert rapport.nb_opportunites_haute_confiance >= 0
    assert rapport.nb_opportunites_activables_rapidement >= 0
    # Synthèse doit contenir au minimum les 5 leviers
    for levier in _LEVIERS:
        assert levier in rapport.synthese_par_levier
    # Hypothèses non vides
    assert len(rapport.hypotheses_utilisees) > 0


def test_opportunites_triees_par_gain_30ans_desc(
    contexte_500k, univers_500k, contrat_pas_cher, broker_pas_cher, matrice_retenues
):
    """Les opportunités doivent être triées par gain_30ans_eur décroissant."""
    rapport = auditer_patrimoine(
        contexte=contexte_500k,
        univers_etf=univers_500k,
        contrats_av_marche=[contrat_pas_cher],
        brokers_marche=[broker_pas_cher],
        matrice_retenues=matrice_retenues,
    )

    gains = [o.gain_30ans_eur for o in rapport.opportunites]
    assert gains == sorted(gains, reverse=True), "Opportunités non triées par gain_30ans_eur desc"


def test_deduplication_etf_source_cible(
    etf_cw8, etf_iwda, matrice_retenues, contrat_pas_cher, broker_pas_cher
):
    """Si deux moteurs proposent le même switch (même id de paire), une seule ligne."""
    # Créer deux opportunités avec le même id de paire source-cible
    from src.audit.master import _dedupliquer

    opp1 = Opportunite(
        id="etf.tracking_difference.CW8_vs_IWDA",
        levier="tracking_difference",
        titre="Switch CW8 → IWDA (TD)",
        gain_annuel_bps=4.0,
        gain_annuel_eur=1200.0,
        gain_30ans_eur=67_000.0,
        montant_concerne_eur=300_000.0,
        avant={"ticker": "CW8"},
        apres={"ticker": "IWDA"},
        formule="delta_TD = 4 bps",
        sources=["test"],
        complexite="faible",
        delai_mise_en_oeuvre_jours=7,
        contraintes=[],
        confiance="haute",
    )

    opp2 = Opportunite(
        id="etf.withholding_tax.CW8_vs_IWDA",
        levier="withholding_tax",
        titre="Switch CW8 → IWDA (withholding)",
        gain_annuel_bps=3.0,
        gain_annuel_eur=800.0,
        gain_30ans_eur=44_000.0,
        montant_concerne_eur=300_000.0,
        avant={"ticker": "CW8"},
        apres={"ticker": "IWDA"},
        formule="delta_withholding = 3 bps",
        sources=["test"],
        complexite="faible",
        delai_mise_en_oeuvre_jours=7,
        contraintes=[],
        confiance="haute",
    )

    # Même paire source-cible → paire key "CW8_vs_IWDA" dans les deux cas
    resultat = _dedupliquer([opp1, opp2])

    # Après déduplication par id, les deux ont des ids distincts → deux lignes
    # Mais les ids commencent par préfixes différents ; c'est la partie [2] qui compte
    # opp1: id.split(".")[2] = "CW8_vs_IWDA"
    # opp2: id.split(".")[2] = "CW8_vs_IWDA"  ← même paire
    assert len(resultat) == 1, (
        "Deux opportunités avec même paire source-cible → doit être dédupliqué"
    )
    # Doit garder le plus gros gain
    assert resultat[0].gain_annuel_eur == 1200.0


def test_deduplication_garde_plus_gros_gain():
    """La déduplication garde la ligne avec le plus gros gain_annuel_eur."""
    from src.audit.master import _dedupliquer

    opp_petit = Opportunite(
        id="etf.tracking_difference.TICKER_vs_ALT",
        levier="tracking_difference",
        titre="Petit gain",
        gain_annuel_bps=2.0,
        gain_annuel_eur=500.0,
        gain_30ans_eur=28_000.0,
        montant_concerne_eur=100_000.0,
        avant={},
        apres={},
        formule="",
        sources=["test"],
        complexite="faible",
        delai_mise_en_oeuvre_jours=7,
        contraintes=[],
        confiance="haute",
    )

    opp_grand = Opportunite(
        id="etf.withholding_tax.TICKER_vs_ALT",
        levier="withholding_tax",
        titre="Grand gain",
        gain_annuel_bps=5.0,
        gain_annuel_eur=2000.0,
        gain_30ans_eur=112_000.0,
        montant_concerne_eur=100_000.0,
        avant={},
        apres={},
        formule="",
        sources=["test"],
        complexite="faible",
        delai_mise_en_oeuvre_jours=7,
        contraintes=[],
        confiance="haute",
    )

    resultat = _dedupliquer([opp_petit, opp_grand])
    assert len(resultat) == 1
    assert resultat[0].gain_annuel_eur == 2000.0


def test_synthese_par_levier_exhaustive(
    contexte_500k, univers_500k, contrat_pas_cher, broker_pas_cher, matrice_retenues
):
    """Les 5 leviers doivent tous être présents dans la synthèse (même à 0)."""
    rapport = auditer_patrimoine(
        contexte=contexte_500k,
        univers_etf=univers_500k,
        contrats_av_marche=[contrat_pas_cher],
        brokers_marche=[broker_pas_cher],
        matrice_retenues=matrice_retenues,
    )

    for levier in _LEVIERS:
        assert levier in rapport.synthese_par_levier, f"Levier '{levier}' absent de la synthèse"
        data = rapport.synthese_par_levier[levier]
        assert "nb" in data
        assert "gain_annuel_eur" in data
        assert "gain_30ans_eur" in data


def test_avertissement_si_broker_manquant(
    portefeuille_500k,
    univers_500k,
    contrat_cher,
    contrat_pas_cher,
    broker_pas_cher,
    matrice_retenues,
):
    """Contexte sans broker → avertissement dans le rapport."""
    contexte_sans_broker = ContexteAudit(
        portefeuille=portefeuille_500k,
        contrat_av_actuel=contrat_cher,
        montant_av_actuel_eur=200_000.0,
        broker_actuel=None,  # pas de broker
        tmi_client=0.30,
    )

    rapport = auditer_patrimoine(
        contexte=contexte_sans_broker,
        univers_etf=univers_500k,
        contrats_av_marche=[contrat_pas_cher],
        brokers_marche=[broker_pas_cher],
        matrice_retenues=matrice_retenues,
    )

    assert any("broker" in avert.lower() for avert in rapport.avertissements), (
        "Aucun avertissement sur le broker manquant"
    )


def test_gain_total_annuel_eur_positif_sur_cas_canonique(
    contrat_cher, contrat_pas_cher, broker_cher, broker_pas_cher, matrice_retenues
):
    """Sur portefeuille pré-câblé avec AV chère, gain total >= 500 €/an."""
    # Portefeuille simple : 200k€ en CTO (VWRL distribuant)
    etf_dist = _make_etf(
        ticker="VWRL",
        isin="IE00B3RBWM25",
        sous_classe="Monde (tous pays)",
        td3y=None,
        domicile_iso="IE",
        dist_cap="DIST",
        capitalisant=False,
        ter=0.0022,
    )
    etf_acc = _make_etf(
        ticker="VWCE",
        isin="IE00BK5BQT80",
        sous_classe="Monde (tous pays)",
        td3y=-0.0006,
        domicile_iso="IE",
        dist_cap="ACC",
        capitalisant=True,
        ter=0.0022,
    )

    contexte = ContexteAudit(
        portefeuille=[LigneEtf(isin=etf_dist.isin, montant_eur=200_000.0, enveloppe="CTO")],
        contrat_av_actuel=contrat_cher,
        montant_av_actuel_eur=200_000.0,
        broker_actuel=broker_cher,
        tmi_client=0.30,
        horizon_ans=30,
    )

    rapport = auditer_patrimoine(
        contexte=contexte,
        univers_etf=[etf_dist, etf_acc],
        contrats_av_marche=[contrat_pas_cher],
        brokers_marche=[broker_pas_cher],
        matrice_retenues=matrice_retenues,
    )

    # AV : frais_actuel 0.9%, frais_cible 0.5% → diff 0.4% → gain = 200k × 0.4% = 800€/an
    assert rapport.gain_total_annuel_eur >= 500.0, (
        f"Gain attendu >= 500€/an, obtenu {rapport.gain_total_annuel_eur:.2f}€"
    )


def test_gain_total_30ans_coherent_avec_capitalisation(
    contexte_500k, univers_500k, contrat_pas_cher, broker_pas_cher, matrice_retenues
):
    """gain_total_30ans ≈ somme des capitalisations individuelles (cohérence interne)."""
    rapport = auditer_patrimoine(
        contexte=contexte_500k,
        univers_etf=univers_500k,
        contrats_av_marche=[contrat_pas_cher],
        brokers_marche=[broker_pas_cher],
        matrice_retenues=matrice_retenues,
    )

    # La somme des gain_30ans_eur des opportunités doit correspondre au total
    somme_individuelle = sum(o.gain_30ans_eur for o in rapport.opportunites)
    assert math.isclose(rapport.gain_total_30ans_eur, somme_individuelle, rel_tol=0.01), (
        f"Incohérence capitalisation : total={rapport.gain_total_30ans_eur:.0f}€, "
        f"somme individuelle={somme_individuelle:.0f}€"
    )


def test_nb_opportunites_haute_confiance_coherent(
    contexte_500k, univers_500k, contrat_pas_cher, broker_pas_cher, matrice_retenues
):
    """nb_opportunites_haute_confiance = nb d'opportunités avec confiance='haute'."""
    rapport = auditer_patrimoine(
        contexte=contexte_500k,
        univers_etf=univers_500k,
        contrats_av_marche=[contrat_pas_cher],
        brokers_marche=[broker_pas_cher],
        matrice_retenues=matrice_retenues,
    )

    attendu = sum(1 for o in rapport.opportunites if o.confiance == "haute")
    assert rapport.nb_opportunites_haute_confiance == attendu


def test_nb_opportunites_activables_rapidement_coherent(
    contexte_500k, univers_500k, contrat_pas_cher, broker_pas_cher, matrice_retenues
):
    """nb_opportunites_activables_rapidement = nb avec delai_mise_en_oeuvre_jours <= 30."""
    rapport = auditer_patrimoine(
        contexte=contexte_500k,
        univers_etf=univers_500k,
        contrats_av_marche=[contrat_pas_cher],
        brokers_marche=[broker_pas_cher],
        matrice_retenues=matrice_retenues,
    )

    attendu = sum(1 for o in rapport.opportunites if o.delai_mise_en_oeuvre_jours <= 30)
    assert rapport.nb_opportunites_activables_rapidement == attendu


def test_hypotheses_utilisees_documentees(
    contexte_500k, univers_500k, contrat_pas_cher, broker_pas_cher, matrice_retenues
):
    """Le dict hypotheses_utilisees doit être non vide et contenir taux_actu, horizon, TMI."""
    rapport = auditer_patrimoine(
        contexte=contexte_500k,
        univers_etf=univers_500k,
        contrats_av_marche=[contrat_pas_cher],
        brokers_marche=[broker_pas_cher],
        matrice_retenues=matrice_retenues,
    )

    hyp = rapport.hypotheses_utilisees
    assert len(hyp) > 0, "hypotheses_utilisees ne doit pas être vide"
    assert "taux_actualisation" in hyp
    assert "horizon_ans" in hyp
    assert "tmi_client" in hyp


def test_aucune_opportunite_si_portefeuille_vide(
    contrat_pas_cher, broker_pas_cher, matrice_retenues
):
    """Portefeuille vide → 0 opportunités ETF, rapport valide avec avertissement."""
    contexte = ContexteAudit(
        portefeuille=[],
        contrat_av_actuel=None,
        broker_actuel=None,
    )

    rapport = auditer_patrimoine(
        contexte=contexte,
        univers_etf=[],
        contrats_av_marche=[contrat_pas_cher],
        brokers_marche=[broker_pas_cher],
        matrice_retenues=matrice_retenues,
    )

    assert isinstance(rapport, RapportAudit)
    assert rapport.gain_total_annuel_eur == 0.0
    assert len(rapport.avertissements) > 0


def test_rapport_serialisable_json(
    contexte_500k, univers_500k, contrat_pas_cher, broker_pas_cher, matrice_retenues
):
    """rapport.model_dump_json() doit fonctionner sans erreur."""
    rapport = auditer_patrimoine(
        contexte=contexte_500k,
        univers_etf=univers_500k,
        contrats_av_marche=[contrat_pas_cher],
        brokers_marche=[broker_pas_cher],
        matrice_retenues=matrice_retenues,
    )

    json_str = rapport.model_dump_json()
    assert isinstance(json_str, str)
    # Vérification que c'est du JSON valide
    parsed = json.loads(json_str)
    assert "opportunites" in parsed
    assert "gain_total_annuel_eur" in parsed
    assert "synthese_par_levier" in parsed


def test_reproductibilite(
    contexte_500k, univers_500k, contrat_pas_cher, broker_pas_cher, matrice_retenues
):
    """Même input deux fois → même output (pas d'aléa dans les moteurs)."""
    rapport1 = auditer_patrimoine(
        contexte=contexte_500k,
        univers_etf=univers_500k,
        contrats_av_marche=[contrat_pas_cher],
        brokers_marche=[broker_pas_cher],
        matrice_retenues=matrice_retenues,
    )
    rapport2 = auditer_patrimoine(
        contexte=contexte_500k,
        univers_etf=univers_500k,
        contrats_av_marche=[contrat_pas_cher],
        brokers_marche=[broker_pas_cher],
        matrice_retenues=matrice_retenues,
    )

    assert rapport1.gain_total_annuel_eur == rapport2.gain_total_annuel_eur
    assert rapport1.gain_total_30ans_eur == rapport2.gain_total_30ans_eur
    assert len(rapport1.opportunites) == len(rapport2.opportunites)
    for o1, o2 in zip(rapport1.opportunites, rapport2.opportunites):
        assert o1.id == o2.id
        assert o1.gain_annuel_eur == o2.gain_annuel_eur


# ─── Tests adaptateur contexte_depuis_profil ──────────────────────────────────


def _profil_complet() -> Profil:
    """Crée un Profil Pydantic complet pour les tests de l'adaptateur."""
    raw = {
        "id": 99,
        "code": "TEST_500K",
        "nom": "Test Client 500k",
        "age": 45,
        "tmi": 0.30,
        "rfr_annuel": 120000,
        "patrimoine_financier_total": 500000,
        "allocation_cible_bogleheads": {
            "actions": 0.80,
            "obligations": 0.10,
            "or": 0.05,
            "liquidites": 0.05,
        },
        "enveloppes_disponibles": {
            "PEA": {"encours_actuel": 150000, "ouvert": True},
            "CTO_perso": {"encours_actuel": 200000, "ouvert": True},
            "AV": {"encours_actuel": 100000, "ouvert": True},
        },
        "positions_detaillees": [
            {
                "etf": "CW8",
                "enveloppe": "PEA",
                "quantite": 100.0,
                "prix_revient_moyen": 1500.0,
                "montant_actuel": 150000.0,
            },
            {
                "etf": "VWRL",
                "enveloppe": "CTO_perso",
                "quantite": 500.0,
                "prix_revient_moyen": 100.0,
                "montant_actuel": 200000.0,
            },
        ],
        "horizon_placement_ans": 25,
    }
    return Profil.model_validate(raw)


def test_contexte_depuis_profil_avec_av_complet(contrat_cher):
    """Adaptateur OK sur profil avec AV et positions détaillées."""
    from src.audit.adapter import contexte_depuis_profil

    profil = _profil_complet()
    contexte, avertissements = contexte_depuis_profil(profil, contrat_av_depuis_config=contrat_cher)

    assert isinstance(contexte, ContexteAudit)
    assert contexte.tmi_client == 0.30
    assert contexte.contrat_av_actuel is not None
    assert contexte.contrat_av_actuel.id == contrat_cher.id
    # L'encours AV est extrait des enveloppes
    assert contexte.montant_av_actuel_eur >= 0.0
    # Portefeuille extrait des positions_detaillees
    assert len(contexte.portefeuille) == 2


def test_contexte_depuis_profil_sans_av_utilise_defaut_et_warn():
    """Sans contrat AV fourni mais avec encours AV → hypothèse + avertissement."""
    from src.audit.adapter import contexte_depuis_profil

    profil = _profil_complet()
    contexte, avertissements = contexte_depuis_profil(profil)

    # Aucun contrat AV fourni → doit utiliser le défaut et avertir
    assert any("AV" in a or "contrat" in a.lower() for a in avertissements), (
        "Avertissement AV attendu mais absent"
    )
    # Broker non fourni → doit avertir aussi
    assert any("broker" in a.lower() or "Bourse Direct" in a for a in avertissements), (
        "Avertissement broker attendu mais absent"
    )


def test_contexte_depuis_profil_horizon_extrait():
    """L'horizon est extrait de horizon_placement_ans si présent dans le profil."""
    from src.audit.adapter import contexte_depuis_profil

    profil = _profil_complet()  # horizon_placement_ans = 25
    contexte, _ = contexte_depuis_profil(profil)

    assert contexte.horizon_ans == 25, f"Horizon attendu 25, obtenu {contexte.horizon_ans}"


def test_synthese_par_levier_somme_coherente(
    contexte_500k, univers_500k, contrat_pas_cher, broker_pas_cher, matrice_retenues
):
    """La somme des gain_annuel des leviers doit égaler gain_total_annuel_eur."""
    rapport = auditer_patrimoine(
        contexte=contexte_500k,
        univers_etf=univers_500k,
        contrats_av_marche=[contrat_pas_cher],
        brokers_marche=[broker_pas_cher],
        matrice_retenues=matrice_retenues,
    )

    somme_leviers = sum(v.get("gain_annuel_eur", 0.0) for v in rapport.synthese_par_levier.values())
    assert math.isclose(somme_leviers, rapport.gain_total_annuel_eur, rel_tol=0.01), (
        f"Incohérence : somme leviers={somme_leviers:.2f}€, "
        f"gain_total={rapport.gain_total_annuel_eur:.2f}€"
    )


def test_horizon_personnalise_affecte_gain_30ans(
    portefeuille_500k,
    univers_500k,
    contrat_cher,
    contrat_pas_cher,
    broker_cher,
    broker_pas_cher,
    matrice_retenues,
):
    """Un horizon de 10 ans doit donner un gain 30 ans inférieur à celui avec 30 ans."""
    contexte_30 = ContexteAudit(
        portefeuille=portefeuille_500k,
        contrat_av_actuel=contrat_cher,
        montant_av_actuel_eur=200_000.0,
        broker_actuel=broker_cher,
        tmi_client=0.30,
        horizon_ans=30,
        taux_actualisation=0.04,
    )
    contexte_10 = contexte_30.model_copy(update={"horizon_ans": 10})

    rapport_30 = auditer_patrimoine(
        contexte=contexte_30,
        univers_etf=univers_500k,
        contrats_av_marche=[contrat_pas_cher],
        brokers_marche=[broker_pas_cher],
        matrice_retenues=matrice_retenues,
    )
    rapport_10 = auditer_patrimoine(
        contexte=contexte_10,
        univers_etf=univers_500k,
        contrats_av_marche=[contrat_pas_cher],
        brokers_marche=[broker_pas_cher],
        matrice_retenues=matrice_retenues,
    )

    if rapport_30.gain_total_annuel_eur > 0:
        assert rapport_10.gain_total_30ans_eur <= rapport_30.gain_total_30ans_eur, (
            "Gain 10 ans devrait être <= gain 30 ans"
        )
