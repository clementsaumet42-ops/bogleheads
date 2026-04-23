#!/usr/bin/env python3
"""
Point d'entrée — génère output/<profil>_<YYYYMMDD>.pdf pour chaque profil client.

Usage :
    python build_pdf.py                          # tous les profils
    python build_pdf.py --profil PROFIL_1_CADRE_SUP   # un seul profil
    python build_pdf.py --profil 1               # par id

Options :
    --cabinet config/pdf_cabinet.yaml  (défaut)
    --output  output/                  (défaut)
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

from src.pdf_builder import generer_pdf
from src.schemas import CabinetConfig


def _charger_config_cabinet(chemin: str) -> CabinetConfig:
    """Charge la configuration cabinet depuis le YAML."""
    p = Path(chemin)
    if not p.exists():
        print(f"⚠️  Fichier cabinet non trouvé : {chemin} — utilisation des valeurs par défaut.")
        return CabinetConfig()
    with p.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return CabinetConfig.model_validate(raw)


def _charger_profils(chemin: str) -> list[dict]:
    """Charge les profils clients depuis le YAML."""
    p = Path(chemin)
    if not p.exists():
        print(f"❌ Fichier profils non trouvé : {chemin}", file=sys.stderr)
        sys.exit(1)
    with p.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data.get("profils", [])


def main() -> None:
    parser = argparse.ArgumentParser(description="Génère les PDFs clients Boglehead.")
    parser.add_argument(
        "--profil",
        default=None,
        help="Code ou id du profil à générer (défaut : tous).",
    )
    parser.add_argument(
        "--cabinet",
        default="config/pdf_cabinet.yaml",
        help="Chemin vers la configuration cabinet.",
    )
    parser.add_argument(
        "--profils",
        default="config/profils_clients.yaml",
        help="Chemin vers les profils clients.",
    )
    parser.add_argument(
        "--output",
        default="output",
        help="Répertoire de sortie.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    config = _charger_config_cabinet(args.cabinet)
    profils = _charger_profils(args.profils)

    # Filtrer si --profil fourni
    if args.profil is not None:
        filtre = args.profil.strip()
        # Essayer par code puis par id
        profils_filtres = [
            p for p in profils if str(p.get("code")) == filtre or str(p.get("id")) == filtre
        ]
        if not profils_filtres:
            print(f"❌ Profil '{filtre}' non trouvé.", file=sys.stderr)
            sys.exit(1)
        profils = profils_filtres

    today = date.today().strftime("%Y%m%d")
    print(f"🏗️  Génération des PDFs clients Boglehead — {len(profils)} profil(s)...\n")

    erreurs = 0
    for profil in profils:
        code = profil.get("code", f"profil_{profil.get('id', 'inconnu')}")
        nom = profil.get("nom", "Client")
        chemin_sortie = output_dir / f"{code}_{today}.pdf"
        try:
            result = generer_pdf(profil, config, str(chemin_sortie))
            taille_kb = result.taille_octets // 1024
            print(
                f"  ✅ {nom:40s} → {chemin_sortie.name}  ({result.nb_pages} pages, {taille_kb} Ko)"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  ❌ {nom}: ERREUR — {exc}", file=sys.stderr)
            erreurs += 1

    print()
    if erreurs:
        print(f"⚠️  {erreurs} erreur(s) lors de la génération.", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"✅ {len(profils)} PDF(s) générés dans '{output_dir}/'.")
        print("   → Chaque fichier est un rapport client 13 pages prêt à remettre.")


if __name__ == "__main__":
    main()
