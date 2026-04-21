# -*- coding: utf-8 -*-
"""
Tests unitaires — Module de fiscalité France 2026.
Teste les fonctions de calcul PFU, CEHR, CDHR, IS, mark-to-market et contrat capitalisation.

Lancement : pytest tests/test_fiscalite.py -v
"""

import pytest
from src.fiscalite import (
    calculer_pfu,
    calculer_cehr,
    calculer_cdhr,
    calculer_is,
    calculer_mark_to_market_is,
    calculer_base_taxable_contrat_cap_is,
    calculer_taux_effectif,
)


# ---------------------------------------------------------------------------
# Tests PFU — Prélèvement Forfaitaire Unique
# ---------------------------------------------------------------------------

class TestPFU:
    """Tests du calcul du Prélèvement Forfaitaire Unique (Flat Tax 31.4%)."""

    def test_pfu_10000(self):
        """PFU sur 10 000 € de plus-value doit être 3 140 €.

        PFU = 31.4 % = 12.8 % IR + 18.6 % PS.
        Référence : art. 200 A CGI.
        """
        resultat = calculer_pfu(10000)
        assert resultat == 3140.0, f"PFU attendu : 3140.0 €, obtenu : {resultat} €"

    def test_pfu_zero(self):
        """PFU sur 0 € doit être 0 €."""
        assert calculer_pfu(0) == 0.0

    def test_pfu_100000(self):
        """PFU sur 100 000 € doit être 31 400 €."""
        assert calculer_pfu(100000) == 31400.0

    def test_pfu_taux_personnalise(self):
        """PFU avec taux personnalisé de 25 % sur 10 000 € doit être 2 500 €."""
        assert calculer_pfu(10000, taux_pfu=0.25) == 2500.0

    def test_pfu_valeur_negative_leve_erreur(self):
        """PFU sur valeur négative doit lever ValueError."""
        with pytest.raises(ValueError):
            calculer_pfu(-1000)

    def test_pfu_precision_decimales(self):
        """PFU sur 1 000.50 € doit être calculé avec précision."""
        resultat = calculer_pfu(1000.50)
        assert resultat == pytest.approx(314.157, abs=0.01)


# ---------------------------------------------------------------------------
# Tests CEHR — Contribution Exceptionnelle sur les Hauts Revenus
# ---------------------------------------------------------------------------

class TestCEHR:
    """Tests du calcul CEHR (art. 223 sexies CGI)."""

    def test_cehr_600000_celibataire(self):
        """CEHR pour RFR 600 000 € (célibataire) = 11 500 €.

        Calcul :
        - Tranche 3 % : (500 000 - 250 000) × 3 % = 250 000 × 0.03 = 7 500 €
        - Tranche 4 % : (600 000 - 500 000) × 4 % = 100 000 × 0.04 = 4 000 €
        - Total : 7 500 + 4 000 = 11 500 €
        """
        resultat = calculer_cehr(600000, "celibataire")
        assert resultat == 11500.0, f"CEHR attendu : 11 500 €, obtenu : {resultat} €"

    def test_cehr_sous_seuil_celibataire(self):
        """Pas de CEHR si RFR ≤ 250 000 € (célibataire)."""
        assert calculer_cehr(250000, "celibataire") == 0.0
        assert calculer_cehr(100000, "celibataire") == 0.0

    def test_cehr_seuil_exact_250k(self):
        """Pas de CEHR si RFR exactement à 250 000 € (seuil non inclus)."""
        assert calculer_cehr(250000, "celibataire") == 0.0

    def test_cehr_tranche1_seulement(self):
        """CEHR uniquement tranche 3 % si RFR entre 250k et 500k.

        RFR = 350 000 € : (350 000 - 250 000) × 3 % = 100 000 × 0.03 = 3 000 €
        """
        assert calculer_cehr(350000, "celibataire") == 3000.0

    def test_cehr_tranche2_seulement(self):
        """CEHR tranche 1 + tranche 2 pour RFR > 500k.

        RFR = 500 001 € : 250 000 × 3 % + 1 × 4 % ≈ 7 500 + 0.04 = 7 500.04 €
        """
        assert calculer_cehr(500001, "celibataire") == pytest.approx(7500.04, abs=0.01)

    def test_cehr_couple_sous_seuil(self):
        """Pas de CEHR pour un couple si RFR ≤ 500 000 €."""
        assert calculer_cehr(500000, "couple") == 0.0

    def test_cehr_couple_600k(self):
        """CEHR pour couple avec RFR 600 000 € = 3 000 €.

        (600 000 - 500 000) × 3 % = 100 000 × 0.03 = 3 000 €
        """
        assert calculer_cehr(600000, "couple") == 3000.0

    def test_cehr_couple_1200000(self):
        """CEHR pour couple RFR 1 200 000 € = (500k×3%) + (200k×4%) = 15k + 8k = 23k €."""
        assert calculer_cehr(1200000, "couple") == 23000.0

    def test_cehr_situation_invalide(self):
        """Situation familiale invalide doit lever ValueError."""
        with pytest.raises(ValueError):
            calculer_cehr(600000, "inconnu")


