"""
Tests Sprint S3 — Générateur PDF client 13 pages.

Baseline : 194 tests (S1+S2). Ajout de ≥ 22 tests S3.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pypdf
import pytest

from src.pdf_builder import (
    _chart_patrimoine_camembert,
    _chart_projection_mc,
    _get,
    charger_config_pdf,
    generer_pdf,
)
from src.schemas import (
    CabinetConfig,
    CabinetInfo,
    PDFFooter,
    PDFStyle,
    ResultatPDF,
    charger_et_valider,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent


@pytest.fixture(scope="module")
def profils():
    return charger_et_valider("profils_clients.yaml")


@pytest.fixture(scope="module")
def profil1(profils):
    return next(p for p in profils.profils if p.id == 1)


@pytest.fixture(scope="module")
def config_pdf():
    return charger_config_pdf()


@pytest.fixture(scope="module")
def pdf_profil1(profil1, config_pdf, tmp_path_factory):
    """Génère le PDF du profil 1 une seule fois pour tous les tests."""
    tmp = tmp_path_factory.mktemp("pdf_test")
    sortie = tmp / "profil1_test.pdf"
    return generer_pdf(profil1, config_pdf, sortie)


# ─── Tests schemas Pydantic S3 ────────────────────────────────────────────────


class TestSchemasPydanticS3:
    def test_cabinet_config_from_yaml(self, config_pdf):
        """CabinetConfig est correctement chargé depuis pdf_cabinet.yaml."""
        assert isinstance(config_pdf, CabinetConfig)
        assert config_pdf.cabinet.nom

    def test_cabinet_info_fields(self, config_pdf):
        """CabinetInfo contient les champs requis."""
        cab = config_pdf.cabinet
        assert cab.numero_orias is not None

    def test_pdf_style_defaults(self):
        """PDFStyle a des valeurs par défaut cohérentes."""
        style = PDFStyle()
        assert style.couleur_primary == "#1a4d8f"
        assert style.couleur_accent == "#d4a017"
        assert style.marges_cm == 2.0
        assert style.format_page == "A4"

    def test_pdf_footer_defaults(self):
        """PDFFooter a une mention légale et un avertissement AMF."""
        footer = PDFFooter()
        assert "confidentiel" in footer.mention_legale.lower()
        assert len(footer.avertissement_amf) > 20

    def test_cabinet_config_minimal(self):
        """CabinetConfig fonctionne avec juste le nom du cabinet."""
        config = CabinetConfig(cabinet=CabinetInfo(nom="Mon Cabinet"))
        assert config.cabinet.nom == "Mon Cabinet"
        assert isinstance(config.style, PDFStyle)
        assert isinstance(config.footer, PDFFooter)

    def test_resultat_pdf_schema(self):
        """ResultatPDF valide les champs requis."""
        res = ResultatPDF(
            chemin="/tmp/test.pdf",
            taille_octets=100000,
            nb_pages=13,
            profil_id=1,
            date_generation="2026-04-23",
        )
        assert res.nb_pages == 13
        assert res.profil_id == 1
        """pdf_cabinet.yaml est enregistré dans _SCHEMAS."""
        from src.schemas import _SCHEMAS

        assert "pdf_cabinet.yaml" in _SCHEMAS
        assert _SCHEMAS["pdf_cabinet.yaml"] is CabinetConfig


# ─── Tests génération PDF profil 1 ───────────────────────────────────────────


class TestGenerationPDFProfil1:
    def test_fichier_cree(self, pdf_profil1):
        """Le fichier PDF est créé."""
        assert Path(pdf_profil1.chemin).exists()

    def test_taille_superieure_50ko(self, pdf_profil1):
        """Le PDF fait plus de 50 Ko."""
        assert pdf_profil1.taille_octets > 50 * 1024

    def test_taille_inferieure_500ko(self, pdf_profil1):
        """Le PDF fait moins de 500 Ko."""
        assert pdf_profil1.taille_octets < 500 * 1024

    def test_nb_pages_egal_13(self, pdf_profil1):
        """Le PDF contient exactement 14 pages (13 S3 + 1 alertes S12)."""
        assert pdf_profil1.nb_pages == 14

    def test_nb_pages_via_pypdf(self, pdf_profil1):
        """Vérification du nombre de pages via pypdf.PdfReader."""
        reader = pypdf.PdfReader(pdf_profil1.chemin)
        assert len(reader.pages) == 14

    def test_profil_id_correct(self, pdf_profil1):
        """ResultatPDF contient le bon profil_id."""
        assert pdf_profil1.profil_id == 1

    def test_date_generation_presente(self, pdf_profil1):
        """La date de génération est renseignée."""
        assert len(pdf_profil1.date_generation) == 10  # YYYY-MM-DD

    def test_contenu_nom_client(self, pdf_profil1):
        """Le PDF contient le nom du client."""
        reader = pypdf.PdfReader(pdf_profil1.chemin)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        assert "Cadre Supérieur" in text or "PROFIL_1" in text

    def test_contenu_patrimoine(self, pdf_profil1):
        """Le PDF contient le patrimoine total."""
        reader = pypdf.PdfReader(pdf_profil1.chemin)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        # 500 000 € apparaît sous diverses formes
        assert "500" in text


# ─── Tests fallbacks ──────────────────────────────────────────────────────────


class TestFallbacks:
    def test_logo_absent_pas_erreur(self, profil1, tmp_path):
        """Si logo_path absent, le PDF est généré sans erreur."""
        config = CabinetConfig(
            cabinet=CabinetInfo(
                nom="Cabinet Test",
                logo_path=None,
            )
        )
        sortie = tmp_path / "no_logo.pdf"
        res = generer_pdf(profil1, config, sortie)
        assert sortie.exists()
        assert res.nb_pages == 14

    def test_logo_path_inexistant_pas_erreur(self, profil1, tmp_path):
        """Si logo_path pointe vers un fichier inexistant, fallback texte."""
        config = CabinetConfig(
            cabinet=CabinetInfo(
                nom="Cabinet Test",
                logo_path="/tmp/logo_qui_nexiste_pas.png",
            )
        )
        sortie = tmp_path / "bad_logo.pdf"
        res = generer_pdf(profil1, config, sortie)
        assert sortie.exists()
        assert res.nb_pages == 14

    def test_fallback_monte_carlo_sans_module(self, profil1, config_pdf, tmp_path):
        """Fallback Monte-Carlo si src.projection indisponible — pas d'erreur fatale."""
        with patch.dict("sys.modules", {"src.projection": None}):
            sortie = tmp_path / "fallback_mc.pdf"
            # Le fallback interne doit prendre le relais sans lever d'exception
            res = generer_pdf(profil1, config_pdf, sortie)
            assert sortie.exists()
            assert res.nb_pages == 14

    def test_fallback_optimiseur_absent(self, profil1, tmp_path):
        """Si S2 optimiseur absent, fallback sur allocation profil sans erreur fatale."""
        config = CabinetConfig(cabinet=CabinetInfo(nom="Cabinet Fallback"))
        with patch.dict("sys.modules", {"src.optimiseur_allocation": None}):
            sortie = tmp_path / "fallback_optim.pdf"
            res = generer_pdf(profil1, config, sortie)
            assert sortie.exists()
            assert res.nb_pages == 14


