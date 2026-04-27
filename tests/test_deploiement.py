"""Tests Sprint S15 Lot C — Plan de déploiement."""

from __future__ import annotations

from src.execution.deploiement import (
    _determiner_mode,
    _estimer_tmi,
    _generer_tranches,
    _sequence_enveloppes,
    plan_deploiement,
)

# ─── Tests _estimer_tmi ───────────────────────────────────────────────────────


class TestEstimerTMI:
    def test_revenu_faible_tmi_zero(self):
        assert _estimer_tmi(10_000) == 0.0

    def test_revenu_moyen_tmi_11(self):
        assert _estimer_tmi(20_000) == 0.11

    def test_revenu_cadre_tmi_30(self):
        assert _estimer_tmi(50_000) == 0.30

    def test_revenu_haut_tmi_41(self):
        assert _estimer_tmi(120_000) == 0.41

    def test_revenu_tres_haut_tmi_45(self):
        assert _estimer_tmi(200_000) == 0.45


# ─── Tests _determiner_mode ───────────────────────────────────────────────────


class TestDeterminerMode:
    def test_capital_faible_lump_sum(self):
        """Capital < 50k€ → lump sum."""
        mode, duree = _determiner_mode(40_000, "équilibré", 10)
        assert mode == "lump_sum"
        assert duree == 0

    def test_horizon_long_lump_sum(self):
        """Horizon > 15 ans → lump sum (même avec capital élevé et profil prudent)."""
        mode, duree = _determiner_mode(200_000, "prudent", 20)
        assert mode == "lump_sum"

    def test_capital_eleve_prudent_dca(self):
        """Capital ≥ 100k€ + profil prudent → DCA."""
        mode, duree = _determiner_mode(150_000, "prudent", 10)
        assert mode == "DCA"
        assert duree > 0

    def test_capital_eleve_equilibre_dca_ou_hybride(self):
        """Capital ≥ 100k€ + profil équilibré → DCA ou hybride."""
        mode, duree = _determiner_mode(120_000, "équilibré", 10)
        assert mode in ("DCA", "hybride")

    def test_mode_override_lump(self):
        """Override lump sum est respecté."""
        mode, duree = _determiner_mode(200_000, "prudent", 5, mode_override="lump")
        assert mode == "lump_sum"

    def test_mode_override_dca(self):
        """Override DCA est respecté."""
        mode, duree = _determiner_mode(30_000, "dynamique", 10, mode_override="dca")
        assert mode == "DCA"

    def test_mode_override_hybride(self):
        """Override hybride est respecté."""
        mode, duree = _determiner_mode(30_000, "dynamique", 10, mode_override="hybride")
        assert mode == "hybride"

    def test_duree_override(self):
        """La durée override est respectée."""
        mode, duree = _determiner_mode(200_000, "prudent", 10, duree_mois_override=9)
        assert duree == 9


# ─── Tests _sequence_enveloppes ───────────────────────────────────────────────


class TestSequenceEnveloppes:
    def test_pea_en_premier(self):
        """PEA doit être en première position si disponible."""
        seq = _sequence_enveloppes(["CTO", "PEA", "AV"])
        assert seq[0] == "PEA"

    def test_per_avant_cto_si_tmi_eleve(self):
        """PER avant CTO si TMI ≥ 30%."""
        seq = _sequence_enveloppes(["CTO", "PEA", "AV", "PER"], tmi=0.30)
        assert seq.index("PER") < seq.index("CTO")

    def test_cto_en_dernier(self):
        """CTO doit être en dernière position."""
        seq = _sequence_enveloppes(["PEA", "AV", "CTO", "PER"], tmi=0.30)
        assert seq[-1] == "CTO"

    def test_enveloppe_seule(self):
        """Une seule enveloppe → séquence à 1 élément."""
        seq = _sequence_enveloppes(["PEA"])
        assert seq == ["PEA"]

    def test_ordre_pea_per_av_cto_tmi_eleve(self):
        """Ordre attendu PEA → PER → AV → CTO avec TMI ≥ 30%."""
        seq = _sequence_enveloppes(["PEA", "AV", "CTO", "PER"], tmi=0.30)
        assert seq[0] == "PEA"
        assert "PER" in seq
        assert seq[-1] == "CTO"


# ─── Tests _generer_tranches ──────────────────────────────────────────────────


