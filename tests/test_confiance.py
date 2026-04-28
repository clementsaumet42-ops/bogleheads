"""Tests pour le calcul de score de confiance — Sprint S20."""

from __future__ import annotations

from src.import_patrimoine.confiance import calculer_confiance
from src.import_patrimoine.modele import LignePatrimoine


def _ligne_base(**kwargs) -> LignePatrimoine:
    defaults = dict(
        isin=None,
        nom_actif="Fonds test",
        quantite=None,
        valorisation_eur=1000.0,
        enveloppe="CTO",
        broker_emetteur="Courtier Test",
        type_actif="ETF",
        source_pdf="test.pdf",
        source_page=1,
        methode_extraction="template:test",
        confiance=0,
    )
    defaults.update(kwargs)
    return LignePatrimoine(**defaults)


def test_confiance_haute_template_isin_valorisation() -> None:
    """Template + ISIN + valorisation + enveloppe + natif → score >= 90."""
    ligne = _ligne_base(isin="FR0010315770", valorisation_eur=1234.56, enveloppe="CTO")
    score = calculer_confiance(
        ligne,
        template_matche=True,
        valorisation_ambigue=False,
        via_ocr=False,
    )
    # template=40 + isin=25 + valorisation=20 + enveloppe=10 + natif=5 = 100
    assert score >= 90


def test_confiance_maximale() -> None:
    """Score maximum = 100 quand tous les critères sont remplis."""
    ligne = _ligne_base(isin="FR0010315770", valorisation_eur=5000.0, enveloppe="PEA")
    score = calculer_confiance(
        ligne,
        template_matche=True,
        valorisation_ambigue=False,
        via_ocr=False,
    )
    assert score == 100


def test_confiance_faible_ocr_sans_template() -> None:
    """OCR + pas de template → score < 30."""
    ligne = _ligne_base(
        isin=None,
        valorisation_eur=500.0,
        enveloppe="Inconnu",
    )
    score = calculer_confiance(
        ligne,
        template_matche=False,
        valorisation_ambigue=True,
        via_ocr=True,
    )
    # pas de template=0, pas d'isin=0, valorisation ambigue=0, enveloppe inconnu=0, ocr=0
    assert score < 30


def test_confiance_sans_isin() -> None:
    """Sans ISIN, le score est réduit de 25."""
    ligne_avec = _ligne_base(isin="FR0010315770", enveloppe="CTO")
    ligne_sans = _ligne_base(isin=None, enveloppe="CTO")

    score_avec = calculer_confiance(ligne_avec, template_matche=True)
    score_sans = calculer_confiance(ligne_sans, template_matche=True)

    assert score_avec - score_sans == 25


def test_confiance_via_ocr_penalise() -> None:
    """OCR coûte 5 points."""
    ligne = _ligne_base(isin="FR0010315770", enveloppe="CTO")
    score_natif = calculer_confiance(ligne, template_matche=True, via_ocr=False)
    score_ocr = calculer_confiance(ligne, template_matche=True, via_ocr=True)
    assert score_natif - score_ocr == 5


def test_confiance_borne_0_100() -> None:
    """Le score est toujours entre 0 et 100."""
    ligne = _ligne_base()
    score = calculer_confiance(ligne, template_matche=False, via_ocr=True)
    assert 0 <= score <= 100


def test_field_validator_confiance_borne() -> None:
    """Le field_validator de LignePatrimoine borne le score."""
    ligne = _ligne_base(confiance=200)
    assert ligne.confiance == 100

    ligne2 = _ligne_base(confiance=-50)
    assert ligne2.confiance == 0


def test_field_validator_isin_invalide() -> None:
    """Un ISIN invalide est remis à None par le validateur."""
    ligne = _ligne_base(isin="INVALIDE")
    assert ligne.isin is None


def test_field_validator_isin_valide() -> None:
    """Un ISIN valide est conservé."""
    ligne = _ligne_base(isin="FR0010315770")
    assert ligne.isin == "FR0010315770"