# ─── Tests 6 profils ─────────────────────────────────────────────────────────


class TestSixProfils:
    def test_tous_profils_generent_sans_erreur(self, profils, tmp_path):
        """Les 6 profils génèrent un PDF sans erreur."""
        config = CabinetConfig(cabinet=CabinetInfo(nom="Cabinet Test"))
        for profil in profils.profils:
            sortie = tmp_path / f"{profil.code}_test.pdf"
            res = generer_pdf(profil, config, sortie)
            assert sortie.exists(), f"PDF non créé pour profil {profil.id}"
            assert res.nb_pages == 14, f"Profil {profil.id} : {res.nb_pages} pages au lieu de 14"

    def test_tous_profils_13_pages_pypdf(self, profils, tmp_path):
        """Vérification pypdf : chaque profil donne exactement 14 pages (13 S3 + 1 alertes S12)."""
        config = CabinetConfig(cabinet=CabinetInfo(nom="Cabinet Test"))
        for profil in profils.profils:
            sortie = tmp_path / f"{profil.code}_pypdf.pdf"
            generer_pdf(profil, config, sortie)
            reader = pypdf.PdfReader(str(sortie))
            assert len(reader.pages) == 14, f"Profil {profil.id} : {len(reader.pages)} pages"

    def test_tous_profils_taille_valide(self, profils, tmp_path):
        """Chaque PDF fait entre 50 Ko et 500 Ko."""
        config = CabinetConfig(cabinet=CabinetInfo(nom="Cabinet Test"))
        for profil in profils.profils:
            sortie = tmp_path / f"{profil.code}_taille.pdf"
            res = generer_pdf(profil, config, sortie)
            assert 50 * 1024 <= res.taille_octets <= 500 * 1024, (
                f"Profil {profil.id} : taille {res.taille_octets / 1024:.1f} Ko hors bornes"
            )


