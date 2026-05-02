#!/usr/bin/env python3
"""Génération de la paire de clés ECDSA P-256 pour la signature des snapshots mission.

Usage:
    python tools/init_cabinet_keys.py

Génère:
    config/cabinet/keys/private.pem  — clé privée (NE PAS COMMITTER)
    config/cabinet/keys/public.pem   — clé publique (committer si souhaité)

Procédure:
    1. Exécuter ce script UNE SEULE FOIS par cabinet.
    2. Sauvegarder private.pem en lieu sûr (gestionnaire de mots de passe, HSM...).
    3. Ne JAMAIS committer private.pem dans git.
    4. public.pem peut être commité pour la vérification des snapshots archivés.

Rotation de clé:
    1. Générer une nouvelle paire avec ce script (sauvegarde l'ancienne).
    2. Re-signer les snapshots existants si nécessaire (rare).
    3. Mettre à jour la clé publique dans git.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
KEYS_DIR = ROOT / "config" / "cabinet" / "keys"


def generer_cle_ecdsa_p256() -> None:
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
    except ImportError:
        print("ERREUR: La bibliothèque 'cryptography' est requise.")
        print("Installez-la avec: pip install cryptography")
        sys.exit(1)

    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    private_path = KEYS_DIR / "private.pem"
    public_path = KEYS_DIR / "public.pem"

    # Sauvegarde des anciennes clés si elles existent
    if private_path.exists():
        backup = private_path.with_suffix(".pem.bak")
        private_path.rename(backup)
        print(f"Ancienne clé privée sauvegardée : {backup}")
    if public_path.exists():
        backup = public_path.with_suffix(".pem.bak")
        public_path.rename(backup)
        print(f"Ancienne clé publique sauvegardée : {backup}")

    # Génération
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    # Sérialisation PEM
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)

    # Permissions restrictives sur la clé privée (Unix)
    try:
        private_path.chmod(0o600)
    except Exception:
        pass

    print("\n✅ Paire de clés ECDSA P-256 générée avec succès !")
    print(f"   Clé privée : {private_path}")
    print(f"   Clé publique: {public_path}")
    print("\n⚠️  IMPORTANT:")
    print("   - NE JAMAIS committer private.pem dans git")
    print("   - Vérifiez que config/cabinet/keys/private.pem est dans .gitignore")
    print("   - Sauvegardez private.pem dans un gestionnaire de mots de passe")
    print("\nPour vérifier un snapshot:")
    print("   python -m bogleheads.snapshot verify <snapshot.json>")


if __name__ == "__main__":
    generer_cle_ecdsa_p256()
