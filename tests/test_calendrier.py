"""Tests Sprint S15 Lot D — Calendrier de mise en œuvre."""

from __future__ import annotations

from datetime import date

from src.execution.calendrier import generer_calendrier

# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _plan_lump_sum(enveloppes=None):
    if enveloppes is None:
        enveloppes = ["PEA", "CTO"]
    return {
        "mode": "lump_sum",
        "duree_mois": 0,
        "sequence_enveloppes": enveloppes,
        "tranches": [
            {"mois": 0, "enveloppe": env, "montant_eur": 25_000.0, "justification": "Lump sum"}
            for env in enveloppes
        ],
    }


def _plan_dca(enveloppes=None, duree_mois=6):
    if enveloppes is None:
        enveloppes = ["PEA"]
    tranches = []
    montant_mensuel = 100_000.0 / (len(enveloppes) * duree_mois)
    for mois in range(duree_mois):
        for env in enveloppes:
            tranches.append(
                {
                    "mois": mois,
                    "enveloppe": env,
                    "montant_eur": montant_mensuel,
                    "justification": f"DCA mois {mois + 1}",
                }
            )
    return {
        "mode": "DCA",
        "duree_mois": duree_mois,
        "sequence_enveloppes": enveloppes,
        "tranches": tranches,
    }


def _plan_hybride(enveloppes=None, duree_mois=6):
    if enveloppes is None:
        enveloppes = ["PEA", "AV"]
    tranches = []
    # Tranche lump (mois 0)
    for env in enveloppes:
        tranches.append(
            {"mois": 0, "enveloppe": env, "montant_eur": 25_000.0, "justification": "Hybride lump"}
        )
    # Tranches DCA (mois 1 à duree_mois)
    for mois in range(1, duree_mois + 1):
        for env in enveloppes:
            tranches.append(
                {
                    "mois": mois,
                    "enveloppe": env,
                    "montant_eur": 4_000.0,
                    "justification": "Hybride DCA",
                }
            )
    return {
        "mode": "hybride",
        "duree_mois": duree_mois,
        "sequence_enveloppes": enveloppes,
        "tranches": tranches,
    }


DATE_DEBUT = date(2026, 5, 1)


# ─── Tests structure retour ───────────────────────────────────────────────────


class TestStructureCalendrier:
    def test_retourne_liste(self):
        cal = generer_calendrier(_plan_lump_sum(), DATE_DEBUT)
        assert isinstance(cal, list)

    def test_liste_non_vide(self):
        cal = generer_calendrier(_plan_lump_sum(), DATE_DEBUT)
        assert len(cal) > 0

    def test_champs_requis(self):
        cal = generer_calendrier(_plan_lump_sum(), DATE_DEBUT)
        etape = cal[0]
        assert "ordre" in etape
        assert "date_debut" in etape
        assert "date_fin" in etape
        assert "titre" in etape
        assert "description" in etape
        assert "type" in etape
        assert "depends_on" in etape

    def test_types_valides(self):
        cal = generer_calendrier(_plan_lump_sum(["PEA", "CTO"]), DATE_DEBUT)
        types_valides = {"admin", "virement", "ordre", "controle"}
        for etape in cal:
            assert etape["type"] in types_valides


# ─── Tests séquencement ───────────────────────────────────────────────────────


class TestSequencement:
    def test_admin_avant_virement(self):
        """Les étapes admin précèdent les virements."""
        cal = generer_calendrier(_plan_lump_sum(), DATE_DEBUT)
        etapes_admin = [e for e in cal if e["type"] == "admin"]
        etapes_virement = [e for e in cal if e["type"] == "virement"]
        if etapes_admin and etapes_virement:
            max_date_admin = max(e["date_fin"] for e in etapes_admin)
            min_date_virement = min(e["date_debut"] for e in etapes_virement)
            assert max_date_admin <= min_date_virement

    def test_virement_avant_ordre(self):
        """Les virements précèdent les ordres."""
        cal = generer_calendrier(_plan_lump_sum(), DATE_DEBUT)
        for etape_ordre in (e for e in cal if e["type"] == "ordre"):
            deps = etape_ordre["depends_on"]
            assert len(deps) > 0
            for dep_id in deps:
                dep_etape = next((e for e in cal if e["ordre"] == dep_id), None)
                assert dep_etape is not None
                assert dep_etape["type"] == "virement"

    def test_controle_apres_ordres(self):
        """Les contrôles suivent les ordres."""
        cal = generer_calendrier(_plan_lump_sum(), DATE_DEBUT)
        etapes_ordre = [e for e in cal if e["type"] == "ordre"]
        etapes_controle = [e for e in cal if e["type"] == "controle"]
        if etapes_ordre and etapes_controle:
            min_date_controle = min(e["date_debut"] for e in etapes_controle)
            # Au moins un ordre doit précéder le premier contrôle
            assert any(e["date_debut"] <= min_date_controle for e in etapes_ordre)

    def test_numeros_uniques(self):
        """Chaque étape a un numéro d'ordre unique."""
        cal = generer_calendrier(_plan_lump_sum(["PEA", "AV", "CTO"]), DATE_DEBUT)
        ordres = [e["ordre"] for e in cal]
        assert len(ordres) == len(set(ordres))

    def test_dates_coherentes(self):
        """date_debut ≤ date_fin pour chaque étape."""
        cal = generer_calendrier(_plan_lump_sum(), DATE_DEBUT)
        for etape in cal:
            assert etape["date_debut"] <= etape["date_fin"]


