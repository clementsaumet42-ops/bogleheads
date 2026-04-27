"""Tests Sprint S16 — Module mission CGP."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from src.mission.checklist import ETAPES_CANONIQUES, ETAPES_PAR_CLE, PHASES
from src.mission.etat import (
    EtatEtape,
    EtatMission,
    _slug,
    charger_mission,
    creer_mission,
    lister_missions,
    sauvegarder_mission,
    supprimer_mission,
)
from src.mission.progress import calculer_progression, detecter_blocages

# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """Redirige le répertoire de persistance vers un dossier temporaire."""
    import src.mission.etat as etat_mod

    monkeypatch.setattr(etat_mod, "_DEFAULT_DATA_DIR", tmp_path / "missions")
    return tmp_path / "missions"


@pytest.fixture
def mission_vierge(tmp_data_dir) -> EtatMission:
    """Crée une mission vierge dans le dossier temporaire."""
    return creer_mission("Dupont Jean", "Alice CGP")


@pytest.fixture
def mission_rdv1_valide(mission_vierge) -> EtatMission:
    """Mission avec les étapes RDV1 validées."""
    m = mission_vierge
    m.etapes["profil_saisi"] = EtatEtape.VALIDE
    m.etapes["lettre_mission"] = EtatEtape.VALIDE
    m.etapes["profilage_mif"] = EtatEtape.VALIDE
    sauvegarder_mission(m)
    return m


@pytest.fixture
def mission_complete(mission_vierge) -> EtatMission:
    """Mission avec toutes les étapes validées."""
    m = mission_vierge
    for cle in list(m.etapes.keys()):
        m.etapes[cle] = EtatEtape.VALIDE
    sauvegarder_mission(m)
    return m


# ─── Tests création mission ───────────────────────────────────────────────────


class TestCreerMission:
    def test_cree_avec_bons_champs(self, tmp_data_dir):
        m = creer_mission("Martin Sophie", "Bob CGP")
        assert m.nom_client == "Martin Sophie"
        assert m.cgp == "Bob CGP"
        assert m.date_creation == date.today()
        assert m.date_derniere_maj == date.today()

    def test_mission_id_est_slug(self, tmp_data_dir):
        m = creer_mission("Müller Klaus", "CGP")
        assert "muller" in m.mission_id or "m_ller" in m.mission_id or "muller" in m.mission_id

    def test_etapes_initialisees_non_commence(self, tmp_data_dir):
        m = creer_mission("Test Client", "CGP")
        for etape in ETAPES_CANONIQUES:
            assert m.etapes[etape.cle] == EtatEtape.NON_COMMENCE

    def test_toutes_etapes_canoniques_presentes(self, tmp_data_dir):
        m = creer_mission("Test Client", "CGP")
        for etape in ETAPES_CANONIQUES:
            assert etape.cle in m.etapes

    def test_fichier_json_cree(self, tmp_data_dir):
        m = creer_mission("Fichier Test", "CGP")
        assert m.chemin_persistance.exists()

    def test_doublon_genere_id_unique(self, tmp_data_dir):
        m1 = creer_mission("Dupont Jean", "CGP")
        m2 = creer_mission("Dupont Jean", "CGP")
        assert m1.mission_id != m2.mission_id


# ─── Tests sauvegarde / chargement ────────────────────────────────────────────


class TestPersistance:
    def test_sauvegarder_et_charger_roundtrip(self, mission_vierge):
        mission_vierge.etapes["profil_saisi"] = EtatEtape.VALIDE
        mission_vierge.notes["profil_saisi"] = "Note test"
        sauvegarder_mission(mission_vierge)

        rechargee = charger_mission(mission_vierge.mission_id)
        assert rechargee.etapes["profil_saisi"] == EtatEtape.VALIDE
        assert rechargee.notes["profil_saisi"] == "Note test"
        assert rechargee.nom_client == mission_vierge.nom_client

    def test_chargement_fichier_inexistant_leve_erreur(self, tmp_data_dir):
        with pytest.raises(FileNotFoundError):
            charger_mission("mission_inexistante_xyz")

    def test_to_dict_serialisable_json(self, mission_vierge):
        d = mission_vierge.to_dict()
        # Doit être sérialisable JSON sans erreur
        json_str = json.dumps(d)
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["mission_id"] == mission_vierge.mission_id

    def test_from_dict_reconstitue_correctement(self, mission_vierge):
        d = mission_vierge.to_dict()
        rechargee = EtatMission.from_dict(d, mission_vierge.chemin_persistance)
        assert rechargee.mission_id == mission_vierge.mission_id
        assert rechargee.nom_client == mission_vierge.nom_client
        assert rechargee.cgp == mission_vierge.cgp

    def test_maj_date_derniere_maj_a_la_sauvegarde(self, mission_vierge):
        sauvegarder_mission(mission_vierge)
        assert mission_vierge.date_derniere_maj == date.today()

    def test_lister_missions_retourne_toutes(self, tmp_data_dir):
        creer_mission("Client A", "CGP")
        creer_mission("Client B", "CGP")
        missions = lister_missions()
        assert len(missions) >= 2

    def test_supprimer_mission(self, mission_vierge, tmp_data_dir):
        mid = mission_vierge.mission_id
        assert mission_vierge.chemin_persistance.exists()
        supprimer_mission(mid)
        assert not mission_vierge.chemin_persistance.exists()

    def test_supprimer_mission_inexistante_ne_crash_pas(self, tmp_data_dir):
        supprimer_mission("mission_inexistante_xyz")  # Ne doit pas lever


# ─── Tests state machine transitions ─────────────────────────────────────────


class TestStateMachine:
    def test_transition_non_commence_vers_en_cours(self, mission_vierge):
        m = mission_vierge
        assert m.etapes["profil_saisi"] == EtatEtape.NON_COMMENCE
        m.etapes["profil_saisi"] = EtatEtape.EN_COURS
        assert m.etapes["profil_saisi"] == EtatEtape.EN_COURS

    def test_transition_en_cours_vers_valide(self, mission_vierge):
        m = mission_vierge
        m.etapes["profil_saisi"] = EtatEtape.EN_COURS
        m.etapes["profil_saisi"] = EtatEtape.VALIDE
        assert m.etapes["profil_saisi"] == EtatEtape.VALIDE

    def test_transition_vers_bloque(self, mission_vierge):
        m = mission_vierge
        m.etapes["profil_saisi"] = EtatEtape.BLOQUE
        assert m.etapes["profil_saisi"] == EtatEtape.BLOQUE

    def test_transition_vers_skip(self, mission_vierge):
        m = mission_vierge
        m.etapes["monte_carlo"] = EtatEtape.SKIP
        assert m.etapes["monte_carlo"] == EtatEtape.SKIP

    def test_tous_les_etats_enum_valides(self):
        assert EtatEtape.NON_COMMENCE.value == "⬜"
        assert EtatEtape.EN_COURS.value == "🟡"
        assert EtatEtape.VALIDE.value == "✅"
        assert EtatEtape.BLOQUE.value == "🔴"
        assert EtatEtape.SKIP.value == "⏭️"

    def test_persistance_apres_transition(self, mission_vierge):
        m = mission_vierge
        m.etapes["profil_saisi"] = EtatEtape.VALIDE
        sauvegarder_mission(m)
        rechargee = charger_mission(m.mission_id)
        assert rechargee.etapes["profil_saisi"] == EtatEtape.VALIDE


# ─── Tests détection de blocages ─────────────────────────────────────────────


class TestDetecterBlocages:
    def test_mission_vierge_a_des_blocages(self, mission_vierge):
        """Les étapes avec dépendances sont bloquées dès le départ."""
        bloquees = detecter_blocages(mission_vierge)
        cles_bloquees = [e.cle for e in bloquees]
        # profilage_mif dépend de profil_saisi (non validé)
        assert "profilage_mif" in cles_bloquees

    def test_etape_sans_dependance_non_bloquee(self, mission_vierge):
        """profil_saisi n'a aucune dépendance → pas bloquée."""
        bloquees = detecter_blocages(mission_vierge)
        cles_bloquees = [e.cle for e in bloquees]
        assert "profil_saisi" not in cles_bloquees

    def test_dependance_validee_debloque_etape(self, mission_vierge):
        m = mission_vierge
        m.etapes["profil_saisi"] = EtatEtape.VALIDE
        bloquees = detecter_blocages(m)
        cles_bloquees = [e.cle for e in bloquees]
        # profilage_mif depend de profil_saisi validé → plus bloquée
        assert "profilage_mif" not in cles_bloquees

    def test_skip_debloque_aussi(self, mission_vierge):
        m = mission_vierge
        m.etapes["profil_saisi"] = EtatEtape.SKIP
        bloquees = detecter_blocages(m)
        cles_bloquees = [e.cle for e in bloquees]
        assert "profilage_mif" not in cles_bloquees

    def test_mission_complete_aucun_blocage(self, mission_complete):
        bloquees = detecter_blocages(mission_complete)
        assert bloquees == []

    def test_etape_validee_non_incluse_dans_blocages(self, mission_vierge):
        m = mission_vierge
        m.etapes["profil_saisi"] = EtatEtape.VALIDE
        bloquees = detecter_blocages(m)
        cles_bloquees = [e.cle for e in bloquees]
        assert "profil_saisi" not in cles_bloquees


