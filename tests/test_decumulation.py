"""Tests moteur de decumulation fiscal-optimal.

Couvre :
- Regles fiscales par enveloppe (PEA, AV, CTO, PER, PEE)
- Optimiseur d'ordre de retrait (priorite enveloppes peu taxees)
- Simulateur multi-annees
"""

from __future__ import annotations

import pytest

from src.decumulation.optimiseur_retraits import (
    EnveloppeDecumulation,
    optimiser_retraits_annuels,
)
from src.decumulation.regles_enveloppes import (
    ContexteFiscal,
    cout_marginal_retrait,
    fiscalite_retrait,
    fiscalite_retrait_av,
    fiscalite_retrait_cto,
    fiscalite_retrait_pea,
    fiscalite_retrait_pee,
    fiscalite_retrait_per_capital,
)
from src.decumulation.simulateur_annuel import simuler_decumulation

# ── Tests regles PEA ──────────────────────────────────────────────────────


def test_pea_apres_5_ans_pas_d_ir():
    res = fiscalite_retrait_pea(
        montant_brut=10_000,
        ratio_pv=0.30,
        duree_detention_ans=10,
    )
    assert res["ir"] == 0.0
    # PS = 17.2% de la PV (3000 €) = 516 € (taux PS configure)
    assert res["ps"] > 0
    assert res["taux_effectif"] < 0.10  # tres favorable


def test_pea_avant_2_ans_taxe_au_tmi():
    res = fiscalite_retrait_pea(
        montant_brut=10_000,
        ratio_pv=0.30,
        duree_detention_ans=1,
        tmi=0.41,
    )
    pv = 3_000
    assert res["ir"] == pytest.approx(pv * 0.41)


def test_pea_2_a_5_ans_pfu():
    res = fiscalite_retrait_pea(
        montant_brut=10_000,
        ratio_pv=0.30,
        duree_detention_ans=3,
    )
    pv = 3_000
    assert res["ir"] == pytest.approx(pv * 0.128)


# ── Tests regles AV ───────────────────────────────────────────────────────


def test_av_8_ans_dans_abattement_zero_ir():
    """Petit retrait AV > 8 ans dans la limite de l'abattement : 0 IR."""
    contexte = ContexteFiscal(situation="celibataire", encours_av_total_foyer=100_000)
    res = fiscalite_retrait_av(
        montant_brut=15_000,
        ratio_pv=0.20,  # PV = 3000 € < abattement 4600 €
        duree_detention_ans=10,
        contexte=contexte,
    )
    assert res["ir"] == 0.0
    assert res["abattement_utilise"] == pytest.approx(3_000)


def test_av_8_ans_au_dela_abattement_taxe_a_7_5():
    """Retrait AV > 8 ans au-dela abattement, encours < 150k : PFL 7.5%."""
    contexte = ContexteFiscal(situation="celibataire", encours_av_total_foyer=100_000)
    res = fiscalite_retrait_av(
        montant_brut=50_000,
        ratio_pv=0.30,  # PV = 15000 €
        duree_detention_ans=10,
        contexte=contexte,
        versements_avant_2017_ratio=0.0,  # tous post-2017
    )
    # PV imposable = 15000 - 4600 = 10400 €. PFL 7.5% = 780 €.
    assert res["abattement_utilise"] == pytest.approx(4_600)
    assert res["ir"] == pytest.approx((15_000 - 4_600) * 0.075, rel=0.05)


def test_av_8_ans_encours_eleve_taxe_a_12_8():
    """Retrait AV > 8 ans, encours > 150k : PFU 12.8% sur la part hors abattement."""
    contexte = ContexteFiscal(situation="celibataire", encours_av_total_foyer=400_000)
    res = fiscalite_retrait_av(
        montant_brut=50_000,
        ratio_pv=0.30,
        duree_detention_ans=10,
        contexte=contexte,
        versements_avant_2017_ratio=0.0,
    )
    pv_imposable = 15_000 - 4_600
    assert res["ir"] == pytest.approx(pv_imposable * 0.128, rel=0.05)


def test_av_couple_abattement_double():
    contexte = ContexteFiscal(situation="couple", encours_av_total_foyer=100_000)
    res = fiscalite_retrait_av(
        montant_brut=30_000,
        ratio_pv=0.30,  # PV = 9000 €, exactement abattement couple
        duree_detention_ans=10,
        contexte=contexte,
    )
    assert res["abattement_utilise"] == pytest.approx(9_000)
    assert res["ir"] == 0.0


def test_av_moins_4_ans_pas_d_abattement():
    contexte = ContexteFiscal(situation="celibataire")
    res = fiscalite_retrait_av(
        montant_brut=20_000,
        ratio_pv=0.30,
        duree_detention_ans=2,
        contexte=contexte,
    )
    pv = 6_000
    assert res["abattement_utilise"] == 0.0
    assert res["ir"] == pytest.approx(pv * 0.128)


