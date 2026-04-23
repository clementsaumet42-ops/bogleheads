import openpyxl
from src.excel.styles import (
    COULEUR_SUBHEADER, COULEUR_LIGHT_GREY,
    _fill, _font, _align,
    style_header, set_col_width, ajouter_disclaimer, titre_section,
)


# ─── Onglet 12 : Tutoriel Solveur ───────────────────────────────────
def creer_onglet_tuto_solveur(wb: openpyxl.Workbook):
    ws = wb.create_sheet("Tuto_Solveur")
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:F1")
    c = ws["A1"]
    c.value = "🧮 TUTORIEL SOLVEUR EXCEL — OPTIMISATION ASSET LOCATION"
    style_header(c, size=14)
    ws.row_dimensions[1].height = 30

    ajouter_disclaimer(ws, 2, 1, 6)

    row = 4
    sections = [
        ("🎯 OBJECTIF DU SOLVEUR", [
            "Le Solveur Excel permet de résoudre le problème d'asset location optimal :",
            "→ Quels ETF mettre dans quelle enveloppe pour maximiser le capital net après impôts ?",
            "",
            "Formulation mathématique :",
            "  Variables : x_ij = montant en € de l'ETF i dans l'enveloppe j",
            "  Fonction objectif : MAXIMISER Σ VAN_après_impôts(x_ij) sur l'horizon",
            "  Contraintes :",
            "    (1) Eligibilité : x_ij = 0 si ETF i non éligible à enveloppe j",
            "    (2) Plafonds : Σi x_ij ≤ plafond_j (PEA ≤ 150 000€)",
            "    (3) Allocation : Σj x_ij = allocation_cible_i × patrimoine_total ± tolérance",
            "    (4) Non-négativité : x_ij ≥ 0",
            "    (5) Budget : Σi Σj x_ij = patrimoine_total",
        ]),
        ("📐 TYPE DE PROBLÈME D'OPTIMISATION", [
            "Vocabulaire de l'optimisation :",
            "  • LP (Linear Programming) : si la fonction objectif est linéaire en x_ij",
            "    → Cas simplifié : taux fiscaux fixes, pas de coûts non-linéaires",
            "  • QP (Quadratic Programming) : si on optimise la variance du portefeuille",
            "    → Cas Markowitz : covariances entre actifs = terme quadratique",
            "  • MILP (Mixed Integer LP) : si on ajoute des variables 0/1 d'ouverture d'enveloppe",
            "    → Exemple : décider si ouvrir un PER (variable binaire y_PER ∈ {0,1})",
            "",
            "Pour l'asset location Boglehead :",
            "  → Problème LP (linéaire) si taux fiscaux supposés fixes",
            "  → Solveur GRG non linéaire si on inclut les effets d'interaction fiscale",
            "  → MILP si décisions d'ouverture d'enveloppe (nécessite OpenSolver)",
        ]),
        ("🛠️ ACTIVATION DU SOLVEUR EXCEL (WINDOWS)", [
            "Étape 1 : Fichier → Options → Compléments",
            "Étape 2 : En bas de page, 'Gérer : Compléments Excel' → Atteindre",
            "Étape 3 : Cocher 'Solveur' → OK",
            "Étape 4 : L'onglet Données affiche maintenant le bouton 'Solveur'",
            "",
            "Sur Mac :",
            "Étape 1 : Excel → Préférences → Compléments",
            "Étape 2 : Cocher Solveur → OK",
            "Étape 3 : Onglet Outils → Solveur",
        ]),
        ("🔧 PARAMÉTRAGE DU SOLVEUR (EXEMPLE PROFIL 3)", [
            "Contexte Profil 3 — Dirigeant PME — 3 000 000€ de patrimoine financier",
            "Enveloppes : PEA (saturé 150k€), PER (80k€), CTO perso (400k€),",
            "             CTO IS (500k€), Contrat Cap IS (1 200k€)",
            "",
            "Cellule objectif : =SOMME(VAN_nette_par_enveloppe)",
            "  → VAN nette PEA = Σ(ETFi_PEA) × (1+r)^H × (1 - 0.186)",
            "  → VAN nette PER = Σ(ETFi_PER) × (1+r)^H × (1 - 0.186)",
            "  → VAN nette Contrat Cap IS = Σ(ETFi_CapIS) × [(1+r)^H - base_forfaitaire_IS]",
            "  → VAN nette CTO IS = Σ(ETFi_CTOIS) × (1+r)^H × (1 - IS_MTM_annuel)",
            "  → VAN nette CTO perso = Σ(ETFi_CTO) × (1+r)^H × (1 - 0.314)",
            "",
            "Variables à modifier : cellules x_ij (montants par ETF × enveloppe)",
            "Maximiser : cellule objectif = Σ VAN nettes",
        ]),
        ("⚙️ CONTRAINTES À SAISIR", [
            "Contrainte 1 — Éligibilité (bloquer les combinaisons interdites) :",
            "  → x_IWDA_PEA = 0 (iShares MSCI World non éligible PEA car physique)",
            "  → x_CW8_Contrat_Cap_IS = 0 (ETF swap PEA non disponible en assurance)",
            "",
            "Contrainte 2 — Plafond PEA :",
            "  → Σ(toutes enveloppes PEA) ≤ 150 000 - encours_actuel",
            "",
            "Contrainte 3 — Allocation cible (±5 pts de tolérance) :",
            "  → Σ(ETF actions toutes enveloppes) ≥ 0.50 × patrimoine_total",
            "  → Σ(ETF actions toutes enveloppes) ≤ 0.60 × patrimoine_total",
            "",
            "Contrainte 4 — Budget total :",
            "  → Σi Σj x_ij = 3 000 000 €",
            "",
            "Contrainte 5 — Non-négativité :",
            "  → Toutes les cellules x_ij ≥ 0",
        ]),
        ("🚀 OPENSOLVER — RECOMMANDÉ POUR LES GRANDS PROBLÈMES", [
            "Le Solveur intégré Excel est limité à 200 variables et 100 contraintes.",
            "Pour les portefeuilles complexes (6 enveloppes × 60 ETF = 360 variables),",
            "utiliser OpenSolver : https://opensolver.org",
            "",
            "Avantages OpenSolver vs Solveur Excel :",
            "  • Illimité en variables et contraintes",
            "  • Algorithmes plus puissants (CBC, GLPK, Gurobi)",
            "  • Résout les MILP (décisions binaires d'ouverture d'enveloppe)",
            "  • Export du modèle LP pour vérification",
            "",
            "Installation OpenSolver :",
            "  1. Télécharger sur opensolver.org",
            "  2. Extraire et copier dans C:\\Users\\[user]\\AppData\\Roaming\\Microsoft\\Excel\\XLSTART",
            "  3. Redémarrer Excel → onglet 'OpenSolver' apparaît",
        ]),
        ("🐛 TROUBLESHOOTING", [
            "Problème : 'Le Solveur n'a pas trouvé de solution réalisable'",
            "  → Vérifier que les contraintes d'allocation ne se contredisent pas",
            "  → Vérifier que le budget total ≥ Σ plafonds minimum des enveloppes",
            "  → Relaxer la contrainte d'allocation (±5% → ±10%)",
            "",
            "Problème : 'La solution courante est optimale' mais sous-optimale",
            "  → Le Solveur a trouvé un optimum local — essayer plusieurs points de départ",
            "  → Utiliser l'option 'Essais multiples' si disponible",
            "  → Passer au solveur GRG avec recherche aléatoire",
            "",
            "Problème : Les variables ETF IS ont une valeur trop faible",
            "  → Vérifier que l'hypothèse MTM est bien encodée dans la VAN IS",
            "  → Le Solveur 'fuit' le CTO IS à cause du MTM — c'est le bon comportement !",
            "",
            "Conseil CGP : Toujours valider la solution du Solveur manuellement.",
            "La qualité de l'optimisation dépend entièrement des hypothèses de rendement.",
        ]),
        ("📊 EXEMPLE NUMÉRIQUE — PROFIL 3 SIMPLIFIÉ", [
            "Patrimoine : 3 000 000 € | Horizon : 15 ans | Rendement supposé : 6%/an",
            "",
            "Capital brut en 15 ans : 3 000 000 × (1.06)^15 = 7 189 670 €",
            "Gain brut total : 4 189 670 €",
            "",
            "Scénario naïf CTO (PFU 31.4%) :",
            "  Impôts = 4 189 670 × 31.4% = 1 315 556 €",
            "  Capital net = 5 874 114 €",
            "",
            "Scénario optimisé Profil 3 :",
            "  Contrat Cap IS (1.2M€) : base forfaitaire ≈ 39 600€/an × IS 15% = 5 940€/an → négligeable",
            "  PEA (150k€) saturé : PS 18.6% seulement sur gains PEA",
            "  PER (80k€) : PS 18.6% sur gains + IR sortie réduit",
            "  CTO perso (400k€) : PFU 31.4% standard",
            "  Gain fiscal estimé vs naïf CTO : +15 à +25% de capital net",
            "",
            "⚠️ Ces chiffres sont illustratifs. Voir onglet Comparatif_Profils pour les calculs.",
        ]),
    ]

    for titre_section_text, lignes in sections:
        row = titre_section(ws, row, titre_section_text, 1, 6)
        for ligne in lignes:
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
            cell = ws.cell(row=row, column=1, value=ligne)
            if ligne.startswith("  ") or ligne.startswith("→"):
                cell.font = _font(size=10, italic=True)
                cell.fill = _fill(COULEUR_LIGHT_GREY)
            elif ligne.startswith("Étape") or ligne.startswith("Contrainte") or ligne.startswith("Problème") or ligne.startswith("Avantage"):
                cell.font = _font(size=10, bold=True, color=COULEUR_SUBHEADER)
            elif ligne == "":
                ws.row_dimensions[row].height = 8
            else:
                cell.font = _font(size=10)
            cell.alignment = _align("left", "center", wrap=True)
            ws.row_dimensions[row].height = max(ws.row_dimensions[row].height or 15, 15)
            row += 1
        row += 1

    set_col_width(ws, 1, 100)
    for i in range(2, 7):
        set_col_width(ws, i, 5)
    ws.freeze_panes = "A3"
