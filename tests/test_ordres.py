"""Tests Sprint S15 Lot B — Plan d'exécution chiffré."""

from __future__ import annotations

import csv
import io
import math
from pathlib import Path
from types import SimpleNamespace

from src.execution.ordres import (
    _calculer_quantite,
    _estimer_frais_courtage,
    export_ordres_csv,
    generer_ordres,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _broker(
    frais_courtage_eur=1.0,
    frais_courtage_pct=None,
    minimum_ordre_eur=0.0,
):
    return SimpleNamespace(
        frais_courtage_actions_euronext_eur=frais_courtage_eur,
        frais_courtage_actions_euronext_pct=frais_courtage_pct,
        minimum_ordre_eur=minimum_ordre_eur,
    )


def _allocation_simple():
    return {
        "PEA": {"IE0031442068": 30_000.0},
        "CTO": {"IE00B4L5Y983": 20_000.0},
    }


def _prix_ref():
    return {
        "IE0031442068": 350.0,  # CW8
        "IE00B4L5Y983": 85.0,  # IWDA
    }


def _contexte_simple():
    broker_pea = _broker(frais_courtage_eur=1.0)
    broker_cto = _broker(frais_courtage_eur=0.99)
    return {
        "brokers": {"PEA": broker_pea, "CTO": broker_cto},
        "noms_etf": {
            "IE0031442068": "Amundi MSCI World PEA",
            "IE00B4L5Y983": "iShares MSCI World",
        },
        "tickers_etf": {"IE0031442068": "CW8", "IE00B4L5Y983": "IWDA"},
    }


# ─── Tests calcul quantité ────────────────────────────────────────────────────


class TestCalculerQuantite:
    def test_pea_arrondi_entier(self):
        """PEA → quantité entière (floor)."""
        qte, reliquat = _calculer_quantite(1000.0, 350.0, "PEA")
        assert qte == math.floor(1000.0 / 350.0)
        assert qte == 2
        assert abs(reliquat - (1000.0 - 2 * 350.0)) < 0.01

    def test_cto_arrondi_entier(self):
        """CTO → quantité entière."""
        qte, reliquat = _calculer_quantite(500.0, 85.0, "CTO")
        assert qte == math.floor(500.0 / 85.0)
        assert qte == 5
        assert abs(reliquat - (500.0 - 5 * 85.0)) < 0.01

    def test_av_fractions_possibles(self):
        """AV → fractions de parts autorisées (UC)."""
        qte, reliquat = _calculer_quantite(1000.0, 350.0, "AV")
        assert isinstance(qte, float)
        assert abs(qte - 1000.0 / 350.0) < 0.000001
        assert reliquat == 0.0

    def test_prix_zero_retourne_zero(self):
        """Prix nul → quantité 0, tout en reliquat."""
        qte, reliquat = _calculer_quantite(1000.0, 0.0, "PEA")
        assert qte == 0.0
        assert reliquat == 1000.0

    def test_reliquat_total_correct(self):
        """Quantité × prix + reliquat = montant initial."""
        montant = 10_000.0
        prix = 157.0
        qte, reliquat = _calculer_quantite(montant, prix, "PEA")
        assert abs(qte * prix + reliquat - montant) < 0.01


# ─── Tests frais courtage ─────────────────────────────────────────────────────


class TestEstimerFraisCourtage:
    def test_frais_fixe(self):
        broker = _broker(frais_courtage_eur=1.0)
        frais = _estimer_frais_courtage(10_000.0, 100.0, broker)
        assert frais == 1.0

    def test_frais_pct(self):
        broker = _broker(frais_courtage_eur=None, frais_courtage_pct=0.001)
        frais = _estimer_frais_courtage(10_000.0, 100.0, broker)
        assert abs(frais - 10.0) < 0.01

    def test_broker_none_frais_zero(self):
        frais = _estimer_frais_courtage(10_000.0, 100.0, None)
        assert frais == 0.0


# ─── Tests generer_ordres ─────────────────────────────────────────────────────


class TestGenererOrdres:
    def test_structure_resultat(self):
        plan = generer_ordres(_allocation_simple(), _prix_ref(), _contexte_simple())
        assert "ordres" in plan
        assert "reliquats" in plan
        assert "frais_total" in plan

    def test_nombre_ordres_correct(self):
        """2 positions → 2 ordres."""
        plan = generer_ordres(_allocation_simple(), _prix_ref(), _contexte_simple())
        assert len(plan["ordres"]) == 2

    def test_champs_ordre(self):
        plan = generer_ordres(_allocation_simple(), _prix_ref(), _contexte_simple())
        ordre = plan["ordres"][0]
        assert "enveloppe" in ordre
        assert "isin" in ordre
        assert "quantite" in ordre
        assert "prix_limite_eur" in ordre
        assert "frais_courtage_eur" in ordre
        assert "montant_reel_eur" in ordre
        assert ordre["type_ordre"] == "limité"

    def test_prix_limite_dans_tolerance(self):
        """Prix limite = prix_ref × (1 + tolerance)."""
        plan = generer_ordres(_allocation_simple(), _prix_ref(), _contexte_simple())
        for ordre in plan["ordres"]:
            prix_ref = ordre["prix_reference_eur"]
            prix_limite = ordre["prix_limite_eur"]
            assert abs(prix_limite / prix_ref - 1.02) < 0.0001

    def test_reliquats_non_negatifs(self):
        plan = generer_ordres(_allocation_simple(), _prix_ref(), _contexte_simple())
        for _env, rel in plan["reliquats"].items():
            assert rel >= 0.0

    def test_frais_total_somme_ordres(self):
        """frais_total == somme des frais par ordre."""
        plan = generer_ordres(_allocation_simple(), _prix_ref(), _contexte_simple())
        total_calcule = sum(o["frais_courtage_eur"] for o in plan["ordres"])
        assert abs(plan["frais_total"] - total_calcule) < 0.01

    def test_prix_manquant_ordre_ignore(self):
        """Si le prix est manquant, l'ordre est ignoré sans erreur."""
        alloc = {"PEA": {"ISIN_INCONNU": 10_000.0}}
        prix = {}
        plan = generer_ordres(alloc, prix, {})
        assert len(plan["ordres"]) == 0

    def test_montant_trop_faible_ignore(self):
        """Montant < 1€ → ordre ignoré."""
        alloc = {"PEA": {"IE0031442068": 0.50}}
        plan = generer_ordres(alloc, _prix_ref(), _contexte_simple())
        assert len(plan["ordres"]) == 0

    def test_tolerance_personnalisee(self):
        """Tolérance de 1% → prix limite = prix_ref × 1.01."""
        plan = generer_ordres(
            {"PEA": {"IE0031442068": 5_000.0}},
            _prix_ref(),
            _contexte_simple(),
            tolerance_prix=0.01,
        )
        ordre = plan["ordres"][0]
        assert abs(ordre["prix_limite_eur"] / ordre["prix_reference_eur"] - 1.01) < 0.0001

    def test_enveloppe_vide_ignoree(self):
        """Enveloppe sans positions → pas d'ordres."""
        alloc = {"PEA": {}, "CTO": {"IE00B4L5Y983": 5_000.0}}
        plan = generer_ordres(alloc, _prix_ref(), _contexte_simple())
        assert len(plan["ordres"]) == 1
        assert plan["ordres"][0]["enveloppe"] == "CTO"


# ─── Tests export CSV ─────────────────────────────────────────────────────────


class TestExportOrdresCSV:
    def test_csv_genere_non_vide(self):
        plan = generer_ordres(_allocation_simple(), _prix_ref(), _contexte_simple())
        csv_content = export_ordres_csv(plan)
        assert len(csv_content) > 0

    def test_csv_contient_en_tete(self):
        plan = generer_ordres(_allocation_simple(), _prix_ref(), _contexte_simple())
        csv_content = export_ordres_csv(plan)
        assert "enveloppe" in csv_content
        assert "isin" in csv_content

    def test_csv_contient_donnees(self):
        plan = generer_ordres(_allocation_simple(), _prix_ref(), _contexte_simple())
        csv_content = export_ordres_csv(plan)
        # Vérifier que les enveloppes apparaissent
        assert "PEA" in csv_content
        assert "CTO" in csv_content

    def test_csv_parseable(self):
        """Le CSV généré est parseable par le module csv."""
        plan = generer_ordres(_allocation_simple(), _prix_ref(), _contexte_simple())
        csv_content = export_ordres_csv(plan)
        # Lire les premières lignes de données (avant la synthèse)
        lignes = csv_content.split("\n")
        reader = csv.DictReader(io.StringIO("\n".join(lignes[:3])))
        rows = list(reader)
        assert len(rows) >= 1

    def test_export_csv_vers_fichier(self, tmp_path):
        """L'export vers un fichier fonctionne sans erreur."""
        plan = generer_ordres(_allocation_simple(), _prix_ref(), _contexte_simple())
        chemin = str(tmp_path / "ordres.csv")
        result = export_ordres_csv(plan, path=chemin)
        assert result == chemin
        assert Path(chemin).exists()

    def test_csv_contient_frais_total(self):
        """Le CSV contient la ligne FRAIS TOTAL."""
        plan = generer_ordres(_allocation_simple(), _prix_ref(), _contexte_simple())
        csv_content = export_ordres_csv(plan)
        assert "FRAIS TOTAL" in csv_content