# ── Tests regles CTO et PER ───────────────────────────────────────────────


def test_cto_pfu_30():
    res = fiscalite_retrait_cto(montant_brut=10_000, ratio_pv=0.40)
    pv = 4_000
    assert res["ir"] == pytest.approx(pv * 0.128)
    assert res["ps"] > 0


def test_per_capital_versements_deduits_taxe_au_tmi():
    """Sortie PER capital, versements deduits : TMI sur capital + PFU sur PV."""
    res = fiscalite_retrait_per_capital(
        montant_brut=10_000,
        ratio_pv=0.30,
        versements_deduits_ratio=1.0,  # tous deduits
        tmi=0.30,
    )
    capital = 7_000
    pv = 3_000
    expected_ir = capital * 0.30 + pv * 0.128
    assert res["ir"] == pytest.approx(expected_ir, rel=0.01)


def test_per_capital_non_deduit_seulement_pv_taxe():
    res = fiscalite_retrait_per_capital(
        montant_brut=10_000,
        ratio_pv=0.30,
        versements_deduits_ratio=0.0,
        tmi=0.30,
    )
    pv = 3_000
    assert res["ir"] == pytest.approx(pv * 0.128, rel=0.01)


def test_pee_debloque_zero_ir():
    res = fiscalite_retrait_pee(montant_brut=10_000, ratio_pv=0.40, debloque=True)
    assert res["ir"] == 0.0
    assert res["ps"] > 0


def test_pee_non_debloque_renvoie_zero():
    res = fiscalite_retrait_pee(montant_brut=10_000, ratio_pv=0.40, debloque=False)
    assert res["net"] == 0.0


# ── Tests dispatcher ──────────────────────────────────────────────────────


def test_dispatcher_pea():
    contexte = ContexteFiscal(tmi=0.30)
    res = fiscalite_retrait("PEA", 10_000, 0.30, contexte, duree_detention_ans=10)
    assert res["ir"] == 0.0


def test_dispatcher_inconnu_leve_erreur():
    contexte = ContexteFiscal()
    with pytest.raises(ValueError, match="inconnu"):
        fiscalite_retrait("CRYPTO", 10_000, 0.30, contexte)


# ── Tests optimiseur ──────────────────────────────────────────────────────


def _enveloppes_typiques():
    """Patrimoine type retraite : PEA mature + AV > 8 ans + CTO."""
    return [
        EnveloppeDecumulation(
            nom="PEA Antoine",
            type_="PEA",
            valeur=150_000,
            versements_cumules=80_000,
            duree_detention_ans=12,
        ),
        EnveloppeDecumulation(
            nom="AV Generali",
            type_="AV",
            valeur=200_000,
            versements_cumules=120_000,
            duree_detention_ans=15,
        ),
        EnveloppeDecumulation(
            nom="CTO joint",
            type_="CTO",
            valeur=100_000,
            versements_cumules=60_000,
        ),
    ]


def test_optimiseur_atteint_le_besoin_net():
    plan = optimiser_retraits_annuels(
        besoin_net_annuel=30_000,
        enveloppes=_enveloppes_typiques(),
        contexte=ContexteFiscal(situation="couple", tmi=0.30),
    )
    assert plan.couverture_atteinte
    assert plan.total_net == pytest.approx(30_000, rel=0.01)


def test_optimiseur_priorise_pea_mature_sur_cto():
    """PEA > 5 ans (5% effectif) doit etre priorise sur CTO (12% effectif)."""
    enveloppes = [
        EnveloppeDecumulation(
            nom="PEA mature",
            type_="PEA",
            valeur=200_000,
            versements_cumules=100_000,
            duree_detention_ans=10,
        ),
        EnveloppeDecumulation(
            nom="CTO",
            type_="CTO",
            valeur=200_000,
            versements_cumules=100_000,
        ),
    ]
    plan = optimiser_retraits_annuels(
        besoin_net_annuel=20_000,
        enveloppes=enveloppes,
    )
    # Le PEA est utilise prioritairement
    pea_used = sum(r.montant_brut for r in plan.retraits if r.type_enveloppe == "PEA")
    cto_used = sum(r.montant_brut for r in plan.retraits if r.type_enveloppe == "CTO")
    assert pea_used > cto_used