# ─── Tests calcul de progression ─────────────────────────────────────────────


class TestCalculerProgression:
    def test_mission_vierge_pct_global_zero(self, mission_vierge):
        prog = calculer_progression(mission_vierge)
        assert prog["pct_global"] == 0

    def test_mission_complete_pct_global_cent(self, mission_complete):
        prog = calculer_progression(mission_complete)
        assert prog["pct_global"] == 100

    def test_mission_complete_pct_obligatoire_cent(self, mission_complete):
        prog = calculer_progression(mission_complete)
        assert prog["pct_obligatoire"] == 100

    def test_pct_global_entre_zero_et_cent(self, mission_rdv1_valide):
        prog = calculer_progression(mission_rdv1_valide)
        assert 0 < prog["pct_global"] < 100

    def test_pct_par_rdv_rdv1_present(self, mission_vierge):
        prog = calculer_progression(mission_vierge)
        assert "RDV1" in prog["pct_par_rdv"]

    def test_pct_rdv1_cent_apres_validation(self, mission_vierge):
        m = mission_vierge
        for etape in ETAPES_CANONIQUES:
            if etape.rdv == "RDV1":
                m.etapes[etape.cle] = EtatEtape.VALIDE
        prog = calculer_progression(m)
        assert prog["pct_par_rdv"]["RDV1"] == 100

    def test_prochaine_etape_non_none_sur_mission_vierge(self, mission_vierge):
        prog = calculer_progression(mission_vierge)
        assert prog["prochaine_etape"] is not None

    def test_prochaine_etape_none_sur_mission_complete(self, mission_complete):
        prog = calculer_progression(mission_complete)
        assert prog["prochaine_etape"] is None

    def test_alertes_presentes_si_blocages(self, mission_vierge):
        prog = calculer_progression(mission_vierge)
        # Des étapes ont des dépendances non validées → alertes
        assert len(prog["alertes"]) > 0

    def test_alertes_vides_si_mission_complete(self, mission_complete):
        prog = calculer_progression(mission_complete)
        assert prog["alertes"] == []

    def test_etapes_bloquees_dans_progression(self, mission_vierge):
        prog = calculer_progression(mission_vierge)
        assert isinstance(prog["etapes_bloquees"], list)

    def test_skip_compte_dans_pct_global(self, mission_vierge):
        m = mission_vierge
        # Marquer quelques étapes SKIP
        m.etapes["monte_carlo"] = EtatEtape.SKIP
        m.etapes["revue_3_mois"] = EtatEtape.SKIP
        prog = calculer_progression(m)
        assert prog["pct_global"] > 0

    def test_skip_ne_compte_pas_dans_pct_obligatoire(self, mission_vierge):
        m = mission_vierge
        # monte_carlo est obligatoire=False, skip ne doit pas affecter pct_obligatoire
        m.etapes["monte_carlo"] = EtatEtape.SKIP
        prog_sans = calculer_progression(mission_vierge)
        prog_avec = calculer_progression(m)
        # pct_obligatoire ne doit pas changer car monte_carlo n'est pas obligatoire
        assert prog_avec["pct_obligatoire"] == prog_sans["pct_obligatoire"]


