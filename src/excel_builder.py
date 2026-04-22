# -*- coding: utf-8 -*-
"""
Constructeur du classeur Excel — outil CGP Bogleheads France 2026.
Génère un classeur openpyxl complet avec 8 feuilles structurées.

Feuilles générées :
1. Paramètres_Client
2. Paramètres_Fiscalité_2026
3. Enveloppes
4. Univers_ETF
5. Allocation_Cible
6. Asset_Location_Matrice
7. Rebalancement
8. Reporting_Client
"""

from __future__ import annotations
from openpyxl import Workbook
from openpyxl.styles import (
    PatternFill, Font, Alignment, Border, Side, numbers
)
from openpyxl.styles.numbers import FORMAT_PERCENTAGE_00, FORMAT_NUMBER_COMMA_SEPARATED1
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import Rule, CellIsRule, FormulaRule
from openpyxl.utils import get_column_letter


# ---------------------------------------------------------------------------
# Constantes de style
# ---------------------------------------------------------------------------

# Couleurs enveloppes
COULEURS_ENVELOPPES = {
    "cto_perso":       "FFF2CC",   # Jaune pâle
    "cto_is":          "FCE4D6",   # Orange très pâle
    "contrat_capi_is": "DDEBF7",   # Bleu très pâle
    "pea":             "E2EFDA",   # Vert très pâle
    "per":             "EAD1DC",   # Violet très pâle
    "pee":             "D9EAD3",   # Vert menthe très pâle
}

# Couleurs de mise en forme conditionnelle
ROUGE_CLAIR = "FFCCCC"
VERT_CLAIR = "CCFFCC"
GRIS_CLAIR = "D9D9D9"
ORANGE_CLAIR = "FFE0B2"

# Couleur non-éligible (grisé)
GRIS_NON_ELIGIBLE = "BFBFBF"

# Police par défaut
POLICE_TITRE = Font(bold=True, size=12)
POLICE_EN_TETE = Font(bold=True, size=10, color="FFFFFF")
POLICE_CORPS = Font(size=10)
POLICE_AVERTISSEMENT = Font(bold=True, color="C00000")

# Remplissage en-têtes
FILL_EN_TETE_BLEU = PatternFill(fill_type="solid", fgColor="1F497D")
FILL_EN_TETE_VERT = PatternFill(fill_type="solid", fgColor="375623")
FILL_EN_TETE_ORANGE = PatternFill(fill_type="solid", fgColor="974706")
FILL_TITRE_PAGE = PatternFill(fill_type="solid", fgColor="2F5496")

# Alignement centré
ALIGN_CENTRE = Alignment(horizontal="center", vertical="center", wrap_text=True)
ALIGN_GAUCHE = Alignment(horizontal="left", vertical="center", wrap_text=True)
ALIGN_DROITE = Alignment(horizontal="right", vertical="center")


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def _appliquer_bordure(ws, min_row: int, max_row: int, min_col: int, max_col: int):
    """Applique une bordure fine à une plage de cellules.

    Args:
        ws: Feuille de calcul openpyxl.
        min_row, max_row, min_col, max_col: Bornes de la plage.
    """
    bordure_fine = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    for row in ws.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
        for cell in row:
            cell.border = bordure_fine


def _en_tete_feuille(ws, titre: str, sous_titre: str = ""):
    """Crée un en-tête visuel pour une feuille.

    Args:
        ws: Feuille de calcul.
        titre: Titre principal.
        sous_titre: Sous-titre optionnel.
    """
    ws["A1"] = titre
    ws["A1"].font = Font(bold=True, size=14, color="FFFFFF")
    ws["A1"].fill = FILL_TITRE_PAGE
    ws["A1"].alignment = ALIGN_CENTRE
    ws.merge_cells("A1:J1")

    if sous_titre:
        ws["A2"] = sous_titre
        ws["A2"].font = Font(italic=True, size=10, color="595959")
        ws["A2"].alignment = ALIGN_CENTRE
        ws.merge_cells("A2:J2")


def _cellule_etiquette(ws, row: int, col: int, valeur: str):
    """Formate une cellule comme étiquette (gras, fond bleu clair).

    Args:
        ws: Feuille de calcul.
        row, col: Position de la cellule.
        valeur: Texte de l'étiquette.
    """
    cell = ws.cell(row=row, column=col, value=valeur)
    cell.font = Font(bold=True, size=10)
    cell.fill = PatternFill(fill_type="solid", fgColor="DCE6F1")
    cell.alignment = ALIGN_GAUCHE


def _cellule_valeur(ws, row: int, col: int, valeur, format_nombre: str | None = None):
    """Formate une cellule comme valeur éditable.

    Args:
        ws: Feuille de calcul.
        row, col: Position.
        valeur: Valeur de la cellule.
        format_nombre: Format numérique openpyxl.
    """
    cell = ws.cell(row=row, column=col, value=valeur)
    cell.font = POLICE_CORPS
    cell.fill = PatternFill(fill_type="solid", fgColor="FFFFD9")
    cell.alignment = ALIGN_GAUCHE
    if format_nombre:
        cell.number_format = format_nombre
    return cell


