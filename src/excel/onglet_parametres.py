import openpyxl
from openpyxl.styles import Font
from src.excel.styles import (
    COULEUR_HEADER, COULEUR_SUBHEADER, COULEUR_AVERTISSEMENT, COULEUR_OK,
    COULEUR_LIGHT_GREY, COULEUR_LIGHT_BLUE,
    _fill, _font, _align, _thin_border,
    style_header, style_subheader, style_data,
    set_col_width, ajouter_disclaimer, titre_section,
)


# ─── Onglet 1 : Paramètres Client ───────────────────────────────────
def creer_onglet_parametres_client(wb: openpyxl.Workbook, profil: dict = None):
    ws = wb.create_sheet("Paramètres_Client")
    ws.sheet_view.showGridLines = False

    # Titre principal
    ws.merge_cells("A1:F1")
    c = ws["A1"]
    c.value = "🏦 PARAMÈTRES CLIENT — BOGLEHEAD FR 2026"
    style_header(c, size=14)
    ws.row_dimensions[1].height = 30

    row = ajouter_disclaimer(ws, 2, 1, 6)

    if profil:
        row = titre_section(ws, row, "📋 IDENTITÉ ET SITUATION FISCALE", 1, 6)
        infos = [
            ("Nom / Référence", profil.get("nom", "—")),
            ("Âge", profil.get("age", "—")),
            ("Situation familiale", profil.get("situation_familiale", "—")),
            ("TMI (Taux Marginal d'Imposition)", f"{profil.get('tmi', 0)*100:.0f}%"),
            ("RFR annuel estimé", profil.get("rfr_annuel", 0)),
            ("Régime fiscal", profil.get("regime_fiscal", "—")),
            ("CEHR applicable", "Oui" if profil.get("cehr_applicable") else "Non"),
            ("CDHR applicable", "Oui" if profil.get("cdhr_applicable") else "Non"),
        ]
        for label, val in infos:
            ws.cell(row=row, column=1, value=label).font = _font(bold=True)
            ws.cell(row=row, column=1).fill = _fill(COULEUR_LIGHT_GREY)
            ws.cell(row=row, column=2, value=val)
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                ws.cell(row=row, column=2).number_format = "#,##0 €"
            row += 1

        row += 1
        row = titre_section(ws, row, "💰 PATRIMOINE ET CAPACITÉ D'ÉPARGNE", 1, 6)
        infos2 = [
            ("Patrimoine financier total", profil.get("patrimoine_financier_total", 0)),
            ("Patrimoine immobilier", profil.get("patrimoine_immobilier", 0)),
            ("Revenus annuels bruts", profil.get("revenus_annuels_bruts", 0)),
            ("Capacité d'épargne annuelle", profil.get("capacite_epargne_annuelle", 0)),
            ("Horizon de placement (ans)", profil.get("horizon_placement_ans", 0)),
            ("Score de risque (SRRI / 7)", profil.get("score_risque", "—")),
        ]
        for label, val in infos2:
            ws.cell(row=row, column=1, value=label).font = _font(bold=True)
            ws.cell(row=row, column=1).fill = _fill(COULEUR_LIGHT_GREY)
            cell = ws.cell(row=row, column=2, value=val)
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                cell.number_format = "#,##0 €" if val > 100 else "0"
            row += 1

        row += 1
        row = titre_section(ws, row, "🎯 OBJECTIFS", 1, 6)
        ws.cell(row=row, column=1, value="Objectif principal").font = _font(bold=True)
        ws.cell(row=row, column=1).fill = _fill(COULEUR_LIGHT_GREY)
        ws.cell(row=row, column=2, value=profil.get("objectif_principal", "—"))
        ws.row_dimensions[row].height = 20
        row += 1
        for i, obj in enumerate(profil.get("objectifs_secondaires", []), 1):
            ws.cell(row=row, column=1, value=f"Objectif secondaire {i}").fill = _fill(COULEUR_LIGHT_GREY)
            ws.cell(row=row, column=2, value=obj)
            row += 1
    else:
        row = titre_section(ws, row, "📋 SAISIR LES PARAMÈTRES CLIENT ICI", 1, 6)
        champs = [
            ("Nom / Référence client", ""),
            ("Âge", 0),
            ("Situation familiale", ""),
            ("TMI (%)", 0.30),
            ("RFR annuel (€)", 0),
            ("Régime fiscal", "IR"),
            ("Patrimoine financier total (€)", 0),
            ("Capacité d'épargne annuelle (€)", 0),
            ("Horizon de placement (ans)", 0),
            ("Score de risque (1-7)", 4),
        ]
        for label, val in champs:
            ws.cell(row=row, column=1, value=label).font = _font(bold=True)
            ws.cell(row=row, column=1).fill = _fill(COULEUR_LIGHT_GREY)
            ws.cell(row=row, column=2, value=val)
            row += 1

    set_col_width(ws, 1, 40)
    set_col_width(ws, 2, 35)
    for c in range(3, 7):
        set_col_width(ws, c, 15)
    ws.freeze_panes = "A3"


