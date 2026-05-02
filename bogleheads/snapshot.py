"""CLI de vérification des snapshots mission.

Usage:
    python -m bogleheads.snapshot verify <snapshot.json> [--public-key <public.pem>]
    python -m bogleheads.snapshot verify <snapshot.json>  # clé publique auto-détectée

Exit codes:
    0 — snapshot valide
    1 — signature invalide ou mismatch SHA-256
    2 — erreur (fichier introuvable, etc.)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def cmd_verify(args: argparse.Namespace) -> int:
    """Sous-commande 'verify'."""
    chemin = Path(args.snapshot)
    if not chemin.exists():
        print(f"❌ Fichier introuvable : {chemin}", file=sys.stderr)
        return 2

    cle_pub = Path(args.public_key) if args.public_key else None

    from src.mission.snapshot import verifier_snapshot_fichier

    result = verifier_snapshot_fichier(chemin, cle_pub)

    for line in result["details"]:
        print(line)
    for line in result["erreurs"]:
        print(line, file=sys.stderr)

    if result["ok"]:
        print("\n✅ Snapshot valide")
        return 0
    else:
        print(f"\n❌ Snapshot INVALIDE ({len(result['erreurs'])} erreur(s))")
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Vérification cryptographique des snapshots mission Boglehead"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_parser = subparsers.add_parser("verify", help="Vérifie un snapshot")
    verify_parser.add_argument("snapshot", help="Chemin vers le fichier snapshot.json")
    verify_parser.add_argument(
        "--public-key",
        default=None,
        help="Chemin vers la clé publique PEM (optionnel)",
    )

    args = parser.parse_args(argv)

    if args.command == "verify":
        return cmd_verify(args)
    else:
        parser.print_help()
        return 2


if __name__ == "__main__":
    sys.exit(main())
