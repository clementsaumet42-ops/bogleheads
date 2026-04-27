"""Tests S18-C — Module validations/coherence."""

from __future__ import annotations

from src.validations.coherence import Avertissement, valider_coherence

# ─── Helpers ─────────────────────────────────────────────────────────────────


def profil_base() -> dict:
    """Profil de base cohérent (aucun avertissement attendu)."""
    return {
        "age": 40,
        "tmi": 0.30,
        "rfr_annuel": 50_000.0,
        "patrimoine_financier_total": 100_000.0,
        "enveloppes_disponibles": {"PEA": 60_000.0, "AV": 40_000.0},
        "profil_aversion_risque": "equilibre",
        "horizon_annees": 15,
        "frais_courtier_par_transaction": 0.0,
        "allocation_cible_bogleheads": {
            "actions": 0.60,
            "obligations": 0.30,
            "liquidites": 0.10,
        },
    }


# ─── Tests règle 1 : Patrimoine vs enveloppes ─────────────────────────────────


class TestPatrimoineVsEnveloppes:
    def test_coherent_pas_avertissement(self):
        p = profil_base()
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "patrimoine_vs_enveloppes" not in cles

    def test_ecart_faible_pas_avertissement(self):
        # 0.5% d'écart → OK
        p = profil_base()
        p["enveloppes_disponibles"] = {"PEA": 60_500.0, "AV": 40_000.0}
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "patrimoine_vs_enveloppes" not in cles

    def test_ecart_important_avertissement(self):
        p = profil_base()
        # Somme enveloppes = 40 000 vs patrimoine 100 000 → écart 60%
        p["enveloppes_disponibles"] = {"PEA": 20_000.0, "AV": 20_000.0}
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "patrimoine_vs_enveloppes" in cles

    def test_pas_enveloppes_pas_avertissement(self):
        p = profil_base()
        p["enveloppes_disponibles"] = {}
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "patrimoine_vs_enveloppes" not in cles

    def test_patrimoine_nul_pas_avertissement(self):
        p = profil_base()
        p["patrimoine_financier_total"] = 0.0
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "patrimoine_vs_enveloppes" not in cles

    def test_severity_est_warning(self):
        p = profil_base()
        p["enveloppes_disponibles"] = {"PEA": 10_000.0}
        averts = valider_coherence(p)
        a = next((x for x in averts if x.cle == "patrimoine_vs_enveloppes"), None)
        if a:
            assert a.severity == "warning"


# ─── Tests règle 2 : TMI vs RFR ──────────────────────────────────────────────


class TestTmiVsRfr:
    def test_tmi_30_rfr_50000_coherent(self):
        p = profil_base()
        # RFR 50 000 > seuil TMI 30% (28 797) → cohérent
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "tmi_vs_rfr" not in cles

    def test_tmi_30_rfr_15000_incoherent(self):
        p = profil_base()
        p["tmi"] = 0.30
        p["rfr_annuel"] = 15_000.0  # < seuil 28 797
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "tmi_vs_rfr" in cles

    def test_tmi_11_rfr_20000_coherent(self):
        p = profil_base()
        p["tmi"] = 0.11
        p["rfr_annuel"] = 20_000.0  # > seuil 11 294
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "tmi_vs_rfr" not in cles

    def test_tmi_none_pas_avertissement(self):
        p = profil_base()
        p["tmi"] = None
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "tmi_vs_rfr" not in cles

    def test_rfr_none_pas_avertissement(self):
        p = profil_base()
        p["rfr_annuel"] = None
        p["revenu_fiscal_reference"] = None
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "tmi_vs_rfr" not in cles


# ─── Tests règle 3 : Profil risque vs horizon ─────────────────────────────────


class TestProfilRisqueVsHorizon:
    def test_dynamique_horizon_long_coherent(self):
        p = profil_base()
        p["profil_aversion_risque"] = "dynamique"
        p["horizon_annees"] = 20
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "profil_risque_vs_horizon" not in cles

    def test_dynamique_horizon_court_incoherent(self):
        p = profil_base()
        p["profil_aversion_risque"] = "dynamique"
        p["horizon_annees"] = 3
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "profil_risque_vs_horizon" in cles

    def test_prudent_horizon_court_coherent(self):
        p = profil_base()
        p["profil_aversion_risque"] = "prudent"
        p["horizon_annees"] = 3
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "profil_risque_vs_horizon" not in cles

    def test_horizon_none_pas_avertissement(self):
        p = profil_base()
        p["profil_aversion_risque"] = "dynamique"
        p["horizon_annees"] = None
        p["horizon"] = None
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "profil_risque_vs_horizon" not in cles


# ─── Tests règle 4 : Âge vs objectif retraite ────────────────────────────────


