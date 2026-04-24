from __future__ import annotations

from src.profilage.synthese import ProfilConsolide, synthetiser_profil


def test_synthetiser_simple():
    pc = synthetiser_profil("moyenne")
    assert isinstance(pc, ProfilConsolide)
    assert pc.recommandation_allocation is not None


def test_delta_aligne():
    pc = synthetiser_profil("moyenne")
    assert pc.delta_confiance == "aligne"