# ─── Tests checklist ─────────────────────────────────────────────────────────


class TestChecklist:
    def test_etapes_canoniques_non_vide(self):
        assert len(ETAPES_CANONIQUES) > 0

    def test_toutes_les_cles_uniques(self):
        cles = [e.cle for e in ETAPES_CANONIQUES]
        assert len(cles) == len(set(cles))

    def test_etapes_par_cle_coherent(self):
        for etape in ETAPES_CANONIQUES:
            assert etape.cle in ETAPES_PAR_CLE
            assert ETAPES_PAR_CLE[etape.cle] is etape

    def test_dependances_referencent_cles_existantes(self):
        cles = {e.cle for e in ETAPES_CANONIQUES}
        for etape in ETAPES_CANONIQUES:
            for dep in etape.depends_on:
                assert dep in cles, f"Dépendance inconnue '{dep}' dans '{etape.cle}'"

    def test_phases_canoniques_valides(self):
        phases_valides = set(PHASES)
        for etape in ETAPES_CANONIQUES:
            assert etape.phase in phases_valides, f"Phase inconnue '{etape.phase}'"

    def test_pages_streamlit_existantes_ou_none(self):
        """Vérifie que chaque page_streamlit référencée existe dans pages/."""
        pages_dir = Path(__file__).parent.parent / "pages"
        for etape in ETAPES_CANONIQUES:
            if etape.page_streamlit is not None:
                page_path = pages_dir / etape.page_streamlit
                assert page_path.exists(), (
                    f"Page '{etape.page_streamlit}' référencée dans "
                    f"'{etape.cle}' introuvable dans pages/"
                )

    def test_rdv_valeurs_valides(self):
        rdv_valides = {None, "RDV1", "RDV2"}
        for etape in ETAPES_CANONIQUES:
            assert etape.rdv in rdv_valides, f"RDV invalide '{etape.rdv}' dans '{etape.cle}'"

    def test_au_moins_une_etape_obligatoire(self):
        assert any(e.obligatoire for e in ETAPES_CANONIQUES)

    def test_au_moins_une_etape_optionnelle(self):
        assert any(not e.obligatoire for e in ETAPES_CANONIQUES)


# ─── Tests slug ───────────────────────────────────────────────────────────────


class TestSlug:
    def test_accent_remplace(self):
        assert "e" in _slug("éléphant")

    def test_espaces_remplacent_par_underscore(self):
        result = _slug("Dupont Jean")
        assert " " not in result
        assert "_" in result

    def test_majuscules_minuscules(self):
        assert _slug("DUPONT") == "dupont"

    def test_caracteres_speciaux_supprimes(self):
        result = _slug("Dupont-Jean & Cie.")
        assert "&" not in result
        assert "." not in result
