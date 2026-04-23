"""Tests for Pydantic v2 schemas."""

import pytest
from pydantic import ValidationError

from src.schemas import (
    AllocationCible,
    ETF,
    ETFEligibilite,
    Enveloppe,
    EnveloppesWrapper,
    Fiscalite2026,
    GlidePath,
    ParamsProjection,
    Profil,
    ProfilsWrapper,
    RebalancementFlux,
    UniversETFWrapper,
    charger_et_valider,
)


class TestChargerEtValider:
    def test_univers_etf(self):
        data = charger_et_valider("univers_etf.yaml")
        assert isinstance(data, UniversETFWrapper)
        assert len(data.univers_etf) > 0

    def test_enveloppes(self):
        data = charger_et_valider("enveloppes.yaml")
        assert isinstance(data, EnveloppesWrapper)
        assert len(data.enveloppes) > 0

    def test_profils_clients(self):
        data = charger_et_valider("profils_clients.yaml")
        assert isinstance(data, ProfilsWrapper)
        assert len(data.profils) > 0
        assert data.disclaimer

    def test_fiscalite_2026(self):
        data = charger_et_valider("fiscalite_2026.yaml")
        assert isinstance(data, Fiscalite2026)
        assert data.annee == 2026

    def test_projection_params(self):
        data = charger_et_valider("projection_params.yaml")
        assert isinstance(data, ParamsProjection)

    def test_glide_paths(self):
        data = charger_et_valider("glide_paths.yaml")
        assert isinstance(data, GlidePath)

    def test_rebalancement_flux(self):
        data = charger_et_valider("rebalancement_flux.yaml")
        assert isinstance(data, RebalancementFlux)

    def test_fichier_inconnu_leve_keyerror(self):
        with pytest.raises(KeyError):
            charger_et_valider("inconnu.yaml")

    def test_fichier_absent_leve_fileerror(self):
        with pytest.raises(KeyError):
            charger_et_valider("absent.yaml")


class TestETFEligibilite:
    def test_defaults_false(self):
        e = ETFEligibilite()
        assert e.PEA is False
        assert e.AV_UC is False

    def test_creation(self):
        e = ETFEligibilite(PEA=True, CTO_perso=True)
        assert e.PEA is True
        assert e.CTO_perso is True
        assert e.PER is False


class TestETF:
    def test_etf_valide(self):
        etf = ETF(
            isin="IE0031442068",
            ticker="CW8",
            nom="Amundi MSCI World",
            emetteur="Amundi",
            classe_actifs="Actions",
            ter=0.0038,
            devise="EUR",
            domicile="Irlande",
            capitalisant=True,
            eur_hedged=False,
        )
        assert etf.isin == "IE0031442068"
        assert etf.ter == 0.0038

    def test_ter_negatif_invalide(self):
        with pytest.raises(ValidationError):
            ETF(
                isin="XX",
                ticker="XX",
                nom="Test",
                emetteur="Test",
                classe_actifs="Actions",
                ter=-0.01,
                devise="EUR",
                domicile="France",
                capitalisant=True,
                eur_hedged=False,
            )

    def test_univers_etf_isin_uniques(self):
        data = charger_et_valider("univers_etf.yaml")
        isins = [e.isin for e in data.univers_etf]
        assert len(isins) == len(set(isins)), "ISINs must be unique"

    def test_univers_etf_ter_positifs(self):
        data = charger_et_valider("univers_etf.yaml")
        for etf in data.univers_etf:
            assert etf.ter >= 0


class TestAllocationCible:
    def test_allocation_valide(self):
        a = AllocationCible(actions=0.60, obligations=0.30, liquidites=0.10)
        assert a.actions == 0.60

    def test_somme_pas_egal_1_invalide(self):
        with pytest.raises(ValidationError):
            AllocationCible(actions=0.50, obligations=0.30, liquidites=0.05)

    def test_actions_hors_range_invalide(self):
        with pytest.raises(ValidationError):
            AllocationCible(actions=1.5, obligations=0.0, liquidites=0.0)


class TestProfils:
    def test_profils_chargement(self):
        data = charger_et_valider("profils_clients.yaml")
        for profil in data.profils:
            assert profil.age >= 0
            assert 0 <= profil.tmi <= 1

    def test_allocation_profil_somme_1(self):
        data = charger_et_valider("profils_clients.yaml")
        for profil in data.profils:
            alloc = profil.allocation_cible_bogleheads
            total = alloc.actions + alloc.obligations + alloc.immobilier_cote + alloc.or_ + alloc.liquidites
            assert abs(total - 1.0) < 0.02, f"Profil {profil.id}: total={total}"


class TestFiscalite2026:
    def test_taux_ps_positif(self):
        data = charger_et_valider("fiscalite_2026.yaml")
        assert data.prelevements_sociaux.taux_global > 0
        assert data.pfu.taux_ir > 0

    def test_annee(self):
        data = charger_et_valider("fiscalite_2026.yaml")
        assert data.annee == 2026
