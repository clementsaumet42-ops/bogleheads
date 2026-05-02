"""Tests cryptographiques des snapshots mission — Bloc A2."""

from __future__ import annotations

import json

import pytest


@pytest.fixture(scope="module")
def tmp_keys(tmp_path_factory):
    """Génère une paire de clés ECDSA P-256 dans un dossier temporaire."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    keys_dir = tmp_path_factory.mktemp("keys")
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    private_path = keys_dir / "private.pem"
    public_path = keys_dir / "public.pem"

    private_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return {"private": private_path, "public": public_path}


@pytest.fixture
def snapshot_simple():
    """Snapshot minimal pour les tests."""
    from src.mission.snapshot import construire_snapshot_mission

    return construire_snapshot_mission(
        mission_id="test_mission_crypto_001",
        inputs_client={"client": "Test Client", "age": 45},
        frozen_ts="2026-01-15T10:00:00",
    )


class TestConstruireSnapshot:
    def test_contient_champs_requis(self, snapshot_simple):
        assert "mission_id" in snapshot_simple
        assert "timestamp" in snapshot_simple
        assert "hypotheses_fiscales" in snapshot_simple
        assert "config_cabinet" in snapshot_simple
        assert "versions_deps" in snapshot_simple
        assert "git_commit" in snapshot_simple
        assert "schema_version" in snapshot_simple

    def test_mission_id_correct(self, snapshot_simple):
        assert snapshot_simple["mission_id"] == "test_mission_crypto_001"

    def test_timestamp_fige(self, snapshot_simple):
        assert snapshot_simple["timestamp"] == "2026-01-15T10:00:00"

    def test_versions_deps_presentes(self, snapshot_simple):
        deps = snapshot_simple["versions_deps"]
        assert "numpy" in deps
        assert deps["numpy"] != "not_installed"

    def test_hypotheses_fiscales_non_vides(self, snapshot_simple):
        assert len(snapshot_simple["hypotheses_fiscales"]) > 0

    def test_inputs_client_present(self, snapshot_simple):
        assert snapshot_simple["inputs_client"]["age"] == 45


class TestSignatureECDSA:
    def test_signer_produit_bytes(self, snapshot_simple, tmp_keys):
        from src.mission.snapshot import signer_snapshot

        sig = signer_snapshot(snapshot_simple, tmp_keys["private"])
        assert isinstance(sig, bytes)
        assert len(sig) > 0

    def test_verifier_signature_valide(self, snapshot_simple, tmp_keys):
        from src.mission.snapshot import signer_snapshot, verifier_signature

        sig = signer_snapshot(snapshot_simple, tmp_keys["private"])
        assert verifier_signature(snapshot_simple, sig, tmp_keys["public"]) is True

    def test_signature_invalide_apres_alteration(self, snapshot_simple, tmp_keys):
        from src.mission.snapshot import signer_snapshot, verifier_signature

        sig = signer_snapshot(snapshot_simple, tmp_keys["private"])
        snapshot_altere = dict(snapshot_simple)
        snapshot_altere["mission_id"] = "mission_ALTEREE"
        assert verifier_signature(snapshot_altere, sig, tmp_keys["public"]) is False

    def test_cle_privee_inexistante_leve_error(self, snapshot_simple, tmp_path):
        from src.mission.snapshot import signer_snapshot

        cle_absente = tmp_path / "inexistante.pem"
        with pytest.raises(FileNotFoundError):
            signer_snapshot(snapshot_simple, cle_absente)

    def test_cle_publique_inexistante_leve_error(self, snapshot_simple, tmp_keys, tmp_path):
        from src.mission.snapshot import signer_snapshot, verifier_signature

        sig = signer_snapshot(snapshot_simple, tmp_keys["private"])
        cle_absente = tmp_path / "inexistante_pub.pem"
        with pytest.raises(FileNotFoundError):
            verifier_signature(snapshot_simple, sig, cle_absente)

    def test_determinisme_signature_bytes_differents(self, snapshot_simple, tmp_keys):
        """ECDSA est non-déterministe par design (k aléatoire) → deux signatures différentes."""
        from src.mission.snapshot import signer_snapshot, verifier_signature

        sig1 = signer_snapshot(snapshot_simple, tmp_keys["private"])
        sig2 = signer_snapshot(snapshot_simple, tmp_keys["private"])
        # Les deux doivent être valides même si différentes
        assert verifier_signature(snapshot_simple, sig1, tmp_keys["public"]) is True
        assert verifier_signature(snapshot_simple, sig2, tmp_keys["public"]) is True


class TestSauvegardeEtChargement:
    def test_sauvegarder_cree_deux_fichiers(self, snapshot_simple, tmp_keys, tmp_path):
        from src.mission.snapshot import sauvegarder_snapshot_signe, signer_snapshot

        sig = signer_snapshot(snapshot_simple, tmp_keys["private"])
        dossier = tmp_path / "annexes" / "snapshot"
        j, s = sauvegarder_snapshot_signe(snapshot_simple, sig, dossier, "test_mission")
        assert j.exists()
        assert s.exists()
        assert j.suffix == ".json"
        assert s.name.endswith(".json.sig")

    def test_round_trip_json_identique(self, snapshot_simple, tmp_keys, tmp_path):
        from src.mission.snapshot import (
            charger_snapshot_depuis_fichier,
            sauvegarder_snapshot_signe,
            signer_snapshot,
        )

        sig = signer_snapshot(snapshot_simple, tmp_keys["private"])
        dossier = tmp_path / "snap"
        j, _ = sauvegarder_snapshot_signe(snapshot_simple, sig, dossier, "test_round")
        rechargé = charger_snapshot_depuis_fichier(j)
        assert rechargé["mission_id"] == snapshot_simple["mission_id"]
        assert rechargé["timestamp"] == snapshot_simple["timestamp"]


class TestVerifierSnapshotFichier:
    def test_snapshot_valide_retourne_ok(self, snapshot_simple, tmp_keys, tmp_path):
        from src.mission.snapshot import (
            sauvegarder_snapshot_signe,
            signer_snapshot,
            verifier_snapshot_fichier,
        )

        sig = signer_snapshot(snapshot_simple, tmp_keys["private"])
        dossier = tmp_path / "snap"
        j, _ = sauvegarder_snapshot_signe(snapshot_simple, sig, dossier, "test_valid")
        result = verifier_snapshot_fichier(j, tmp_keys["public"])
        assert result["ok"] is True
        assert len(result["erreurs"]) == 0

    def test_snapshot_altere_retourne_erreur(self, snapshot_simple, tmp_keys, tmp_path):
        from src.mission.snapshot import (
            sauvegarder_snapshot_signe,
            signer_snapshot,
            verifier_snapshot_fichier,
        )

        sig = signer_snapshot(snapshot_simple, tmp_keys["private"])
        dossier = tmp_path / "snap2"
        dossier.mkdir(parents=True)
        j, s = sauvegarder_snapshot_signe(snapshot_simple, sig, dossier, "test_altere")
        # Altérer le JSON après signature
        data = json.loads(j.read_bytes())
        data["mission_id"] = "ALTERE"
        j.write_bytes(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2).encode())
        result = verifier_snapshot_fichier(j, tmp_keys["public"])
        assert result["ok"] is False
        assert any("INVALIDE" in e for e in result["erreurs"])

    def test_fichier_inexistant_retourne_erreur(self, tmp_path):
        from src.mission.snapshot import verifier_snapshot_fichier

        j = tmp_path / "inexistant.json"
        result = verifier_snapshot_fichier(j)
        assert result["ok"] is False