def _creer_table(ws, ref: str, nom: str, style_nom: str = "TableStyleMedium9") -> Table:
    """Crée une table structurée openpyxl.

    Args:
        ws: Feuille de calcul.
        ref: Référence de la plage (ex: 'A3:F20').
        nom: Nom de la table (doit être unique dans le classeur).
        style_nom: Nom du style de table Excel.

    Returns:
        Objet Table créé et ajouté à la feuille.
    """
    table = Table(displayName=nom, ref=ref)
    style = TableStyleInfo(
        name=style_nom,
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    table.tableStyleInfo = style
    ws.add_table(table)
    return table


# ---------------------------------------------------------------------------
# Feuille 1 : Paramètres_Client
# ---------------------------------------------------------------------------

def _creer_feuille_parametres_client(wb: Workbook) -> None:
    """Crée la feuille de paramètres client avec champs éditables.

    Args:
        wb: Classeur openpyxl.
    """
    ws = wb.create_sheet("Paramètres_Client")
    ws.sheet_view.showGridLines = False

    _en_tete_feuille(
        ws,
        "⚙️ Paramètres Client — CGP Bogleheads France 2026",
        "Remplir les champs jaunes — ces paramètres alimentent les calculs des autres feuilles",
    )

    # Largeurs des colonnes
    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 40
    ws.row_dimensions[1].height = 30
    ws.row_dimensions[2].height = 18

    # Titre section 1
    ws["A4"] = "👤 INFORMATIONS PERSONNELLES"
    ws["A4"].font = Font(bold=True, size=11, color="1F497D")
    ws.merge_cells("A4:C4")

    parametres_perso = [
        ("Âge du titulaire (ans)", 40, "#"),
        ("Situation familiale", "celibataire", None),
        ("Tranche Marginale d'Imposition (TMI)", 0.30, "0%"),
        ("Revenu Fiscal de Référence (RFR, €)", 80000, "#,##0 €"),
        ("Horizon de placement (ans)", 20, "#"),
        ("Objectif rendement annuel net (%)", 0.05, "0.0%"),
        ("Tolérance au risque (1=faible, 5=élevée)", 3, "#"),
    ]

    row = 5
    for label, valeur_defaut, fmt in parametres_perso:
        _cellule_etiquette(ws, row, 1, label)
        _cellule_valeur(ws, row, 2, valeur_defaut, fmt)
        row += 1

    # Validation liste TMI
    dv_tmi = DataValidation(
        type="list",
        formula1='"11%,30%,41%,45%"',
        allow_blank=False,
        showErrorMessage=True,
        errorTitle="TMI invalide",
        error="Sélectionner une TMI valide : 11%, 30%, 41%, 45%",
    )
    dv_tmi.add(ws["B7"])
    ws.add_data_validation(dv_tmi)

    # Validation situation familiale
    dv_sitfam = DataValidation(
        type="list",
        formula1='"celibataire,couple,veuf"',
        allow_blank=False,
    )
    dv_sitfam.add(ws["B6"])
    ws.add_data_validation(dv_sitfam)

    # Titre section 2 — Patrimoine
    ws.cell(row=row + 1, column=1).value = "💰 PATRIMOINE & ENVELOPPES"
    ws.cell(row=row + 1, column=1).font = Font(bold=True, size=11, color="1F497D")
    ws.merge_cells(f"A{row+1}:C{row+1}")
    row += 2

    parametres_patrimoine = [
        ("Patrimoine financier total (€)", 500000, "#,##0 €"),
        ("Dont : PEA existant (€)", 50000, "#,##0 €"),
        ("Dont : PER existant (€)", 30000, "#,##0 €"),
        ("Dont : PEE existant (€)", 20000, "#,##0 €"),
        ("Dont : CTO perso existant (€)", 100000, "#,##0 €"),
        ("Détient une société IS ?", "Non", None),
        ("Si oui — trésorerie disponible société (€)", 0, "#,##0 €"),
    ]

    for label, valeur_defaut, fmt in parametres_patrimoine:
        _cellule_etiquette(ws, row, 1, label)
        _cellule_valeur(ws, row, 2, valeur_defaut, fmt)
        row += 1

    # Validation Oui/Non
    dv_oninon = DataValidation(type="list", formula1='"Oui,Non"', allow_blank=False)
    dv_oninon.add(ws.cell(row=row - 2, column=2))
    ws.add_data_validation(dv_oninon)

    # Titre section 3 — Paramètres de simulation
    ws.cell(row=row + 1, column=1).value = "📊 PARAMÈTRES DE SIMULATION"
    ws.cell(row=row + 1, column=1).font = Font(bold=True, size=11, color="1F497D")
    ws.merge_cells(f"A{row+1}:C{row+1}")
    row += 2

    parametres_simulation = [
        ("Profil de risque", "equilibre", None),
        ("Règle âge-en-obligations ?", "Oui", None),
        ("Variante règle âge (standard/conservateur/agressif)", "standard", None),
        ("Méthode rebalancement", "relatif_5pct", None),
        ("Taux actualisation flux futurs (%)", 0.04, "0.0%"),
    ]

    for label, valeur_defaut, fmt in parametres_simulation:
        _cellule_etiquette(ws, row, 1, label)
        _cellule_valeur(ws, row, 2, valeur_defaut, fmt)
        row += 1

    # Validation profil de risque
    dv_profil = DataValidation(
        type="list",
        formula1='"prudent,equilibre,dynamique"',
        allow_blank=False,
    )
    dv_profil.add(ws.cell(row=row - 5, column=2))
    ws.add_data_validation(dv_profil)

    # Note légale
    note_row = row + 2
    ws.cell(row=note_row, column=1).value = (
        "⚠️ AVERTISSEMENT : Les calculs fournis sont indicatifs et pédagogiques. "
        "Ils ne constituent pas un conseil en investissement. Consulter un professionnel "
        "agréé pour toute décision patrimoniale."
    )
    ws.cell(row=note_row, column=1).font = POLICE_AVERTISSEMENT
    ws.cell(row=note_row, column=1).alignment = Alignment(wrap_text=True)
    ws.merge_cells(f"A{note_row}:C{note_row}")
    ws.row_dimensions[note_row].height = 45

    _appliquer_bordure(ws, 5, row - 1, 1, 2)


# ---------------------------------------------------------------------------
# Feuille 2 : Paramètres_Fiscalité_2026
# ---------------------------------------------------------------------------

def _creer_feuille_fiscalite(wb: Workbook, fiscalite: dict) -> None:
    """Crée la feuille des paramètres fiscaux 2026.

    Args:
        wb: Classeur openpyxl.
        fiscalite: Dictionnaire issu de fiscalite_2026.yaml.
    """
    ws = wb.create_sheet("Paramètres_Fiscalité_2026")
    ws.sheet_view.showGridLines = False

    _en_tete_feuille(
        ws,
        "📋 Paramètres Fiscaux France 2026",
        "Sources : LF 2026, LFSS 2026, CGI, BOFiP — taux marqués À VALIDER à confirmer sur texte officiel",
    )

    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 50
    ws.row_dimensions[1].height = 30
    ws.row_dimensions[2].height = 18

    # En-têtes du tableau
    en_tetes = ["Paramètre", "Valeur", "Source / Commentaire"]
    row = 4
    for col, texte in enumerate(en_tetes, start=1):
        cell = ws.cell(row=row, column=col, value=texte)
        cell.font = POLICE_EN_TETE
        cell.fill = FILL_EN_TETE_BLEU
        cell.alignment = ALIGN_CENTRE

    row = 5
    # Construction des lignes depuis le YAML
    lignes_fiscalite = _extraire_lignes_fiscalite(fiscalite)

    for label, valeur, commentaire in lignes_fiscalite:
        ws.cell(row=row, column=1).value = label
        ws.cell(row=row, column=1).font = Font(size=10)
        ws.cell(row=row, column=1).alignment = ALIGN_GAUCHE

        cell_val = ws.cell(row=row, column=2, value=valeur)
        cell_val.alignment = ALIGN_CENTRE
        cell_val.font = Font(size=10, bold=True)
        # Format numérique selon le type
        if isinstance(valeur, float) and 0 < valeur <= 1:
            cell_val.number_format = "0.0%"

        ws.cell(row=row, column=3).value = commentaire
        ws.cell(row=row, column=3).font = Font(size=9, italic=True, color="595959")
        ws.cell(row=row, column=3).alignment = ALIGN_GAUCHE

        # Alternance des lignes
        if row % 2 == 0:
            for col in range(1, 4):
                ws.cell(row=row, column=col).fill = PatternFill(
                    fill_type="solid", fgColor="F2F2F2"
                )
        row += 1

    # Création de la table structurée
    last_row = row - 1
    ref_table = f"A4:{get_column_letter(3)}{last_row}"
    _creer_table(ws, ref_table, "tblFiscalite", "TableStyleMedium2")

    _appliquer_bordure(ws, 4, last_row, 1, 3)


def _extraire_lignes_fiscalite(fiscalite: dict) -> list[tuple]:
    """Extrait les lignes de données fiscales depuis le dictionnaire YAML.

    Args:
        fiscalite: Dictionnaire de paramètres fiscaux.

    Returns:
        Liste de tuples (label, valeur, commentaire).
    """
    lignes = []

    # PFU
    pfu = fiscalite.get("pfu", {})
    lignes += [
        ("PFU — Taux total (Flat Tax)", pfu.get("taux_total", 0.314), "Art. 200 A CGI — 12.8% IR + 18.6% PS"),
        ("PFU — Quote-part IR", pfu.get("taux_ir", 0.128), "Art. 200 A CGI"),
        ("PFU — Quote-part PS", pfu.get("taux_ps", 0.186), "Art. L136-6 CSS + ord. 96-50"),
        ("PFU — Abattement dividendes option barème", pfu.get("abattement_dividendes_bareme", 0.40), "Art. 158-3-2° CGI"),
    ]

    # Prélèvements sociaux
    ps = fiscalite.get("prelevements_sociaux", {})
    detail = ps.get("detail", {})
    lignes += [
        ("PS — Taux total", ps.get("taux_total", 0.186), "À VALIDER LF/LFSS 2026"),
        ("PS — CSG", detail.get("csg", 0.099), "Art. L136-6 CSS — 9.9%"),
        ("PS — CRDS", detail.get("crds", 0.005), "Ord. 96-50 — 0.5%"),
        ("PS — Prélèvement solidarité", detail.get("prelevement_solidarite", 0.075), "Art. 235 ter ZD CGI — 7.5%"),
        ("PS — Contribution additionnelle", detail.get("contribution_additionnelle", 0.007), "À VALIDER LFSS 2026 — 0.7%"),
        ("PS — Sortie PER capital (gains)", ps.get("taux_sortie_per_capital", 0.103), "À VALIDER BOFiP"),
    ]

    # CEHR
    cehr = fiscalite.get("cehr", {})
    cel = cehr.get("celibataire", {})
    cpl = cehr.get("couple", {})
    lignes += [
        ("CEHR — Taux tranche 1 (3%)", cehr.get("taux_tranche_1", 0.03), "Art. 223 sexies CGI — célib > 250k€ / couple > 500k€"),
        ("CEHR — Taux tranche 2 (4%)", cehr.get("taux_tranche_2", 0.04), "Art. 223 sexies CGI — célib > 500k€ / couple > 1M€"),
        ("CEHR — Seuil célib tranche 1 (€)", cel.get("seuil_3pct", 250000), "RFR > 250 000 € pour célibataire"),
        ("CEHR — Seuil célib tranche 2 (€)", cel.get("seuil_4pct", 500000), "RFR > 500 000 € pour célibataire"),
        ("CEHR — Seuil couple tranche 1 (€)", cpl.get("seuil_3pct", 500000), "RFR > 500 000 € pour couple/PACS"),
        ("CEHR — Seuil couple tranche 2 (€)", cpl.get("seuil_4pct", 1000000), "RFR > 1 000 000 € pour couple/PACS"),
    ]

    # CDHR
    cdhr = fiscalite.get("cdhr", {})
    lignes += [
        ("CDHR — Taux effectif minimal", cdhr.get("taux_minimal", 0.20), "LF 2025 art. 3 — À VALIDER reconduite 2026"),
        ("CDHR — Seuil célibataire (€)", cdhr.get("seuil_celibataire", 250000), "RFR > 250 000 € célib"),
        ("CDHR — Seuil couple (€)", cdhr.get("seuil_couple", 500000), "RFR > 500 000 € couple"),
    ]

    # IS
    is_data = fiscalite.get("is", {})
    lignes += [
        ("IS — Taux réduit PME", is_data.get("taux_reduit", 0.15), "Art. 219 I b CGI — PME (CA < 10M€)"),
        ("IS — Plafond taux réduit (€)", is_data.get("seuil_taux_reduit", 42500), "42 500 € depuis LF 2024 (relevé de 38 120 €)"),
        ("IS — Taux normal", is_data.get("taux_normal", 0.25), "Art. 219 CGI"),
    ]

    # TME et plafonds
    lignes += [
        ("TME — Taux Moyen Emprunts d'État", fiscalite.get("tme", 0.030), "À paramétrer — publication Banque de France"),
        ("Plafond PEA (€)", fiscalite.get("plafonds", {}).get("pea", 150000), "Art. L221-30 CMF"),
        ("Plafond PEA-PME cumulé (€)", fiscalite.get("plafonds", {}).get("pea_pme", 225000), "Art. L221-32-1 CMF"),
    ]

    return lignes


# ---------------------------------------------------------------------------
# Feuille 3 : Enveloppes
# ---------------------------------------------------------------------------

def _creer_feuille_enveloppes(wb: Workbook, enveloppes_data: dict) -> None:
    """Crée la feuille de synthèse des enveloppes d'investissement.

    Args:
        wb: Classeur openpyxl.
        enveloppes_data: Dictionnaire issu de enveloppes.yaml.
    """
    ws = wb.create_sheet("Enveloppes")
    ws.sheet_view.showGridLines = False

    _en_tete_feuille(
        ws,
        "🏦 Enveloppes d'Investissement — Synthèse Fiscale",
        "Comparaison des 6 enveloppes disponibles selon le profil client",
    )

    # Largeurs colonnes
    largeurs = [20, 30, 15, 30, 25, 25, 25, 12, 35]
    for i, largeur in enumerate(largeurs, start=1):
        ws.column_dimensions[get_column_letter(i)].width = largeur
    ws.row_dimensions[1].height = 30

    # En-têtes
    en_tetes = [
        "ID", "Nom", "Plafond (€)", "Éligibilité ETFs",
        "Fiscalité entrée", "Fiscalité courante", "Fiscalité sortie",
        "Blocage", "Avantages clés",
    ]
    row = 4
    for col, texte in enumerate(en_tetes, start=1):
        cell = ws.cell(row=row, column=col, value=texte)
        cell.font = POLICE_EN_TETE
        cell.fill = FILL_EN_TETE_VERT
        cell.alignment = ALIGN_CENTRE

    enveloppes_list = enveloppes_data.get("enveloppes", []) if isinstance(enveloppes_data, dict) else enveloppes_data

    row = 5
    for env in enveloppes_list:
        env_id = env.get("id", "")
        couleur = COULEURS_ENVELOPPES.get(env_id, "FFFFFF")
        fill_env = PatternFill(fill_type="solid", fgColor=couleur)

        # Synthèse de la fiscalité de sortie
        fs = env.get("fiscalite_sortie", {})
        if isinstance(fs, dict):
            taux_sortie = fs.get("taux_effectif_moyen") or fs.get("taux_effectif_sortie_apres_5ans") or fs.get("taux_effectif_sortie", "")
            desc_sortie = f"Taux eff. ≈ {taux_sortie:.0%}" if isinstance(taux_sortie, float) else str(taux_sortie)
        else:
            desc_sortie = str(fs)

        # Synthèse des avantages
        avantages = env.get("avantages", [])
        avantages_str = " | ".join(avantages[:2]) if avantages else ""

        # Fiscalité courante
        fc = env.get("fiscalite_courante", {})
        if isinstance(fc, dict):
            fc_str = fc.get("commentaire", "")[:80] if fc.get("commentaire") else ""
        else:
            fc_str = ""

        # Fiscalité entrée
        fe = env.get("fiscalite_entree", {})
        if isinstance(fe, dict):
            fe_deductible = "✅ Déductible" if fe.get("deductible") else "❌ Non déductible"
        else:
            fe_deductible = ""

        valeurs = [
            env_id,
            env.get("nom", ""),
            env.get("plafond", "Sans plafond"),
            env.get("eligibilite_etf", "")[:60],
            fe_deductible,
            fc_str,
            desc_sortie,
            "Oui" if env.get("blocage") else "Non",
            avantages_str,
        ]

        for col, valeur in enumerate(valeurs, start=1):
            cell = ws.cell(row=row, column=col, value=valeur)
            cell.fill = fill_env
            cell.alignment = ALIGN_GAUCHE
            cell.font = Font(size=9)

        ws.row_dimensions[row].height = 45
        row += 1

    last_row = row - 1
    ref_table = f"A4:{get_column_letter(9)}{last_row}"
    _creer_table(ws, ref_table, "tblEnveloppes", "TableStyleMedium7")
    _appliquer_bordure(ws, 4, last_row, 1, 9)


# ---------------------------------------------------------------------------
# Feuille 4 : Univers_ETF
# ---------------------------------------------------------------------------

def _creer_feuille_etf(wb: Workbook, etf_data: dict) -> None:
    """Crée la feuille de l'univers ETF avec tableau structuré.

    Args:
        wb: Classeur openpyxl.
        etf_data: Dictionnaire issu de univers_etf.yaml.
    """
    ws = wb.create_sheet("Univers_ETF")
    ws.sheet_view.showGridLines = False

    _en_tete_feuille(
        ws,
        "📈 Univers ETF Boglehead — France 2026",
        "~25 ETFs sélectionnés selon critères : TER, liquidité, éligibilité fiscale",
    )

    largeurs = [18, 12, 45, 20, 30, 8, 8, 12, 14, 8, 8, 8, 8, 8]
    for i, largeur in enumerate(largeurs, start=1):
        ws.column_dimensions[get_column_letter(i)].width = largeur
    ws.row_dimensions[1].height = 30

    en_tetes = [
        "ISIN", "Ticker", "Nom", "Émetteur", "Classe d'Actifs",
        "TER %", "Devise", "Domicile", "Type",
        "PEA", "PER", "PEE", "CTO", "PEA-PME",
    ]

    row = 4
    for col, texte in enumerate(en_tetes, start=1):
        cell = ws.cell(row=row, column=col, value=texte)
        cell.font = POLICE_EN_TETE
        cell.fill = FILL_EN_TETE_ORANGE
        cell.alignment = ALIGN_CENTRE

    etfs = etf_data.get("etfs", []) if isinstance(etf_data, dict) else []
    row = 5
    for etf in etfs:
        eligibilite = etf.get("eligibilite", {})

        valeurs = [
            etf.get("isin", ""),
            etf.get("ticker", ""),
            etf.get("nom", ""),
            etf.get("emetteur", ""),
            etf.get("classe_actifs", ""),
            etf.get("ter", 0) * 100 if isinstance(etf.get("ter"), float) else etf.get("ter", 0),
            etf.get("devise", ""),
            etf.get("domicile", ""),
            etf.get("type", ""),
            "✅" if eligibilite.get("pea") else "❌",
            "✅" if eligibilite.get("per") else "❌",
            "✅" if eligibilite.get("pee") else "❌",
            "✅" if eligibilite.get("cto") else "❌",
            "✅" if eligibilite.get("pea_pme") else "❌",
        ]

        for col, valeur in enumerate(valeurs, start=1):
            cell = ws.cell(row=row, column=col, value=valeur)
            cell.alignment = ALIGN_CENTRE if col >= 9 else ALIGN_GAUCHE
            cell.font = Font(size=9)

        # Coloration selon type
        if etf.get("type") == "capitalisant":
            ws.cell(row=row, column=9).fill = PatternFill(fill_type="solid", fgColor="E2EFDA")
        else:
            ws.cell(row=row, column=9).fill = PatternFill(fill_type="solid", fgColor="FCE4D6")

        row += 1

    last_row = row - 1
    ref_table = f"A4:{get_column_letter(14)}{last_row}"
    _creer_table(ws, ref_table, "tblETF", "TableStyleMedium5")
    _appliquer_bordure(ws, 4, last_row, 1, 14)


# ---------------------------------------------------------------------------
# Feuille 5 : Allocation_Cible
# ---------------------------------------------------------------------------

def _creer_feuille_allocation(wb: Workbook) -> None:
    """Crée la feuille d'allocation cible avec la règle âge-en-obligations.

    Args:
        wb: Classeur openpyxl.
    """
    ws = wb.create_sheet("Allocation_Cible")
    ws.sheet_view.showGridLines = False

    _en_tete_feuille(
        ws,
        "🎯 Allocation Cible — Approche Bogleheads",
        "Règle : pct_obligations ≈ âge (age-in-bonds rule) | Profils prudent / équilibré / dynamique",
    )

    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 18
    ws.column_dimensions["E"].width = 25
    ws.row_dimensions[1].height = 30

    # ---- Tableau 1 : Profils prédéfinis ----
    ws["A4"] = "📊 PROFILS D'ALLOCATION PRÉDÉFINIS"
    ws["A4"].font = Font(bold=True, size=11, color="1F497D")
    ws.merge_cells("A4:E4")

    en_tetes_profils = ["Classe d'Actifs", "Prudent", "Équilibré", "Dynamique", "Description"]
    row = 5
    for col, texte in enumerate(en_tetes_profils, start=1):
        cell = ws.cell(row=row, column=col, value=texte)
        cell.font = POLICE_EN_TETE
        cell.fill = FILL_EN_TETE_BLEU
        cell.alignment = ALIGN_CENTRE

    lignes_profils = [
        ("Actions", 0.30, 0.60, 0.80, "Inclut monde, émergents, small cap"),
        ("Obligations", 0.70, 0.40, 0.20, "Inclut souverains, crédit IG"),
        ("Liquidités", 0.00, 0.00, 0.00, "Hors scope (fonds monétaire si besoin)"),
        ("TOTAL", 1.00, 1.00, 1.00, "Doit totaliser 100%"),
    ]

    row = 6
    for label, prudent, equilibre, dynamique, desc in lignes_profils:
        is_total = label == "TOTAL"
        ws.cell(row=row, column=1).value = label
        ws.cell(row=row, column=1).font = Font(bold=is_total, size=10)
        for col, val in enumerate([prudent, equilibre, dynamique], start=2):
            cell = ws.cell(row=row, column=col, value=val)
            cell.number_format = "0%"
            cell.alignment = ALIGN_CENTRE
            cell.font = Font(bold=is_total, size=10)
        ws.cell(row=row, column=5).value = desc
        ws.cell(row=row, column=5).font = Font(size=9, italic=True)
        row += 1

    last_row_profils = row - 1
    _creer_table(ws, f"A5:E{last_row_profils}", "tblProfils", "TableStyleMedium9")
    _appliquer_bordure(ws, 5, last_row_profils, 1, 5)

    # ---- Tableau 2 : Règle âge-en-obligations ----
    row += 2
    ws.cell(row=row, column=1).value = "🎂 RÈGLE ÂGE-EN-OBLIGATIONS (Bogleheads)"
    ws.cell(row=row, column=1).font = Font(bold=True, size=11, color="1F497D")
    ws.merge_cells(f"A{row}:E{row}")
    row += 1

    en_tetes_age = ["Âge", "% Obligations (std)", "% Actions (std)", "% Oblig (conserv.)", "% Oblig (agressif)"]
    for col, texte in enumerate(en_tetes_age, start=1):
        cell = ws.cell(row=row, column=col, value=texte)
        cell.font = POLICE_EN_TETE
        cell.fill = FILL_EN_TETE_BLEU
        cell.alignment = ALIGN_CENTRE

    first_age_row = row + 1
    ages = [25, 30, 35, 40, 45, 50, 55, 60, 65, 70]
    row += 1
    for age in ages:
        pct_oblig_std = min(age / 100.0, 1.0)
        pct_act_std = 1.0 - pct_oblig_std
        pct_oblig_conserv = min((age + 10) / 100.0, 1.0)
        pct_oblig_agressif = max((age - 10) / 100.0, 0.0)

        valeurs = [age, pct_oblig_std, pct_act_std, pct_oblig_conserv, pct_oblig_agressif]
        for col, val in enumerate(valeurs, start=1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.alignment = ALIGN_CENTRE
            cell.font = Font(size=10)
            if col > 1:
                cell.number_format = "0%"
        row += 1

    last_age_row = row - 1
    _creer_table(ws, f"A{first_age_row - 1}:E{last_age_row}", "tblAgeObligations", "TableStyleLight1")
    _appliquer_bordure(ws, first_age_row - 1, last_age_row, 1, 5)

    # ---- Tableau 3 : Décomposition sous-classes ----
    row += 2
    ws.cell(row=row, column=1).value = "🔍 DÉCOMPOSITION DES SOUS-CLASSES D'ACTIFS"
    ws.cell(row=row, column=1).font = Font(bold=True, size=11, color="1F497D")
    ws.merge_cells(f"A{row}:E{row}")
    row += 1

    en_tetes_sous = ["Poche", "Sous-classe", "% de la poche", "ETF de référence", "Remarque"]
    for col, texte in enumerate(en_tetes_sous, start=1):
        cell = ws.cell(row=row, column=col, value=texte)
        cell.font = POLICE_EN_TETE
        cell.fill = FILL_EN_TETE_VERT
        cell.alignment = ALIGN_CENTRE

    first_sous_row = row + 1
    sous_classes = [
        ("Actions", "Monde (MSCI World)", 0.60, "EWLD / IWDA / SWRD", "Cœur portefeuille"),
        ("Actions", "Émergents (MSCI EM)", 0.15, "PAEEM / EIMI", "Diversification pays émergents"),
        ("Actions", "Europe (MSCI Europe)", 0.15, "ESE / IMEU", "Complément zone euro"),
        ("Actions", "Small Cap Monde", 0.10, "WPEA", "Prime taille — optionnel"),
        ("Obligations", "État Zone Euro", 0.50, "MTS / IEAG", "Ancre sécurité"),
        ("Obligations", "État USA (Treasuries)", 0.20, "VUTY", "Diversification risque souverain"),
        ("Obligations", "Crédit IG Euro", 0.20, "CORP", "Rendement supplémentaire"),
        ("Obligations", "Haut rendement", 0.10, "IHYG", "Optionnel — risque crédit élevé"),
    ]

    row += 1
    for poche, sous_classe, pct, etf_ref, remarque in sous_classes:
        couleur = "E2EFDA" if poche == "Actions" else "DDEBF7"
        fill = PatternFill(fill_type="solid", fgColor=couleur)
        for col, val in enumerate([poche, sous_classe, pct, etf_ref, remarque], start=1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.fill = fill
            cell.font = Font(size=9)
            cell.alignment = ALIGN_CENTRE if col == 3 else ALIGN_GAUCHE
            if col == 3:
                cell.number_format = "0%"
        row += 1

    last_sous_row = row - 1
    _creer_table(ws, f"A{first_sous_row - 1}:E{last_sous_row}", "tblSousClasses", "TableStyleLight9")
    _appliquer_bordure(ws, first_sous_row - 1, last_sous_row, 1, 5)


# ---------------------------------------------------------------------------
# Feuille 6 : Asset_Location_Matrice
# ---------------------------------------------------------------------------

def _creer_feuille_asset_location(wb: Workbook, etf_data: dict, fiscalite: dict | None = None) -> None:
    """Crée la matrice ETF × Enveloppe pour l'asset location.

    Inclut les contraintes d'éligibilité (cellules grisées si non éligible),
    les plafonds par enveloppe, et des cellules prêtes pour le Solveur Excel.

    Args:
        wb: Classeur openpyxl.
        etf_data: Dictionnaire issu de univers_etf.yaml.
        fiscalite: Dictionnaire issu de fiscalite_2026.yaml (pour les taux de sortie).
    """
    ws = wb.create_sheet("Asset_Location_Matrice")
    ws.sheet_view.showGridLines = False

    _en_tete_feuille(
        ws,
        "🧩 Matrice Asset Location — ETF × Enveloppe",
        "Cellules grisées = non éligible | Objectif : maximiser VAN nette d'impôts | Prêt pour Solveur Excel",
    )

    # Identifiants et noms des enveloppes
    enveloppes_ids = ["cto_perso", "cto_is", "contrat_capi_is", "pea", "per", "pee"]
    enveloppes_noms = ["CTO Perso", "CTO IS", "Capi IS", "PEA", "PER", "PEE"]
    plafonds = {
        "cto_perso": "Sans plafond",
        "cto_is": "Sans plafond",
        "contrat_capi_is": "Sans plafond",
        "pea": "150 000 €",
        "per": "Variable",
        "pee": "25% salaire",
    }
    taux_sortie = {
        "cto_perso": "31.4%",
        "cto_is": "25%",
        "contrat_capi_is": "25%",
        "pea": "17.2%",
        "per": "TMI+10.3%",
        "pee": "17.2%",
    }

    # Largeurs colonnes
    ws.column_dimensions["A"].width = 10   # ISIN
    ws.column_dimensions["B"].width = 8    # Ticker
    ws.column_dimensions["C"].width = 40   # Nom ETF
    ws.column_dimensions["D"].width = 22   # Classe actifs
    ws.column_dimensions["E"].width = 8    # Type

    n_env = len(enveloppes_ids)
    for i in range(n_env):
        ws.column_dimensions[get_column_letter(6 + i)].width = 14

    # En-têtes fixes
    en_tetes_fixes = ["ISIN", "Ticker", "Nom ETF", "Classe Actifs", "Type"]
    row = 4
    for col, texte in enumerate(en_tetes_fixes, start=1):
        cell = ws.cell(row=row, column=col, value=texte)
        cell.font = POLICE_EN_TETE
        cell.fill = FILL_EN_TETE_BLEU
        cell.alignment = ALIGN_CENTRE

    # En-têtes enveloppes avec couleurs
    for i, (env_id, nom) in enumerate(zip(enveloppes_ids, enveloppes_noms)):
        col = 6 + i
        couleur_hex = COULEURS_ENVELOPPES.get(env_id, "FFFFFF")
        cell = ws.cell(row=4, column=col, value=nom)
        cell.font = Font(bold=True, size=10)
        cell.fill = PatternFill(fill_type="solid", fgColor=couleur_hex)
        cell.alignment = ALIGN_CENTRE

    # Plafonds
    ws.cell(row=5, column=1).value = "Plafond"
    ws.cell(row=5, column=1).font = Font(bold=True, size=9, italic=True)
    for i, env_id in enumerate(enveloppes_ids):
        cell = ws.cell(row=5, column=6 + i, value=plafonds[env_id])
        cell.font = Font(size=9, italic=True)
        cell.alignment = ALIGN_CENTRE

    # Taux de sortie
    ws.cell(row=6, column=1).value = "Taux sortie"
    ws.cell(row=6, column=1).font = Font(bold=True, size=9, italic=True)
    for i, env_id in enumerate(enveloppes_ids):
        cell = ws.cell(row=6, column=6 + i, value=taux_sortie[env_id])
        cell.font = Font(size=9, italic=True, color="C00000")
        cell.alignment = ALIGN_CENTRE

    # Remplissage des ETFs
    etfs = etf_data.get("etfs", []) if isinstance(etf_data, dict) else []
    row = 7
    fill_non_eligible = PatternFill(fill_type="solid", fgColor=GRIS_NON_ELIGIBLE)
    fill_eligible = PatternFill(fill_type="solid", fgColor="FFFFFF")

    for etf in etfs:
        eligibilite = etf.get("eligibilite", {})

        # Colonnes fixes
        valeurs_fixes = [
            etf.get("isin", ""),
            etf.get("ticker", ""),
            etf.get("nom", ""),
            etf.get("classe_actifs", ""),
            etf.get("type", ""),
        ]
        for col, val in enumerate(valeurs_fixes, start=1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.font = Font(size=9)
            cell.alignment = ALIGN_GAUCHE

        # Colonnes enveloppes
        for i, env_id in enumerate(enveloppes_ids):
            col = 6 + i
            est_eligible = eligibilite.get(env_id, False)

            if not est_eligible:
                # Cellule grisée — non éligible
                cell = ws.cell(row=row, column=col, value="—")
                cell.fill = fill_non_eligible
                cell.font = Font(size=9, color="808080")
                cell.alignment = ALIGN_CENTRE
            else:
                # Cellule éditable — montant à allouer (défaut 0)
                cell = ws.cell(row=row, column=col, value=0)
                cell.fill = fill_eligible
                cell.number_format = "#,##0 €"
                cell.font = Font(size=9)
                cell.alignment = ALIGN_DROITE

        ws.row_dimensions[row].height = 30
        row += 1

    last_etf_row = row - 1

    # Ligne totaux par enveloppe (pour contraintes Solveur)
    row += 1
    ws.cell(row=row, column=1).value = "TOTAL enveloppe"
    ws.cell(row=row, column=1).font = Font(bold=True, size=10)
    ws.merge_cells(f"A{row}:E{row}")

    for i, env_id in enumerate(enveloppes_ids):
        col = 6 + i
        # Formule somme de la colonne (uniquement les lignes avec valeurs numériques)
        col_lettre = get_column_letter(col)
        ws.cell(row=row, column=col).value = f"=SUMIF({col_lettre}7:{col_lettre}{last_etf_row},\"<>—\")"
        ws.cell(row=row, column=col).font = Font(bold=True, size=10)
        ws.cell(row=row, column=col).number_format = "#,##0 €"
        ws.cell(row=row, column=col).fill = PatternFill(fill_type="solid", fgColor="FFF2CC")
        ws.cell(row=row, column=col).alignment = ALIGN_DROITE

    # Cellule objectif VAN nette d'impôts
    row += 2
    ws.cell(row=row, column=1).value = "📍 CELLULE OBJECTIF — VAN nette d'impôts"
    ws.cell(row=row, column=1).font = Font(bold=True, size=11, color="C00000")
    ws.merge_cells(f"A{row}:E{row}")

    row += 1
    ws.cell(row=row, column=1).value = "VAN nette d'impôts (estimation simplifiée)"
    ws.cell(row=row, column=1).font = Font(bold=True, size=10)

    # Taux de sortie extraits de la configuration fiscale (ou valeurs par défaut documentées)
    if fiscalite:
        pfu = fiscalite.get("pfu", {}).get("taux_total", 0.314)
        is_25 = fiscalite.get("is", {}).get("taux_normal", 0.25)
        ps = fiscalite.get("prelevements_sociaux", {}).get("taux_total", 0.172)
        tmi_moyen = 0.30 + ps  # Approximation PER sortie : TMI moyen 30% + PS
    else:
        pfu, is_25, ps, tmi_moyen = 0.314, 0.25, 0.172, 0.413
    # CTO Perso=PFU, CTO IS=IS25%, ContratCapi=IS25%, PEA=PS, PER=TMI+PS, PEE=PS
    taux_sortie_num = [pfu, is_25, is_25, ps, tmi_moyen, ps]
    formule_parts = []
    for i, taux in enumerate(taux_sortie_num):
        col = 6 + i
        col_lettre = get_column_letter(col)
        formule_parts.append(
            f"SUMIF({col_lettre}7:{col_lettre}{last_etf_row},\"<>—\")*(1-{taux})"
        )

    ws.cell(row=row, column=6).value = "=" + "+".join(formule_parts)
    ws.cell(row=row, column=6).font = Font(bold=True, size=11, color="1F497D")
    ws.cell(row=row, column=6).number_format = "#,##0 €"
    ws.cell(row=row, column=6).fill = PatternFill(fill_type="solid", fgColor="E2EFDA")

    _appliquer_bordure(ws, 4, last_etf_row, 1, 5 + n_env)

    # Note d'utilisation
    row += 2
    ws.cell(row=row, column=1).value = (
        "💡 Utilisation du Solveur Excel : Définir la cellule VAN comme objectif à maximiser. "
        "Variables : cellules blanches (allocations en €). "
        "Contraintes : totaux ≤ plafonds enveloppes, sommes = allocations cibles, cellules grisées = 0."
    )
    ws.cell(row=row, column=1).font = Font(size=9, italic=True, color="595959")
    ws.cell(row=row, column=1).alignment = Alignment(wrap_text=True)
    ws.merge_cells(f"A{row}:{get_column_letter(5 + n_env)}{row}")
    ws.row_dimensions[row].height = 45


# ---------------------------------------------------------------------------
# Feuille 7 : Rebalancement
# ---------------------------------------------------------------------------

def _creer_feuille_rebalancement(wb: Workbook) -> None:
    """Crée la feuille de rebalancement avec calcul de coût fiscal.

    Args:
        wb: Classeur openpyxl.
    """
    ws = wb.create_sheet("Rebalancement")
    ws.sheet_view.showGridLines = False

    _en_tete_feuille(
        ws,
        "⚖️ Rebalancement — Bandes de Tolérance & Coût Fiscal",
        "Méthodes : ±5 pts absolus (relatif_5pct) ou ±25% relatif (Larry Swedroe) | Cash-flow rebalancing prioritaire",
    )

    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 15
    ws.column_dimensions["C"].width = 15
    ws.column_dimensions["D"].width = 15
    ws.column_dimensions["E"].width = 15
    ws.column_dimensions["F"].width = 20
    ws.row_dimensions[1].height = 30

    # ---- Section 1 : Allocation actuelle ----
    row = 4
    ws["A4"] = "📊 SAISIE DE L'ALLOCATION ACTUELLE"
    ws["A4"].font = Font(bold=True, size=11, color="1F497D")
    ws.merge_cells("A4:F4")
    row = 5

    en_tetes_alloc = [
        "Classe d'Actifs", "Montant actuel (€)", "% Actuel",
        "% Cible", "Écart (pts)", "Statut"
    ]
    for col, texte in enumerate(en_tetes_alloc, start=1):
        cell = ws.cell(row=row, column=col, value=texte)
        cell.font = POLICE_EN_TETE
        cell.fill = FILL_EN_TETE_BLEU
        cell.alignment = ALIGN_CENTRE

    row = 6
    # Ligne Actions
    ws.cell(row=row, column=1).value = "Actions"
    _cellule_valeur(ws, row, 2, 300000, "#,##0 €")
    ws.cell(row=row, column=3).value = "=B6/B9"
    ws.cell(row=row, column=3).number_format = "0.0%"
    ws.cell(row=row, column=4).value = 0.60
    ws.cell(row=row, column=4).number_format = "0%"
    ws.cell(row=row, column=5).value = "=C6-D6"
    ws.cell(row=row, column=5).number_format = "+0.0%;-0.0%"
    ws.cell(row=row, column=6).value = '=IF(ABS(C6-D6)<=0.05,"✅ Dans bandes","⚠️ Hors bandes")'
    row += 1

    # Ligne Obligations
    ws.cell(row=row, column=1).value = "Obligations"
    _cellule_valeur(ws, row, 2, 180000, "#,##0 €")
    ws.cell(row=row, column=3).value = "=B7/B9"
    ws.cell(row=row, column=3).number_format = "0.0%"
    ws.cell(row=row, column=4).value = 0.40
    ws.cell(row=row, column=4).number_format = "0%"
    ws.cell(row=row, column=5).value = "=C7-D7"
    ws.cell(row=row, column=5).number_format = "+0.0%;-0.0%"
    ws.cell(row=row, column=6).value = '=IF(ABS(C7-D7)<=0.05,"✅ Dans bandes","⚠️ Hors bandes")'
    row += 1

    # Ligne Liquidités
    ws.cell(row=row, column=1).value = "Liquidités"
    _cellule_valeur(ws, row, 2, 20000, "#,##0 €")
    ws.cell(row=row, column=3).value = "=B8/B9"
    ws.cell(row=row, column=3).number_format = "0.0%"
    ws.cell(row=row, column=4).value = 0.00
    ws.cell(row=row, column=4).number_format = "0%"
    ws.cell(row=row, column=5).value = "=C8-D8"
    ws.cell(row=row, column=5).number_format = "+0.0%;-0.0%"
    ws.cell(row=row, column=6).value = '=IF(ABS(C8-D8)<=0.05,"✅ Dans bandes","⚠️ Hors bandes")'
    row += 1

    # Ligne Total
    ws.cell(row=row, column=1).value = "TOTAL"
    ws.cell(row=row, column=1).font = Font(bold=True)
    ws.cell(row=row, column=2).value = "=SUM(B6:B8)"
    ws.cell(row=row, column=2).number_format = "#,##0 €"
    ws.cell(row=row, column=2).font = Font(bold=True)
    ws.cell(row=row, column=3).value = "=SUM(C6:C8)"
    ws.cell(row=row, column=3).number_format = "0.0%"
    ws.cell(row=row, column=3).font = Font(bold=True)

    _creer_table(ws, f"A5:F{row}", "tblAllocationActuelle", "TableStyleMedium2")
    _appliquer_bordure(ws, 5, row, 1, 6)

    # Mise en forme conditionnelle — rouge si hors bandes
    rouge_fill = PatternFill(start_color=ROUGE_CLAIR, end_color=ROUGE_CLAIR, fill_type="solid")
    vert_fill = PatternFill(start_color=VERT_CLAIR, end_color=VERT_CLAIR, fill_type="solid")

    for r in [6, 7, 8]:
        ws.conditional_formatting.add(
            f"F{r}",
            FormulaRule(formula=[f'F{r}="⚠️ Hors bandes"'], fill=rouge_fill),
        )
        ws.conditional_formatting.add(
            f"F{r}",
            FormulaRule(formula=[f'F{r}="✅ Dans bandes"'], fill=vert_fill),
        )

    # ---- Section 2 : Paramètres de tolérance ----
    row += 3
    ws.cell(row=row, column=1).value = "⚙️ PARAMÈTRES DE TOLÉRANCE"
    ws.cell(row=row, column=1).font = Font(bold=True, size=11, color="1F497D")
    ws.merge_cells(f"A{row}:F{row}")
    row += 1

    params_tolerance = [
        ("Méthode de tolérance", "relatif_5pct", "Valeurs : relatif_5pct, larry_swedroe"),
        ("Bande absolue (±pts)", 0.05, "Pour méthode relatif_5pct : ±5 points"),
        ("Bande relative Swedroe (%)", 0.25, "Pour méthode Swedroe : ±25% de la cible"),
    ]
    debut_tolerance = row
    for label, val, commentaire in params_tolerance:
        _cellule_etiquette(ws, row, 1, label)
        _cellule_valeur(ws, row, 2, val, "0%" if isinstance(val, float) else None)
        ws.cell(row=row, column=3).value = commentaire
        ws.cell(row=row, column=3).font = Font(size=9, italic=True)
        ws.merge_cells(f"C{row}:F{row}")
        row += 1
    _appliquer_bordure(ws, debut_tolerance, row - 1, 1, 2)

    # ---- Section 3 : Calcul coût fiscal arbitrage ----
    row += 2
    ws.cell(row=row, column=1).value = "💰 CALCUL DU COÛT FISCAL D'UN ARBITRAGE"
    ws.cell(row=row, column=1).font = Font(bold=True, size=11, color="1F497D")
    ws.merge_cells(f"A{row}:F{row}")
    row += 1

    en_tetes_arbitrage = [
        "Paramètre", "Valeur", "Actions (CTO)", "Obligations (PEA)",
        "Obligations (PER)", "Commentaire"
    ]
    for col, texte in enumerate(en_tetes_arbitrage, start=1):
        cell = ws.cell(row=row, column=col, value=texte)
        cell.font = POLICE_EN_TETE
        cell.fill = FILL_EN_TETE_ORANGE
        cell.alignment = ALIGN_CENTRE

    row += 1
    debut_arbitrage = row
    arbitrage_params = [
        ("PV latente estimée (€)", 50000, 50000, 20000, 20000, "Modifier selon la situation"),
        ("Taux imposition enveloppe", "", 0.314, 0.172, 0.413, "CTO=31.4% | PEA=17.2% | PER=41.3% (TMI41+PS10.3%)"),
        ("Impôt immédiat (€)", "", "=C_PV*C_TAUX", "=D_PV*D_TAUX", "=E_PV*E_TAUX", "=pv_latente × taux"),
        ("Coût opportunité 10 ans (€)", "", "Voir formule", "Voir formule", "Voir formule", "=impôt×((1+7%)^10-1)"),
        ("Recommandation", "", "Arbitrage coûteux", "Moins coûteux", "Coûteux si TMI élevée", ""),
    ]

    for label, val_a, val_b, val_c, val_d, comm in arbitrage_params:
        ws.cell(row=row, column=1).value = label
        ws.cell(row=row, column=1).font = Font(bold=True, size=9)
        ws.cell(row=row, column=2).value = val_a
        ws.cell(row=row, column=3).value = val_b
        ws.cell(row=row, column=4).value = val_c
        ws.cell(row=row, column=5).value = val_d
        ws.cell(row=row, column=6).value = comm
        ws.cell(row=row, column=6).font = Font(size=9, italic=True)
        for col in [3, 4, 5]:
            cell = ws.cell(row=row, column=col)
            if isinstance(cell.value, float) and 0 < cell.value <= 1:
                cell.number_format = "0.0%"
            elif isinstance(cell.value, (int, float)) and cell.value > 1:
                cell.number_format = "#,##0 €"
        row += 1

    _appliquer_bordure(ws, debut_arbitrage - 1, row - 1, 1, 6)

    # ---- Section 4 : Recommandation rééquilibrage ----
    row += 2
    ws.cell(row=row, column=1).value = "💡 STRATÉGIE DE RÉÉQUILIBRAGE RECOMMANDÉE"
    ws.cell(row=row, column=1).font = Font(bold=True, size=11, color="1F497D")
    ws.merge_cells(f"A{row}:F{row}")
    row += 1

    conseils = [
        ("1. CASH-FLOW REBALANCING", "Utiliser les nouveaux versements et dividendes pour acheter les classes sous-pondérées — AUCUN coût fiscal", "PRIORITÉ 1"),
        ("2. COUPON STRIPPING", "Réorienter les dividendes/coupons distribués vers les classes déficitaires", "PRIORITÉ 2"),
        ("3. ARBITRAGE ENVELOPPE EXONÉRÉE", "Rééquilibrer en vendant/achetant à l'intérieur du PEA (exonéré IR) ou du PER", "PRIORITÉ 3"),
        ("4. ARBITRAGE CTO (DERNIER RECOURS)", "Seulement si déséquilibre > bandes et impossible autrement — minimiser les PV réalisées", "DERNIER RECOURS"),
    ]

    for strategie, description, priorite in conseils:
        ws.cell(row=row, column=1).value = strategie
        ws.cell(row=row, column=1).font = Font(bold=True, size=10)
        ws.cell(row=row, column=2).value = description
        ws.cell(row=row, column=2).font = Font(size=9)
        ws.merge_cells(f"B{row}:E{row}")
        cell_prio = ws.cell(row=row, column=6, value=priorite)
        cell_prio.font = Font(bold=True, size=9)
        if "PRIORITÉ 1" in priorite:
            cell_prio.fill = PatternFill(fill_type="solid", fgColor=VERT_CLAIR)
        elif "DERNIER" in priorite:
            cell_prio.fill = PatternFill(fill_type="solid", fgColor=ROUGE_CLAIR)
        else:
            cell_prio.fill = PatternFill(fill_type="solid", fgColor=ORANGE_CLAIR)
        row += 1

    _appliquer_bordure(ws, row - 4, row - 1, 1, 6)


# ---------------------------------------------------------------------------
# Feuille 8 : Reporting_Client
# ---------------------------------------------------------------------------

def _creer_feuille_reporting(wb: Workbook) -> None:
    """Crée la feuille de reporting client avec synthèse globale.

    Args:
        wb: Classeur openpyxl.
    """
    ws = wb.create_sheet("Reporting_Client")
    ws.sheet_view.showGridLines = False

    _en_tete_feuille(
        ws,
        "📄 Reporting Client — Synthèse Patrimoniale Bogleheads",
        "Synthèse par enveloppe, par classe d'actifs | Valeur ajoutée fiscale vs scénario CTO naïf",
    )

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 18
    ws.column_dimensions["E"].width = 18
    ws.column_dimensions["F"].width = 25
    ws.row_dimensions[1].height = 30

    # ---- Bloc 1 : Synthèse globale ----
    row = 4
    ws["A4"] = "🌐 SYNTHÈSE GLOBALE DU PATRIMOINE"
    ws["A4"].font = Font(bold=True, size=12, color="1F497D")
    ws.merge_cells("A4:F4")
    row = 5

    synthese_globale = [
        ("Patrimoine financier total", "=Paramètres_Client!B12", "#,##0 €", ""),
        ("Dont PEA", "=Paramètres_Client!B13", "#,##0 €", ""),
        ("Dont PER", "=Paramètres_Client!B14", "#,##0 €", ""),
        ("Dont PEE", "=Paramètres_Client!B15", "#,##0 €", ""),
        ("Dont CTO Perso", "=Paramètres_Client!B16", "#,##0 €", ""),
        ("TMI", "=Paramètres_Client!B7", "0%", ""),
        ("Horizon de placement", "=Paramètres_Client!B10", "# ans", ""),
        ("Profil de risque", "=Paramètres_Client!B22", "@", ""),
    ]

    for label, valeur, fmt, commentaire in synthese_globale:
        _cellule_etiquette(ws, row, 1, label)
        cell = ws.cell(row=row, column=2, value=valeur)
        cell.font = Font(bold=True, size=10)
        cell.fill = PatternFill(fill_type="solid", fgColor="EBF1DE")
        cell.alignment = ALIGN_DROITE
        if fmt and fmt != "@":
            cell.number_format = fmt
        if commentaire:
            ws.cell(row=row, column=3).value = commentaire
            ws.cell(row=row, column=3).font = Font(size=9, italic=True)
        row += 1

    _appliquer_bordure(ws, 5, row - 1, 1, 2)

    # ---- Bloc 2 : Répartition par enveloppe ----
    row += 2
    ws.cell(row=row, column=1).value = "🏦 RÉPARTITION PAR ENVELOPPE"
    ws.cell(row=row, column=1).font = Font(bold=True, size=12, color="1F497D")
    ws.merge_cells(f"A{row}:F{row}")
    row += 1

    en_tetes_env = ["Enveloppe", "Valeur actuelle (€)", "% Patrimoine", "Plafond", "Espace restant (€)", "Taux sortie"]
    for col, texte in enumerate(en_tetes_env, start=1):
        cell = ws.cell(row=row, column=col, value=texte)
        cell.font = POLICE_EN_TETE
        cell.fill = FILL_EN_TETE_BLEU
        cell.alignment = ALIGN_CENTRE

    debut_env = row + 1
    row += 1

    enveloppes_reporting = [
        ("CTO Personne Physique", "=Paramètres_Client!B16", "Sans plafond", "N/A", "31.4%", "cto_perso"),
        ("CTO Société IS", 0, "Sans plafond", "N/A", "25%", "cto_is"),
        ("Contrat Capitalisation IS", 0, "Sans plafond", "N/A", "25%", "contrat_capi_is"),
        ("PEA", "=Paramètres_Client!B13", "150 000 €", "=150000-Paramètres_Client!B13", "17.2%", "pea"),
        ("PER Individuel", "=Paramètres_Client!B14", "Variable", "N/A", "TMI+10.3%", "per"),
        ("PEE", "=Paramètres_Client!B15", "25% salaire brut", "N/A", "17.2%", "pee"),
        ("TOTAL", "=SUM(B{0}:B{1})", "", "", "", ""),
    ]

    total_formula_start = row
    for i, (nom, valeur, plafond, espace, taux, env_id) in enumerate(enveloppes_reporting):
        if nom == "TOTAL":
            valeur = f"=SUM(B{total_formula_start}:B{row-1})"
            ws.cell(row=row, column=1).value = nom
            ws.cell(row=row, column=1).font = Font(bold=True)
            cell_total = ws.cell(row=row, column=2, value=valeur)
            cell_total.font = Font(bold=True)
            cell_total.number_format = "#,##0 €"
            cell_total.alignment = ALIGN_DROITE
            ws.cell(row=row, column=3).value = "=B{}/B{}&\"\"".format(row, row)
            ws.cell(row=row, column=3).number_format = "0.0%"
        else:
            couleur = COULEURS_ENVELOPPES.get(env_id, "FFFFFF")
            fill = PatternFill(fill_type="solid", fgColor=couleur)
            ws.cell(row=row, column=1).value = nom
            ws.cell(row=row, column=1).fill = fill
            ws.cell(row=row, column=1).font = Font(bold=False, size=10)

            cell_val = ws.cell(row=row, column=2, value=valeur)
            cell_val.fill = fill
            cell_val.number_format = "#,##0 €"
            cell_val.alignment = ALIGN_DROITE

            pct_row = row
            total_row = total_formula_start + len(enveloppes_reporting) - 1
            cell_pct = ws.cell(row=row, column=3)
            cell_pct.value = f"=IFERROR(B{pct_row}/B{total_row + 1},0)"
            cell_pct.number_format = "0.0%"
            cell_pct.fill = fill
            cell_pct.alignment = ALIGN_CENTRE

            ws.cell(row=row, column=4).value = plafond
            ws.cell(row=row, column=4).fill = fill
            ws.cell(row=row, column=4).alignment = ALIGN_CENTRE

            cell_espace = ws.cell(row=row, column=5, value=espace)
            cell_espace.fill = fill
            if isinstance(espace, str) and espace.startswith("="):
                cell_espace.number_format = "#,##0 €"
            cell_espace.alignment = ALIGN_DROITE

            cell_taux = ws.cell(row=row, column=6, value=taux)
            cell_taux.fill = fill
            cell_taux.font = Font(color="C00000", bold=True, size=10)
            cell_taux.alignment = ALIGN_CENTRE

        row += 1

    _creer_table(ws, f"A{debut_env - 1}:F{row - 1}", "tblReportingEnveloppes", "TableStyleMedium4")
    _appliquer_bordure(ws, debut_env - 1, row - 1, 1, 6)

    # ---- Bloc 3 : Valeur ajoutée fiscale ----
    row += 2
    ws.cell(row=row, column=1).value = "📈 VALEUR AJOUTÉE FISCALE VS SCÉNARIO NAÏF (TOUT CTO)"
    ws.cell(row=row, column=1).font = Font(bold=True, size=12, color="1F497D")
    ws.merge_cells(f"A{row}:F{row}")
    row += 1

    en_tetes_va = [
        "Scénario", "Gain brut hypothétique (€)", "Impôt estimé (€)",
        "Gain net (€)", "Taux effectif", "Avantage vs CTO (€)"
    ]
    for col, texte in enumerate(en_tetes_va, start=1):
        cell = ws.cell(row=row, column=col, value=texte)
        cell.font = POLICE_EN_TETE
        cell.fill = FILL_EN_TETE_VERT
        cell.alignment = ALIGN_CENTRE

    debut_va = row + 1
    row += 1

    # Hypothèse : rendement 7% sur 100k€ sur 10 ans
    gain_hypothetique = 96715  # (1.07^10 - 1) × 100 000

    scenarios = [
        ("Tout CTO (scénario naïf)", gain_hypothetique, gain_hypothetique * 0.314, gain_hypothetique * 0.686, 0.314, 0),
        ("Optimisé PEA 60%", gain_hypothetique, gain_hypothetique * (0.6 * 0.172 + 0.4 * 0.314),
         gain_hypothetique * (1 - (0.6 * 0.172 + 0.4 * 0.314)), 0.6 * 0.172 + 0.4 * 0.314, None),
        ("Optimisé PEA + PER (TMI 30%)", gain_hypothetique, gain_hypothetique * 0.18,
         gain_hypothetique * 0.82, 0.18, None),
        ("Optimisé PEA + PER (TMI 41%)", gain_hypothetique, gain_hypothetique * 0.16,
         gain_hypothetique * 0.84, 0.16, None),
    ]

    impot_cto = gain_hypothetique * 0.314  # Référence CTO

    for nom, gain_brut, impot, gain_net, taux_eff, avantage in scenarios:
        if avantage is None:
            avantage = impot_cto - impot

        for col, val in enumerate([nom, gain_brut, impot, gain_net, taux_eff, avantage], start=1):
            cell = ws.cell(row=row, column=col, value=round(val, 2) if isinstance(val, float) else val)
            cell.font = Font(size=10)
            cell.alignment = ALIGN_CENTRE if col > 1 else ALIGN_GAUCHE
            if col in [2, 3, 4, 6]:
                cell.number_format = "#,##0 €"
            elif col == 5:
                cell.number_format = "0.0%"

        # Colorer la ligne référence en gris
        if "naïf" in nom:
            for col in range(1, 7):
                ws.cell(row=row, column=col).fill = PatternFill(fill_type="solid", fgColor=GRIS_CLAIR)

        row += 1

    _creer_table(ws, f"A{debut_va - 1}:F{row - 1}", "tblValeurAjoutee", "TableStyleMedium3")
    _appliquer_bordure(ws, debut_va - 1, row - 1, 1, 6)

    # ---- Note hypothèses ----
    row += 1
    ws.cell(row=row, column=1).value = (
        "📌 Hypothèses : Gain brut = rendement 7%/an × 10 ans × 100 000 € de capital initial. "
        "Taux effectifs approximatifs selon la composition des enveloppes. "
        "⚠️ Ces projections sont purement indicatives — ne constituent pas un conseil en investissement."
    )
    ws.cell(row=row, column=1).font = Font(size=9, italic=True, color="595959")
    ws.cell(row=row, column=1).alignment = Alignment(wrap_text=True)
    ws.merge_cells(f"A{row}:F{row}")
    ws.row_dimensions[row].height = 45


# ---------------------------------------------------------------------------
# Fonction principale de construction du classeur
# ---------------------------------------------------------------------------

def construire_workbook(
    fiscalite: dict,
    enveloppes_data: dict,
    etf_data: dict,
) -> Workbook:
    """Construit le classeur Excel complet Bogleheads CGP France 2026.

    Crée les 8 feuilles structurées avec tableaux, validations et mises en forme.

    Args:
        fiscalite: Dictionnaire issu de config/fiscalite_2026.yaml.
        enveloppes_data: Dictionnaire issu de config/enveloppes.yaml.
        etf_data: Dictionnaire issu de config/univers_etf.yaml.

    Returns:
        Classeur openpyxl prêt à être sauvegardé.
    """
    wb = Workbook()

    # Suppression de la feuille par défaut créée par openpyxl
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]

    # Création des 8 feuilles dans l'ordre
    _creer_feuille_parametres_client(wb)
    _creer_feuille_fiscalite(wb, fiscalite)
    _creer_feuille_enveloppes(wb, enveloppes_data)
    _creer_feuille_etf(wb, etf_data)
    _creer_feuille_allocation(wb)
    _creer_feuille_asset_location(wb, etf_data, fiscalite)
    _creer_feuille_rebalancement(wb)
    _creer_feuille_reporting(wb)

    # Propriétés du classeur
    wb.properties.title = "Outil CGP Bogleheads France 2026"
    wb.properties.creator = "CGP Bogleheads — Gestion Indicielle Passive"
    wb.properties.description = (
        "Outil de conseil patrimonial Bogleheads — "
        "Allocation d'actifs, asset location, rebalancement, fiscalité 2026"
    )

    return wb
