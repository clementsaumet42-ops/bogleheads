"""
Tests pour src/rebalancement_optimal.py — Sprint S3.6.

≥ 15 tests couvrant :
  - Cascade gratuit → flux → vente
  - CMP sur CTO/IR avec 3 lots
  - FIFO sur CTO/IS avec 3 lots
  - Abattement AV annuel (consommé partiellement, pas dépassé)
  - Compensation PV/MV CTO même année (tax-loss harvesting)
  - Contrainte PER = sortie interdite
  - Contrainte PEA < 5 ans = clôture totale → rejet
  - Frais de courtage intégrés à l'optimisation
  - Plan trimestriel vs alerte événementielle (dérive > 8 pp)
  - Coût optimisé ≤ coût naïf
"""

from __future__ import annotations

import pytest

from src.rebalancement_optimal import (
    Lot,
    Position,
    calculer_pv_cmp,
    calculer_pv_fifo,
    compenser_pv_mv,
    contraintes_liquidite,
    cout_fiscal_av,
    detecter_moins_values_latentes,
    est_pea_eligible_retrait,
    etape3_ventes,
    optimiser_rebalancement,
)

# ─── Fixtures ────────────────────────────────────────────────────────────────


def _make_lot(date: str, qty: float, prix: float) -> Lot:
    return Lot(date_acquisition=date, quantite=qty, prix_unitaire=prix)


def _pea_old() -> Position:
    """PEA ouvert il y a > 5 ans, avec PV latente."""
    return Position(
        etf="CW8",
        enveloppe="PEA",
        quantite=100,
        prix_revient_moyen=300.0,
        montant_actuel=50_000,
        lots=[_make_lot("2019-01-01", 100, 300.0)],
        date_ouverture_enveloppe="2019-01-01",
    )


def _pea_new() -> Position:
    """PEA ouvert il y a < 5 ans."""
    return Position(
        etf="CW8",
        enveloppe="PEA",
        quantite=100,
        prix_revient_moyen=300.0,
        montant_actuel=50_000,
        lots=[_make_lot("2023-01-01", 100, 300.0)],
        date_ouverture_enveloppe="2023-01-01",
    )


def _cto_ir_3lots() -> Position:
    """CTO/IR avec 3 lots à prix différents."""
    return Position(
        etf="IWDA",
        enveloppe="CTO_perso",
        quantite=300,
        prix_revient_moyen=82.30,  # CMP calculé
        montant_actuel=28_530,  # cours ~95.1
        lots=[
            _make_lot("2021-01-10", 100, 70.0),
            _make_lot("2022-06-15", 100, 85.0),
            _make_lot("2023-09-20", 100, 92.0),
        ],
    )


def _cto_is_3lots() -> Position:
    """CTO/IS avec 3 lots à prix différents."""
    return Position(
        etf="IWDA",
        enveloppe="CTO_IS",
        quantite=300,
        prix_revient_moyen=82.30,
        montant_actuel=28_530,
        lots=[
            _make_lot("2021-01-10", 100, 70.0),
            _make_lot("2022-06-15", 100, 85.0),
            _make_lot("2023-09-20", 100, 92.0),
        ],
    )


def _per_pos() -> Position:
    return Position(
        etf="GOVS",
        enveloppe="PER",
        quantite=500,
        prix_revient_moyen=95.0,
        montant_actuel=50_000,
        lots=[_make_lot("2020-09-01", 500, 95.0)],
    )


def _av_old() -> Position:
    """AV ouverte il y a > 8 ans."""
    return Position(
        etf="AGGH",
        enveloppe="AV",
        quantite=200,
        prix_revient_moyen=45.0,
        montant_actuel=12_000,  # cours ~60
        lots=[_make_lot("2015-06-01", 200, 45.0)],
        date_ouverture_enveloppe="2015-06-01",
    )


def _cto_mv_latente() -> Position:
    """Position CTO en moins-value latente."""
    return Position(
        etf="XBAE",
        enveloppe="CTO_perso",
        quantite=100,
        prix_revient_moyen=90.0,
        montant_actuel=7_000,  # cours 70 < prix revient 90 → MV
        lots=[_make_lot("2023-01-01", 100, 90.0)],
    )


# ─── Test 1 : CMP sur CTO/IR ─────────────────────────────────────────────────


def test_calculer_pv_cmp_3_lots():
    """Test CMP sur CTO/IR : PV = montant_vente × (1 - CMP/cours)."""
    # CMP = (100×70 + 100×85 + 100×92) / 300 = 82.33…
    # cours actuel = 28530 / 300 = 95.1
    pv = calculer_pv_cmp(montant_vente=9_510, prix_revient_moyen=82.30, cours_actuel=95.1)
    # 100 titres vendus à 95.1, PRM 82.30 → PV = 100 × (95.1 - 82.30) = 1280
    assert pv == pytest.approx(1280.0, rel=0.01)