def test_optimiseur_priorise_av_dans_abattement():
    """AV > 8 ans dans abattement (PS seuls) doit battre PEA si abattement dispo."""
    enveloppes = [
        EnveloppeDecumulation(
            nom="AV mature",
            type_="AV",
            valeur=200_000,
            versements_cumules=100_000,
            duree_detention_ans=10,
        ),
        EnveloppeDecumulation(
            nom="CTO",
            type_="CTO",
            valeur=200_000,
            versements_cumules=100_000,
        ),
    ]
    plan = optimiser_retraits_annuels(
        besoin_net_annuel=10_000,
        enveloppes=enveloppes,
        contexte=ContexteFiscal(situation="celibataire", encours_av_total_foyer=200_000),
    )
    # Premier retrait sur AV (abattement)
    assert plan.retraits[0].type_enveloppe == "AV"
    assert plan.abattement_av_consomme > 0


def test_optimiseur_signale_deficit_si_patrimoine_insuffisant():
    enveloppes = [
        EnveloppeDecumulation(
            nom="Petit CTO",
            type_="CTO",
            valeur=10_000,
            versements_cumules=8_000,
        ),
    ]
    plan = optimiser_retraits_annuels(
        besoin_net_annuel=50_000,
        enveloppes=enveloppes,
    )
    assert not plan.couverture_atteinte
    assert plan.deficit_residuel > 0
    assert any("deficit" in a.lower() or "insuffisant" in a.lower() for a in plan.avertissements)


def test_cout_marginal_pea_inferieur_a_cto():
    """Sanity check : taux marginal PEA > 5 ans < taux marginal CTO."""
    contexte = ContexteFiscal()
    taux_pea = cout_marginal_retrait("PEA", 1_000, 0.30, contexte, duree_detention_ans=10)
    taux_cto = cout_marginal_retrait("CTO", 1_000, 0.30, contexte)
    assert taux_pea < taux_cto


def test_optimiseur_besoin_zero():
    plan = optimiser_retraits_annuels(
        besoin_net_annuel=0,
        enveloppes=_enveloppes_typiques(),
    )
    assert plan.total_brut == 0
    assert plan.couverture_atteinte


# ── Tests simulateur multi-annees ─────────────────────────────────────────


def test_simulateur_projection_5_ans():
    proj = simuler_decumulation(
        enveloppes_initiales=_enveloppes_typiques(),
        besoin_net_annuel_initial=20_000,
        horizon_ans=5,
        rendement_annuel=0.04,
        inflation_annuelle=0.02,
        contexte_initial=ContexteFiscal(situation="couple", tmi=0.30),
    )
    assert len(proj.annees) == 5
    assert proj.annees_couvertes == 5
    # Patrimoine final < initial mais > 0
    assert 0 < proj.patrimoine_final < proj.patrimoine_initial


def test_simulateur_besoin_indexe_inflation():
    proj = simuler_decumulation(
        enveloppes_initiales=_enveloppes_typiques(),
        besoin_net_annuel_initial=10_000,
        horizon_ans=3,
        rendement_annuel=0.03,
        inflation_annuelle=0.02,
    )
    # Annee 1 : 10000, annee 2 : 10200, annee 3 : 10404
    assert proj.annees[0].besoin_net_annee == pytest.approx(10_000)
    assert proj.annees[1].besoin_net_annee == pytest.approx(10_200)
    assert proj.annees[2].besoin_net_annee == pytest.approx(10_404, rel=0.001)


def test_simulateur_rend_abattement_chaque_annee():
    """L'abattement AV se reinitialise chaque annee fiscale."""
    enveloppes = [
        EnveloppeDecumulation(
            nom="AV",
            type_="AV",
            valeur=500_000,
            versements_cumules=300_000,
            duree_detention_ans=15,
        ),
    ]
    proj = simuler_decumulation(
        enveloppes_initiales=enveloppes,
        besoin_net_annuel_initial=10_000,
        horizon_ans=3,
        rendement_annuel=0.0,
        inflation_annuelle=0.0,
        contexte_initial=ContexteFiscal(situation="couple"),
    )
    # Chaque annee doit pouvoir consommer son abattement
    for annee in proj.annees:
        assert annee.plan.abattement_av_consomme > 0


def test_simulateur_detecte_epuisement():
    """Si besoin > capacite, on detecte une enveloppe epuisee."""
    enveloppes = [
        EnveloppeDecumulation(
            nom="Petit PEA",
            type_="PEA",
            valeur=20_000,
            versements_cumules=15_000,
            duree_detention_ans=10,
        ),
        EnveloppeDecumulation(
            nom="CTO",
            type_="CTO",
            valeur=200_000,
            versements_cumules=150_000,
        ),
    ]
    proj = simuler_decumulation(
        enveloppes_initiales=enveloppes,
        besoin_net_annuel_initial=30_000,
        horizon_ans=5,
        rendement_annuel=0.0,
        inflation_annuelle=0.0,
    )
    assert "Petit PEA" in proj.enveloppes_epuisees
    assert proj.enveloppes_epuisees["Petit PEA"] <= 2  # epuise vite
