"""Tests S13 Lot A — Validation soft de cohérence catalogue."""

from __future__ import annotations

from types import SimpleNamespace

from src.catalogue.coherence import (
    IncoherenceLigne,
    _trouver_broker,
    _trouver_contrat_av,
    _trouver_etf,
    _trouver_teneur_per,
    verifier_coherence,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _make_etf(isin, ticker, pea=False, cto=True, av=False, per=False):
    elig = SimpleNamespace(PEA=pea, CTO_perso=cto, AV_UC=av, PER=per, CTO_IS=cto)
    return SimpleNamespace(
        isin=isin,
        ticker=ticker,
        nom=f"ETF {ticker}",
        eligibilite=elig,
        domicile_iso="IE",
        ter=0.002,
    )


def _make_broker(bid, nom, pea=False, cto=True, per=False, av=False, etfs_dispo=None):
    return SimpleNamespace(
        id=bid,
        nom=nom,
        pea_disponible=pea,
        cto_disponible=cto,
        per_disponible=per,
        av_disponible=av,
        etfs_disponibles=etfs_dispo,
    )


def _make_contrat_av(cid, nom):
    return SimpleNamespace(id=cid, nom=nom)


def _make_teneur_per(tid, nom):
    return SimpleNamespace(id=tid, nom=nom, etfs_disponibles=None)


def _make_ligne(enveloppe, isin=None, ticker=None, broker=None, assureur=None, teneur=None):
    return SimpleNamespace(
        enveloppe=enveloppe,
        etf_isin=isin,
        etf_ticker=ticker,
        broker=broker,
        assureur=assureur,
        teneur=teneur,
        provider=None,
        libelle_libre=None,
    )


def _make_profil(lignes):
    return SimpleNamespace(composition_actuelle=lignes)


# ─── Tests lookup ──────────────────────────────────────────────────────────────


class TestTrouver:
    def test_trouver_etf_par_isin(self):
        etfs = [_make_etf("IE00B4L5Y983", "IWDA")]
        assert _trouver_etf("IE00B4L5Y983", etfs) is not None

    def test_trouver_etf_par_ticker(self):
        etfs = [_make_etf("IE00B4L5Y983", "IWDA")]
        assert _trouver_etf("iwda", etfs) is not None  # case-insensitive

    def test_trouver_etf_inconnu(self):
        assert _trouver_etf("UNKNOWN", []) is None

    def test_trouver_etf_none(self):
        assert _trouver_etf(None, []) is None

    def test_trouver_broker_par_id(self):
        brokers = [_make_broker("degiro", "DEGIRO")]
        assert _trouver_broker("degiro", brokers) is not None

    def test_trouver_broker_par_nom(self):
        brokers = [_make_broker("degiro", "DEGIRO")]
        assert _trouver_broker("DEGIRO", brokers) is not None

    def test_trouver_contrat_av(self):
        contrats = [_make_contrat_av("linxea_spirit", "Linxea Spirit")]
        assert _trouver_contrat_av("linxea_spirit", contrats) is not None

    def test_trouver_teneur_per(self):
        teneurs = [_make_teneur_per("linxea_spirit_per", "Linxea Spirit PER")]
        assert _trouver_teneur_per("linxea_spirit_per", teneurs) is not None


# ─── Tests vérification cohérence ─────────────────────────────────────────────


class TestVerifierCoherence:
    """verifier_coherence ne lève jamais d'exception."""

    def test_profil_vide_retourne_liste_vide(self):
        profil = _make_profil([])
        result = verifier_coherence(profil, [], [], [], [])
        assert result == []

    def test_profil_none_retourne_liste_vide(self):
        result = verifier_coherence(None, [], [], [], [])
        assert result == []

    def test_etf_connu_pea_eligible_pas_incoherence(self):
        etfs = [_make_etf("FR0010315770", "CW8", pea=True)]
        ligne = _make_ligne("PEA", isin="FR0010315770")
        profil = _make_profil([ligne])
        incoherences = verifier_coherence(profil, etfs, [], [], [])
        codes = [i.code for i in incoherences]
        assert "ETF_INCOMPATIBLE_ENVELOPPE" not in codes

    def test_etf_inconnu_genere_warning(self):
        ligne = _make_ligne("PEA", isin="INCONNU_ISIN")
        profil = _make_profil([ligne])
        incoherences = verifier_coherence(profil, [], [], [], [])
        assert any(i.code == "ETF_INCONNU" for i in incoherences)
        # Jamais d'exception
        assert all(isinstance(i, IncoherenceLigne) for i in incoherences)

    def test_etf_non_eligible_pea_genere_error(self):
        etfs = [_make_etf("IE00B4L5Y983", "IWDA", pea=False, cto=True)]
        ligne = _make_ligne("PEA", isin="IE00B4L5Y983")
        profil = _make_profil([ligne])
        incoherences = verifier_coherence(profil, etfs, [], [], [])
        assert any(
            i.code == "ETF_INCOMPATIBLE_ENVELOPPE" and i.severite == "error" for i in incoherences
        )

    def test_broker_pas_enveloppe_pea(self):
        brokers = [_make_broker("ib", "Interactive Brokers", pea=False, cto=True)]
        etfs = [_make_etf("FR0010315770", "CW8", pea=True)]
        ligne = _make_ligne("PEA", isin="FR0010315770", broker="ib")
        profil = _make_profil([ligne])
        incoherences = verifier_coherence(profil, etfs, brokers, [], [])
        assert any(i.code == "PROVIDER_PAS_ENVELOPPE" for i in incoherences)

    def test_broker_avec_pea_pas_incoherence(self):
        brokers = [_make_broker("fortuneo", "Fortuneo", pea=True)]
        etfs = [_make_etf("FR0010315770", "CW8", pea=True)]
        ligne = _make_ligne("PEA", isin="FR0010315770", broker="fortuneo")
        profil = _make_profil([ligne])
        incoherences = verifier_coherence(profil, etfs, brokers, [], [])
        codes = [i.code for i in incoherences]
        assert "PROVIDER_PAS_ENVELOPPE" not in codes

    def test_provider_pas_etf_broker_liste_renseignee(self):
        brokers = [_make_broker("degiro", "DEGIRO", pea=True, etfs_dispo=["FR0010315770"])]
        etfs = [_make_etf("IE00B4L5Y983", "IWDA", pea=False, cto=True)]
        ligne = _make_ligne("CTO", isin="IE00B4L5Y983", broker="degiro")
        profil = _make_profil([ligne])
        incoherences = verifier_coherence(profil, etfs, brokers, [], [])
        assert any(i.code == "PROVIDER_PAS_ETF" for i in incoherences)

    def test_broker_liste_none_pas_incoherence_etf(self):
        """Si etfs_disponibles=None, on ne génère pas d'incoherence PROVIDER_PAS_ETF."""
        brokers = [_make_broker("degiro", "DEGIRO", cto=True, etfs_dispo=None)]
        etfs = [_make_etf("IE00B4L5Y983", "IWDA", cto=True)]
        ligne = _make_ligne("CTO", isin="IE00B4L5Y983", broker="degiro")
        profil = _make_profil([ligne])
        incoherences = verifier_coherence(profil, etfs, brokers, [], [])
        codes = [i.code for i in incoherences]
        assert "PROVIDER_PAS_ETF" not in codes

    def test_jamais_exception_avec_objets_malformes(self):
        """verifier_coherence ne lève jamais même avec des objets brisés."""
        lignes_brisees = [object(), None, SimpleNamespace()]
        profil = SimpleNamespace(composition_actuelle=lignes_brisees)
        result = verifier_coherence(profil, [], [], [], [])
        assert isinstance(result, list)

    def test_severite_error_incompatibilite_enveloppe(self):
        etfs = [_make_etf("IE00B4L5Y983", "IWDA", pea=False)]
        ligne = _make_ligne("PEA", isin="IE00B4L5Y983")
        profil = _make_profil([ligne])
        incoherences = verifier_coherence(profil, etfs, [], [], [])
        errors = [i for i in incoherences if i.code == "ETF_INCOMPATIBLE_ENVELOPPE"]
        assert errors[0].severite == "error"

    def test_suggestion_presente_si_alternatif_pea(self):
        etfs = [
            _make_etf("IE00B4L5Y983", "IWDA", pea=False),
            _make_etf("FR0010315770", "CW8", pea=True),
        ]
        ligne = _make_ligne("PEA", isin="IE00B4L5Y983")
        profil = _make_profil([ligne])
        incoherences = verifier_coherence(profil, etfs, [], [], [])
        errors = [i for i in incoherences if i.code == "ETF_INCOMPATIBLE_ENVELOPPE"]
        assert errors[0].suggestion is not None

    def test_ligne_sans_etf_pas_incoherence_etf(self):
        """Une ligne sans ISIN/ticker ne génère pas de warning ETF_INCONNU."""
        ligne = _make_ligne("CTO")  # pas d'ETF
        profil = _make_profil([ligne])
        incoherences = verifier_coherence(profil, [], [], [], [])
        codes = [i.code for i in incoherences]
        assert "ETF_INCONNU" not in codes

    def test_contrat_av_trouve_pas_provider_pas_enveloppe(self):
        """Si provider trouvé dans contrats_av pour AV, pas de PROVIDER_PAS_ENVELOPPE."""
        contrats_av = [_make_contrat_av("linxea_spirit", "Linxea Spirit")]
        etfs = [_make_etf("FR0010315770", "CW8", av=True)]
        ligne = _make_ligne("AV", isin="FR0010315770", assureur="linxea_spirit")
        profil = _make_profil([ligne])
        incoherences = verifier_coherence(profil, etfs, [], contrats_av, [])
        codes = [i.code for i in incoherences]
        assert "PROVIDER_PAS_ENVELOPPE" not in codes

    def test_teneur_per_trouve_pas_provider_pas_enveloppe(self):
        """Si provider trouvé dans teneurs_per pour PER, pas de PROVIDER_PAS_ENVELOPPE."""
        teneurs = [_make_teneur_per("linxea_spirit_per", "Linxea Spirit PER")]
        etfs = [_make_etf("FR0010315770", "CW8", per=True)]
        ligne = _make_ligne("PER", isin="FR0010315770", teneur="linxea_spirit_per")
        profil = _make_profil([ligne])
        incoherences = verifier_coherence(profil, etfs, [], [], teneurs)
        codes = [i.code for i in incoherences]
        assert "PROVIDER_PAS_ENVELOPPE" not in codes

    def test_plusieurs_lignes_independantes(self):
        """Chaque ligne est vérifiée indépendamment."""
        etfs = [_make_etf("FR0010315770", "CW8", pea=True)]
        ligne_ok = _make_ligne("PEA", isin="FR0010315770")
        ligne_ko = _make_ligne("PEA", isin="INCONNU")
        profil = _make_profil([ligne_ok, ligne_ko])
        incoherences = verifier_coherence(profil, etfs, [], [], [])
        # ligne_ko génère ETF_INCONNU sur idx=1
        assert any(i.ligne_idx == 1 and i.code == "ETF_INCONNU" for i in incoherences)
        # ligne_ok (idx=0) ne génère pas d'incoherence
        assert not any(i.ligne_idx == 0 for i in incoherences)