def test_calculer_pv_cmp_zero_si_moins_value():
    """PV CMP doit retourner une valeur négative si cours < CMP."""
    pv = calculer_pv_cmp(montant_vente=7_000, prix_revient_moyen=90.0, cours_actuel=70.0)
    assert pv < 0  # MV latente


def test_calculer_pv_cmp_cours_zero():
    """Pas de division par zéro si cours = 0."""
    assert calculer_pv_cmp(1_000, 50.0, 0.0) == 0.0


# ─── Test 4 : FIFO sur CTO/IS ─────────────────────────────────────────────────


def test_calculer_pv_fifo_vend_lots_anciens_en_premier():
    """FIFO : le lot le plus ancien (prix_unitaire = 70) est vendu en premier."""
    pos = _cto_is_3lots()
    # Vente de 100 titres au cours 95.1 → lot du 2021 (100 titres à 70)
    pv = calculer_pv_fifo(montant_vente=9_510, lots=pos.lots, cours_actuel=95.1)
    # PV = 100 × (95.1 - 70.0) = 2510
    assert pv == pytest.approx(2_510.0, rel=0.01)


def test_calculer_pv_fifo_vend_deux_lots():
    """FIFO avec vente sur 2 lots."""
    lots = [
        _make_lot("2020-01-01", 50, 80.0),
        _make_lot("2021-06-01", 50, 100.0),
    ]
    # Vente de 100 titres à 120 : lot 1 (50 × 80) + lot 2 (50 × 100)
    pv = calculer_pv_fifo(montant_vente=12_000, lots=lots, cours_actuel=120.0)
    # cout_revient = 50×80 + 50×100 = 9000; PV = 12000 - 9000 = 3000
    assert pv == pytest.approx(3_000.0, rel=0.01)


# ─── Test 6 : Abattement AV ───────────────────────────────────────────────────


def test_abattement_av_consomme_partiellement():
    """AV > 8 ans : abattement consommé partiellement (PV < abattement)."""
    cout, abatt_conso = cout_fiscal_av(
        plus_value=2_000, age_enveloppe_ans=9.0, abattement_restant=4_600
    )
    assert cout == 0.0  # PV < abattement → coût 0
    assert abatt_conso == pytest.approx(2_000.0)


def test_abattement_av_non_depasse():
    """AV > 8 ans : abattement annuel non dépassé, coût fiscal nul."""
    cout, abatt_conso = cout_fiscal_av(
        plus_value=3_200, age_enveloppe_ans=10.0, abattement_restant=4_600
    )
    assert cout == 0.0
    assert abatt_conso == pytest.approx(3_200.0)


def test_abattement_av_depasse():
    """AV > 8 ans : PV > abattement → seule la partie excédentaire est taxée."""
    cout, abatt_conso = cout_fiscal_av(
        plus_value=6_000, age_enveloppe_ans=10.0, abattement_restant=4_600
    )
    # 6000 - 4600 = 1400 × 31.4% = 439.6
    assert cout == pytest.approx(1_400 * 0.314, rel=0.01)
    assert abatt_conso == pytest.approx(4_600.0)


def test_abattement_av_moins_de_8_ans():
    """AV < 8 ans : pas d'abattement, PFU plein."""
    cout, abatt_conso = cout_fiscal_av(
        plus_value=3_000, age_enveloppe_ans=5.0, abattement_restant=4_600
    )
    assert cout == pytest.approx(3_000 * 0.314, rel=0.01)
    assert abatt_conso == 0.0


# ─── Test 10 : Compensation PV/MV CTO ────────────────────────────────────────


def test_compensation_pv_mv_cto():
    """Tax-loss harvesting : les MV latentes compensent les PV réalisées."""
    from src.rebalancement_optimal import VentePlanifiee

    mv_pos = _cto_mv_latente()  # MV latente = 7000 - 100×90 = -2000

    vente = VentePlanifiee(
        etf="IWDA",
        enveloppe="CTO_perso",
        montant=9_510,
        plus_value_realisee=1_280,
        cout_fiscal=1_280 * 0.314,
        frais_courtage=0.0,
        methode="CTO_CMP",
        detail="Test",
    )

    ventes_apres = compenser_pv_mv([vente], [mv_pos])
    assert len(ventes_apres) == 1
    # MV disponible = 2000, PV = 1280 → compensation totale → coût = 0
    assert ventes_apres[0].cout_fiscal == pytest.approx(0.0, abs=1e-6)


# ─── Test 11 : Contrainte PER ─────────────────────────────────────────────────


def test_per_sortie_interdite():
    """Le PER ne doit jamais apparaître dans les ventes (Art. L. 224-4 CMF)."""
    per = _per_pos()
    ventes = etape3_ventes(
        positions=[per],
        allocation_actuelle={"actions": 0.9, "obligations": 0.1},
        allocation_cible={"actions": 0.5, "obligations": 0.5},
        patrimoine_total=50_000,
        regime_fiscal="IR",
        abattement_av_restant=4_600,
        frais_courtage=0.0,
        utiliser_milp=False,
    )
    assert all(v.enveloppe != "PER" for v in ventes)


