"""
Tests pour src/pdf_builder.py — Sprint S3.

Valide :
- Génération PDF 13 pages pour chaque profil
- Taille > 50 Ko
- Fallback texte si logo_path absent
- Tous les 3+ profils génèrent sans erreur
- Contenu : nom client, patrimoine total, allocation cible
- Cohérence allocation page 6 = profil YAML
- Présence d'images (graphiques matplotlib, pages 4 et 9)
- Reproductibilité : même entrée → même sortie (modulo date figée)
- Test style : couleurs primary/accent dans la config
- Test ResultatPDF metadata
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# ─── Fixtures ─────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent
CONFIG_DIR = REPO_ROOT / "config"


@pytest.fixture(scope="session")
def profils_data() -> dict:
    with open(CONFIG_DIR / "profils_clients.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="session")
def profil_1(profils_data: dict) -> dict:
    """Profil Cadre Supérieur Salarié (id=1)."""
    return next(p for p in profils_data["profils"] if p["id"] == 1)


@pytest.fixture(scope="session")
def profil_2(profils_data: dict) -> dict:
    return next(p for p in profils_data["profils"] if p["id"] == 2)


@pytest.fixture(scope="session")
def profil_3(profils_data: dict) -> dict:
    return next(p for p in profils_data["profils"] if p["id"] == 3)


@pytest.fixture(scope="session")
def cabinet_config():
    from src.schemas import CabinetConfig

    return CabinetConfig()


@pytest.fixture(scope="session")
def pdf_profil_1(profil_1: dict, cabinet_config, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Génère une seule fois le PDF du profil 1 et le réutilise dans les tests."""
    from src.pdf_builder import generer_pdf

    out = tmp_path_factory.mktemp("pdfs") / "profil_1.pdf"
    generer_pdf(profil_1, cabinet_config, str(out))
    return out


# ─── Test 1 : génération complète + taille + pages ────────────────────────────


class TestGenerationPDF:
    def test_pdf_cree_taille_pages(self, profil_1: dict, cabinet_config, tmp_path: Path) -> None:
        """Le PDF est créé, fait > 50 Ko et contient exactement 13 pages."""
        from src.pdf_builder import generer_pdf

        out = tmp_path / "test.pdf"
        result = generer_pdf(profil_1, cabinet_config, str(out))

        assert out.exists(), "Le fichier PDF doit exister"
        assert result.taille_octets > 50_000, (
            f"Taille attendue > 50 Ko, obtenu {result.taille_octets} octets"
        )
        assert result.nb_pages == 13, f"Attendu 13 pages, obtenu {result.nb_pages}"

    def test_nb_pages_pypdf(self, pdf_profil_1: Path) -> None:
        """Vérification du nombre de pages via pypdf."""
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_profil_1))
        assert len(reader.pages) == 13

    def test_resultat_pdf_metadata(self, profil_1: dict, cabinet_config, tmp_path: Path) -> None:
        """ResultatPDF contient les métadonnées correctes."""
        from src.pdf_builder import generer_pdf
        from src.schemas import ResultatPDF

        out = tmp_path / "meta.pdf"
        result = generer_pdf(profil_1, cabinet_config, str(out))

        assert isinstance(result, ResultatPDF)
        assert result.nb_pages == 13
        assert result.taille_octets > 0
        assert result.profil_code != ""
        assert result.date_generation != ""
        assert result.chemin == str(out)


# ─── Test 2 : fallback texte si logo absent ────────────────────────────────────


class TestFallbackLogo:
    def test_logo_absent_pas_erreur(self, profil_1: dict, tmp_path: Path) -> None:
        """Génération sans erreur si logo_path absent ou fichier inexistant."""
        from src.pdf_builder import generer_pdf
        from src.schemas import CabinetConfig, CabinetInfo, PDFStyle

        config_sans_logo = CabinetConfig(
            cabinet=CabinetInfo(nom="Cabinet Test", logo_path=None),
            style=PDFStyle(),
        )
        out = tmp_path / "no_logo.pdf"
        result = generer_pdf(profil_1, config_sans_logo, str(out))
        assert out.exists()
        assert result.nb_pages == 13

    def test_logo_chemin_invalide_fallback_texte(self, profil_1: dict, tmp_path: Path) -> None:
        """Logo avec chemin inexistant → fallback texte, pas d'erreur."""
        from src.pdf_builder import generer_pdf
        from src.schemas import CabinetConfig, CabinetInfo

        config = CabinetConfig(
            cabinet=CabinetInfo(nom="Cabinet Test", logo_path="/chemin/inexistant/logo.png")
        )
        out = tmp_path / "bad_logo.pdf"
        result = generer_pdf(profil_1, config, str(out))
        assert out.exists()
        assert result.nb_pages == 13


