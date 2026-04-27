"""Tests pour le détecteur d'émetteur — Sprint S20."""

from __future__ import annotations

import pytest

from src.import_patrimoine.detecteur_emetteur import detecter_emetteur

# Textes d'en-tête synthétiques par émetteur
HEADERS_EMETTEURS = [
    ("BOURSE DIRECT SA - Relevé de portefeuille", "Bourse Direct", "bourse_direct"),
    ("BOURSORAMA - Relevé de compte titres", "Boursorama Banque", "boursorama"),
    ("Fortuneo Banque - Synthèse de portefeuille", "Fortuneo", "fortuneo"),
    ("BNP PARIBAS - Relevé de titres", "BNP Paribas", "bnp_paribas"),
    ("Société Générale - Relevé de portefeuille", "Société Générale", "societe_generale"),
    ("Crédit Agricole - Relevé de titres", "Crédit Agricole", "credit_agricole"),
    ("CIC - Relevé de compte titres", "CIC / Crédit Mutuel", "cic_cm"),
    ("Generali Vie - Relevé de contrat", "Generali", "generali"),
    ("LINXEA Spirit - Relevé annuel", "Linxea", "linxea"),
    ("AXA France Vie - Relevé de portefeuille", "AXA", "axa"),
]


@pytest.mark.parametrize("texte,emetteur_attendu,template_attendu", HEADERS_EMETTEURS)
def test_detection_emetteur_connu(texte: str, emetteur_attendu: str, template_attendu: str) -> None:
    """Chaque texte synthétique doit détecter le bon émetteur."""
    emetteur, template = detecter_emetteur(texte)
    assert emetteur == emetteur_attendu, f"Attendu '{emetteur_attendu}', obtenu '{emetteur}'"
    assert template == template_attendu, (
        f"Attendu template '{template_attendu}', obtenu '{template}'"
    )


def test_detection_emetteur_inconnu() -> None:
    """Un texte sans signature connue retourne (None, None)."""
    texte = "Relevé de compte - Établissement Fictif SA - 01/01/2024"
    emetteur, template = detecter_emetteur(texte)
    assert emetteur is None
    assert template is None


def test_detection_emetteur_vide() -> None:
    """Un texte vide retourne (None, None)."""
    emetteur, template = detecter_emetteur("")
    assert emetteur is None
    assert template is None


def test_detection_insensible_casse() -> None:
    """La détection fonctionne en insensible à la casse."""
    texte = "bourse direct sa - relevé annuel"
    emetteur, template = detecter_emetteur(texte)
    assert emetteur == "Bourse Direct"
    assert template == "bourse_direct"


def test_detection_orias_bourse_direct() -> None:
    """Détection via numéro ORIAS de Bourse Direct."""
    texte = "Intermédiaire enregistré sous le numéro ORIAS 07 005 622"
    emetteur, template = detecter_emetteur(texte)
    assert emetteur == "Bourse Direct"