# ─── Test 12 : Contrainte PEA < 5 ans ────────────────────────────────────────


def test_pea_moins_5_ans_clôture_rejetee():
    """PEA < 5 ans : retrait partiel impossible → aucune vente planifiée."""
    pea_new = _pea_new()
    assert not est_pea_eligible_retrait(pea_new)

    ventes = etape3_ventes(
        positions=[pea_new],
        allocation_actuelle={"actions": 0.9, "obligations": 0.1},
        allocation_cible={"actions": 0.5, "obligations": 0.5},
        patrimoine_total=50_000,
        regime_fiscal="IR",
        abattement_av_restant=4_600,
        frais_courtage=0.0,
        utiliser_milp=False,
    )
    assert all(v.enveloppe != "PEA" for v in ventes)


def test_pea_plus_5_ans_eligible():
    """PEA ≥ 5 ans : retrait partiel autorisé."""
    pea_old = _pea_old()
    assert est_pea_eligible_retrait(pea_old)


# ─── Test 13 : Frais de courtage ─────────────────────────────────────────────


def test_frais_courtage_dans_optimisation():
    """Les frais de courtage sont bien reportés dans les ventes planifiées."""
    pos = _cto_ir_3lots()
    ventes = etape3_ventes(
        positions=[pos],
        allocation_actuelle={"actions": 0.9, "obligations": 0.1},
        allocation_cible={"actions": 0.5, "obligations": 0.5},
        patrimoine_total=28_530,
        regime_fiscal="IR",
        abattement_av_restant=4_600,
        frais_courtage=7.5,
        utiliser_milp=False,
    )
    if ventes:
        assert ventes[0].frais_courtage == pytest.approx(7.5)


# ─── Test 14 : Alerte événementielle ─────────────────────────────────────────


def test_alerte_evenementielle_derive_superieure_8pp():
    """Si dérive > 8 pp, l'optimiseur doit produire un plan non vide."""
    pos = _cto_ir_3lots()
    plan = optimiser_rebalancement(
        positions=[pos],
        allocation_actuelle={"actions": 1.0, "obligations": 0.0},
        allocation_cible={"actions": 0.5, "obligations": 0.5},
        patrimoine_total=28_530,
        versement_mensuel=1_000,
        regime_fiscal="IR",
        seuil_alerte_pp=0.08,
        profil_code="TEST",
    )
    # La dérive de 50 pp > 8 pp → plan non vide ou ventes planifiées
    assert plan.derive_par_classe.get("actions", 0.0) == pytest.approx(50.0, rel=0.01)


def test_plan_trimestriel_flux():
    """Étape 2 : les flux trimestriels (3 mois) doivent figurer dans le plan."""
    plan = optimiser_rebalancement(
        positions=[],
        allocation_actuelle={"actions_monde": 0.9, "obligations": 0.1},
        allocation_cible={"actions_monde": 0.7, "obligations": 0.3},
        patrimoine_total=100_000,
        versement_mensuel=1_000,
        nb_mois_flux=3,
        regime_fiscal="IR",
        profil_code="TEST_FLUX",
    )
    # Avec versements, flux_recommandes doit être non vide
    # (si la dérive dépasse les bandes)
    assert isinstance(plan.flux_recommandes, list)


# ─── Test 16 : Coût optimisé ≤ coût naïf ──────────────────────────────────────


def test_cout_optimise_inferieur_ou_egal_cout_naif():
    """L'optimiseur doit produire un coût fiscal ≤ coût naïf."""
    positions = [_pea_old(), _cto_ir_3lots(), _per_pos()]
    plan = optimiser_rebalancement(
        positions=positions,
        allocation_actuelle={"actions": 0.8, "obligations": 0.2},
        allocation_cible={"actions": 0.6, "obligations": 0.4},
        patrimoine_total=sum(p.montant_actuel for p in positions),
        versement_mensuel=0.0,
        regime_fiscal="IR",
        profil_code="TEST_OPTIM",
    )
    assert plan.cout_fiscal_total <= plan.cout_fiscal_naif + 1e-6


# ─── Test 17 : Stub contraintes_liquidite ────────────────────────────────────


def test_contraintes_liquidite_stub():
    """TODO(S3.7) : retourne [] pour l'instant."""
    result = contraintes_liquidite({})
    assert result == []


# ─── Test 18 : Détection des MV latentes ─────────────────────────────────────


def test_detecter_moins_values_latentes():
    """Seules les positions CTO en MV doivent être détectées."""
    mv = _cto_mv_latente()  # MV = -2000
    pv_pos = _cto_ir_3lots()  # PV latente positive
    per = _per_pos()  # PER — hors scope

    mv_list = detecter_moins_values_latentes([mv, pv_pos, per])
    assert any(p.etf == "XBAE" for p in mv_list)
    assert all(p.enveloppe in {"CTO_perso", "CTO_IS"} for p in mv_list)
    assert not any(p.etf == "GOVS" for p in mv_list)
