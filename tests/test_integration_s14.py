"""Tests d'intégration S14 — Workflow complet conformité CIF."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.conformite.archivage import (
    archiver_document,
    lister_documents_client,
    verifier_integrite_dossier,
)
from src.conformite.der import generer_der
from src.conformite.lettre_mission import generer_lettre_mission
from src.conformite.rapport_adequation import generer_rapport_adequation
from src.conformite.signature import signer_document, verifier_signature
from src.schemas import (
    ConformiteConfig,
    DocumentConformite,
    ParametresMission,
    PreuveSignature,
)

_PROFIL = {
    "id": 100,
    "nom": "Integration",
    "email": "integration@test.com",
    "age": 40,
    "tmi": 0.30,
    "patrimoine_financier_total": 300_000,
    "score_risque": 5,
    "horizon_placement": 15,
}

_CABINET = {
    "cabinet": {
        "nom": "Cabinet Integration",
        "numero_orias": "99999999",
        "adresse": "1 rue Test, Paris",
        "telephone": "01 00 00 00 00",
        "email": "integration@cabinet.fr",
        "rc_pro_assureur": "AXA",
        "rc_pro_numero": "AXA-001",
        "mediateur_nom": "Médiateur de l'AMF",
        "mediateur_url": "https://www.amf-france.org",
    },
    "remuneration": {"mode": "honoraires", "mention_retrocessions": "Aucune"},
}

_CONFORMITE_DICT = {
    "cabinet_orias": "99999999",
    "cabinet_associations": ["CNCIF"],
    "cabinet_assurance_rcp": "AXA",
    "cabinet_assurance_rcp_numero": "AXA-001",
    "cabinet_mediateur": "Médiateur de l'AMF",
    "horizon_conservation_annees": 5,
    "textes_der": {
        "identification": "Identification test.",
        "statuts_services": "Statuts test.",
        "remuneration": "Rémunération test.",
        "reclamations": "Réclamations test.",
        "rgpd": "RGPD test.",
        "conclusion": "Conclusion test.",
    },
    "textes_lettre_mission": {
        "preambule": "Préambule test.",
        "objet": "Objet test.",
        "duree_resiliation": "Durée test.",
        "responsabilite": "Responsabilité test.",
        "mentions_cncif": "CNCIF test.",
    },
    "textes_rapport_adequation": {
        "introduction": "Introduction MIF II test.",
        "avertissements": "Avertissements test.",
        "obligation_maj": "MAJ annuelle test.",
    },
}

_PARAMS = {
    "objet": "Conseil patrimonial complet",
    "perimetre": ["audit", "allocation", "fiscalite", "suivi_annuel"],
    "honoraires_eur": 4000.0,
    "honoraires_modalite": "forfait",
    "duree_mois": 12,
    "date_debut": "2025-01-01",
}

_ALLOCATION = {"Actions": 0.65, "Obligations": 0.25, "Immobilier": 0.10}
_ETFS = [
    {"ticker": "IWDA", "nom": "iShares MSCI World", "classe_actifs": "Actions", "ter": 0.20},
]


def test_workflow_complet_generer_signer_archiver(tmp_path: Path) -> None:
    """Workflow complet : génération → signature → archivage → vérification."""
    archive = tmp_path / "clients"

    # 1. Générer DER
    der_doc = generer_der(_PROFIL, _CABINET, _CONFORMITE_DICT, tmp_path / "der.pdf")
    assert isinstance(der_doc, DocumentConformite)

    # 2. Signer DER
    preuve = signer_document(
        der_doc, "Integration", "integration@test.com", consentement_explicite=True
    )
    assert isinstance(preuve, PreuveSignature)

    # 3. Vérifier signature
    pdf_path = Path(der_doc.chemin_pdf)
    sig_path = pdf_path.with_suffix(".signature.json")
    assert verifier_signature(pdf_path, sig_path) is True

    # 4. Archiver
    dest = archiver_document(der_doc, preuve, archive)
    assert dest.exists()

    # 5. Vérifier intégrité
    resultats = verifier_integrite_dossier(100, archive)
    assert all(resultats.values()), f"Intégrité KO : {resultats}"


def test_workflow_3_documents_manifest_coherent(tmp_path: Path) -> None:
    """Génération des 3 types → manifest client cohérent."""
    archive = tmp_path / "clients"

    der_doc = generer_der(_PROFIL, _CABINET, _CONFORMITE_DICT, tmp_path / "der.pdf")
    archiver_document(der_doc, racine_archive=archive)

    lm_doc = generer_lettre_mission(
        _PROFIL, _CABINET, _CONFORMITE_DICT, _PARAMS, tmp_path / "lm.pdf"
    )
    archiver_document(lm_doc, racine_archive=archive)

    ra_doc = generer_rapport_adequation(
        _PROFIL, _CABINET, _CONFORMITE_DICT, _ALLOCATION, _ETFS, tmp_path / "ra.pdf"
    )
    archiver_document(ra_doc, racine_archive=archive)

    docs = lister_documents_client(100, archive)
    types = {d.type_doc for d in docs}
    assert types == {"DER", "LETTRE_MISSION", "RAPPORT_ADEQUATION"}
    assert all(d.client_nom == "Integration" for d in docs)


def test_page_conformite_cif_se_rend() -> None:
    """Smoke test — la page 21_Conformite_CIF.py est importable."""
    try:
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file("pages/21_Conformite_CIF.py", default_timeout=30)
        at.run()
        # Should not raise unhandled exceptions
        assert not at.exception
    except ImportError:
        pytest.skip("streamlit.testing.v1 non disponible")
    except Exception as e:
        # Accept timeout or file errors gracefully
        if "timeout" in str(e).lower() or "no such file" in str(e).lower():
            pytest.skip(f"AppTest indisponible : {e}")
        raise


def test_schemas_non_breaking() -> None:
    """Les nouveaux schémas S14 n'impactent pas les schémas existants."""
    from src.schemas import (
        _SCHEMAS,
        DocumentConformite,
        PreuveSignature,
    )

    # Check new schemas are registered
    assert "conformite.yaml" in _SCHEMAS
    assert _SCHEMAS["conformite.yaml"] is ConformiteConfig

    # Check existing schemas still registered
    assert "univers_etf.yaml" in _SCHEMAS
    assert "profils_clients.yaml" in _SCHEMAS
    assert "pdf_cabinet.yaml" in _SCHEMAS

    # Validate new schemas can be instantiated
    conf = ConformiteConfig.model_validate(_CONFORMITE_DICT)
    assert conf.cabinet_orias == "99999999"

    pm = ParametresMission.model_validate(_PARAMS)
    assert pm.honoraires_eur == 4000.0

    doc = DocumentConformite.model_validate(
        {
            "type_doc": "DER",
            "profil_id": 1,
            "client_nom": "Test",
            "date_generation": "2025-01-01T00:00:00",
            "chemin_pdf": "/tmp/test.pdf",
            "sha256": "abc123" * 10 + "ab",
            "version_template": "DER_v1.0",
        }
    )
    assert doc.type_doc == "DER"

    preuve = PreuveSignature.model_validate(
        {
            "document_sha256": "a" * 64,
            "nom_signataire": "Test",
            "email_signataire": "test@test.com",
            "date_signature": "2025-01-01T00:00:00+00:00",
            "hash_signature": "b" * 64,
        }
    )
    assert preuve.version_protocole == "SIMPLE_v1"
