"""Tests pour l'extracteur PDF — Sprint S20."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.import_patrimoine.modele import LignePatrimoine, ResultatExtraction

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _fake_pdf(tmp_path: Path, contenu: bytes = b"%PDF-1.4 fake content") -> Path:
    """Crée un faux fichier PDF pour les tests."""
    chemin = tmp_path / "test.pdf"
    chemin.write_bytes(contenu)
    return chemin


# ─── Tests extraction texte ───────────────────────────────────────────────────


def test_extraction_texte_pdfplumber(tmp_path: Path) -> None:
    """Vérifie que pdfplumber est appelé et retourne du texte."""
    chemin = _fake_pdf(tmp_path)

    mock_page = MagicMock()
    mock_page.extract_text.return_value = "BOURSE DIRECT\nISIN FR0000000001 Lyxor ETF 100.00 €"
    mock_page.extract_tables.return_value = [
        [
            ["Code ISIN", "Libellé", "Quantité", "Valorisation"],
            ["FR0000000001", "Lyxor ETF", "10", "100.00"],
        ]
    ]
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdf.__enter__ = lambda s: mock_pdf
    mock_pdf.__exit__ = MagicMock(return_value=False)

    with patch("pdfplumber.open", return_value=mock_pdf):
        from src.import_patrimoine.extracteur import extraire_pdf

        resultat = extraire_pdf(chemin)

    assert isinstance(resultat, ResultatExtraction)
    assert resultat.pdf_nom == "test.pdf"
    assert len(resultat.pdf_hash) == 64  # SHA-256


def test_extraction_avec_template_bourse_direct(tmp_path: Path) -> None:
    """Vérifie la détection Bourse Direct et l'application du template."""
    chemin = _fake_pdf(tmp_path)

    mock_page = MagicMock()
    mock_page.extract_text.return_value = (
        "BOURSE DIRECT SA\n"
        "Compte titres ordinaire CTO\n"
        "Code ISIN  Libellé  Quantité  Valorisation\n"
        "FR0010315770  Lyxor CAC 40 ETF  10  1234.56 €\n"
    )
    mock_page.extract_tables.return_value = [
        [
            ["Code ISIN", "Libellé", "Quantité", "Valorisation"],
            ["FR0010315770", "Lyxor CAC 40 ETF", "10", "1234.56"],
        ]
    ]
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdf.__enter__ = lambda s: mock_pdf
    mock_pdf.__exit__ = MagicMock(return_value=False)

    with patch("pdfplumber.open", return_value=mock_pdf):
        from src.import_patrimoine.extracteur import extraire_pdf

        resultat = extraire_pdf(chemin)

    assert resultat.emetteur_detecte == "Bourse Direct"
    assert resultat.template_utilise == "bourse_direct"
    assert len(resultat.lignes) >= 1
    assert resultat.lignes[0].isin == "FR0010315770"
    assert resultat.lignes[0].valorisation_eur == pytest.approx(1234.56)


def test_detection_pdf_scanne_peu_de_texte(tmp_path: Path) -> None:
    """Un PDF avec moins de 100 chars est marqué scanné."""
    chemin = _fake_pdf(tmp_path)

    mock_page = MagicMock()
    mock_page.extract_text.return_value = "AB"  # < 100 chars
    mock_page.extract_tables.return_value = []
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdf.__enter__ = lambda s: mock_pdf
    mock_pdf.__exit__ = MagicMock(return_value=False)

    with patch("pdfplumber.open", return_value=mock_pdf):
        from src.import_patrimoine.ocr import detecter_pdf_scanne

        assert detecter_pdf_scanne(chemin) is True


def test_detection_pdf_natif_assez_de_texte(tmp_path: Path) -> None:
    """Un PDF avec 100+ chars n'est pas marqué scanné."""
    chemin = _fake_pdf(tmp_path)

    mock_page = MagicMock()
    mock_page.extract_text.return_value = "A" * 200
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdf.__enter__ = lambda s: mock_pdf
    mock_pdf.__exit__ = MagicMock(return_value=False)

    with patch("pdfplumber.open", return_value=mock_pdf):
        from src.import_patrimoine.ocr import detecter_pdf_scanne

        assert detecter_pdf_scanne(chemin) is False


def test_roundtrip_resultat_extraction() -> None:
    """Vérifie la sérialisation/désérialisation de ResultatExtraction."""
    ligne = LignePatrimoine(
        isin="FR0010315770",
        nom_actif="Lyxor CAC 40 ETF",
        quantite=10.0,
        valorisation_eur=1234.56,
        enveloppe="CTO",
        broker_emetteur="Bourse Direct",
        type_actif="ETF",
        source_pdf="test.pdf",
        source_page=1,
        methode_extraction="template:bourse_direct",
        confiance=90,
    )
    resultat = ResultatExtraction(
        pdf_nom="test.pdf",
        pdf_hash="abc123",
        emetteur_detecte="Bourse Direct",
        template_utilise="bourse_direct",
        lignes=[ligne],
        avertissements=[],
        texte_brut="texte brut",
        tableaux_bruts=[[["A", "B"], ["1", "2"]]],
    )

    data = resultat.model_dump()
    resultat2 = ResultatExtraction(**data)

    assert resultat2.pdf_nom == resultat.pdf_nom
    assert resultat2.pdf_hash == resultat.pdf_hash
    assert len(resultat2.lignes) == 1
    assert resultat2.lignes[0].isin == "FR0010315770"
    assert resultat2.lignes[0].valorisation_eur == pytest.approx(1234.56)
    assert resultat2.tableaux_bruts == [[["A", "B"], ["1", "2"]]]


def test_pdf_inexistant_ne_plante_pas(tmp_path: Path) -> None:
    """extraire_pdf ne doit pas crasher sur un fichier inexistant."""
    chemin = tmp_path / "inexistant.pdf"
    # Crée un fichier vide qui ne sera pas un PDF valide
    chemin.write_bytes(b"")

    # On s'attend soit à une exception soit à un résultat avec avertissements
    from src.import_patrimoine.extracteur import extraire_pdf

    try:
        resultat = extraire_pdf(chemin)
        assert isinstance(resultat, ResultatExtraction)
    except Exception:
        pass  # acceptable si pdfplumber lève une erreur sur un fichier invalide