# ---------------------------------------------------------------------------
# Tests CDHR — Contribution Différentielle sur les Hauts Revenus
# ---------------------------------------------------------------------------

class TestCDHR:
    """Tests du calcul CDHR (LF 2025 art. 3 — À VALIDER reconduite 2026)."""

    def test_cdhr_plancher_20pct(self):
        """CDHR garantit un taux effectif minimal de 20 % pour RFR > 250k€.

        RFR = 300 000 €, impôt = 40 000 € → taux = 13.3 % < 20 %
        CDHR = 300 000 × 20 % - 40 000 = 60 000 - 40 000 = 20 000 €
        """
        resultat = calculer_cdhr(300000, 40000, "celibataire")
        assert resultat == 20000.0, f"CDHR attendu : 20 000 €, obtenu : {resultat} €"

    def test_cdhr_taux_deja_superieur(self):
        """Pas de CDHR si le taux effectif est déjà supérieur à 20 %.

        RFR = 300 000 €, impôt = 70 000 € → taux = 23.3 % > 20 % → CDHR = 0 €
        """
        assert calculer_cdhr(300000, 70000, "celibataire") == 0.0

    def test_cdhr_sous_seuil(self):
        """Pas de CDHR si RFR ≤ 250 000 € (célibataire)."""
        assert calculer_cdhr(200000, 30000, "celibataire") == 0.0

    def test_cdhr_seuil_exact_250k(self):
        """Pas de CDHR pour RFR exactement 250 000 €."""
        assert calculer_cdhr(250000, 40000, "celibataire") == 0.0

    def test_cdhr_taux_exactement_20pct(self):
        """Pas de CDHR si le taux effectif est exactement 20 %.

        RFR = 300 000 €, impôt = 60 000 € → taux = 20 % exact → CDHR = 0 €
        """
        assert calculer_cdhr(300000, 60000, "celibataire") == 0.0

    def test_cdhr_couple(self):
        """CDHR pour couple avec RFR 600 000 € et impôt faible.

        Seuil couple = 500 000 €
        Impôt minimal = 600 000 × 20 % = 120 000 €
        CDHR = 120 000 - 50 000 = 70 000 €
        """
        resultat = calculer_cdhr(600000, 50000, "couple")
        assert resultat == 70000.0


# ---------------------------------------------------------------------------
# Tests IS — Impôt sur les Sociétés
# ---------------------------------------------------------------------------

