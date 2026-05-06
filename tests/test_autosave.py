"""Tests S18-A — Module autosave."""

from __future__ import annotations

import json

import pytest

from src.mission.autosave import (
    filtrer_session_state,
    restaurer_session,
    sauvegarder_immediatement,
)
from src.mission.etat import EtatMission, charger_mission, creer_mission, sauvegarder_mission

# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    import src.mission.etat as etat_mod

    monkeypatch.setattr(etat_mod, "_DEFAULT_DATA_DIR", tmp_path / "missions")
    return tmp_path / "missions"


@pytest.fixture
def mission_vierge(tmp_data_dir) -> EtatMission:
    return creer_mission("Dupont Jean", "Alice EC")


# ─── Tests filtrer_session_state ─────────────────────────────────────────────


class TestFiltrerSessionState:
    def test_valeur_simple_conservee(self):
        state = {"age": 45, "nom": "Dupont", "tmi": 0.30}
        result = filtrer_session_state(state)
        assert result["age"] == 45
        assert result["nom"] == "Dupont"
        assert result["tmi"] == 0.30

    def test_cle_interne_exclue(self):
        state = {"_internal": "ignore", "_btn_ok": True, "age": 30}
        result = filtrer_session_state(state)
        assert "_internal" not in result
        assert "_btn_ok" not in result
        assert "age" in result

    def test_objet_non_serialisable_exclu(self):
        class MonObjet:
            pass

        state = {"valide": 42, "invalide": MonObjet()}
        result = filtrer_session_state(state)
        assert "valide" in result
        assert "invalide" not in result

    def test_dataframe_converti_en_liste(self):
        pytest.importorskip("pandas")
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        state = {"df": df}
        result = filtrer_session_state(state)
        assert "df" in result
        assert isinstance(result["df"], list)

    def test_liste_et_dict_conserves(self):
        state = {"liste": [1, 2, 3], "nested": {"x": 1}}
        result = filtrer_session_state(state)
        assert result["liste"] == [1, 2, 3]
        assert result["nested"] == {"x": 1}

    def test_none_conserve(self):
        state = {"valeur": None}
        result = filtrer_session_state(state)
        assert "valeur" in result
        assert result["valeur"] is None

    def test_resultat_est_serialisable_json(self):
        state = {"age": 45, "nom": "Dupont", "tmi": 0.30, "liste": [1, 2]}
        result = filtrer_session_state(state)
        json_str = json.dumps(result)
        assert isinstance(json_str, str)


# ─── Tests round-trip session_state via EtatMission ──────────────────────────


class TestRoundTripSession:
    def test_snapshot_sauvegarde_et_recharge(self, mission_vierge):
        snapshot = {"age": 45, "nom": "Dupont", "tmi": 0.30}
        mission_vierge.session_state_snapshot = snapshot
        sauvegarder_mission(mission_vierge)

        rechargee = charger_mission(mission_vierge.mission_id)
        assert rechargee.session_state_snapshot == snapshot

    def test_snapshot_none_par_defaut(self, mission_vierge):
        assert mission_vierge.session_state_snapshot is None

    def test_ancienne_mission_sans_snapshot_charge_sans_erreur(self, tmp_data_dir):
        """Rétro-compatibilité : missions S16 sans session_state_snapshot."""

        # Créer un fichier JSON ancien (sans session_state_snapshot)

        mission_id = "old_mission_test"
        chemin = tmp_data_dir / f"{mission_id}.json"
        tmp_data_dir.mkdir(parents=True, exist_ok=True)
        chemin.write_text(
            json.dumps(
                {
                    "mission_id": mission_id,
                    "nom_client": "Ancien Client",
                    "conseiller": "EC",
                    "date_creation": "2024-01-01",
                    "date_derniere_maj": "2024-01-01",
                    "etapes": {},
                    "notes": {},
                    # PAS de session_state_snapshot
                }
            ),
            encoding="utf-8",
        )

        etat = charger_mission(mission_id)
        assert etat.session_state_snapshot is None
        assert etat.nom_client == "Ancien Client"

    def test_to_dict_sans_snapshot_ne_contient_pas_la_cle(self, mission_vierge):
        d = mission_vierge.to_dict()
        assert "session_state_snapshot" not in d

    def test_to_dict_avec_snapshot_contient_la_cle(self, mission_vierge):
        mission_vierge.session_state_snapshot = {"age": 45}
        d = mission_vierge.to_dict()
        assert "session_state_snapshot" in d
        assert d["session_state_snapshot"] == {"age": 45}


# ─── Tests restaurer_session ──────────────────────────────────────────────────


class TestRestaurerSession:
    def test_restaure_snapshot_existant(self, mission_vierge):
        snapshot = {"age": 45, "tmi": 0.30}
        mission_vierge.session_state_snapshot = snapshot
        sauvegarder_mission(mission_vierge)

        result = restaurer_session(mission_vierge.mission_id)
        assert result == snapshot

    def test_retourne_dict_vide_si_pas_de_snapshot(self, mission_vierge):
        result = restaurer_session(mission_vierge.mission_id)
        assert result == {}

    def test_retourne_dict_vide_si_mission_inexistante(self, tmp_data_dir):
        result = restaurer_session("mission_inexistante_xyz")
        assert result == {}


# ─── Tests sauvegarder_immediatement ─────────────────────────────────────────


class TestSauvegarderImmediatement:
    def test_sauvegarde_cle_simple(self, mission_vierge):
        sauvegarder_immediatement(mission_vierge.mission_id, "age", 45)
        rechargee = charger_mission(mission_vierge.mission_id)
        assert rechargee.session_state_snapshot is not None
        assert rechargee.session_state_snapshot["age"] == 45

    def test_sauvegarde_merge_avec_snapshot_existant(self, mission_vierge):
        mission_vierge.session_state_snapshot = {"nom": "Dupont"}
        sauvegarder_mission(mission_vierge)

        sauvegarder_immediatement(mission_vierge.mission_id, "age", 45)
        rechargee = charger_mission(mission_vierge.mission_id)
        assert rechargee.session_state_snapshot["nom"] == "Dupont"
        assert rechargee.session_state_snapshot["age"] == 45

    def test_valeur_non_serialisable_ignoree_sans_erreur(self, mission_vierge):
        class Objet:
            pass

        sauvegarder_immediatement(mission_vierge.mission_id, "mauvais", Objet())
        rechargee = charger_mission(mission_vierge.mission_id)
        # La clé ne doit pas être présente
        snapshot = rechargee.session_state_snapshot or {}
        assert "mauvais" not in snapshot

    def test_mission_inexistante_ne_leve_pas(self, tmp_data_dir):
        sauvegarder_immediatement("mission_inexistante_xyz", "age", 45)
