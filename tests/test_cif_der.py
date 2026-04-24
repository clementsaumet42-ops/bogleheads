from __future__ import annotations

import pypdf


def test_generer_der(tmp_path):
    from src.cif.der import generer_der

    cfg = {
        "cabinet": {
            "nom": "Cabinet",
            "nom_ec": "Dupont",
            "prenom_ec": "Jean",
            "adresse": "Paris",
            "telephone": "",
            "email": "test@test.fr",
            "numero_orias": "12345678",
            "rc_pro_assureur": "AXA",
            "rc_pro_numero": "P001",
            "rc_pro_montant_eur": 1500000,
            "mediateur_nom": "AMF",
            "mediateur_url": "https://amf-france.org",
            "conflits_interets": "Aucune",
        },
        "remuneration": {"mode": "honoraires", "mention_retrocessions": "Aucune"},
    }
    out = tmp_path / "der.pdf"
    path = generer_der(cfg, out)
    assert path.exists()
    r = pypdf.PdfReader(str(path))
    assert len(r.pages) == 2