class TestGenererTranches:
    def test_lump_sum_tranche_unique_par_env(self):
        """Lump sum → une tranche par enveloppe, toutes au mois 0."""
        tranches = _generer_tranches(100_000, "lump_sum", 0, ["PEA", "CTO"])
        assert all(t["mois"] == 0 for t in tranches)
        assert len(tranches) == 2

    def test_lump_sum_montant_total(self):
        """La somme des tranches = capital total."""
        capital = 100_000.0
        tranches = _generer_tranches(capital, "lump_sum", 0, ["PEA", "AV", "CTO"])
        total = sum(t["montant_eur"] for t in tranches)
        assert abs(total - capital) < 1.0

    def test_dca_etalement_correct(self):
        """DCA sur 6 mois avec 1 enveloppe → 6 tranches."""
        tranches = _generer_tranches(60_000, "DCA", 6, ["PEA"])
        assert len(tranches) == 6
        mois_uniques = sorted({t["mois"] for t in tranches})
        assert mois_uniques == list(range(6))

    def test_dca_montant_total(self):
        """La somme des tranches DCA = capital total."""
        capital = 120_000.0
        tranches = _generer_tranches(capital, "DCA", 12, ["PEA", "CTO"])
        total = sum(t["montant_eur"] for t in tranches)
        assert abs(total - capital) < 1.0

    def test_hybride_premiere_tranche_lump(self):
        """Mode hybride : la première tranche (mois 0) = 50% du capital."""
        capital = 100_000.0
        tranches = _generer_tranches(capital, "hybride", 6, ["PEA"])
        lump_tranches = [t for t in tranches if t["mois"] == 0]
        total_lump = sum(t["montant_eur"] for t in lump_tranches)
        assert abs(total_lump - capital * 0.5) < 1.0

    def test_hybride_montant_total(self):
        """La somme des tranches hybride = capital total."""
        capital = 200_000.0
        tranches = _generer_tranches(capital, "hybride", 6, ["PEA", "AV"])
        total = sum(t["montant_eur"] for t in tranches)
        assert abs(total - capital) < 1.0

    def test_tranches_ont_justification(self):
        """Chaque tranche a une justification."""
        tranches = _generer_tranches(50_000, "DCA", 3, ["PEA"])
        for t in tranches:
            assert "justification" in t
            assert len(t["justification"]) > 0


# ─── Tests plan_deploiement ───────────────────────────────────────────────────


class TestPlanDeploiement:
    def test_structure_resultat(self):
        result = plan_deploiement(
            capital_total=80_000,
            profil="équilibré",
            horizon_annees=15,
            age=40,
            rfr=60_000,
            enveloppes_disponibles=["PEA", "CTO"],
        )
        assert "mode" in result
        assert "duree_mois" in result
        assert "sequence_enveloppes" in result
        assert "tranches" in result

    def test_pea_premier_dans_sequence(self):
        result = plan_deploiement(
            capital_total=100_000,
            profil="équilibré",
            horizon_annees=10,
            age=35,
            rfr=70_000,
            enveloppes_disponibles=["CTO", "PEA", "AV"],
        )
        seq = result["sequence_enveloppes"]
        assert seq[0] == "PEA"

    def test_override_mode_respecte(self):
        result = plan_deploiement(
            capital_total=200_000,
            profil="prudent",
            horizon_annees=10,
            age=50,
            rfr=100_000,
            enveloppes_disponibles=["PEA", "CTO"],
            mode_override="lump_sum",
        )
        assert result["mode"] == "lump_sum"

    def test_tranches_non_vides(self):
        result = plan_deploiement(
            capital_total=50_000,
            profil="dynamique",
            horizon_annees=20,
            age=30,
            rfr=40_000,
            enveloppes_disponibles=["PEA"],
        )
        assert len(result["tranches"]) > 0

    def test_per_prioritaire_tmi_eleve(self):
        """PER avant CTO si RFR élevé (TMI ≥ 30%)."""
        result = plan_deploiement(
            capital_total=150_000,
            profil="équilibré",
            horizon_annees=10,
            age=45,
            rfr=80_000,  # TMI 30%
            enveloppes_disponibles=["CTO", "PEA", "PER", "AV"],
        )
        seq = result["sequence_enveloppes"]
        # PEA en premier
        assert seq[0] == "PEA"
        # PER avant CTO
        assert seq.index("PER") < seq.index("CTO")
