import pytest
from src.rebalancement_flux import (
    EtatPortefeuille,
    calculer_ecarts,
    repartir_versement,
    simuler_versements_recurrents,
    comparer_cout_fiscal,
    charger_config,
)


def test_charger_config():
    cfg = charger_config()
    assert "bandes_tolerance" in cfg
    assert "taux_fiscalite_par_enveloppe" in cfg


def test_poids_somme_1():
    p = EtatPortefeuille(actions_monde=60_000, obligations=40_000)
    poids = p.poids_actuels()
    assert abs(sum(poids.values()) - 1.0) < 1e-9
    assert poids["actions_monde"] == 0.6
    assert poids["obligations"] == 0.4


def test_total_correct():
    p = EtatPortefeuille(actions_monde=60_000, obligations=40_000, monetaire=10_000)
    assert p.total == 110_000


def test_ecarts_classes_sous_ponderees():
    # 100 k€ avec 50/50, cible 70/30 : actions sous-pondérées, obligs sur-pondérées
    p = EtatPortefeuille(actions_monde=50_000, obligations=50_000)
    cible = {"actions_monde": 0.7, "obligations": 0.3}
    ecarts = calculer_ecarts(p, cible)
    e_actions = [e for e in ecarts if e.classe == "actions_monde"][0]
    e_obligs = [e for e in ecarts if e.classe == "obligations"][0]
    assert e_actions.sous_pondere
    assert not e_obligs.sous_pondere
    assert abs(e_actions.ecart_pct - 0.2) < 1e-9


def test_repartition_verse_sur_sous_ponderee():
    # Portefeuille 100k : 50 actions / 50 obligs, cible 70/30, versement 10k
    # Déficit actions = 20k, surplus obligs = 20k → flux 10k doit aller à 100% sur actions
    p = EtatPortefeuille(actions_monde=50_000, obligations=50_000)
    cible = {"actions_monde": 0.7, "obligations": 0.3}
    rep = repartir_versement(p, cible, 10_000)
    assert rep.repartition["actions_monde"] == pytest.approx(10_000, rel=1e-6)
    assert rep.repartition["obligations"] == pytest.approx(0.0, abs=1e-6)


def test_aucune_vente():
    """Le rebalancement par flux ne doit JAMAIS produire de montant négatif."""
    p = EtatPortefeuille(actions_monde=80_000, obligations=20_000)
    cible = {"actions_monde": 0.5, "obligations": 0.5}   # obligs très sous-pondérées
    rep = repartir_versement(p, cible, 5_000)
    for montant in rep.repartition.values():
        assert montant >= 0


def test_versement_zero():
    p = EtatPortefeuille(actions_monde=60_000, obligations=40_000)
    cible = {"actions_monde": 0.7, "obligations": 0.3}
    rep = repartir_versement(p, cible, 0)
    assert all(v == 0.0 for v in rep.repartition.values())


def test_versement_superieur_au_deficit():
    """Si versement > déficit, le surplus doit être réparti selon allocation cible."""
    p = EtatPortefeuille(actions_monde=50_000, obligations=50_000)
    cible = {"actions_monde": 0.7, "obligations": 0.3}
    # Déficit actions = 20k. Versement = 100k → surplus 80k à répartir 70/30.
    rep = repartir_versement(p, cible, 100_000)
    # Au moins 20k a dû aller dans actions
    assert rep.repartition["actions_monde"] >= 20_000


def test_simulation_recurrente_rebalance_avec_le_temps():
    p = EtatPortefeuille(actions_monde=50_000, obligations=50_000)
    cible = {"actions_monde": 0.7, "obligations": 0.3}
    historique = simuler_versements_recurrents(p, cible, 1_000, nb_mois=36)
    assert len(historique) == 36
    # Dans la dernière répartition, il devrait rester moins d'écart
    dernier = historique[-1]
    premier = historique[0]
    # L'allocation finale du dernier mois doit être plus proche de la cible
    assert abs(dernier.allocation_finale["actions_monde"] - 0.7) < abs(
        premier.allocation_finale["actions_monde"] - 0.7
    )


def test_comparaison_fiscale_cto():
    cmp = comparer_cout_fiscal(10_000, "CTO_perso")
    # PV 30% × PFU 31.4% × 10k = 942€
    assert cmp.cout_fiscal_vente == pytest.approx(942.0, rel=0.01)
    assert cmp.cout_fiscal_flux == 0.0
    assert cmp.economie_fiscale == cmp.cout_fiscal_vente


def test_comparaison_fiscale_per_zero():
    # PER : 0% en accumulation
    cmp = comparer_cout_fiscal(10_000, "PER")
    assert cmp.cout_fiscal_vente == 0.0


def test_recommandation_necessite_vente_si_derive_trop_forte():
    # Dérive énorme : actions 95% réel vs 50% cible → besoin de vente
    p = EtatPortefeuille(actions_monde=95_000, obligations=5_000)
    cible = {"actions_monde": 0.5, "obligations": 0.5}
    rep = repartir_versement(p, cible, 1_000)
    assert rep.necessite_vente