# ─── Onglet 2 : Fiscalité 2026 ──────────────────────────────────────
def creer_onglet_fiscalite(wb: openpyxl.Workbook, params_fiscaux: dict):
    ws = wb.create_sheet("Paramètres_Fiscalité_2026")
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:G1")
    c = ws["A1"]
    c.value = "📊 PARAMÈTRES FISCAUX 2026 — FRANCE"
    style_header(c, size=14)
    ws.row_dimensions[1].height = 30

    row = ajouter_disclaimer(ws, 2, 1, 7)

    # ── PFU ──
    row = titre_section(ws, row, "🔢 PRÉLÈVEMENT FORFAITAIRE UNIQUE (PFU / FLAT TAX)", 1, 7)
    headers = ["Composante", "Taux", "Application", "Notes"]
    for i, h in enumerate(headers, 1):
        style_subheader(ws.cell(row=row, column=i, value=h))
    row += 1
    pfu_data = [
        ("IR (Impôt sur le Revenu)", "12,8%", "Dividendes + Plus-values", "Taux fixe PFU"),
        ("Prélèvements Sociaux (PS)", "18,6%", "Dividendes + Plus-values + PEA sortie", "CSG 12,1% + CRDS 0,5% + Solidarité 6%"),
        ("PFU TOTAL", "31,4%", "CTO personnel par défaut", "12,8% + 18,6%"),
        ("Option barème IR", "TMI + 18,6%", "Sur option — si TMI < 12,8%", "Abattement 40% dividendes si option barème"),
    ]
    for data in pfu_data:
        for j, val in enumerate(data, 1):
            cell = ws.cell(row=row, column=j, value=val)
            style_data(cell, bg=COULEUR_LIGHT_GREY if row % 2 == 0 else None)
        row += 1

    row += 1
    # ── Enveloppes fiscalité sortie ──
    row = titre_section(ws, row, "🏦 FISCALITÉ PAR ENVELOPPE (SORTIE)", 1, 7)
    headers = ["Enveloppe", "IR sortie", "PS sortie", "Total sortie", "Avantage vs CTO", "Plafond versement", "Remarque clé"]
    for i, h in enumerate(headers, 1):
        style_subheader(ws.cell(row=row, column=i, value=h))
    row += 1
    env_data = [
        ("CTO personnel", "12,8% (PFU)", "18,6%", "31,4%", "Référence", "Illimité", "Scénario de référence"),
        ("PEA (après 5 ans)", "0% (exonéré)", "18,6%", "18,6%", "−12,8% vs CTO", "150 000 €", "PRIORITÉ — 12,8% économisés"),
        ("PEA (avant 5 ans)", "12,8%", "18,6%", "31,4%", "Aucun", "150 000 €", "Équivalent CTO avant 5 ans"),
        ("PER (retraite)", "TMI retraite", "18,6% gains", "Variable", "Transfert fiscal", "Illimité", "Déduction à l'entrée = avantage si TMI baisse"),
        ("PEE", "0% (exonéré)", "18,6%", "18,6%", "−12,8% vs CTO", "Illimité", "Abondement employeur = TRI immédiat"),
        ("Contrat cap IS", "IS 15/25%", "N/A (IS)", "15-25%", "vs CTO IS MTM", "Illimité", "Pas de mark-to-market = avantage majeur IS"),
        ("CTO IS", "IS 15/25% + MTM", "N/A (IS)", "15-25%*", "* MTM pénalisant", "Illimité", "⚠️ Mark-to-market annuel sur OPCVM"),
    ]
    for i, data in enumerate(env_data):
        bg = COULEUR_LIGHT_GREY if i % 2 == 0 else None
        for j, val in enumerate(data, 1):
            cell = ws.cell(row=row, column=j, value=val)
            style_data(cell, bg=bg)
            if j == 5:  # Avantage
                if "12,8%" in str(val):
                    cell.font = Font(bold=True, color=COULEUR_OK, size=10)
                elif "⚠️" in str(val) or "pénalisant" in str(val):
                    cell.font = Font(bold=True, color=COULEUR_AVERTISSEMENT, size=10)
        row += 1

    row += 1
    # ── IS ──
    row = titre_section(ws, row, "🏢 IMPÔT SUR LES SOCIÉTÉS (IS)", 1, 7)
    headers = ["Tranche bénéfice", "Taux IS", "Conditions", "Exemple", "", "", ""]
    for i, h in enumerate(headers, 1):
        style_subheader(ws.cell(row=row, column=i, value=h))
    row += 1
    is_data = [
        ("0 → 42 500 €", "15% (taux réduit)", "CA < 10M€, capital ≥75% pers. physiques", "42 500 € × 15% = 6 375 € IS"),
        ("Au-delà de 42 500 €", "25% (taux normal)", "Sur la fraction > 42 500 €", "57 500 € × 25% = 14 375 € IS"),
        ("Exemple 100 000 € bénéfice", "→ IS = 20 750 €", "Taux effectif = 20,75%", "42 500×15% + 57 500×25%"),
    ]
    for data in is_data:
        for j, val in enumerate(data, 1):
            style_data(ws.cell(row=row, column=j, value=val))
        row += 1

    row += 1
    # ── CEHR/CDHR ──
    row = titre_section(ws, row, "⚠️ CEHR ET CDHR (HAUTS REVENUS)", 1, 7)
    ws.cell(row=row, column=1, value="CEHR (Célibataire)").font = _font(bold=True)
    ws.cell(row=row, column=2, value="RFR 250 001 – 500 000 € → +3%")
    ws.cell(row=row, column=3, value="RFR > 500 000 € → +4%")
    ws.cell(row=row, column=4, value="S'ajoute au PFU/barème")
    row += 1
    ws.cell(row=row, column=1, value="CEHR (Couple)").font = _font(bold=True)
    ws.cell(row=row, column=2, value="RFR 500 001 – 1 000 000 € → +3%")
    ws.cell(row=row, column=3, value="RFR > 1 000 000 € → +4%")
    row += 1
    ws.cell(row=row, column=1, value="CDHR (LF 2025)").font = _font(bold=True)
    ws.cell(row=row, column=2, value="Taux effectif minimum 20% si RFR > 250 000 € (célibataire)")
    ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=6)
    row += 1

    row += 1
    # ── Contrat cap IS ──
    row = titre_section(ws, row, "📜 CONTRAT DE CAPITALISATION IS (ART. 238 SEPTIES E CGI)", 1, 7)
    ws.cell(row=row, column=1, value="Formule base taxable annuelle").font = _font(bold=True)
    ws.cell(row=row, column=2, value="Base = 105% × TME × Prime versée")
    ws.cell(row=row, column=3, value="Exemple: 1 000 000 € × 3% × 105% = 31 500 € base/an")
    ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=7)
    row += 1
    ws.cell(row=row, column=1, value="IS sur base forfaitaire").font = _font(bold=True)
    ws.cell(row=row, column=2, value="31 500 € × 15% = 4 725 € IS/an (vs MTM CTO IS)")
    ws.cell(row=row, column=3, value="⚠️ TME = taux en vigueur à la SOUSCRIPTION — vérifier avec assureur")
    ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=7)
    row += 1
    ws.cell(row=row, column=1, value="Absence de mark-to-market").font = _font(bold=True, color=COULEUR_OK)
    ws.cell(row=row, column=2, value="✅ Avantage MAJEUR vs CTO IS : pas de taxation des PV latentes")
    ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=7)
    row += 1

    for col, w in [(1, 30), (2, 22), (3, 22), (4, 22), (5, 20), (6, 18), (7, 35)]:
        set_col_width(ws, col, w)
    ws.freeze_panes = "A3"