class TestIS:
    """Tests du calcul de l'Impôt sur les Sociétés (art. 219 CGI)."""

    def test_is_50000(self):
        """IS sur 50 000 € de bénéfice doit être 8 250 €.

        Calcul :
        - Taux réduit 15 % sur 42 500 € = 6 375 €
        - Taux normal 25 % sur (50 000 - 42 500) = 7 500 € = 1 875 €
        - Total : 6 375 + 1 875 = 8 250 €
        Source : art. 219 I b CGI, LF 2024 (relèvement à 42 500 €)
        """
        resultat = calculer_is(50000)
        assert resultat == 8250.0, f"IS attendu : 8 250 €, obtenu : {resultat} €"

    def test_is_42500_plafond_taux_reduit(self):
        """IS sur 42 500 € = 15 % × 42 500 = 6 375 €."""
        assert calculer_is(42500) == 6375.0

    def test_is_sous_plafond(self):
        """IS sur 20 000 € = 15 % × 20 000 = 3 000 €."""
        assert calculer_is(20000) == 3000.0

    def test_is_benefice_nul(self):
        """IS sur bénéfice nul = 0 €."""
        assert calculer_is(0) == 0.0

    def test_is_deficit(self):
        """IS sur déficit (bénéfice négatif) = 0 € (report déficitaire)."""
        assert calculer_is(-10000) == 0.0

    def test_is_100000(self):
        """IS sur 100 000 € = 15%×42500 + 25%×57500 = 6375 + 14375 = 20750 €."""
        assert calculer_is(100000) == 20750.0

    def test_is_taux_personnalises(self):
        """IS avec taux personnalisés."""
        resultat = calculer_is(100000, seuil_taux_reduit=50000, taux_reduit=0.10, taux_normal=0.20)
        assert resultat == 50000 * 0.10 + 50000 * 0.20
        assert resultat == 15000.0


# ---------------------------------------------------------------------------
# Tests Mark-to-Market IS — art. 209-0 A CGI
# ---------------------------------------------------------------------------

class TestMarkToMarketIS:
    """Tests du calcul mark-to-market IS (piège ETF en CTO société)."""

    def test_mark_to_market_5pct(self):
        """Hausse de 5 % sur 100 000 € = 5 000 € de base imposable.

        MÊME SANS CESSION — art. 209-0 A CGI oblige à taxer la plus-value latente.
        """
        resultat = calculer_mark_to_market_is(100000, 105000)
        assert resultat["base_imposable"] == 5000.0, (
            f"Base imposable attendue : 5 000 €, obtenu : {resultat['base_imposable']} €"
        )

    def test_mark_to_market_is_du(self):
        """IS dû sur gain latent de 5 000 € au taux normal 25 % = 1 250 €."""
        resultat = calculer_mark_to_market_is(100000, 105000)
        assert resultat["is_du"] == 1250.0

    def test_mark_to_market_perte(self):
        """Perte latente de 3 000 € → base imposable négative, IS nul."""
        resultat = calculer_mark_to_market_is(100000, 97000)
        assert resultat["base_imposable"] == -3000.0
        assert resultat["is_du"] == 0.0

    def test_mark_to_market_neutre(self):
        """Valeur stable → base imposable nulle, IS nul."""
        resultat = calculer_mark_to_market_is(100000, 100000)
        assert resultat["base_imposable"] == 0.0
        assert resultat["is_du"] == 0.0

    def test_mark_to_market_taux_personnalise(self):
        """IS mark-to-market avec taux IS personnalisé."""
        resultat = calculer_mark_to_market_is(100000, 115000, taux_is=0.15)
        assert resultat["base_imposable"] == 15000.0
        assert resultat["is_du"] == 2250.0


# ---------------------------------------------------------------------------
# Tests Contrat Capitalisation IS — art. 38 sexdecies GB Ann. III CGI
# ---------------------------------------------------------------------------

