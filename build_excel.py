#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Point d'entrée principal — génère output/portefeuille_bogleheads.xlsx
Usage: python build_excel.py
"""
import yaml
from pathlib import Path
from src.excel_builder import construire_workbook


def charger_yaml(chemin):
    """Charge un fichier YAML et retourne le contenu sous forme de dictionnaire.

    Args:
        chemin: Chemin vers le fichier YAML.

    Returns:
        Contenu du fichier YAML.
    """
    with open(chemin, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def main():
    """Fonction principale — charge les YAML et génère le classeur Excel."""
    print("🔄 Chargement des configurations...")
    fiscalite = charger_yaml('config/fiscalite_2026.yaml')
    enveloppes = charger_yaml('config/enveloppes.yaml')
    etf_data = charger_yaml('config/univers_etf.yaml')

    print("🏗️  Construction du classeur Excel...")
    wb = construire_workbook(fiscalite, enveloppes, etf_data)

    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    chemin_sortie = output_dir / 'portefeuille_bogleheads.xlsx'
    wb.save(chemin_sortie)
    print(f"✅ Fichier généré : {chemin_sortie}")
    print(f"   Feuilles créées : {wb.sheetnames}")


if __name__ == '__main__':
    main()