# ─── Test 3 : tous les profils génèrent sans erreur ───────────────────────────


class TestTousProfils:
    def test_profil_1_genere(self, profil_1: dict, cabinet_config, tmp_path: Path) -> None:
        from src.pdf_builder import generer_pdf

        result = generer_pdf(profil_1, cabinet_config, str(tmp_path / "p1.pdf"))
        assert result.nb_pages == 13

    def test_profil_2_genere(self, profil_2: dict, cabinet_config, tmp_path: Path) -> None:
        from src.pdf_builder import generer_pdf

        result = generer_pdf(profil_2, cabinet_config, str(tmp_path / "p2.pdf"))
        assert result.nb_pages == 13

    def test_profil_3_genere(self, profil_3: dict, cabinet_config, tmp_path: Path) -> None:
        from src.pdf_builder import generer_pdf

        result = generer_pdf(profil_3, cabinet_config, str(tmp_path / "p3.pdf"))
        assert result.nb_pages == 13


# ─── Test 4 : contenu du PDF ──────────────────────────────────────────────────


class TestContenuPDF:
    def test_nom_client_present(self, pdf_profil_1: Path) -> None:
        """Le nom du client apparaît dans le PDF (avec gestion latin-1)."""
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_profil_1))
        full_text = " ".join(page.extract_text() or "" for page in reader.pages)
        # "Cadre Supérieur Salarié" → ascii-safe "Cadre Superieur Salarie"
        assert "Cadre" in full_text, "Le nom du client doit apparaître dans le PDF"

    def test_patrimoine_total_present(self, pdf_profil_1: Path) -> None:
        """Le patrimoine total est mentionné dans le PDF."""
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_profil_1))
        full_text = " ".join(page.extract_text() or "" for page in reader.pages)
        # Patrimoine 500000 -> "500 000" ou "500000" ou "500"
        assert any(s in full_text for s in ["500 000", "500000", "500"]), (
            "Le patrimoine total doit apparaître dans le PDF"
        )

    def test_allocation_cible_presente(self, pdf_profil_1: Path, profil_1: dict) -> None:
        """L'allocation cible (% actions) est mentionnée dans le PDF."""
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_profil_1))
        full_text = " ".join(page.extract_text() or "" for page in reader.pages)
        # Allocation actions = 65% pour profil 1
        assert "65" in full_text, "L'allocation cible (65%) doit apparaître dans le PDF"


# ─── Test 5 : cohérence allocation page 6 ────────────────────────────────────


class TestCoherenceAllocation:
    def test_allocation_affichee_correspond_profil(
        self, pdf_profil_1: Path, profil_1: dict
    ) -> None:
        """L'allocation affichée en page 6 correspond à l'allocation du profil YAML."""
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_profil_1))
        # Page 6 (index 5)
        page_6_text = reader.pages[5].extract_text() or ""
        alloc = profil_1["allocation_cible_bogleheads"]
        # 65% → "65"
        pct_actions = int(alloc["actions"] * 100)
        assert str(pct_actions) in page_6_text, (
            f"L'allocation actions ({pct_actions}%) doit apparaître en page 6"
        )


# ─── Test 6 : graphiques présents ────────────────────────────────────────────


class TestGraphiques:
    def test_camembert_page_4(self, pdf_profil_1: Path) -> None:
        """Page 4 (patrimoine actuel) contient un graphique (camembert)."""
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_profil_1))
        page_4 = reader.pages[3]
        assert len(page_4.images) > 0, "La page 4 doit contenir au moins un graphique"

    def test_monte_carlo_page_9(self, pdf_profil_1: Path) -> None:
        """Page 9 (projection) contient un graphique Monte-Carlo."""
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_profil_1))
        page_9 = reader.pages[8]
        assert len(page_9.images) > 0, "La page 9 doit contenir au moins un graphique"


# ─── Test 7 : style / couleurs ───────────────────────────────────────────────


