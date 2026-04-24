"""Tests pour l'assurance vie (AV)"""

import pytest

from src.fiscalite.assurance_vie import (
    ContratAV,
    VersementAV,
    calculer_fiscalite_rachat,
)


def test_contrat_av_moins_4_ans_pfu():
    """Test AV < 4 ans : PFU 12.8% + PS, pas d'abattement"""
    contrat = ContratAV(
        date_ouverture="2023-01-01",
        versements=[VersementAV(date="2023-01-01", montant=10000)],
        valeur_actuelle=12000,
        type_fonds="uc",
    )
    profil = {"situation": "celibataire", "tmi": 0.30, "rfr": 50000}
    operation = {
        "contrat": contrat,
        "montant_brut": 12000,
        "gains": 2000,
        "date_rachat": "2025-01-01",  # 2 ans
        "total_contrats_foyer": 12000,
    }
    result = calculer_fiscalite_rachat(operation, profil)

    assert result.impot_ir == pytest.approx(2000 * 0.128)
    assert result.prelevements_sociaux == pytest.approx(2000 * 0.186)


def test_contrat_av_plus_8_ans_avant_2017_pfl_7_5():
    """Test AV > 8 ans, versements avant 27/09/2017 : PFL 7.5%"""
    contrat = ContratAV(
        date_ouverture="2010-01-01",
        versements=[VersementAV(date="2015-01-01", montant=100000)],
        valeur_actuelle=150000,
        type_fonds="uc",
    )
    profil = {"situation": "celibataire", "tmi": 0.30, "rfr": 50000}
    operation = {
        "contrat": contrat,
        "montant_brut": 50000,
        "gains": 10000,
        "date_rachat": "2024-01-01",  # 14 ans
        "total_contrats_foyer": 150000,
        "abattement_deja_utilise": 0,
    }
    result = calculer_fiscalite_rachat(operation, profil)

    # Gains après abattement : 10 000 - 4 600 = 5 400
    gains_apres_abattement = max(0, 10000 - 4600)
    assert result.impot_ir == pytest.approx(gains_apres_abattement * 0.075)


def test_contrat_av_plus_8_ans_apres_2017_sous_150k():
    """Test AV > 8 ans, versements après 27/09/2017, encours < 150k : PFL 7.5%"""
    contrat = ContratAV(
        date_ouverture="2010-01-01",
        versements=[VersementAV(date="2020-01-01", montant=100000)],
        valeur_actuelle=130000,
        type_fonds="uc",
    )
    profil = {"situation": "celibataire", "tmi": 0.30, "rfr": 50000}
    operation = {
        "contrat": contrat,
        "montant_brut": 40000,
        "gains": 8000,
        "date_rachat": "2024-01-01",
        "total_contrats_foyer": 130000,  # < 150k
        "abattement_deja_utilise": 0,
    }
    result = calculer_fiscalite_rachat(operation, profil)

    # Gains après abattement : 8 000 - 4 600 = 3 400
    gains_apres_abattement = max(0, 8000 - 4600)
    assert result.impot_ir == pytest.approx(gains_apres_abattement * 0.075)


def test_contrat_av_plus_8_ans_apres_2017_au_dela_150k():
    """Test AV > 8 ans, versements après 27/09/2017, encours > 150k : PFU 12.8%"""
    contrat = ContratAV(
        date_ouverture="2010-01-01",
        versements=[VersementAV(date="2020-01-01", montant=200000)],
        valeur_actuelle=250000,
        type_fonds="uc",
    )
    profil = {"situation": "celibataire", "tmi": 0.30, "rfr": 50000}
    operation = {
        "contrat": contrat,
        "montant_brut": 50000,
        "gains": 10000,
        "date_rachat": "2024-01-01",
        "total_contrats_foyer": 250000,  # > 150k
        "abattement_deja_utilise": 0,
    }
    result = calculer_fiscalite_rachat(operation, profil)

    # Gains après abattement : 10 000 - 4 600 = 5 400
    gains_apres_abattement = max(0, 10000 - 4600)
    assert result.impot_ir == pytest.approx(gains_apres_abattement * 0.128)


