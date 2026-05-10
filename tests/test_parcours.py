"""Tests src/mission/parcours.py — mapping pages<->phases + helpers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src.mission.checklist import ETAPES_CANONIQUES
from src.mission.etat import EtatEtape, EtatMission
from src.mission.parcours import (
    PHASES_PAR_CLE,
    PHASES_PAR_NUMERO,
    PHASES_PARCOURS,
    phase_courante,
    phase_d_une_etape,
    phase_d_une_page,
    phases_terminees,
    prochaine_page_recommandee,
    progression_par_phase,
)

# ── Structure des phases ─────────────────────────────────────────────────


def test_7_phases_definies():
    assert len(PHASES_PARCOURS) == 7
    assert {p.numero for p in PHASES_PARCOURS} == {1, 2, 3, 4, 5, 6, 7}


def test_phases_ordre_numerique():
    numeros = [p.numero for p in PHASES_PARCOURS]
    assert numeros == sorted(numeros)


def test_index_par_cle_et_numero_coherents():
    for phase in PHASES_PARCOURS:
        assert PHASES_PAR_CLE[phase.cle] is phase
        assert PHASES_PAR_NUMERO[phase.numero] is phase


def test_chaque_phase_a_titre_objectif_livrable():
    for phase in PHASES_PARCOURS:
        assert phase.titre.strip()
        assert phase.objectif.strip()
        assert phase.livrable_principal.strip()
        assert phase.duree_indicative.strip()


# ── Mapping pages -> phases ──────────────────────────────────────────────


def test_mapping_pages_couvre_pages_reelles():
    """Toute page mappee doit exister dans pages/."""
    pages_dir = Path(__file__).parent.parent / "pages"
    pages_existantes = {p.name for p in pages_dir.glob("*.py")}
    for phase in PHASES_PARCOURS:
        for page in phase.pages:
            assert page in pages_existantes, (
                f"Page mappee phase {phase.numero} absente de pages/ : {page}"
            )


def test_pas_de_doublon_de_page_entre_phases():
    """Une page ne doit appartenir qu'a une seule phase."""
    seen: dict[str, int] = {}
    for phase in PHASES_PARCOURS:
        for page in phase.pages:
            assert page not in seen, f"Page {page} mappee aux phases {seen[page]} et {phase.numero}"
            seen[page] = phase.numero


def test_phase_d_une_page_avec_extension():
    phase = phase_d_une_page("24_Import_Patrimoine.py")
    assert phase is not None
    assert phase.cle == "diagnostic"


def test_phase_d_une_page_sans_extension():
    phase = phase_d_une_page("05_Allocation")
    assert phase is not None
    assert phase.cle == "recommandations"


def test_phase_d_une_page_inconnue_renvoie_none():
    assert phase_d_une_page("99_NEXISTE_PAS.py") is None


# ── Mapping etapes -> phases ─────────────────────────────────────────────


def test_etapes_mappees_existent_dans_checklist():
    cles_checklist = {e.cle for e in ETAPES_CANONIQUES}
    for phase in PHASES_PARCOURS:
        for cle in phase.etapes_canoniques:
            assert cle in cles_checklist, (
                f"Etape {cle} mappee phase {phase.numero} absente de checklist"
            )


def test_phase_d_une_etape():
    assert phase_d_une_etape("profil_saisi").cle == "onboarding"
    assert phase_d_une_etape("allocation_cible").cle == "recommandations"
    assert phase_d_une_etape("conformite").cle == "livrables"


def test_phase_etape_inconnue_renvoie_none():
    assert phase_d_une_etape("blabla_inconnue") is None


# ── Logique de phase courante ────────────────────────────────────────────


def _mission_neuve(tmp_path) -> EtatMission:
    return EtatMission(
        mission_id="test",
        nom_client="Test",
        cgp="EC",
        date_creation=date.today(),
        date_derniere_maj=date.today(),
        etapes={e.cle: EtatEtape.NON_COMMENCE for e in ETAPES_CANONIQUES},
        chemin_persistance=tmp_path / "test.json",
    )


def test_phase_courante_mission_neuve_est_onboarding(tmp_path):
    """Phase 1 n'a pas d'etapes obligatoires : on tombe direct sur onboarding."""
    etat = _mission_neuve(tmp_path)
    phase = phase_courante(etat)
    assert phase.cle == "onboarding"


def test_phase_courante_avance_apres_validation(tmp_path):
    etat = _mission_neuve(tmp_path)
    # Valide les etapes obligatoires de l'onboarding
    for cle in ("profil_saisi", "profilage_mif", "lettre_mission"):
        etat.etapes[cle] = EtatEtape.VALIDE
    phase = phase_courante(etat)
    assert phase.cle == "recommandations"  # diagnostic n'a pas d'etape obligatoire


def test_phase_courante_passe_en_suivi_si_tout_valide(tmp_path):
    etat = _mission_neuve(tmp_path)
    for e in ETAPES_CANONIQUES:
        etat.etapes[e.cle] = EtatEtape.VALIDE
    phase = phase_courante(etat)
    assert phase.cle == "suivi_annuel"


# ── Progression et terminees ─────────────────────────────────────────────


def test_progression_par_phase_neuve_a_zero(tmp_path):
    etat = _mission_neuve(tmp_path)
    progressions = progression_par_phase(etat)
    assert all(v == 0 for v in progressions.values())


def test_progression_par_phase_remonte_apres_validation(tmp_path):
    etat = _mission_neuve(tmp_path)
    etat.etapes["profil_saisi"] = EtatEtape.VALIDE
    progressions = progression_par_phase(etat)
    # Onboarding a 3 etapes -> 33%
    assert progressions[2] == pytest.approx(33, abs=1)


def test_phases_terminees_vide_si_neuve(tmp_path):
    etat = _mission_neuve(tmp_path)
    assert phases_terminees(etat) == []


def test_phases_terminees_inclut_onboarding_apres_validation(tmp_path):
    etat = _mission_neuve(tmp_path)
    for cle in ("profil_saisi", "profilage_mif", "lettre_mission"):
        etat.etapes[cle] = EtatEtape.VALIDE
    terminees = phases_terminees(etat)
    cles = [p.cle for p in terminees]
    assert "onboarding" in cles


# ── Prochaine page recommandee ───────────────────────────────────────────


def test_prochaine_page_neuve_renvoie_onboarding(tmp_path):
    etat = _mission_neuve(tmp_path)
    page = prochaine_page_recommandee(etat)
    assert page == "04_Profil.py"


def test_prochaine_page_apres_onboarding_renvoie_recommandations(tmp_path):
    etat = _mission_neuve(tmp_path)
    for cle in ("profil_saisi", "profilage_mif", "lettre_mission"):
        etat.etapes[cle] = EtatEtape.VALIDE
    page = prochaine_page_recommandee(etat)
    assert page == "05_Allocation.py"


def test_prochaine_page_phase_7_renvoie_none(tmp_path):
    """La phase suivi n'a pas encore de page dediee."""
    etat = _mission_neuve(tmp_path)
    for e in ETAPES_CANONIQUES:
        etat.etapes[e.cle] = EtatEtape.VALIDE
    page = prochaine_page_recommandee(etat)
    assert page is None
