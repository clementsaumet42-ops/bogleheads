"""Snapshot mission complet avec signature ECDSA P-256.

Génère un snapshot cryptographiquement signé de toutes les hypothèses,
paramètres cabinet, inputs client et versions de dépendances, au moment
de la génération du ZIP livrables.

Usage CLI:
    python -m bogleheads.snapshot verify <snapshot.json>
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default paths
ROOT = Path(__file__).parent.parent.parent
KEYS_DIR = ROOT / "config" / "cabinet" / "keys"
PRIVATE_KEY_PATH = KEYS_DIR / "private.pem"
PUBLIC_KEY_PATH = KEYS_DIR / "public.pem"

_DEPS_CRITIQUES = ["numpy", "scipy", "pandas", "reportlab", "cryptography"]


def _git_commit_sha() -> str:
    """Retourne le SHA du commit HEAD courant, ou 'unknown' si git indisponible."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=ROOT,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _versions_deps() -> dict[str, str]:
    """Collecte les versions des dépendances Python critiques."""
    versions = {}
    for dep in _DEPS_CRITIQUES:
        try:
            versions[dep] = importlib.metadata.version(dep)
        except importlib.metadata.PackageNotFoundError:
            versions[dep] = "not_installed"
    return versions


def _charger_config_cabinet() -> dict[str, Any]:
    """Charge config/cabinet.yaml ou cabinet.example.yaml comme fallback."""
    cabinet_path = ROOT / "config" / "cabinet.yaml"
    example_path = ROOT / "config" / "cabinet.example.yaml"
    chemin = cabinet_path if cabinet_path.exists() else example_path
    if not chemin.exists():
        return {"source": "absent"}
    import yaml

    with open(chemin, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _charger_hypotheses_fiscales() -> dict[str, Any]:
    """Charge les hypothèses actives depuis le catalogue."""
    try:
        from src.hypotheses.catalogue import _get_catalogue
        from src.hypotheses.snapshot import _hypothese_to_dict

        catalogue = dict(_get_catalogue())
        return {cle: _hypothese_to_dict(h) for cle, h in sorted(catalogue.items())}
    except Exception as exc:
        logger.warning("Impossible de charger les hypothèses : %s", exc)
        return {}


def construire_snapshot_mission(
    mission_id: str,
    inputs_client: dict[str, Any] | None = None,
    livrables_sha256: dict[str, str] | None = None,
    frozen_ts: str | None = None,
) -> dict[str, Any]:
    """Construit le dict complet du snapshot mission.

    Args:
        mission_id: Identifiant unique de la mission.
        inputs_client: Données client validées (YAML/dict sérialisable).
        livrables_sha256: Mapping {nom_fichier: sha256_hex} des livrables générés.
        frozen_ts: Timestamp ISO figé (pour tests). Si None, utilise datetime.now().

    Returns:
        Dict JSON-sérialisable représentant le snapshot complet.
    """
    ts = frozen_ts or os.environ.get("MISSION_TEST_FROZEN_TIME") or datetime.now().isoformat()

    snapshot: dict[str, Any] = {
        "schema_version": "1.0",
        "mission_id": mission_id,
        "timestamp": ts,
        "git_commit": _git_commit_sha(),
        "hypotheses_fiscales": _charger_hypotheses_fiscales(),
        "config_cabinet": _charger_config_cabinet(),
        "versions_deps": _versions_deps(),
        "inputs_client": inputs_client or {},
        "livrables_sha256": livrables_sha256 or {},
    }
    return snapshot


def _snapshot_bytes(snapshot: dict[str, Any]) -> bytes:
    """Sérialise le snapshot en bytes déterministes (JSON trié)."""
    return json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")


def sha256_snapshot(snapshot: dict[str, Any]) -> str:
    """Calcule le SHA-256 du snapshot."""
    return hashlib.sha256(_snapshot_bytes(snapshot)).hexdigest()


def signer_snapshot(
    snapshot: dict[str, Any],
    cle_privee_path: Path | None = None,
) -> bytes:
    """Signe le snapshot avec la clé ECDSA P-256 du cabinet.

    Args:
        snapshot: Dict snapshot (sera sérialisé en JSON trié).
        cle_privee_path: Chemin vers private.pem. Défaut: config/cabinet/keys/private.pem.

    Returns:
        Signature DER encodée en bytes.

    Raises:
        FileNotFoundError: Si la clé privée est introuvable.
        RuntimeError: Si la bibliothèque cryptography n'est pas disponible.
    """
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
    except ImportError as e:
        raise RuntimeError(
            "La bibliothèque 'cryptography' est requise pour signer les snapshots. "
            "Installez-la avec: pip install cryptography"
        ) from e

    chemin = cle_privee_path or PRIVATE_KEY_PATH
    if not chemin.exists():
        raise FileNotFoundError(
            f"Clé privée introuvable : {chemin}\n"
            "Générez la paire de clés avec: python tools/init_cabinet_keys.py"
        )

    pem_bytes = chemin.read_bytes()
    private_key = serialization.load_pem_private_key(pem_bytes, password=None)

    if not isinstance(private_key, ec.EllipticCurvePrivateKey):
        raise ValueError("La clé privée doit être de type ECDSA (courbe elliptique).")

    data = _snapshot_bytes(snapshot)
    signature = private_key.sign(data, ec.ECDSA(hashes.SHA256()))
    return signature


def verifier_signature(
    snapshot: dict[str, Any],
    signature: bytes,
    cle_publique_path: Path | None = None,
) -> bool:
    """Vérifie la signature ECDSA du snapshot.

    Returns:
        True si la signature est valide, False sinon.
    """
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
    except ImportError:
        raise RuntimeError("La bibliothèque 'cryptography' est requise.")

    chemin = cle_publique_path or PUBLIC_KEY_PATH
    if not chemin.exists():
        raise FileNotFoundError(f"Clé publique introuvable : {chemin}")

    pem_bytes = chemin.read_bytes()
    public_key = serialization.load_pem_public_key(pem_bytes)

    data = _snapshot_bytes(snapshot)
    try:
        public_key.verify(signature, data, ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False


def sauvegarder_snapshot_signe(
    snapshot: dict[str, Any],
    signature: bytes,
    dossier: Path,
    mission_id: str,
) -> tuple[Path, Path]:
    """Sauvegarde snapshot.json + snapshot.json.sig dans le dossier donné.

    Returns:
        Tuple (chemin_json, chemin_sig).
    """
    dossier.mkdir(parents=True, exist_ok=True)
    ts_safe = snapshot.get("timestamp", "unknown").replace(":", "-").replace("T", "_")[:19]
    base = f"snapshot_{mission_id}_{ts_safe}"

    chemin_json = dossier / f"{base}.json"
    chemin_sig = dossier / f"{base}.json.sig"

    chemin_json.write_bytes(_snapshot_bytes(snapshot))
    chemin_sig.write_bytes(signature)

    logger.info("Snapshot sauvegardé : %s", chemin_json)
    logger.info("Signature sauvegardée : %s", chemin_sig)

    return chemin_json, chemin_sig


def charger_snapshot_depuis_fichier(chemin_json: Path) -> dict[str, Any]:
    """Charge un snapshot depuis un fichier JSON."""
    return json.loads(chemin_json.read_bytes())


def verifier_snapshot_fichier(
    chemin_json: Path,
    cle_publique_path: Path | None = None,
) -> dict[str, Any]:
    """Vérifie un snapshot (signature + SHA-256 des livrables référencés).

    Returns:
        Dict avec clés 'ok' (bool), 'details' (list of str), 'erreurs' (list of str).
    """
    details: list[str] = []
    erreurs: list[str] = []

    # 1. Charger le snapshot
    try:
        snapshot = charger_snapshot_depuis_fichier(chemin_json)
        details.append(f"Snapshot chargé : {chemin_json.name}")
    except Exception as exc:
        erreurs.append(f"Impossible de charger le snapshot : {exc}")
        return {"ok": False, "details": details, "erreurs": erreurs}

    # 2. Vérifier la signature si disponible
    chemin_sig = chemin_json.with_suffix(".json.sig")
    if chemin_sig.exists():
        try:
            sig_bytes = chemin_sig.read_bytes()
            valide = verifier_signature(snapshot, sig_bytes, cle_publique_path)
            if valide:
                details.append("✅ Signature cryptographique valide")
            else:
                erreurs.append("❌ Signature cryptographique INVALIDE")
        except FileNotFoundError as exc:
            erreurs.append(f"Clé publique manquante : {exc}")
        except Exception as exc:
            erreurs.append(f"Erreur vérification signature : {exc}")
    else:
        details.append(
            "⚠️  Fichier de signature absent (.json.sig) — vérification crypto ignorée"
        )

    # 3. Recalculer SHA-256 des livrables référencés
    livrables_sha = snapshot.get("livrables_sha256", {})
    dossier_base = chemin_json.parent.parent  # remonte au-dessus de annexes/snapshot/
    for nom_fichier, sha_attendu in livrables_sha.items():
        chemin_livrable = dossier_base / nom_fichier
        if not chemin_livrable.exists():
            details.append(f"  Livrable absent (skipped) : {nom_fichier}")
            continue
        sha_reel = hashlib.sha256(chemin_livrable.read_bytes()).hexdigest()
        if sha_reel == sha_attendu:
            details.append(f"✅ {nom_fichier} : SHA-256 OK")
        else:
            erreurs.append(
                f"❌ {nom_fichier} : SHA-256 MISMATCH\n"
                f"   attendu : {sha_attendu}\n"
                f"   calculé : {sha_reel}"
            )

    ok = len(erreurs) == 0
    return {"ok": ok, "details": details, "erreurs": erreurs}


# Keep legacy stubs for backward compatibility
def calculer_snapshot(chemin_dossier: Path) -> str:
    """Calcule le SHA-256 agrégé d'un dossier mission (legacy)."""
    raise NotImplementedError("Utilisez construire_snapshot_mission() à la place.")


def verifier_snapshot(chemin_dossier: Path, snapshot_attendu: str) -> bool:
    """Vérifie l'intégrité d'un dossier mission via son snapshot (legacy)."""
    raise NotImplementedError("Utilisez verifier_snapshot_fichier() à la place.")