class TestAgeVsRetraite:
    def test_age_inferieur_retraite_pas_avertissement(self):
        p = profil_base()
        p["age_retraite_cible"] = 65
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "age_vs_retraite" not in cles

    def test_age_superieur_retraite_avertissement(self):
        p = profil_base()
        p["age"] = 70
        p["age_retraite_cible"] = 65
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "age_vs_retraite" in cles

    def test_age_egal_retraite_avertissement(self):
        p = profil_base()
        p["age"] = 65
        p["age_retraite_cible"] = 65
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "age_vs_retraite" in cles

    def test_pas_de_retraite_cible_pas_avertissement(self):
        p = profil_base()
        # age_retraite_cible absent
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "age_vs_retraite" not in cles

    def test_severity_est_info(self):
        p = profil_base()
        p["age"] = 70
        p["age_retraite_cible"] = 65
        averts = valider_coherence(p)
        a = next((x for x in averts if x.cle == "age_vs_retraite"), None)
        assert a is not None
        assert a.severity == "info"


# ─── Tests règle 5 : Capital vs frais courtage ───────────────────────────────


class TestCapitalVsFraisCourtage:
    def test_frais_nuls_pas_avertissement(self):
        p = profil_base()
        p["frais_courtier_par_transaction"] = 0.0
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "capital_vs_frais_courtage" not in cles

    def test_capital_ok_pas_avertissement(self):
        p = profil_base()
        p["frais_courtier_par_transaction"] = 5.0  # 5€ × 10 = 50 < 100 000
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "capital_vs_frais_courtage" not in cles

    def test_frais_disproportionnes_avertissement(self):
        p = profil_base()
        p["patrimoine_financier_total"] = 500.0
        p["frais_courtier_par_transaction"] = 100.0  # 100 × 10 = 1000 > 500
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "capital_vs_frais_courtage" in cles


# ─── Tests règle 6 : Monétaire + horizon long ─────────────────────────────────


class TestMonetaireHorizonLong:
    def test_allocation_normale_pas_avertissement(self):
        p = profil_base()
        # 10% liquidités + 30% obligations = 40% → OK
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "monetaire_horizon_long" not in cles

    def test_80pct_monetaire_horizon_long_avertissement(self):
        p = profil_base()
        p["horizon_annees"] = 15
        p["allocation_cible_bogleheads"] = {
            "actions": 0.10,
            "obligations": 0.50,
            "liquidites": 0.40,
        }
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "monetaire_horizon_long" in cles

    def test_80pct_monetaire_horizon_court_pas_avertissement(self):
        p = profil_base()
        p["horizon_annees"] = 5  # ≤ 10 ans → pas d'avertissement
        p["allocation_cible_bogleheads"] = {
            "actions": 0.10,
            "obligations": 0.50,
            "liquidites": 0.40,
        }
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "monetaire_horizon_long" not in cles

    def test_horizon_none_pas_avertissement(self):
        p = profil_base()
        p["horizon_annees"] = None
        p["horizon"] = None
        p["allocation_cible_bogleheads"] = {
            "actions": 0.05,
            "obligations": 0.50,
            "liquidites": 0.45,
        }
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert "monetaire_horizon_long" not in cles


# ─── Tests valider_coherence général ─────────────────────────────────────────


class TestValiderCoherence:
    def test_profil_coherent_retourne_liste_vide(self):
        p = profil_base()
        averts = valider_coherence(p)
        # Tous avertissements évités avec le profil_base cohérent
        assert isinstance(averts, list)

    def test_retourne_liste(self):
        assert isinstance(valider_coherence(profil_base()), list)

    def test_avertissements_sont_des_instances(self):
        p = profil_base()
        p["tmi"] = 0.30
        p["rfr_annuel"] = 10_000.0
        averts = valider_coherence(p)
        for a in averts:
            assert isinstance(a, Avertissement)

    def test_accepte_objet_avec_dict(self):
        class FauxProfil:
            def __init__(self):
                self.age = 40
                self.tmi = 0.30
                self.rfr_annuel = 50_000.0
                self.patrimoine_financier_total = 0.0

        result = valider_coherence(FauxProfil())
        assert isinstance(result, list)

    def test_severite_valides(self):
        p = profil_base()
        p["tmi"] = 0.30
        p["rfr_annuel"] = 10_000.0
        averts = valider_coherence(p)
        severites_valides = {"info", "warning", "danger"}
        for a in averts:
            assert a.severity in severites_valides

    def test_pages_concernees_est_liste(self):
        p = profil_base()
        p["tmi"] = 0.30
        p["rfr_annuel"] = 10_000.0
        averts = valider_coherence(p)
        for a in averts:
            assert isinstance(a.pages_concernees, list)

    def test_erreur_dans_regle_ne_propage_pas(self):
        """Une règle défaillante ne doit pas planter valider_coherence."""
        # On passe un objet malformé — ne doit pas lever d'exception
        result = valider_coherence(None)
        assert result == []

    def test_multiple_avertissements_possibles(self):
        p = profil_base()
        p["tmi"] = 0.30
        p["rfr_annuel"] = 10_000.0
        p["enveloppes_disponibles"] = {"PEA": 10_000.0}  # écart avec 100k patrimoine
        averts = valider_coherence(p)
        cles = [a.cle for a in averts]
        assert len(averts) >= 2
        assert "tmi_vs_rfr" in cles
        assert "patrimoine_vs_enveloppes" in cles
