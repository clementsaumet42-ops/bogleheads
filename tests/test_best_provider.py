"""Tests S13 Lot C — Best Provider."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.catalogue.best_provider import (
    CoutTotalProvider,
    _cout_broker,
    _cout_contrat_av,
    _cout_teneur_per,
    _encours_moyen,
    _filtre_enveloppe_broker,
    _filtre_etf_broker,
    _ter_moyen,
    classer_providers,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _make_broker(
    bid, nom, pea=True, cto=True, per=False, av=False, courtage_eur=1.0, garde=0.0, inact=0.0
):
    return SimpleNamespace(
        id=bid,
        nom=nom,
        pea_disponible=pea,
        cto_disponible=cto,
        per_disponible=per,
        av_disponible=av,
        pea_pme_disponible=False,
        frais_courtage_actions_euronext_eur=courtage_eur,
        frais_courtage_actions_euronext_pct=None,
        frais_garde_annuel_eur=garde,
        frais_inactivite_annuel_eur=inact,
        etfs_disponibles=None,
    )


def _make_contrat_av(cid, nom, frais_uc=0.005, frais_entree=0.0, frais_arb=0.0):
    return SimpleNamespace(
        id=cid,
        nom=nom,
        frais_gestion_uc_pct=frais_uc,
        frais_entree_pct=frais_entree,
        frais_arbitrage_pct=frais_arb,
    )


def _make_teneur_per(
    tid, nom, frais_uc=0.006, frais_entree=0.0, frais_arb=0.0, frais_versement=0.0
):
    return SimpleNamespace(
        id=tid,
        nom=nom,
        frais_gestion_uc_pct=frais_uc,
        frais_entree_pct=frais_entree,
        frais_arbitrage_pct=frais_arb,
        frais_versement_pct=frais_versement,
    )


def _make_etf(isin, ter=0.002):
    return SimpleNamespace(isin=isin, ticker=f"ETF_{isin[:4]}", ter=ter)


def _make_profil(enveloppes, patrimoine=100_000):
    composition = [SimpleNamespace(enveloppe=e) for e in enveloppes]
    return SimpleNamespace(
        composition_actuelle=composition,
        patrimoine_financier_total=patrimoine,
    )


# ─── Tests _encours_moyen ─────────────────────────────────────────────────────


class TestEncoursMoyen:
    def test_horizon_zero_retourne_initial(self):
        assert _encours_moyen(100_000, 0) == 100_000

    def test_horizon_positif_superieur_initial(self):
        result = _encours_moyen(100_000, 10)
        assert result > 100_000

    def test_valeur_approximativement_correcte(self):
        # 100k × (1+6%)^10 ≈ 179k, moyenne ≈ 139k
        result = _encours_moyen(100_000, 10, 0.06)
        assert 130_000 < result < 150_000


# ─── Tests _ter_moyen ─────────────────────────────────────────────────────────


class TestTerMoyen:
    def test_retourne_defaut_si_vide(self):
        assert _ter_moyen([], None) == pytest.approx(0.003)

    def test_retourne_defaut_si_pas_dans_univers(self):
        result = _ter_moyen(["IE00B4L5Y983"], [_make_etf("AUTRE", ter=0.001)])
        assert result == pytest.approx(0.003)

    def test_ter_calcule_correctement(self):
        etfs = [_make_etf("IE00B4L5Y983", ter=0.002), _make_etf("FR0010315770", ter=0.004)]
        result = _ter_moyen(["IE00B4L5Y983", "FR0010315770"], etfs)
        assert result == pytest.approx(0.003)

    def test_ter_un_seul_etf(self):
        etfs = [_make_etf("IE00B4L5Y983", ter=0.0020)]
        result = _ter_moyen(["IE00B4L5Y983"], etfs)
        assert result == pytest.approx(0.002)


# ─── Tests _cout_broker ───────────────────────────────────────────────────────


class TestCoutBroker:
    def test_retourne_cout_total_provider(self):
        broker = _make_broker("degiro", "DEGIRO", courtage_eur=2.0)
        result = _cout_broker(broker, "PEA", 50_000, [], 10)
        assert isinstance(result, CoutTotalProvider)
        assert result.cout_total_10y_eur > 0

    def test_type_provider_broker(self):
        broker = _make_broker("degiro", "DEGIRO")
        result = _cout_broker(broker, "PEA", 50_000, [], 10)
        assert result.type_provider == "broker"

    def test_broker_casse_retourne_none(self):
        """Si erreur, retourne None sans lever."""
        result = _cout_broker(None, "PEA", 50_000, [], 10)
        assert result is None

    def test_courtage_inclus_dans_cout(self):
        broker_cher = _make_broker("cher", "Broker Cher", courtage_eur=100.0)
        broker_pas_cher = _make_broker("pascher", "Broker Pas Cher", courtage_eur=0.5)
        cout_cher = _cout_broker(broker_cher, "PEA", 50_000, ["IE00B4L5Y983"], 10)
        cout_pas_cher = _cout_broker(broker_pas_cher, "PEA", 50_000, ["IE00B4L5Y983"], 10)
        assert cout_cher.cout_total_10y_eur > cout_pas_cher.cout_total_10y_eur


# ─── Tests _cout_contrat_av ───────────────────────────────────────────────────


class TestCoutContratAV:
    def test_retourne_cout_total_provider(self):
        contrat = _make_contrat_av("linxea_spirit", "Linxea Spirit")
        result = _cout_contrat_av(contrat, 30_000, [], 10)
        assert isinstance(result, CoutTotalProvider)
        assert result.cout_total_10y_eur > 0
        assert result.type_provider == "assureur_av"

    def test_frais_gestion_uc_influence_cout(self):
        cheap = _make_contrat_av("cheap", "Cheap AV", frais_uc=0.005)
        expensive = _make_contrat_av("expensive", "Expensive AV", frais_uc=0.020)
        cout_cheap = _cout_contrat_av(cheap, 30_000, [], 10)
        cout_expensive = _cout_contrat_av(expensive, 30_000, [], 10)
        assert cout_expensive.cout_total_10y_eur > cout_cheap.cout_total_10y_eur


# ─── Tests _cout_teneur_per ───────────────────────────────────────────────────


class TestCoutTeneurPER:
    def test_retourne_cout_total_provider(self):
        teneur = _make_teneur_per("linxea_spirit_per", "Linxea Spirit PER")
        result = _cout_teneur_per(teneur, 20_000, [], 10)
        assert isinstance(result, CoutTotalProvider)
        assert result.type_provider == "teneur_per"

    def test_frais_entree_inclus_une_fois(self):
        sans_entree = _make_teneur_per("t1", "T1 PER", frais_entree=0.0)
        avec_entree = _make_teneur_per("t2", "T2 PER", frais_entree=0.02)
        cout_sans = _cout_teneur_per(sans_entree, 10_000, [], 10)
        cout_avec = _cout_teneur_per(avec_entree, 10_000, [], 10)
        diff = cout_avec.cout_total_10y_eur - cout_sans.cout_total_10y_eur
        assert abs(diff - 200.0) < 1.0  # 2% × 10 000 = 200 € une seule fois


# ─── Tests _filtre_enveloppe_broker ───────────────────────────────────────────


class TestFiltreEnveloppeBroker:
    def test_pea_disponible(self):
        broker = _make_broker("fortuneo", "Fortuneo", pea=True)
        assert _filtre_enveloppe_broker(broker, "PEA") is True

    def test_pea_non_disponible(self):
        broker = _make_broker("ib", "IB", pea=False)
        assert _filtre_enveloppe_broker(broker, "PEA") is False

    def test_enveloppe_inconnue_retourne_true(self):
        broker = _make_broker("x", "X")
        assert _filtre_enveloppe_broker(broker, "ENVELOPPE_INCONNUE") is True


# ─── Tests _filtre_etf_broker ─────────────────────────────────────────────────


class TestFiltreEtfBroker:
    def test_none_retourne_true(self):
        broker = _make_broker("x", "X")
        broker.etfs_disponibles = None
        assert _filtre_etf_broker(broker, ["IE00B4L5Y983"]) is True

    def test_etf_disponible(self):
        broker = _make_broker("x", "X")
        broker.etfs_disponibles = ["IE00B4L5Y983", "FR0010315770"]
        assert _filtre_etf_broker(broker, ["IE00B4L5Y983"]) is True

    def test_etf_non_disponible(self):
        broker = _make_broker("x", "X")
        broker.etfs_disponibles = ["FR0010315770"]
        assert _filtre_etf_broker(broker, ["IE00B4L5Y983"]) is False


# ─── Tests classer_providers ──────────────────────────────────────────────────


class TestClasserProviders:
    def test_retourne_dict_par_enveloppe(self):
        profil = _make_profil(["PEA", "AV", "PER"])
        brokers = [_make_broker("degiro", "DEGIRO", pea=True)]
        contrats = [_make_contrat_av("linxea", "Linxea Spirit")]
        teneurs = [_make_teneur_per("linxea_per", "Linxea PER")]
        result = classer_providers(
            profil=profil,
            allocation_cible={"PEA": 0.4, "AV": 0.3, "PER": 0.3},
            etfs_retenus=[],
            brokers=brokers,
            contrats_av=contrats,
            teneurs_per=teneurs,
        )
        assert isinstance(result, dict)
        assert "PEA" in result
        assert "AV" in result
        assert "PER" in result

    def test_trie_par_cout_croissant(self):
        profil = _make_profil(["AV"])
        contrats = [
            _make_contrat_av("expensive", "Expensive AV", frais_uc=0.020),
            _make_contrat_av("cheap", "Cheap AV", frais_uc=0.005),
        ]
        result = classer_providers(
            profil=profil,
            allocation_cible={"AV": 1.0},
            etfs_retenus=[],
            contrats_av=contrats,
        )
        candidats = result["AV"]
        assert len(candidats) == 2
        assert candidats[0].cout_total_10y_eur <= candidats[1].cout_total_10y_eur

    def test_meilleur_score_100(self):
        profil = _make_profil(["AV"])
        contrats = [
            _make_contrat_av("c1", "AV1", frais_uc=0.005),
            _make_contrat_av("c2", "AV2", frais_uc=0.020),
        ]
        result = classer_providers(
            profil=profil,
            allocation_cible={"AV": 1.0},
            etfs_retenus=[],
            contrats_av=contrats,
        )
        assert result["AV"][0].score == 100.0

    def test_filtre_pea_brokers(self):
        profil = _make_profil(["PEA"])
        brokers = [
            _make_broker("pea_ok", "PEA OK", pea=True),
            _make_broker("pea_ko", "PEA KO", pea=False),
        ]
        result = classer_providers(
            profil=profil,
            allocation_cible={"PEA": 1.0},
            etfs_retenus=[],
            brokers=brokers,
        )
        ids = [c.provider_id for c in result["PEA"]]
        assert "pea_ok" in ids
        assert "pea_ko" not in ids

    def test_profil_vide_fallback_enveloppes(self):
        """Profil sans composition → fallback sur enveloppes standard."""
        profil = SimpleNamespace(composition_actuelle=[], patrimoine_financier_total=100_000)
        result = classer_providers(
            profil=profil,
            allocation_cible={},
            etfs_retenus=[],
        )
        assert isinstance(result, dict)

    def test_jamais_exception(self):
        """classer_providers ne doit pas lever même avec inputs invalides."""
        result = classer_providers(
            profil=None,
            allocation_cible={},
            etfs_retenus=[],
        )
        assert isinstance(result, dict)