# ─── Tests graphiques matplotlib ──────────────────────────────────────────────


class TestGraphiques:
    def test_camembert_patrimoine_genere(self, tmp_path):
        """Le camembert patrimoine génère un fichier PNG."""
        enveloppes = {"PEA": 80000, "PER": 50000, "CTO": 150000}
        path = _chart_patrimoine_camembert(enveloppes, str(tmp_path))
        assert path is not None
        assert Path(path).exists()
        assert Path(path).stat().st_size > 1000

    def test_camembert_vide_retourne_none(self, tmp_path):
        """Camembert avec enveloppes vides → None sans erreur."""
        path = _chart_patrimoine_camembert({}, str(tmp_path))
        assert path is None

    def test_projection_mc_genere(self, tmp_path):
        """La projection Monte-Carlo génère un PNG et des stats."""
        alloc = {"actions": 0.6, "obligations": 0.3, "or": 0.1}
        chart_path, stats = _chart_projection_mc(
            capital_initial=200000,
            versement_annuel=12000,
            horizon=20,
            allocation=alloc,
            objectif=None,
            tmp_dir=str(tmp_path),
            seed=42,
        )
        assert chart_path is not None
        assert Path(chart_path).exists()
        assert "mediane_final" in stats
        assert stats["mediane_final"] > 0

    def test_projection_mc_reproductible(self, tmp_path):
        """Même seed → même capital médian final."""
        alloc = {"actions": 0.7, "obligations": 0.3}
        _, stats1 = _chart_projection_mc(100000, 5000, 10, alloc, None, str(tmp_path), seed=123)
        _, stats2 = _chart_projection_mc(100000, 5000, 10, alloc, None, str(tmp_path), seed=123)
        assert abs(stats1["mediane_final"] - stats2["mediane_final"]) < 1


# ─── Tests reproductibilité ───────────────────────────────────────────────────


class TestReproductibilite:
    def test_meme_profil_meme_nb_pages(self, profil1, config_pdf, tmp_path):
        """Même profil + même config → même nombre de pages."""
        sortie1 = tmp_path / "rep1.pdf"
        sortie2 = tmp_path / "rep2.pdf"
        res1 = generer_pdf(profil1, config_pdf, sortie1)
        res2 = generer_pdf(profil1, config_pdf, sortie2)
        assert res1.nb_pages == res2.nb_pages == 14

    def test_meme_profil_meme_contenu_textuel(self, profil1, config_pdf, tmp_path):
        """Même profil → le nom du client apparaît dans les deux PDFs."""
        sortie1 = tmp_path / "rep_txt1.pdf"
        sortie2 = tmp_path / "rep_txt2.pdf"
        generer_pdf(profil1, config_pdf, sortie1)
        generer_pdf(profil1, config_pdf, sortie2)

        for path in (sortie1, sortie2):
            reader = pypdf.PdfReader(str(path))
            text = "".join(p.extract_text() or "" for p in reader.pages)
            assert "Cadre" in text or "500" in text


# ─── Tests helper _get ───────────────────────────────────────────────────────


