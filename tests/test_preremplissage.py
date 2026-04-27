"""Tests S18-B — Module préremplissage."""

from __future__ import annotations

from src.preremplissage.deductions import (
    deduire_allocation_cible,
    deduire_esperance_vie,
    deduire_profil_risque,
    deduire_tmi,
)
from src.preremplissage.suggestions import (
    Suggestion,
    suggerer_allocation_cible,
    suggerer_esperance_vie,
    suggerer_profil_risque,
    suggerer_tmi,
)

# ─── Tests règle 1 : TMI ──────────────────────────────────────────────────────


class TestDeduireTmi:
    def test_revenu_nul_tmi_zero(self):
        assert deduire_tmi(0) == 0.0

    def test_revenu_negatif_tmi_zero(self):
        assert deduire_tmi(-1000) == 0.0

    def test_petit_revenu_tmi_zero_ou_11(self):
        # Revenu net 15 000€ → imposable 13 500 → > 11 294 → TMI 11%
        tmi = deduire_tmi(15_000)
        assert tmi in (0.0, 0.11)

    def test_revenu_moyen_tmi_30(self):
        # Revenu net 45 000€ → imposable 40 500 → TMI 30%
        tmi = deduire_tmi(45_000)
        assert tmi == 0.30

    def test_revenu_eleve_tmi_41(self):
        # Revenu net 120 000€ → imposable 108 000 → TMI 41%
        tmi = deduire_tmi(120_000)
        assert tmi == 0.41

    def test_revenu_tres_eleve_tmi_45(self):
        # Revenu net 250 000€ → imposable 225 000 → TMI 45%
        tmi = deduire_tmi(250_000)
        assert tmi == 0.45

    def test_couple_plus_favorable_que_celibataire(self):
        # Avec 2 parts, la TMI peut être inférieure
        tmi_cel = deduire_tmi(50_000, "celibataire", 0)
        tmi_couple = deduire_tmi(50_000, "couple", 0)
        # Le couple a 2 parts → quotient divisé par 2 → TMI ≤ tmi célibataire
        assert tmi_couple <= tmi_cel

    def test_enfants_peuvent_reduire_tmi(self):
        # 3 enfants = parts supplémentaires
        tmi_0 = deduire_tmi(80_000, "celibataire", 0)
        tmi_3 = deduire_tmi(80_000, "celibataire", 3)
        assert tmi_3 <= tmi_0

    def test_retourne_float(self):
        assert isinstance(deduire_tmi(50_000), float)


# ─── Tests règle 2 : Profil risque ───────────────────────────────────────────


class TestDeduireProfilRisque:
    def test_age_inferieur_30_dynamique(self):
        assert deduire_profil_risque(25) == "dynamique"

    def test_age_30_equilibre(self):
        assert deduire_profil_risque(30) == "equilibre"

    def test_age_40_equilibre(self):
        assert deduire_profil_risque(40) == "equilibre"

    def test_age_50_prudent(self):
        assert deduire_profil_risque(50) == "prudent"

    def test_age_60_prudent(self):
        assert deduire_profil_risque(60) == "prudent"

    def test_age_65_conservateur(self):
        assert deduire_profil_risque(65) == "conservateur"

    def test_age_70_conservateur(self):
        assert deduire_profil_risque(70) == "conservateur"

    def test_horizon_court_affine_vers_prudent(self):
        # Jeune (25 ans) mais horizon 3 ans → prudent max
        profil = deduire_profil_risque(25, horizon_annees=3)
        assert profil == "prudent"

    def test_horizon_tres_court_affine_vers_prudent(self):
        profil = deduire_profil_risque(35, horizon_annees=2)
        assert profil == "prudent"

    def test_horizon_long_ne_change_pas(self):
        # Horizon 20 ans → pas d'affinage vers prudent
        profil = deduire_profil_risque(25, horizon_annees=20)
        assert profil == "dynamique"

    def test_retourne_string(self):
        assert isinstance(deduire_profil_risque(40), str)

    def test_valeurs_valides(self):
        valides = {"dynamique", "equilibre", "prudent", "conservateur"}
        for age in [20, 35, 55, 70]:
            assert deduire_profil_risque(age) in valides