# ─── Tests DCA ────────────────────────────────────────────────────────────────


class TestCalendrierDCA:
    def test_dca_plusieurs_mois(self):
        """DCA 6 mois → étapes réparties sur ~6 mois."""
        cal = generer_calendrier(_plan_dca(duree_mois=6), DATE_DEBUT)
        dates_virements = [e["date_debut"] for e in cal if e["type"] == "virement"]
        # Au moins 2 dates distinctes pour un DCA multi-mois
        assert len(set(dates_virements)) >= 2

    def test_dca_revue_m6_presente(self):
        """DCA ≥ 6 mois → étape 'revue intermédiaire M+6' présente."""
        cal = generer_calendrier(_plan_dca(duree_mois=6), DATE_DEBUT)
        titres = [e["titre"].lower() for e in cal]
        assert any("m+6" in t or "revue" in t for t in titres)

    def test_rebalancing_annuel_present(self):
        """Rebalancing annuel M+12 toujours présent."""
        cal = generer_calendrier(_plan_lump_sum(), DATE_DEBUT)
        titres = [e["titre"].lower() for e in cal]
        assert any("m+12" in t or "rebalancing" in t or "rebalancement" in t for t in titres)


# ─── Tests hybride ────────────────────────────────────────────────────────────


class TestCalendrierHybride:
    def test_hybride_etapes_presentes(self):
        """Le mode hybride génère des étapes d'admin, virement et ordre."""
        cal = generer_calendrier(_plan_hybride(), DATE_DEBUT)
        types = {e["type"] for e in cal}
        assert "admin" in types
        assert "virement" in types
        assert "ordre" in types


# ─── Tests dépendances ────────────────────────────────────────────────────────


class TestDependances:
    def test_depends_on_liste(self):
        """Le champ depends_on est toujours une liste."""
        cal = generer_calendrier(_plan_lump_sum(), DATE_DEBUT)
        for etape in cal:
            assert isinstance(etape["depends_on"], list)

    def test_depends_on_referent_etapes_existantes(self):
        """Chaque ID dans depends_on réfère à une étape existante."""
        cal = generer_calendrier(_plan_lump_sum(["PEA", "AV"]), DATE_DEBUT)
        ids_existants = {e["ordre"] for e in cal}
        for etape in cal:
            for dep_id in etape["depends_on"]:
                assert dep_id in ids_existants, (
                    f"Étape {etape['ordre']} dépend de {dep_id} qui n'existe pas"
                )


# ─── Tests dates ─────────────────────────────────────────────────────────────


class TestDates:
    def test_premiere_etape_commence_date_debut(self):
        """La première étape (admin) commence à la date_debut."""
        cal = generer_calendrier(_plan_lump_sum(), DATE_DEBUT)
        etapes_admin = [e for e in cal if e["type"] == "admin"]
        if etapes_admin:
            assert etapes_admin[0]["date_debut"] == DATE_DEBUT

    def test_rebalancing_annuel_apres_un_an(self):
        """Le rebalancing annuel est après 1 an."""
        from datetime import timedelta

        cal = generer_calendrier(_plan_lump_sum(), DATE_DEBUT)
        rebal = next(
            (e for e in cal if "M+12" in e["titre"] or "annuel" in e["titre"].lower()), None
        )
        if rebal:
            assert rebal["date_debut"] >= DATE_DEBUT + timedelta(days=360)