class TestGetHelper:
    def test_get_attribut_simple(self, config_pdf):
        """_get récupère un attribut simple."""
        assert _get(config_pdf, "cabinet.nom")

    def test_get_attribut_inexistant_retourne_default(self, config_pdf):
        """_get retourne le défaut si l'attribut n'existe pas."""
        assert _get(config_pdf, "cabinet.champ_inexistant", "DEFAULT") == "DEFAULT"

    def test_get_sur_dict(self):
        """_get fonctionne aussi sur les dicts."""
        d = {"a": {"b": 42}}
        assert _get(d, "a.b") == 42

    def test_get_none_obj_retourne_default(self):
        """_get retourne le défaut si l'objet est None."""
        assert _get(None, "a.b", "fallback") == "fallback"


# ─── Tests exemples committés ─────────────────────────────────────────────────


class TestExemplesCommites:
    def test_exemples_existent(self):
        """Les 6 fichiers exemple existent dans examples/."""
        examples_dir = ROOT / "examples"
        if not examples_dir.exists():
            pytest.skip("Dossier examples/ non présent")
        codes = [
            "PROFIL_1_CADRE_SUP",
            "PROFIL_2_DIRIGEANT_GG",
            "PROFIL_3_DIRIGEANT_PME",
            "PROFIL_4_PROFESSION_LIBERALE",
            "PROFIL_5_JEUNE_CADRE",
            "PROFIL_6_PRE_RETRAITE",
        ]
        for code in codes:
            pdf_path = examples_dir / f"{code}_exemple.pdf"
            assert pdf_path.exists(), f"Fichier exemple manquant : {pdf_path.name}"

    def test_exemples_13_pages(self):
        """Les fichiers exemple ont 14 pages (13 S3 + 1 alertes S12)."""
        examples_dir = ROOT / "examples"
        if not examples_dir.exists():
            pytest.skip("Dossier examples/ non présent")
        for pdf_path in examples_dir.glob("*_exemple.pdf"):
            reader = pypdf.PdfReader(str(pdf_path))
            assert len(reader.pages) == 14, (
                f"{pdf_path.name} : {len(reader.pages)} pages au lieu de 14"
            )

    def test_exemples_taille_valide(self):
        """Les fichiers exemple font entre 50 Ko et 500 Ko."""
        examples_dir = ROOT / "examples"
        if not examples_dir.exists():
            pytest.skip("Dossier examples/ non présent")
        for pdf_path in examples_dir.glob("*_exemple.pdf"):
            taille = pdf_path.stat().st_size
            assert 50 * 1024 <= taille <= 500 * 1024, (
                f"{pdf_path.name} : {taille / 1024:.1f} Ko hors bornes"
            )


# ─── Tests S5 — pages conditionnelles ────────────────────────────────────────

_profils_all = __import__("src.schemas", fromlist=["charger_et_valider"]).charger_et_valider(
    "profils_clients.yaml"
)
PROFIL = next(p for p in _profils_all.profils if p.id == 1)


class TestPagesS5:
    """Tests S5 — 4 nouvelles pages conditionnelles."""

    def test_generer_pdf_17_pages_avec_profil_consolide(self, tmp_path):
        from pypdf import PdfReader

        from src.profilage.synthese import ProfilConsolide

        pc = ProfilConsolide(aversion_declaree="moyenne", delta_confiance="aligne")
        out = tmp_path / "nrp_17.pdf"
        cfg = charger_config_pdf()
        result = generer_pdf(PROFIL, cfg, out, profil_consolide=pc)
        reader = PdfReader(str(result.chemin))
        assert len(reader.pages) == 18

    def test_generer_pdf_17_pages_avec_capital_humain(self, tmp_path):
        from pypdf import PdfReader

        from src.profilage.capital_humain import CapitalHumain

        ch = CapitalHumain(revenus_nets_annuels=80000, annees_restantes=20)
        out = tmp_path / "nrp_17b.pdf"
        cfg = charger_config_pdf()
        result = generer_pdf(PROFIL, cfg, out, capital_humain_data=ch)
        reader = PdfReader(str(result.chemin))
        assert len(reader.pages) == 18

    def test_generer_pdf_13_pages_par_defaut(self, tmp_path):
        from pypdf import PdfReader

        out = tmp_path / "nrp_13.pdf"
        cfg = charger_config_pdf()
        result = generer_pdf(PROFIL, cfg, out)
        reader = PdfReader(str(result.chemin))
        assert len(reader.pages) == 14
