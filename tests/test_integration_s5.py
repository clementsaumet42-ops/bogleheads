from __future__ import annotations


def test_references_legales():
    from src.cif.references_legales import REFERENCES, citer

    assert len(REFERENCES) > 5
    assert "Art." in citer("ART_L541_1_CMF")
    assert "[INCONNU]" in citer("INCONNU")


def test_questionnaire_mif2():
    from src.cif.questionnaire_mif2 import QuestionnaireMIF2

    q = QuestionnaireMIF2(connait_actions=True, annees_experience="plus_5")
    assert q.niveau_connaissance_global() in ("debutant", "intermediaire", "avance")


def test_export_cloud_stub():
    from src.cif.export_cloud import archiver_dossier_client

    r = archiver_dossier_client("C1", [])
    assert r["statut"] == "stub"


def test_profil_amf():
    from src.profilage.amf import ProfilAMF

    p = ProfilAMF(connait_actions=True, connait_obligations=True, a_deja_investi=True)
    assert p.niveau_connaissance_global() == "intermediaire"
