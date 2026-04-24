from __future__ import annotations

from src.profilage.capital_humain import CapitalHumain


def test_valeur_calculee():
    ch = CapitalHumain(revenus_nets_annuels=60000, annees_restantes=20)
    assert ch.valeur_actualisee_eur > 0


def test_zero_annees():
    ch = CapitalHumain(revenus_nets_annuels=60000, annees_restantes=0)
    assert ch.valeur_actualisee_eur == 0.0


def test_bond_like_stable():
    ch = CapitalHumain(
        revenus_nets_annuels=50000, annees_restantes=10, stabilite_emploi="tres_stable"
    )
    assert ch.part_bond_like == 0.80
