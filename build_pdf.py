#!/usr/bin/env python3
"""
Point d'entrée — génère les PDFs clients Boglehead FR.

Usage :
    python build_pdf.py                               # tous les profils
    python build_pdf.py --profil PROFIL_1_CADRE_SUP  # un seul profil

Sortie : output/<code_profil>_<YYYYMMDD>.pdf
"""

import argparse
import sys
from datetime import date
from pathlib import Path

from src.pdf_builder import charger_config_pdf, generer_pdf
from src.schemas import charger_et_valider


def main():
    parser = argparse.ArgumentParser(description="Génère les PDFs clients Boglehead FR.")
    parser.add_argument(
        "--profil",
        type=str,
        default=None,
        help="Code du profil à générer (ex: PROFIL_1_CADRE_SUP). Si omis, génère tous les profils.",
    )
    args = parser.parse_args()

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    today_str = date.today().strftime("%Y%m%d")

    print("📄 Génération des PDFs clients Boglehead FR...")

    # Charger la configuration du cabinet
    try:
        config_pdf = charger_config_pdf()
        print(f"  ✓ Configuration cabinet : {config_pdf.cabinet.nom}")
    except Exception as exc:
        print(f"  ⚠️  Impossible de charger config/pdf_cabinet.yaml ({exc}) — config par défaut")
        from src.schemas import CabinetConfig, CabinetInfo

        config_pdf = CabinetConfig(cabinet=CabinetInfo(nom="Cabinet Patrimoine"))

    # Charger les profils clients
    try:
        profils_data = charger_et_valider("profils_clients.yaml")
        profils = profils_data.profils
    except Exception as exc:
        print(f"❌ Erreur chargement profils : {exc}", file=sys.stderr)
        sys.exit(1)

    # Filtrer par code profil si demandé
    if args.profil:
        profils = [p for p in profils if p.code == args.profil]
        if not profils:
            print(
                f"❌ Profil '{args.profil}' introuvable. "
                f"Codes disponibles : {[p.code for p in profils_data.profils]}",
                file=sys.stderr,
            )
            sys.exit(1)

    # Générer les PDFs
    erreurs = []
    for profil in profils:
        sortie = output_dir / f"{profil.code}_{today_str}.pdf"
        print(f"  → Profil {profil.id} — {profil.nom} ({profil.code})")
        try:
            resultat = generer_pdf(profil, config_pdf, sortie)
            taille_ko = resultat.taille_octets / 1024
            print(f"     ✓ {sortie.name} — {resultat.nb_pages} pages — {taille_ko:.1f} Ko")
        except Exception as exc:
            print(f"     ❌ Erreur : {exc}", file=sys.stderr)
            erreurs.append((profil.code, str(exc)))

    print()
    if erreurs:
        print(f"⚠️  {len(erreurs)} erreur(s) :")
        for code, msg in erreurs:
            print(f"   • {code} : {msg}")
        sys.exit(1)
    else:
        print(f"✅ {len(profils)} PDF(s) générés dans {output_dir}/")


if __name__ == "__main__":
    main()
