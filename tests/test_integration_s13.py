"""Tests d'intégration S13 — Lots A, B, C."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent


# ─── S13 Lot B — Schemas ──────────────────────────────────────────────────────


class TestSchemasTeneurPER:
    def test_teneurs_per_yaml_valide(self):
        """teneurs_per.yaml est valide selon le schema TeneursPERConfig."""
        from src.schemas import charger_et_valider

        config = charger_et_valider("teneurs_per.yaml")
        assert hasattr(config, "teneurs_per")
        assert len(config.teneurs_per) >= 5

    def test_chaque_teneur_a_id_et_nom(self):
        from src.schemas import charger_et_valider

        config = charger_et_valider("teneurs_per.yaml")
        for t in config.teneurs_per:
            assert t.id
            assert t.nom

    def test_frais_gestion_dans_bornes(self):
        from src.schemas import charger_et_valider

        config = charger_et_valider("teneurs_per.yaml")
        for t in config.teneurs_per:
            assert 0 <= t.frais_gestion_uc_pct <= 0.05

    def test_teneurs_per_enregistre_dans_schemas(self):
        from src.schemas import _SCHEMAS, TeneursPERConfig

        assert "teneurs_per.yaml" in _SCHEMAS
        assert _SCHEMAS["teneurs_per.yaml"] is TeneursPERConfig

    def test_broker_a_etfs_disponibles(self):
        """Le champ etfs_disponibles existe sur Broker (None par défaut)."""
        from src.schemas import Broker

        broker = Broker(
            id="test",
            nom="Test Broker",
            frais_gestion_garde_annuel_eur=0.0,
        )
        assert hasattr(broker, "etfs_disponibles")
        assert broker.etfs_disponibles is None


class TestSchemasBrokerEtfsDisponibles:
    def test_broker_etfs_disponibles_optionnel(self):
        from src.schemas import Broker

        # Sans etfs_disponibles
        b = Broker(id="b1", nom="Broker 1")
        assert b.etfs_disponibles is None

    def test_broker_etfs_disponibles_liste(self):
        from src.schemas import Broker

        b = Broker(id="b2", nom="Broker 2", etfs_disponibles=["IE00B4L5Y983", "FR0010315770"])
        assert b.etfs_disponibles == ["IE00B4L5Y983", "FR0010315770"]

    def test_brokers_yaml_valide(self):
        """brokers.yaml valide avec la nouvelle définition."""
        from src.schemas import charger_et_valider

        config = charger_et_valider("brokers.yaml")
        assert hasattr(config, "brokers")
        for b in config.brokers:
            assert hasattr(b, "etfs_disponibles")


# ─── S13 Lot A — Cohérence intégrée ──────────────────────────────────────────


class TestCoherenceIntegree:
    def test_charger_tous_catalogues(self):
        """Tous les catalogues nécessaires à verifier_coherence se chargent."""
        from src.schemas import (
            charger_et_valider,
        )

        etfs_config = charger_et_valider("univers_etf.yaml")
        brokers_config = charger_et_valider("brokers.yaml")
        av_config = charger_et_valider("contrats_av.yaml")
        per_config = charger_et_valider("teneurs_per.yaml")

        assert hasattr(etfs_config, "univers_etf")
        assert hasattr(brokers_config, "brokers")
        assert hasattr(av_config, "contrats_av")
        assert hasattr(per_config, "teneurs_per")

    def test_verifier_coherence_profil_reel(self):
        """Vérifie la cohérence sur un profil réel sans lever d'exception."""
        from src.catalogue.coherence import verifier_coherence
        from src.schemas import charger_et_valider

        profils = charger_et_valider("profils_clients.yaml")
        profil1 = next(p for p in profils.profils if p.id == 1)

        etfs_config = charger_et_valider("univers_etf.yaml")
        brokers_config = charger_et_valider("brokers.yaml")
        av_config = charger_et_valider("contrats_av.yaml")
        per_config = charger_et_valider("teneurs_per.yaml")

        # Ne doit pas lever
        result = verifier_coherence(
            profil=profil1,
            univers_etf=etfs_config.univers_etf,
            brokers=brokers_config.brokers,
            contrats_av=av_config.contrats_av,
            teneurs_per=per_config.teneurs_per,
        )
        assert isinstance(result, list)
        # Toutes les incohérences ont la bonne structure
        from src.catalogue.coherence import IncoherenceLigne

        for inc in result:
            assert isinstance(inc, IncoherenceLigne)
            assert inc.severite in ("info", "warning", "error")


# ─── S13 Lot C — Best Provider intégré ───────────────────────────────────────


class TestBestProviderIntegre:
    def test_classer_providers_profil_reel(self):
        """classer_providers fonctionne sur un profil réel."""
        from src.catalogue.best_provider import classer_providers
        from src.schemas import charger_et_valider

        profils = charger_et_valider("profils_clients.yaml")
        profil1 = next(p for p in profils.profils if p.id == 1)

        brokers_config = charger_et_valider("brokers.yaml")
        av_config = charger_et_valider("contrats_av.yaml")
        per_config = charger_et_valider("teneurs_per.yaml")
        etfs_config = charger_et_valider("univers_etf.yaml")

        result = classer_providers(
            profil=profil1,
            allocation_cible={"PEA": 0.4, "AV": 0.3, "PER": 0.3},
            etfs_retenus=[],
            brokers=brokers_config.brokers,
            contrats_av=av_config.contrats_av,
            teneurs_per=per_config.teneurs_per,
            univers_etf=etfs_config.univers_etf,
        )
        assert isinstance(result, dict)
        # PER doit avoir des candidats (7 teneurs)
        if "PER" in result:
            assert len(result["PER"]) >= 1

    def test_per_candidats_tries(self):
        """Les teneurs PER sont triés par coût croissant."""
        from src.catalogue.best_provider import classer_providers
        from src.schemas import charger_et_valider

        per_config = charger_et_valider("teneurs_per.yaml")

        class _ProfSimple:
            composition_actuelle = []
            patrimoine_financier_total = 50_000

        result = classer_providers(
            profil=_ProfSimple(),
            allocation_cible={"PER": 1.0},
            etfs_retenus=[],
            teneurs_per=per_config.teneurs_per,
        )
        candidats = result.get("PER", [])
        for i in range(len(candidats) - 1):
            assert candidats[i].cout_total_10y_eur <= candidats[i + 1].cout_total_10y_eur


# ─── S13 — PDF page best_provider ─────────────────────────────────────────────


class TestPDFBestProviderPage:
    def test_page_best_provider_importable(self):
        from src.pdf_builder import _page_best_provider

        assert callable(_page_best_provider)

    def test_page_best_provider_retourne_elems(self):
        from src.pdf_builder import _build_styles, _page_best_provider

        styles = _build_styles()
        elems = _page_best_provider(styles)
        assert isinstance(elems, list)
        assert len(elems) > 0

    def test_pdf_15_pages(self, tmp_path):
        """Le PDF de base a maintenant 16 pages (S15 + plan exécution)."""
        from src.pdf_builder import charger_config_pdf, generer_pdf
        from src.schemas import charger_et_valider

        profils = charger_et_valider("profils_clients.yaml")
        profil1 = next(p for p in profils.profils if p.id == 1)
        config = charger_config_pdf()
        sortie = tmp_path / "test_s13.pdf"
        result = generer_pdf(profil1, config, sortie)
        assert result.nb_pages == 16