class TestStyle:
    def test_couleur_primary_config(self) -> None:
        """La couleur primary est bien stockée dans la config."""
        from src.schemas import CabinetConfig, PDFStyle

        config = CabinetConfig(style=PDFStyle(couleur_primary="#ff0000"))
        assert config.style.couleur_primary == "#ff0000"

    def test_couleur_accent_config(self) -> None:
        """La couleur accent est bien stockée dans la config."""
        from src.schemas import CabinetConfig, PDFStyle

        config = CabinetConfig(style=PDFStyle(couleur_accent="#00ff00"))
        assert config.style.couleur_accent == "#00ff00"

    def test_config_cabinet_yaml_charge(self) -> None:
        """Le fichier config/pdf_cabinet.yaml se charge correctement."""
        from src.schemas import CabinetConfig, charger_et_valider

        config = charger_et_valider("pdf_cabinet.yaml")
        assert isinstance(config, CabinetConfig)
        assert config.cabinet.nom != ""
        assert config.style.couleur_primary.startswith("#")


# ─── Test 8 : reproductibilité ───────────────────────────────────────────────


class TestReproductibilite:
    def test_meme_entree_meme_sortie(self, profil_1: dict, cabinet_config, tmp_path: Path) -> None:
        """Même profil + date figée → même contenu logique (pages, texte, images).

        Note : reportlab embed un timestamp PDF, le binaire peut différer d'une
        exécution à l'autre. On valide donc le contenu logique, pas les octets bruts.
        """
        from datetime import date as _date
        from unittest.mock import patch

        from pypdf import PdfReader

        from src.pdf_builder import generer_pdf

        fixed_date = _date(2026, 1, 15)

        out1 = tmp_path / "repro_1.pdf"
        out2 = tmp_path / "repro_2.pdf"

        with patch("src.pdf_builder.date") as mock_date:
            mock_date.today.return_value = fixed_date
            mock_date.side_effect = lambda *args, **kw: _date(*args, **kw)
            generer_pdf(profil_1, cabinet_config, str(out1))
            generer_pdf(profil_1, cabinet_config, str(out2))

        r1 = PdfReader(str(out1))
        r2 = PdfReader(str(out2))

        # Même nombre de pages
        assert len(r1.pages) == len(r2.pages), "Nombre de pages différent"

        # Même texte sur chaque page
        for i in range(len(r1.pages)):
            t1 = r1.pages[i].extract_text() or ""
            t2 = r2.pages[i].extract_text() or ""
            assert t1 == t2, f"Texte différent en page {i + 1}"

        # Même nombre d'images sur chaque page
        for i in range(len(r1.pages)):
            assert len(r1.pages[i].images) == len(r2.pages[i].images), (
                f"Nombre d'images différent en page {i + 1}"
            )


# ─── Test 9 : plan de rebalancement page 10 ──────────────────────────────────


class TestPlanRebalancement:
    def test_page_10_contient_rebalancement(self, pdf_profil_1: Path) -> None:
        """Page 10 contient du contenu sur le rebalancement."""
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_profil_1))
        page_10_text = reader.pages[9].extract_text() or ""
        # La page doit parler d'arbitrage ou de versements ou de rebalancement
        assert any(
            kw in page_10_text.lower()
            for kw in ["rebalancement", "arbitrage", "versement", "etape", "flux"]
        ), "La page 10 doit contenir le plan de rebalancement"


# ─── Test 10 : schemas Pydantic ───────────────────────────────────────────────


class TestSchemas:
    def test_cabinet_config_defaut(self) -> None:
        """CabinetConfig instanciable avec valeurs par défaut."""
        from src.schemas import CabinetConfig

        config = CabinetConfig()
        assert config.cabinet.nom == "Cabinet Boglehead"
        assert config.style.format_page == "A4"
        assert config.style.marges_cm == 2.0

    def test_resultat_pdf_schema(self) -> None:
        """ResultatPDF valide les champs correctement."""
        from src.schemas import ResultatPDF

        r = ResultatPDF(
            chemin="/tmp/test.pdf",
            taille_octets=128000,
            nb_pages=13,
            profil_code="PROFIL_1",
            date_generation="2026-01-15",
        )
        assert r.nb_pages == 13
        assert r.taille_octets == 128000

    def test_pdf_style_schema(self) -> None:
        """PDFStyle valide et retourne les couleurs correctement."""
        from src.schemas import PDFStyle

        style = PDFStyle(
            couleur_primary="#1a4d8f",
            couleur_accent="#d4a017",
            marges_cm=2.5,
        )
        assert style.couleur_primary == "#1a4d8f"
        assert style.marges_cm == 2.5
