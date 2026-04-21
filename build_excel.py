#!/usr/bin/env python3
"""
Point d'entrée — génère output/portefeuille_bogleheads.xlsx
Usage : python build_excel.py
"""
from pathlib import Path
from src.excel_builder import generer_excel


def main():
    chemin_sortie = Path("output") / "portefeuille_bogleheads.xlsx"
    chemin_sortie.parent.mkdir(exist_ok=True)

    print("🏗️  Génération du fichier Excel Boglehead FR...")
    generer_excel(str(chemin_sortie))
    print("\nOnglets créés :")
    print("  • Paramètres_Client")
    print("  • Paramètres_Fiscalité_2026")
    print("  • Enveloppes")
    print("  • Univers_ETF (avec filtres et mise en forme)")
    print("  • Allocation_Cible")
    print("  • Asset_Location_Matrice")
    print("  • Rebalancement")
    print("  • Reporting_Client")
    print("  • Profils_Types")
    print("  • Profil_1_CADRE")
    print("  • Profil_2_DIRIGEANT")
    print("  • Profil_3_DIRIGEANT (PME)")
    print("  • Profil_4_PROFESSION")
    print("  • Profil_5_JEUNE")
    print("  • Profil_6_PRE")
    print("  • Comparatif_Profils")
    print("  • Tuto_Solveur")
    print("\n📊 Ouvrez le fichier dans Excel et activez le Solveur pour l'optimisation.")


if __name__ == "__main__":
    main()