# ─── Tests règle 3 : Allocation cible ────────────────────────────────────────


class TestDeduireAllocationCible:
    def test_dynamique_actions_elevees(self):
        alloc = deduire_allocation_cible("dynamique")
        assert alloc["actions"] >= 0.70

    def test_conservateur_actions_faibles(self):
        alloc = deduire_allocation_cible("conservateur")
        assert alloc["actions"] <= 0.30

    def test_somme_proche_de_1(self):
        for profil in ["dynamique", "equilibre", "prudent", "conservateur"]:
            alloc = deduire_allocation_cible(profil)
            assert abs(sum(alloc.values()) - 1.0) < 0.01

    def test_horizon_court_reduit_actions(self):
        alloc_long = deduire_allocation_cible("dynamique", horizon_annees=20)
        alloc_court = deduire_allocation_cible("dynamique", horizon_annees=2)
        assert alloc_court["actions"] < alloc_long["actions"]

    def test_profil_inconnu_fallback_equilibre(self):
        alloc = deduire_allocation_cible("inconnu")
        alloc_eq = deduire_allocation_cible("equilibre")
        # Même résultat que équilibré
        assert alloc == alloc_eq

    def test_retourne_dict(self):
        assert isinstance(deduire_allocation_cible("equilibre"), dict)

    def test_valeurs_entre_0_et_1(self):
        for profil in ["dynamique", "equilibre", "prudent", "conservateur"]:
            alloc = deduire_allocation_cible(profil)
            for v in alloc.values():
                assert 0.0 <= v <= 1.0


# ─── Tests règle 4 : Espérance de vie ────────────────────────────────────────


class TestDeduireEsperanceVie:
    def test_homme_60_ans(self):
        ev = deduire_esperance_vie(60, "homme")
        assert 20 < ev < 30  # Environ 23.8 ans

    def test_femme_60_ans_superieure_homme(self):
        ev_h = deduire_esperance_vie(60, "homme")
        ev_f = deduire_esperance_vie(60, "femme")
        assert ev_f > ev_h

    def test_age_jeune_esperance_plus_haute(self):
        ev_30 = deduire_esperance_vie(30, "homme")
        ev_60 = deduire_esperance_vie(60, "homme")
        assert ev_30 > ev_60

    def test_age_hors_table_pas_erreur(self):
        ev = deduire_esperance_vie(5, "homme")
        assert ev > 0

    def test_age_tres_avance_pas_erreur(self):
        ev = deduire_esperance_vie(95, "femme")
        assert ev > 0

    def test_retourne_float(self):
        assert isinstance(deduire_esperance_vie(40, "homme"), float)

    def test_sexe_femme_ou_f_equivalent(self):
        assert deduire_esperance_vie(50, "femme") == deduire_esperance_vie(50, "f")


# ─── Tests API Suggestion ─────────────────────────────────────────────────────


class TestSuggestions:
    def test_suggerer_tmi_retourne_suggestion(self):
        s = suggerer_tmi(45_000)
        assert isinstance(s, Suggestion)
        assert s.cle == "tmi"
        assert s.modifiable is True
        assert "💡" in s.message
        assert "modifiable" in s.message

    def test_suggerer_profil_risque_retourne_suggestion(self):
        s = suggerer_profil_risque(40)
        assert isinstance(s, Suggestion)
        assert s.cle == "profil_risque"
        assert "💡" in s.message

    def test_suggerer_allocation_retourne_suggestion(self):
        s = suggerer_allocation_cible("equilibre")
        assert isinstance(s, Suggestion)
        assert s.cle == "allocation_cible"
        assert isinstance(s.valeur, dict)
        assert "💡" in s.message

    def test_suggerer_esperance_vie_retourne_suggestion(self):
        s = suggerer_esperance_vie(60, "homme")
        assert isinstance(s, Suggestion)
        assert s.cle == "esperance_vie"
        assert isinstance(s.valeur, float)
        assert "💡" in s.message

    def test_toutes_suggestions_sont_modifiables(self):
        suggestions = [
            suggerer_tmi(45_000),
            suggerer_profil_risque(40),
            suggerer_allocation_cible("equilibre"),
            suggerer_esperance_vie(50),
        ]
        for s in suggestions:
            assert s.modifiable is True
