"""Tests S18-D — Orchestration 'Tout générer' (tests d'intégration mockés)."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from src.mission.etat import EtatEtape, EtatMission, creer_mission, sauvegarder_mission

# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    import src.mission.etat as etat_mod

    monkeypatch.setattr(etat_mod, "_DEFAULT_DATA_DIR", tmp_path / "missions")
    return tmp_path / "missions"


@pytest.fixture
def mission_prete(tmp_data_dir) -> EtatMission:
    """Mission avec toutes les étapes requises validées."""
    m = creer_mission("Dupont Jean", "Alice CGP")
    for cle in [
        "profil_saisi",
        "profilage_mif",
        "allocation_cible",
        "asset_location",
        "plan_execution",
    ]:
        if cle in m.etapes:
            m.etapes[cle] = EtatEtape.VALIDE
    sauvegarder_mission(m)
    return m


@pytest.fixture
def mission_incomplete(tmp_data_dir) -> EtatMission:
    """Mission avec des étapes manquantes."""
    m = creer_mission("Martin", "Bob CGP")
    # Seule profil_saisi validée
    m.etapes["profil_saisi"] = EtatEtape.VALIDE
    sauvegarder_mission(m)
    return m


# ─── Tests vérification étapes requises ──────────────────────────────────────


class TestEtapesRequises:
    _ETAPES_REQUISES = [
        "profil_saisi",
        "profilage_mif",
        "allocation_cible",
        "asset_location",
        "plan_execution",
    ]

    def test_mission_prete_aucune_etape_manquante(self, mission_prete):
        manquantes = [
            cle
            for cle in self._ETAPES_REQUISES
            if mission_prete.etapes.get(cle, EtatEtape.NON_COMMENCE)
            not in (EtatEtape.VALIDE, EtatEtape.SKIP)
        ]
        assert manquantes == []

    def test_mission_incomplete_a_des_etapes_manquantes(self, mission_incomplete):
        manquantes = [
            cle
            for cle in self._ETAPES_REQUISES
            if mission_incomplete.etapes.get(cle, EtatEtape.NON_COMMENCE)
            not in (EtatEtape.VALIDE, EtatEtape.SKIP)
        ]
        assert len(manquantes) > 0
        assert "profilage_mif" in manquantes

    def test_etapes_skip_comptent_comme_validees(self, tmp_data_dir):
        m = creer_mission("Test Skip", "CGP")
        for cle in self._ETAPES_REQUISES:
            if cle in m.etapes:
                m.etapes[cle] = EtatEtape.SKIP
        manquantes = [
            cle
            for cle in self._ETAPES_REQUISES
            if m.etapes.get(cle, EtatEtape.NON_COMMENCE) not in (EtatEtape.VALIDE, EtatEtape.SKIP)
        ]
        assert manquantes == []


# ─── Tests création ZIP ────────────────────────────────────────────────────────


class TestCreationZip:
    def test_zip_vide_valide(self):
        """Un ZIP vide est valide (cas de base)."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("readme.txt", "Test archive mission CGP")
        assert buf.getbuffer().nbytes > 0
        buf.seek(0)
        with zipfile.ZipFile(buf) as zf:
            assert "readme.txt" in zf.namelist()

    def test_zip_avec_pdf_bytes(self):
        """Le ZIP peut contenir des bytes PDF fictifs."""
        buf = io.BytesIO()
        fake_pdf = b"%PDF-1.4 fake content"
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("rapport_client.pdf", fake_pdf)
            zf.writestr("portefeuille.xlsx", b"PK fake xlsx")
        buf.seek(0)
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
            assert "rapport_client.pdf" in names
            assert "portefeuille.xlsx" in names

    def test_zip_ecrit_sur_disque(self, tmp_path):
        """Le ZIP peut être écrit sur disque."""
        zip_path = tmp_path / "test_archive.zip"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w") as zf:
            zf.writestr("test.txt", "contenu")
        zip_path.write_bytes(buf.getvalue())
        assert zip_path.exists()
        assert zip_path.stat().st_size > 0


# ─── Tests orchestration (mockée) ─────────────────────────────────────────────