def test_abattement_celibataire_4600():
    """Test abattement AV célibataire 4 600€"""
    contrat = ContratAV(
        date_ouverture="2010-01-01",
        versements=[VersementAV(date="2015-01-01", montant=100000)],
        valeur_actuelle=150000,
        type_fonds="uc",
    )
    profil = {"situation": "celibataire", "tmi": 0.30, "rfr": 50000}
    operation = {
        "contrat": contrat,
        "montant_brut": 50000,
        "gains": 10000,
        "date_rachat": "2024-01-01",
        "total_contrats_foyer": 150000,
        "abattement_deja_utilise": 0,
    }
    result = calculer_fiscalite_rachat(operation, profil)

    # Abattement utilisé : 4 600€
    # IR calculé sur 10 000 - 4 600 = 5 400€
    gains_apres_abattement = 10000 - 4600
    assert result.impot_ir == pytest.approx(gains_apres_abattement * 0.075)


def test_abattement_couple_9200():
    """Test abattement AV couple 9 200€"""
    contrat = ContratAV(
        date_ouverture="2010-01-01",
        versements=[VersementAV(date="2015-01-01", montant=100000)],
        valeur_actuelle=150000,
        type_fonds="uc",
    )
    profil = {"situation": "couple", "tmi": 0.30, "rfr": 100000}
    operation = {
        "contrat": contrat,
        "montant_brut": 50000,
        "gains": 15000,
        "date_rachat": "2024-01-01",
        "total_contrats_foyer": 150000,
        "abattement_deja_utilise": 0,
    }
    result = calculer_fiscalite_rachat(operation, profil)

    # Abattement utilisé : 9 200€
    # IR calculé sur 15 000 - 9 200 = 5 800€
    gains_apres_abattement = 15000 - 9200
    assert result.impot_ir == pytest.approx(gains_apres_abattement * 0.075)


def test_rachats_successifs_epuisement_abattement():
    """Test rachats successifs même année : épuisement abattement"""
    contrat = ContratAV(
        date_ouverture="2010-01-01",
        versements=[VersementAV(date="2015-01-01", montant=100000)],
        valeur_actuelle=150000,
        type_fonds="uc",
    )
    profil = {"situation": "celibataire", "tmi": 0.30, "rfr": 50000}

    # Premier rachat : gains 3 000€, abattement 3 000€
    operation1 = {
        "contrat": contrat,
        "montant_brut": 30000,
        "gains": 3000,
        "date_rachat": "2024-01-01",
        "total_contrats_foyer": 150000,
        "abattement_deja_utilise": 0,
    }
    result1 = calculer_fiscalite_rachat(operation1, profil)
    assert result1.impot_ir == pytest.approx(0.0)  # 3 000 - 3 000 = 0

    # Deuxième rachat : gains 5 000€, abattement restant 1 600€
    operation2 = {
        "contrat": contrat,
        "montant_brut": 50000,
        "gains": 5000,
        "date_rachat": "2024-06-01",
        "total_contrats_foyer": 150000,
        "abattement_deja_utilise": 3000,
    }
    result2 = calculer_fiscalite_rachat(operation2, profil)
    # Gains après abattement : 5 000 - 1 600 = 3 400
    gains_apres_abattement = 5000 - 1600
    assert result2.impot_ir == pytest.approx(gains_apres_abattement * 0.075)


def test_fonds_euro_ps_deja_preleves():
    """Test fonds euro : PS déjà prélevés"""
    contrat = ContratAV(
        date_ouverture="2010-01-01",
        versements=[VersementAV(date="2015-01-01", montant=100000)],
        valeur_actuelle=120000,
        type_fonds="euro",  # Fonds euro
    )
    profil = {"situation": "celibataire", "tmi": 0.30, "rfr": 50000}
    operation = {
        "contrat": contrat,
        "montant_brut": 40000,
        "gains": 8000,
        "date_rachat": "2024-01-01",
        "total_contrats_foyer": 120000,
        "abattement_deja_utilise": 0,
    }
    result = calculer_fiscalite_rachat(operation, profil)

    # PS déjà prélevés = 0
    assert result.prelevements_sociaux == pytest.approx(0.0)


def test_av_luxembourg_fiscalite_fr():
    """Test AV Luxembourg : fiscalité française identique"""
    contrat = ContratAV(
        date_ouverture="2010-01-01",
        versements=[VersementAV(date="2015-01-01", montant=100000)],
        valeur_actuelle=130000,
        type_fonds="uc",
        assureur_pays="luxembourg",
    )
    profil = {"situation": "celibataire", "tmi": 0.30, "rfr": 50000}
    operation = {
        "contrat": contrat,
        "montant_brut": 40000,
        "gains": 8000,
        "date_rachat": "2024-01-01",
        "total_contrats_foyer": 130000,
        "abattement_deja_utilise": 0,
    }
    result = calculer_fiscalite_rachat(operation, profil)

    # Même calcul que AV France
    assert result.total_impots > 0
    assert any("Luxembourg" in av for av in result.avertissements)
