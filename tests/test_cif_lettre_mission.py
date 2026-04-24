from __future__ import annotations

import pypdf


def test_generer_lettre_mission(tmp_path):
    from src.cif.lettre_mission import generer_lettre_mission

    cfg = {
        "cabinet": {
            "nom": "Cabinet",
            "nom_ec": "Dupont",
            "prenom_ec": "Jean",
            "adresse": "Paris",
            "email": "test@test.fr",
            "numero_orias": "12345",
        },
        "remuneration": {"mode": "honoraires", "mention_retrocessions": "Aucune"},
        "tarifs": {
            "mission_initiale_forfait_eur": 3000,
            "suivi_annuel_forfait_eur": 1200,
            "taux_horaire_eur": 250,
        },
    }
    client = {"nom": "Martin", "prenom": "Paul", "adresse": "Lyon", "email": "p@m.fr"}
    out = tmp_path / "lm.pdf"
    path = generer_lettre_mission(cfg, client, out)
    assert path.exists()
    r = pypdf.PdfReader(str(path))
    assert len(r.pages) == 3