class TestContratCapitalisationIS:
    """Tests du calcul de la base forfaitaire du contrat de capitalisation IS."""

    def test_contrat_cap_is_base(self):
        """Prime 100 000 €, TME 3 % → base = 105 % × 3 % × 100 000 = 3 150 €.

        Formule réglementaire : base = 105 % × TME × prime nette.
        Source : art. 38 sexdecies GB Ann. III CGI.
        """
        resultat = calculer_base_taxable_contrat_cap_is(100000, 0.03)
        assert resultat["base_imposable_annuelle"] == 3150.0, (
            f"Base attendue : 3 150 €, obtenu : {resultat['base_imposable_annuelle']} €"
        )

    def test_contrat_cap_is_tme_eleve(self):
        """Base avec TME 5 % sur 200 000 € = 105 % × 5 % × 200 000 = 10 500 €."""
        resultat = calculer_base_taxable_contrat_cap_is(200000, 0.05)
        assert resultat["base_imposable_annuelle"] == 10500.0

    def test_contrat_cap_is_est_du(self):
        """IS estimé sur base 3 150 € au taux 25 % = 787.5 €."""
        resultat = calculer_base_taxable_contrat_cap_is(100000, 0.03)
        assert resultat["is_estime"] == pytest.approx(787.5, abs=0.01)

    def test_contrat_cap_vs_mark_to_market(self):
        """La base forfaitaire est bien inférieure au mark-to-market en cas de gains élevés.

        Scénario : 100 000 € avec +10 % de performance.
        Mark-to-market : base = 10 000 €
        Contrat capitalisation : base = 3 150 € (avec TME 3 %)
        → Avantage fiscal significatif du contrat capitalisation.
        """
        base_mtm = calculer_mark_to_market_is(100000, 110000)["base_imposable"]
        base_cap = calculer_base_taxable_contrat_cap_is(100000, 0.03)["base_imposable_annuelle"]
        assert base_cap < base_mtm, "La base forfaitaire doit être inférieure au mark-to-market"
        assert base_cap == 3150.0
        assert base_mtm == 10000.0


# ---------------------------------------------------------------------------
# Tests Taux Effectif
# ---------------------------------------------------------------------------

class TestTauxEffectif:
    """Tests du calcul du taux effectif d'imposition."""

    def test_taux_effectif_normal(self):
        """Taux effectif 40 000 € / 300 000 € ≈ 13.33 %."""
        taux = calculer_taux_effectif(40000, 300000)
        assert taux == pytest.approx(0.1333, abs=0.001)

    def test_taux_effectif_zero(self):
        """Taux effectif nul si impôt nul."""
        assert calculer_taux_effectif(0, 100000) == 0.0

    def test_taux_effectif_revenu_nul_leve_erreur(self):
        """Revenu nul doit lever ValueError."""
        with pytest.raises(ValueError):
            calculer_taux_effectif(1000, 0)


# ---------------------------------------------------------------------------
# Tests d'intégration — cohérence globale
# ---------------------------------------------------------------------------

class TestIntegration:
    """Tests d'intégration vérifiant la cohérence des calculs fiscaux."""

    def test_pfu_inferieur_bareme_hauts_revenus(self):
        """Pour un contribuable à TMI 41 %, le PFU à 31.4 % est plus avantageux
        que le barème en l'absence de CDHR/CEHR."""
        pfu = calculer_pfu(10000)  # 3 140 €
        bareme_approximatif = 10000 * 0.41 + 10000 * 0.172  # 5 820 €
        assert pfu < bareme_approximatif

    def test_is_plus_bas_que_pfu(self):
        """Pour une PME, l'IS 15 % est plus bas que le PFU 31.4 % (en direct).

        Mais attention : l'IS en société + dividendes = IS + PS/PFU cumulés.
        """
        is_taux_reduit = calculer_is(10000) / 10000  # ≈ 15 %
        assert is_taux_reduit < 0.314

    def test_cumul_cehr_pfu_600k(self):
        """Pour un célibataire avec 600 000 € de RFR dont 10 000 € de PV mobilières.

        Impôt total approximatif = PFU 3 140 € + CEHR 11 500 € = 14 640 €
        """
        pfu = calculer_pfu(10000)
        cehr = calculer_cehr(600000, "celibataire")
        total = pfu + cehr
        assert total == 14640.0