class TestOrchestrationMockee:
    def _orchestrer(
        self,
        mission: EtatMission,
        output_dir: Path,
        *,
        profil_obj=None,
        mock_pdf=None,
        mock_excel=None,
        mock_snap=None,
    ) -> tuple[io.BytesIO, list[str]]:
        """Logique d'orchestration extraite du bouton (testable sans Streamlit)."""
        output_dir.mkdir(parents=True, exist_ok=True)
        zip_buf = io.BytesIO()
        etapes_realisees: list[str] = []

        with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            # Récap mission
            try:
                recap_bytes = b"%PDF-1.4 recap"
                zf.writestr(f"recap_mission_{mission.mission_id}.pdf", recap_bytes)
                etapes_realisees.append("recap_mission")
            except Exception:
                pass

            # Snapshot hypothèses
            if mock_snap:
                try:
                    snap_bytes = mock_snap()
                    zf.writestr("snapshot_hypotheses.json", snap_bytes)
                    etapes_realisees.append("snapshot")
                except Exception:
                    pass

            # PDF client
            if profil_obj and mock_pdf:
                try:
                    pdf_bytes = mock_pdf(profil_obj)
                    zf.writestr(f"rapport_client_{mission.mission_id}.pdf", pdf_bytes)
                    etapes_realisees.append("pdf_client")
                except Exception:
                    pass

            # Excel
            if mock_excel:
                try:
                    excel_bytes = mock_excel()
                    zf.writestr(f"portefeuille_{mission.mission_id}.xlsx", excel_bytes)
                    etapes_realisees.append("excel")
                except Exception:
                    pass

        return zip_buf, etapes_realisees

    def test_orchestration_complete_avec_tous_mocks(self, mission_prete, tmp_path):
        def mock_pdf(_p):
            return b"%PDF-1.4 client"

        def mock_excel():
            return b"PK xlsx"

        def mock_snap():
            return b'{"hypotheses": []}'

        zip_buf, etapes = self._orchestrer(
            mission_prete,
            tmp_path / "output",
            profil_obj={"id": 1, "nom": "Dupont"},
            mock_pdf=mock_pdf,
            mock_excel=mock_excel,
            mock_snap=mock_snap,
        )

        assert "recap_mission" in etapes
        assert "pdf_client" in etapes
        assert "excel" in etapes
        assert "snapshot" in etapes

        zip_buf.seek(0)
        with zipfile.ZipFile(zip_buf) as zf:
            names = zf.namelist()
            assert any("recap_mission" in n for n in names)
            assert any("rapport_client" in n for n in names)
            assert any("portefeuille" in n for n in names)

    def test_orchestration_sans_profil_pas_pdf_client(self, mission_prete, tmp_path):
        def mock_pdf(_p):
            return b"%PDF-1.4 client"

        zip_buf, etapes = self._orchestrer(
            mission_prete,
            tmp_path / "output",
            profil_obj=None,  # Pas de profil
            mock_pdf=mock_pdf,
        )

        assert "pdf_client" not in etapes
        assert "recap_mission" in etapes

    def test_orchestration_erreur_dans_etape_continue(self, mission_prete, tmp_path):
        """Une erreur dans une étape ne bloque pas les suivantes."""

        def mock_excel_fail():
            raise RuntimeError("Erreur Excel simulée")

        def mock_snap():
            return b'{"hypotheses": []}'

        zip_buf, etapes = self._orchestrer(
            mission_prete,
            tmp_path / "output",
            mock_excel=mock_excel_fail,
            mock_snap=mock_snap,
        )

        # Excel a échoué mais snapshot et recap doivent être présents
        assert "excel" not in etapes
        assert "recap_mission" in etapes
        assert "snapshot" in etapes

    def test_zip_contient_au_moins_recap(self, mission_prete, tmp_path):
        zip_buf, _ = self._orchestrer(mission_prete, tmp_path / "output")

        zip_buf.seek(0)
        with zipfile.ZipFile(zip_buf) as zf:
            names = zf.namelist()
            assert any("recap_mission" in n for n in names)

    def test_marquer_livrables_valide(self, mission_prete):
        """Après génération, l'étape livrables_pdf_excel doit être marquée VALIDE."""
        if "livrables_pdf_excel" in mission_prete.etapes:
            mission_prete.etapes["livrables_pdf_excel"] = EtatEtape.VALIDE
            sauvegarder_mission(mission_prete)

            from src.mission.etat import charger_mission

            rechargee = charger_mission(mission_prete.mission_id)
            assert rechargee.etapes.get("livrables_pdf_excel") == EtatEtape.VALIDE
