"""
Générateur Excel — Boglehead FR
Génère output/portefeuille_bogleheads.xlsx avec tous les onglets
"""
import yaml
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule
from pathlib import Path
import datetime

from src.projection import (
    AllocationClasses,
    ParametresProjection,
    charger_params as charger_params_projection,
    projeter_profil,
)

# ─── Palette couleurs ───────────────────────────────────────────────
COULEURS_CLASSES = {
    "Actions": "4472C4",
    "Obligations": "ED7D31",
    "Immobilier": "A9D18E",
    "Or": "FFD966",
    "Matières premières": "9DC3E6",
    "Monétaire": "70AD47",
    "Thématiques": "BF8FBF",
    "Diversifiants": "FF9999",
}

COULEUR_HEADER = "1F3864"
COULEUR_SUBHEADER = "2E75B6"
COULEUR_AVERTISSEMENT = "C00000"
COULEUR_OK = "70AD47"
COULEUR_WARNING = "FFC000"
COULEUR_DANGER = "FF0000"
COULEUR_LIGHT_BLUE = "DDEEFF"
COULEUR_LIGHT_GREY = "F2F2F2"
COULEUR_GOLD = "FFD966"

ROOT = Path(__file__).parent.parent


# ─── Helpers de style ───────────────────────────────────────────────
def load_yaml(filename: str) -> dict:
    with open(ROOT / "config" / filename, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _fill(color: str) -> PatternFill:
    return PatternFill("solid", fgColor=color)


def _font(bold=False, color="000000", size=10, italic=False) -> Font:
    return Font(bold=bold, color=color, size=size, italic=italic)


def _align(h="left", v="center", wrap=False) -> Alignment:
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)


def _thin_border() -> Border:
    s = Side(style="thin")
    return Border(left=s, right=s, top=s, bottom=s)


def style_header(cell, bg=COULEUR_HEADER, fg="FFFFFF", size=11, bold=True):
    cell.fill = _fill(bg)
    cell.font = Font(bold=bold, color=fg, size=size)
    cell.alignment = _align("center", "center", wrap=True)
    cell.border = _thin_border()


def style_subheader(cell, bg=COULEUR_SUBHEADER):
    cell.fill = _fill(bg)
    cell.font = Font(bold=True, color="FFFFFF", size=10)
    cell.alignment = _align("center", "center")
    cell.border = _thin_border()


def style_data(cell, bg=None, bold=False, align_h="left", number_format=None):
    if bg:
        cell.fill = _fill(bg)
    cell.font = _font(bold=bold)
    cell.alignment = _align(align_h)
    cell.border = _thin_border()
    if number_format:
        cell.number_format = number_format


def set_col_width(ws, col: int, width: float):
    ws.column_dimensions[get_column_letter(col)].width = width


def ajouter_disclaimer(ws, row: int, col_start=1, col_end=10) -> int:
    disclaimer = (
        "⚠️ AVERTISSEMENT : Ce fichier est un outil pédagogique d'aide à la décision. "
        "Il ne constitue PAS un conseil en investissement au sens de la Directive MIF II. "
        "Tout conseil doit être personnalisé par un CIF/CGP agréé AMF. "
        "Paramètres fiscaux indicatifs — valider avec votre expert-comptable."
    )
    ws.merge_cells(
        start_row=row, start_column=col_start, end_row=row, end_column=col_end
    )
    cell = ws.cell(row=row, column=col_start, value=disclaimer)
    cell.fill = _fill("FFF2CC")
    cell.font = Font(bold=True, color=COULEUR_AVERTISSEMENT, size=9, italic=True)
    cell.alignment = _align("left", "center", wrap=True)
    ws.row_dimensions[row].height = 35
    return row + 1


def titre_section(ws, row: int, texte: str, col_start=1, col_end=8, bg=COULEUR_SUBHEADER) -> int:
    ws.merge_cells(
        start_row=row, start_column=col_start, end_row=row, end_column=col_end
    )
    cell = ws.cell(row=row, column=col_start, value=texte)
    cell.fill = _fill(bg)
    cell.font = Font(bold=True, color="FFFFFF", size=11)
    cell.alignment = _align("left", "center")
    ws.row_dimensions[row].height = 20
    return row + 1


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


# ─── Onglet 3 : Enveloppes ──────────────────────────────────────────
def creer_onglet_enveloppes(wb: openpyxl.Workbook, enveloppes: list):
    ws = wb.create_sheet("Enveloppes")
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:H1")
    c = ws["A1"]
    c.value = "🏦 ENVELOPPES FISCALES DISPONIBLES — FRANCE 2026"
    style_header(c, size=14)
    ws.row_dimensions[1].height = 30

    row = ajouter_disclaimer(ws, 2, 1, 8)

    headers = ["ID Enveloppe", "Nom complet", "Plafond (€)", "Fiscalité sortie (résumé)",
               "Avantages clés", "Inconvénients", "ETF éligibles", "Notes CGP"]
    row = titre_section(ws, row, "📋 TABLEAU RÉCAPITULATIF DES ENVELOPPES", 1, 8)
    for i, h in enumerate(headers, 1):
        style_subheader(ws.cell(row=row, column=i, value=h))
    row += 1

    env_colors = {
        "PEA": "C6EFCE",
        "PER": "BDD7EE",
        "PEE": "FFEB9C",
        "CTO_perso": "F2F2F2",
        "CTO_IS": "FCE4D6",
        "Contrat_Cap_IS": "E2EFDA",
    }

    for env in enveloppes:
        bg = env_colors.get(env["id"], "FFFFFF")
        plafond = env.get("plafond") or "Illimité"
        if isinstance(plafond, (int, float)):
            plafond = f"{plafond:,} €".replace(",", " ")

        # Sortie fiscale résumée
        sortie = env.get("fiscalite_sortie", "")
        if isinstance(sortie, dict):
            sortie = " | ".join(f"{k}: {v}" for k, v in sortie.items())

        avantages = "\n".join(f"• {a}" for a in env.get("avantages", []))
        inconvenients = "\n".join(f"• {i}" for i in env.get("inconvenients", []))
        etfs = ", ".join(env.get("eligible_etf_types", []))

        row_data = [
            env["id"],
            env["nom"],
            plafond,
            sortie,
            avantages,
            inconvenients,
            etfs,
            env.get("notes", ""),
        ]
        max_lines = max(len(avantages.split("\n")), len(inconvenients.split("\n")), 2)
        ws.row_dimensions[row].height = max(25, max_lines * 15)

        for j, val in enumerate(row_data, 1):
            cell = ws.cell(row=row, column=j, value=val)
            cell.fill = _fill(bg)
            cell.font = _font(size=9, bold=(j == 1))
            cell.alignment = _align("left", "top", wrap=True)
            cell.border = _thin_border()
        row += 1

    # Priorités d'utilisation
    row += 1
    row = titre_section(ws, row, "🎯 ORDRE DE PRIORITÉ D'UTILISATION (BOGLEHEAD FR)", 1, 8)
    priorites = [
        ("1️⃣", "PEE", "TOUJOURS saturer l'abondement employeur en PREMIER — TRI immédiat imbattable"),
        ("2️⃣", "PEA", "Priorité croissance long terme — exonération IR après 5 ans — plafond 150 000 €"),
        ("3️⃣", "PER", "Si TMI actuelle > TMI retraite estimée — déduction fiscale à l'entrée"),
        ("4️⃣", "Contrat Cap IS", "Si holding IS — pour les ETF capitalisants — pas de mark-to-market"),
        ("5️⃣", "CTO perso", "Surplus d'épargne — liquidité maximale — PFU 31,4%"),
        ("⚠️", "CTO IS", "PIÈGE : mark-to-market annuel — préférer contrat cap IS pour les ETF"),
    ]
    for prio, env_id, explication in priorites:
        ws.cell(row=row, column=1, value=prio).font = _font(bold=True, size=12)
        ws.cell(row=row, column=2, value=env_id).font = _font(bold=True, color=COULEUR_SUBHEADER)
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=8)
        ws.cell(row=row, column=3, value=explication).alignment = _align("left", "center", wrap=True)
        ws.row_dimensions[row].height = 20
        row += 1

    widths = [18, 35, 14, 40, 40, 40, 35, 40]
    for i, w in enumerate(widths, 1):
        set_col_width(ws, i, w)
    ws.freeze_panes = "A4"


# ─── Onglet 4 : Univers ETF ─────────────────────────────────────────
def creer_onglet_univers_etf(wb: openpyxl.Workbook, etfs: list):
    ws = wb.create_sheet("Univers_ETF")
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:N1")
    c = ws["A1"]
    c.value = f"📈 UNIVERS ETF — BOGLEHEAD FR 2026 ({len(etfs)} ETF)"
    style_header(c, size=14)
    ws.row_dimensions[1].height = 30

    ajouter_disclaimer(ws, 2, 1, 14)

    headers = [
        "ISIN", "Ticker", "Nom", "Émetteur", "Classe d'actifs", "Sous-classe",
        "TER (%)", "Devise", "Capitalisant", "EUR-Hedgé",
        "PEA", "PER", "CTO", "Notes",
    ]
    for i, h in enumerate(headers, 1):
        style_subheader(ws.cell(row=3, column=i, value=h))
    ws.row_dimensions[3].height = 22

    for idx, etf in enumerate(etfs):
        row = idx + 4
        classe = etf.get("classe_actifs", "")
        bg_hex = COULEURS_CLASSES.get(classe, "FFFFFF")
        # Alternance légère
        bg = bg_hex if idx % 2 == 0 else "FFFFFF"

        elig = etf.get("eligibilite", {})
        row_data = [
            etf.get("isin", ""),
            etf.get("ticker", ""),
            etf.get("nom", ""),
            etf.get("emetteur", ""),
            classe,
            etf.get("sous_classe", ""),
            etf.get("ter", 0),
            etf.get("devise", ""),
            "✅" if etf.get("capitalisant") else "❌",
            "✅" if etf.get("eur_hedged") else "❌",
            "✅" if elig.get("PEA") else "❌",
            "✅" if elig.get("PER") else "❌",
            "✅" if elig.get("CTO_perso") else "❌",
            etf.get("notes", ""),
        ]
        for j, val in enumerate(row_data, 1):
            cell = ws.cell(row=row, column=j, value=val)
            cell.fill = _fill(bg)
            cell.font = _font(size=9)
            cell.alignment = _align("center" if j in (7, 8, 9, 10, 11, 12, 13) else "left", wrap=True)
            cell.border = _thin_border()
            if j == 7:  # TER
                cell.number_format = "0.00%"

    # Tableau Excel structuré
    n_rows = len(etfs)
    if n_rows > 0:
        last_row = n_rows + 3
        tbl = Table(displayName="tblETF", ref=f"A3:N{last_row}")
        style = TableStyleInfo(
            name="TableStyleMedium9",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        tbl.tableStyleInfo = style
        ws.add_table(tbl)

    widths = [16, 8, 50, 20, 15, 25, 8, 8, 10, 10, 6, 6, 6, 45]
    for i, w in enumerate(widths, 1):
        set_col_width(ws, i, w)
    ws.freeze_panes = "A4"
    ws.auto_filter.ref = f"A3:N{len(etfs)+3}"


# ─── Onglet 5 : Allocation Cible ────────────────────────────────────
def creer_onglet_allocation_cible(wb: openpyxl.Workbook, profil: dict = None):
    ws = wb.create_sheet("Allocation_Cible")
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:G1")
    c = ws["A1"]
    c.value = "🎯 ALLOCATION CIBLE — PORTEFEUILLE BOGLEHEAD FR"
    style_header(c, size=14)
    ws.row_dimensions[1].height = 30
    ajouter_disclaimer(ws, 2, 1, 7)

    row = 4
    row = titre_section(ws, row, "📊 ALLOCATION CIBLE PAR CLASSE D'ACTIFS", 1, 7)
    headers = ["Classe d'actifs", "Allocation cible (%)", "Montant (€)", "ETF de référence", "Enveloppe prioritaire", "Justification", "Couleur"]
    for i, h in enumerate(headers, 1):
        style_subheader(ws.cell(row=row, column=i, value=h))
    row += 1

    if profil:
        alloc = profil.get("allocation_cible_bogleheads", {})
        patrimoine = profil.get("patrimoine_financier_total", 0)
        commentaire = alloc.get("commentaire", "")
        classes = {
            "actions": ("Actions", "CW8 (PEA) / IWDA (CTO)", "PEA → CTO → PER"),
            "obligations": ("Obligations", "GOVS / AGGH", "PER → Contrat Cap IS"),
            "immobilier_cote": ("Immobilier coté (REITs)", "IWDP / EPRE", "PER → CTO"),
            "or": ("Or physique (ETC)", "GOLD / IGLN", "CTO → PER"),
            "liquidites": ("Liquidités / Monétaire", "CSH / XEON", "CTO IS → CTO"),
        }
        classe_colors = {
            "actions": "4472C4",
            "obligations": "ED7D31",
            "immobilier_cote": "A9D18E",
            "or": "FFD966",
            "liquidites": "70AD47",
        }
        for key, (label, etf_ref, env_prio) in classes.items():
            pct = alloc.get(key, 0.0)
            montant = pct * patrimoine
            bg = classe_colors.get(key, "FFFFFF")
            row_data = [label, pct, montant, etf_ref, env_prio, "", ""]
            for j, val in enumerate(row_data, 1):
                cell = ws.cell(row=row, column=j, value=val)
                if j == 1:
                    cell.fill = _fill(bg)
                    cell.font = _font(bold=True, size=10)
                elif j == 2:
                    cell.number_format = "0.0%"
                    cell.font = _font(bold=True, size=11)
                    cell.alignment = _align("center")
                elif j == 3:
                    cell.number_format = "#,##0 €"
                elif j == 7:
                    cell.fill = _fill(bg)
                cell.border = _thin_border()
            row += 1

        # Total
        ws.cell(row=row, column=1, value="TOTAL").font = _font(bold=True, size=11)
        ws.cell(row=row, column=1).fill = _fill(COULEUR_HEADER)
        ws.cell(row=row, column=1).font = Font(bold=True, color="FFFFFF", size=11)
        total_pct = sum(v for k, v in alloc.items() if k != "commentaire")
        ws.cell(row=row, column=2, value=total_pct).number_format = "0.0%"
        ws.cell(row=row, column=2).font = _font(bold=True, size=11)
        ws.cell(row=row, column=3, value=patrimoine).number_format = "#,##0 €"
        ws.cell(row=row, column=3).font = _font(bold=True)
        row += 2

        if commentaire:
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=7)
            ws.cell(row=row, column=1, value=f"💬 {commentaire}")
            ws.cell(row=row, column=1).font = _font(italic=True, size=10)
            ws.cell(row=row, column=1).fill = _fill("FFF2CC")
            ws.row_dimensions[row].height = 30
            row += 1
    else:
        ws.cell(row=row, column=1, value="ℹ️ Sélectionner un profil client pour afficher l'allocation.")

    # Règles Boglehead
    row += 1
    row = titre_section(ws, row, "📏 RÈGLES BOGLEHEAD FR (HEURISTIQUES)", 1, 7)
    regles = [
        "Règle de l'âge : % obligations ≈ âge − 10 (heuristique — à adapter au profil risque)",
        "Règle 3 fonds : 1 ETF Monde + 1 ETF Obligations + 1 ETF Émergents",
        "Règle glide path : réduire progressivement les actions à l'approche de la retraite",
        "Rebalancement : méthode Larry Swedroe — si dérive > 25% de la cible (relatif) ou > 5 pts absolus",
        "Asset location : actions croissance en PEA, obligations en PER, or en CTO",
        "Frugalité : privilégier les ETF à TER < 0,20% — chaque point de frais = impact majeur sur 20 ans",
    ]
    for regle in regles:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=7)
        ws.cell(row=row, column=1, value=f"• {regle}")
        ws.cell(row=row, column=1).font = _font(size=10)
        ws.cell(row=row, column=1).fill = _fill(COULEUR_LIGHT_GREY if row % 2 == 0 else "FFFFFF")
        ws.row_dimensions[row].height = 20
        row += 1

    widths = [35, 18, 18, 30, 28, 35, 10]
    for i, w in enumerate(widths, 1):
        set_col_width(ws, i, w)
    ws.freeze_panes = "A4"


# ─── Onglet 6 : Asset Location Matrice ──────────────────────────────
def creer_onglet_asset_location(wb: openpyxl.Workbook, etfs: list, enveloppes: list, profil: dict = None):
    ws = wb.create_sheet("Asset_Location_Matrice")
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:I1")
    c = ws["A1"]
    c.value = "🗺️ MATRICE D'ASSET LOCATION — ETF × ENVELOPPES"
    style_header(c, size=14)
    ws.row_dimensions[1].height = 30
    ajouter_disclaimer(ws, 2, 1, 9)

    row = 4
    row = titre_section(ws, row, "📊 MATRICE ÉLIGIBILITÉ ETF × ENVELOPPE", 1, 9)

    env_ids = ["PEA", "PER", "PEE", "CTO_perso", "CTO_IS", "Contrat_Cap_IS"]
    headers = ["ISIN", "Nom ETF", "Classe"] + env_ids
    for i, h in enumerate(headers, 1):
        style_subheader(ws.cell(row=row, column=i, value=h))
    row += 1

    for etf in etfs:
        elig = etf.get("eligibilite", {})
        classe = etf.get("classe_actifs", "")
        bg_hex = COULEURS_CLASSES.get(classe, "FFFFFF")
        row_data = [etf.get("isin", ""), etf.get("nom", ""), classe]
        for env_id in env_ids:
            row_data.append("✅" if elig.get(env_id) else "—")

        for j, val in enumerate(row_data, 1):
            cell = ws.cell(row=row, column=j, value=val)
            cell.font = _font(size=9)
            cell.border = _thin_border()
            if j <= 3:
                cell.fill = _fill(bg_hex)
                cell.alignment = _align("left", "center", wrap=True)
            else:
                cell.alignment = _align("center")
                if val == "✅":
                    cell.fill = _fill("C6EFCE")
                else:
                    cell.fill = _fill("FCE4D6")
        row += 1

    row += 1
    # Légende
    row = titre_section(ws, row, "🔑 RÈGLES D'ASSET LOCATION BOGLEHEAD FR", 1, 9)
    regles_al = [
        ("Actions mondiales (PEA éligible)", "PEA en PRIORITÉ → CTO → PER", "Économie IR 12,8% sur la totalité des gains"),
        ("Actions hors PEA (ETF physiques)", "PER → CTO perso → Contrat Cap IS", "PER = déduction entrée, CTO = liquidité"),
        ("Obligations / Fixed Income", "PER → Contrat Cap IS → CTO IS", "Rendement fixe mieux dans enveloppe défiscalisée"),
        ("Or (ETCs)", "CTO perso → PER", "ETCs non éligibles PEA — CTO simple"),
        ("REITs / Immobilier coté", "PER → CTO perso", "Dividendes imposables — mieux dans enveloppe"),
        ("Monétaire / Liquidités", "CTO IS → CTO perso", "Faible rendement — hors enveloppes précieuses"),
        ("ETF actions IS (holding)", "Contrat Cap IS > CTO IS", "Éviter le mark-to-market annuel (art. 209-0 A CGI)"),
    ]
    ws.cell(row=row, column=1, value="Classe d'actifs").font = _font(bold=True)
    ws.cell(row=row, column=2, value="Enveloppe recommandée").font = _font(bold=True)
    ws.cell(row=row, column=3, value="Justification").font = _font(bold=True)
    for j in range(1, 4):
        ws.cell(row=row, column=j).fill = _fill(COULEUR_SUBHEADER)
        ws.cell(row=row, column=j).font = Font(bold=True, color="FFFFFF")
    row += 1
    for i, (classe, reco, justif) in enumerate(regles_al):
        bg = COULEUR_LIGHT_GREY if i % 2 == 0 else "FFFFFF"
        ws.cell(row=row, column=1, value=classe).fill = _fill(bg)
        ws.cell(row=row, column=2, value=reco).fill = _fill(bg)
        ws.cell(row=row, column=2).font = _font(bold=True, color=COULEUR_SUBHEADER)
        ws.cell(row=row, column=3, value=justif).fill = _fill(bg)
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=9)
        ws.cell(row=row, column=3).alignment = _align("left", "center", wrap=True)
        row += 1

    widths = [16, 45, 18, 8, 8, 8, 8, 8, 18]
    for i, w in enumerate(widths, 1):
        set_col_width(ws, i, w)
    ws.freeze_panes = "A5"


# ─── Onglet 7 : Rebalancement ───────────────────────────────────────
def creer_onglet_rebalancement(wb: openpyxl.Workbook):
    ws = wb.create_sheet("Rebalancement")
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:H1")
    c = ws["A1"]
    c.value = "⚖️ OUTIL DE REBALANCEMENT — BOGLEHEAD FR"
    style_header(c, size=14)
    ws.row_dimensions[1].height = 30
    ajouter_disclaimer(ws, 2, 1, 8)

    row = 4
    row = titre_section(ws, row, "📊 TABLEAU DE SUIVI DE L'ALLOCATION", 1, 8)
    headers = ["Classe d'actifs", "Cible (%)", "Actuelle (%)", "Dérive (pts abs.)",
               "Dérive (%rel)", "Action", "Montant à arbitrer (€)", "Enveloppe privilégiée"]
    for i, h in enumerate(headers, 1):
        style_subheader(ws.cell(row=row, column=i, value=h))
    row += 1

    classes = ["Actions", "Obligations", "Immobilier coté", "Or", "Liquidités", "TOTAL"]
    cibles = [0.65, 0.20, 0.05, 0.05, 0.05, 1.00]
    env_pref = ["PEA/CTO", "PER/ContratIS", "PER/CTO", "CTO", "CTO", ""]
    patrimoine_exemple = 500000

    for i, (classe, cible, env) in enumerate(zip(classes, cibles, env_pref)):
        is_total = classe == "TOTAL"
        bg = COULEUR_HEADER if is_total else (COULEUR_LIGHT_GREY if i % 2 == 0 else "FFFFFF")
        fg = "FFFFFF" if is_total else "000000"

        ws.cell(row=row, column=1, value=classe).fill = _fill(bg)
        ws.cell(row=row, column=1).font = _font(bold=is_total, color=fg)
        ws.cell(row=row, column=2, value=cible).number_format = "0.0%"
        ws.cell(row=row, column=2).fill = _fill(bg)

        if not is_total:
            # Formule dérive = actuelle - cible
            derive_col = get_column_letter(4)
            actuelle_col = get_column_letter(3)
            cible_col = get_column_letter(2)

            ws.cell(row=row, column=3, value=cible).number_format = "0.0%"  # à saisir
            ws.cell(row=row, column=3).fill = _fill("FFFFC0")  # Zone de saisie
            ws.cell(row=row, column=3).comment = None

            ws.cell(row=row, column=4,
                    value=f"={actuelle_col}{row}-{cible_col}{row}").number_format = "0.0%"
            ws.cell(row=row, column=4).fill = _fill(bg)

            ws.cell(row=row, column=5,
                    value=f"=IF({cible_col}{row}>0,ABS({derive_col}{row})/{cible_col}{row},0)").number_format = "0.0%"
            ws.cell(row=row, column=5).fill = _fill(bg)

            ws.cell(row=row, column=6,
                    value=f'=IF(ABS({derive_col}{row})>0.05,"ARBITRER",IF(E{row}>0.25,"SURVEILLER","OK"))')
            ws.cell(row=row, column=6).alignment = _align("center")

            ws.cell(row=row, column=7,
                    value=f"=ABS({derive_col}{row})*{patrimoine_exemple}").number_format = "#,##0 €"
            ws.cell(row=row, column=7).fill = _fill(bg)

            ws.cell(row=row, column=8, value=env).font = _font(italic=True)
        else:
            ws.cell(row=row, column=3, value=f"=SUM(C{row-5}:C{row-1})").number_format = "0.0%"
            for col in range(2, 9):
                ws.cell(row=row, column=col).fill = _fill(bg)
                ws.cell(row=row, column=col).font = Font(bold=True, color=fg)

        for col in range(1, 9):
            ws.cell(row=row, column=col).border = _thin_border()
        row += 1

    # Mise en forme conditionnelle sur la colonne Action (F)
    from openpyxl.formatting.rule import CellIsRule
    green_fill = PatternFill(bgColor=COULEUR_OK, fill_type="solid")
    red_fill = PatternFill(bgColor=COULEUR_DANGER, fill_type="solid")
    orange_fill = PatternFill(bgColor=COULEUR_WARNING, fill_type="solid")
    action_range = f"F{row-5}:F{row-1}"
    ws.conditional_formatting.add(
        action_range,
        CellIsRule(operator="equal", formula=['"OK"'], fill=green_fill)
    )
    ws.conditional_formatting.add(
        action_range,
        CellIsRule(operator="equal", formula=['"ARBITRER"'], fill=red_fill)
    )
    ws.conditional_formatting.add(
        action_range,
        CellIsRule(operator="equal", formula=['"SURVEILLER"'], fill=orange_fill)
    )

    row += 1
    row = titre_section(ws, row, "📋 MÉTHODE DE REBALANCEMENT — ORDRE DE PRIORITÉ", 1, 8)
    methodes = [
        ("1ère priorité : Versements", "Orienter les nouveaux versements vers les classes sous-pondérées → coût fiscal = 0"),
        ("2ème priorité : Arbitrage intra-enveloppe", "PEA, PER, PEE → arbitrage SANS fiscalité (enveloppe = bouclier fiscal)"),
        ("3ème priorité : Arbitrage CTO", "PFU 31,4% sur les plus-values → calculer le seuil de rentabilité"),
        ("Méthode Swedroe (recommandée)", "Rebalancer si dérive > 25% de la cible (relatif) OU > 5 pts absolus"),
        ("Fréquence recommandée", "Vérification annuelle + après chaque mouvement de marché > 20%"),
        ("Coût fiscal arbitrage CTO", "PV × 31,4% → seuil : dérive > 3-5 ans de surperformance de l'allocation cible"),
    ]
    for methode, explication in methodes:
        ws.cell(row=row, column=1, value=methode).font = _font(bold=True, color=COULEUR_SUBHEADER)
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=8)
        ws.cell(row=row, column=2, value=explication).alignment = _align("left", "center", wrap=True)
        ws.row_dimensions[row].height = 22
        for col in range(1, 9):
            ws.cell(row=row, column=col).border = _thin_border()
        row += 1

    widths = [28, 14, 14, 14, 12, 14, 22, 28]
    for i, w in enumerate(widths, 1):
        set_col_width(ws, i, w)
    ws.freeze_panes = "A5"


# ─── Onglet 8 : Reporting Client ────────────────────────────────────
def creer_onglet_reporting(wb: openpyxl.Workbook, profil: dict = None):
    ws = wb.create_sheet("Reporting_Client")
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:H1")
    c = ws["A1"]
    c.value = "📋 REPORTING CLIENT — BOGLEHEAD FR"
    style_header(c, size=14)
    ws.row_dimensions[1].height = 30

    # Date de génération
    ws.cell(row=2, column=1, value=f"Généré le : {datetime.date.today().strftime('%d/%m/%Y')}")
    ws.cell(row=2, column=1).font = _font(italic=True, size=9)
    row = ajouter_disclaimer(ws, 3, 1, 8)

    if profil:
        row = titre_section(ws, row, f"👤 SYNTHÈSE — {profil.get('nom', 'Client')}", 1, 8)
        ws.cell(row=row, column=1, value="Patrimoine financier total").font = _font(bold=True)
        ws.cell(row=row, column=2, value=profil.get("patrimoine_financier_total", 0)).number_format = "#,##0 €"
        ws.cell(row=row, column=3, value="Capacité d'épargne annuelle").font = _font(bold=True)
        ws.cell(row=row, column=4, value=profil.get("capacite_epargne_annuelle", 0)).number_format = "#,##0 €"
        row += 1
        ws.cell(row=row, column=1, value="Horizon de placement").font = _font(bold=True)
        ws.cell(row=row, column=2, value=f"{profil.get('horizon_placement_ans', 0)} ans")
        ws.cell(row=row, column=3, value="Score de risque SRRI").font = _font(bold=True)
        ws.cell(row=row, column=4, value=f"{profil.get('score_risque', '—')} / 7")
        row += 2

        row = titre_section(ws, row, "🏦 RÉPARTITION PAR ENVELOPPE", 1, 8)
        headers = ["Enveloppe", "Encours actuel (€)", "Versements prévus/an (€)", "Plafond restant (€)", "Avantage fiscal clé", "", "", ""]
        for i, h in enumerate(headers, 1):
            style_subheader(ws.cell(row=row, column=i, value=h))
        row += 1

        env_dispo = profil.get("enveloppes_disponibles", {})
        env_labels = {
            "PEA": ("PEA", "Exonération IR après 5 ans"),
            "PER": ("PER (Plan Épargne Retraite)", "Déduction fiscale à l'entrée"),
            "PEE": ("PEE (Plan Épargne Entreprise)", "Abondement + exonération IR"),
            "CTO_perso": ("CTO Personnel", "Liquidité totale"),
            "CTO_IS": ("CTO IS (Holding)", "Taux IS 15/25%"),
            "Contrat_Cap_IS": ("Contrat Cap. IS (Holding)", "Pas de mark-to-market"),
        }
        total_patrimoine_env = 0
        for env_key, (label, avantage) in env_labels.items():
            env_data = env_dispo.get(env_key)
            if env_data is None:
                continue
            encours = env_data.get("encours_actuel", 0) or 0
            versements = env_data.get("versement_annuel_prevu", 0) or 0
            plafond = env_data.get("plafond", None)
            plafond_restant = max(0, plafond - encours) if plafond else "Illimité"
            total_patrimoine_env += encours

            row_data = [label, encours, versements, plafond_restant, avantage, "", "", ""]
            for j, val in enumerate(row_data, 1):
                cell = ws.cell(row=row, column=j, value=val)
                if j == 2 and isinstance(val, (int, float)):
                    cell.number_format = "#,##0 €"
                elif j == 3 and isinstance(val, (int, float)):
                    cell.number_format = "#,##0 €"
                elif j == 4 and isinstance(val, (int, float)):
                    cell.number_format = "#,##0 €"
                cell.border = _thin_border()
            row += 1

        ws.cell(row=row, column=1, value="TOTAL enveloppes").font = _font(bold=True)
        ws.cell(row=row, column=1).fill = _fill(COULEUR_HEADER)
        ws.cell(row=row, column=1).font = Font(bold=True, color="FFFFFF")
        ws.cell(row=row, column=2, value=total_patrimoine_env).number_format = "#,##0 €"
        ws.cell(row=row, column=2).font = _font(bold=True)
        row += 2

        row = titre_section(ws, row, "🎯 OBJECTIFS ET PRÉCONISATIONS", 1, 8)
        ws.cell(row=row, column=1, value="Objectif principal").font = _font(bold=True)
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=8)
        ws.cell(row=row, column=2, value=profil.get("objectif_principal", "—"))
        ws.row_dimensions[row].height = 20
        row += 1
        for i, obj in enumerate(profil.get("objectifs_secondaires", []), 1):
            ws.cell(row=row, column=1, value=f"Obj. secondaire {i}").font = _font(bold=True)
            ws.cell(row=row, column=1).fill = _fill(COULEUR_LIGHT_GREY)
            ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=8)
            ws.cell(row=row, column=2, value=obj)
            row += 1
    else:
        ws.cell(row=row, column=1, value="ℹ️ Sélectionner un profil pour générer le reporting.")

    widths = [35, 20, 22, 18, 35, 15, 15, 15]
    for i, w in enumerate(widths, 1):
        set_col_width(ws, i, w)
    ws.freeze_panes = "A4"


# ─── Onglet 9 : Profils Types ────────────────────────────────────────
def creer_onglet_profils_types(wb: openpyxl.Workbook, profils: dict):
    ws = wb.create_sheet("Profils_Types")
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:K1")
    c = ws["A1"]
    c.value = "👥 PROFILS CLIENTS TYPES — BOGLEHEAD FR 2026 (FICTIFS ET ILLUSTRATIFS)"
    style_header(c, size=14)
    ws.row_dimensions[1].height = 30
    ajouter_disclaimer(ws, 2, 1, 11)

    row = 4
    row = titre_section(ws, row, "📋 TABLEAU DES 6 PROFILS TYPES", 1, 11)

    headers = [
        "#", "Code", "Profil", "Âge", "TMI", "RFR (€)",
        "Patrimoine Fin. (€)", "Actions", "Obligations", "Score Risque", "Objectif principal"
    ]
    for i, h in enumerate(headers, 1):
        style_subheader(ws.cell(row=row, column=i, value=h))
    row += 1

    profil_colors = [
        "BDD7EE", "C6EFCE", "FFEB9C", "FCE4D6", "E2EFDA", "F2F2F2"
    ]
    for idx, profil in enumerate(profils.get("profils", [])):
        bg = profil_colors[idx % len(profil_colors)]
        alloc = profil.get("allocation_cible_bogleheads", {})
        row_data = [
            profil.get("id"),
            profil.get("code"),
            profil.get("nom"),
            profil.get("age"),
            profil.get("tmi"),
            profil.get("rfr_annuel"),
            profil.get("patrimoine_financier_total"),
            alloc.get("actions", 0),
            alloc.get("obligations", 0),
            profil.get("score_risque"),
            profil.get("objectif_principal"),
        ]
        for j, val in enumerate(row_data, 1):
            cell = ws.cell(row=row, column=j, value=val)
            cell.fill = _fill(bg)
            cell.font = _font(size=9, bold=(j <= 3))
            cell.border = _thin_border()
            cell.alignment = _align("center" if j in (1, 4, 5, 8, 9, 10) else "left")
            if j == 5:
                cell.number_format = "0%"
            elif j in (6, 7):
                cell.number_format = "#,##0"
            elif j in (8, 9):
                cell.number_format = "0%"
        row += 1

    # Tableau structuré
    last_row = row - 1
    tbl = Table(displayName="tblProfils", ref=f"A5:K{last_row}")
    style = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    tbl.tableStyleInfo = style
    ws.add_table(tbl)

    row += 1
    row = titre_section(ws, row, "⚠️ DISCLAIMER LÉGAL", 1, 11)
    ws.merge_cells(start_row=row, start_column=1, end_row=row+2, end_column=11)
    disclaimer_text = profils.get("disclaimer", "Ces profils sont fictifs et illustratifs.")
    ws.cell(row=row, column=1, value=disclaimer_text)
    ws.cell(row=row, column=1).font = _font(italic=True, size=9, color=COULEUR_AVERTISSEMENT)
    ws.cell(row=row, column=1).alignment = _align("left", "top", wrap=True)
    ws.cell(row=row, column=1).fill = _fill("FFF2CC")
    ws.row_dimensions[row].height = 60

    widths = [5, 28, 30, 6, 8, 14, 18, 10, 10, 10, 40]
    for i, w in enumerate(widths, 1):
        set_col_width(ws, i, w)
    ws.freeze_panes = "A5"


# ─── Onglet 10 : Profil Individuel ──────────────────────────────────
def creer_onglet_profil_individuel(
    wb: openpyxl.Workbook,
    profil: dict,
    etfs: list,
    params_fiscaux: dict,
):
    code_parts = profil["code"].split("_")
    code_suffix = code_parts[2][:10] if len(code_parts) >= 3 else profil["code"][:10]
    nom_onglet = f"Profil_{profil['id']}_{code_suffix}"
    ws = wb.create_sheet(nom_onglet)
    ws.sheet_view.showGridLines = False

    # En-tête
    ws.merge_cells("A1:I1")
    c = ws["A1"]
    c.value = f"👤 PROFIL {profil['id']} — {profil['nom'].upper()}"
    style_header(c, size=13)
    ws.row_dimensions[1].height = 28
    ajouter_disclaimer(ws, 2, 1, 9)

    row = 4
    # ── Identité ──
    row = titre_section(ws, row, "📋 PARAMÈTRES DU PROFIL", 1, 9, bg="2E75B6")
    infos = [
        ("Nom", profil.get("nom")),
        ("Âge", f"{profil.get('age')} ans"),
        ("Situation", profil.get("situation_familiale")),
        ("TMI", f"{profil.get('tmi', 0)*100:.0f}%"),
        ("RFR annuel", profil.get("rfr_annuel", 0)),
        ("Patrimoine financier", profil.get("patrimoine_financier_total", 0)),
        ("Capacité épargne / an", profil.get("capacite_epargne_annuelle", 0)),
        ("Horizon placement", f"{profil.get('horizon_placement_ans')} ans"),
        ("Score de risque (SRRI)", f"{profil.get('score_risque')} / 7"),
        ("CEHR applicable", "✅ Oui" if profil.get("cehr_applicable") else "❌ Non"),
        ("CDHR applicable", "✅ Oui" if profil.get("cdhr_applicable") else "❌ Non"),
        ("Holding IS", "✅ Oui" if profil.get("particularites_fiscales", {}).get("holding_is") else "❌ Non"),
    ]
    for i in range(0, len(infos), 2):
        lbl1, val1 = infos[i]
        ws.cell(row=row, column=1, value=lbl1).font = _font(bold=True)
        ws.cell(row=row, column=1).fill = _fill(COULEUR_LIGHT_GREY)
        cell1 = ws.cell(row=row, column=2, value=val1)
        if isinstance(val1, (int, float)):
            cell1.number_format = "#,##0 €"
        if i + 1 < len(infos):
            lbl2, val2 = infos[i + 1]
            ws.cell(row=row, column=4, value=lbl2).font = _font(bold=True)
            ws.cell(row=row, column=4).fill = _fill(COULEUR_LIGHT_GREY)
            cell2 = ws.cell(row=row, column=5, value=val2)
            if isinstance(val2, (int, float)):
                cell2.number_format = "#,##0 €"
        row += 1

    # ── Allocation cible ──
    row += 1
    row = titre_section(ws, row, "🎯 ALLOCATION CIBLE", 1, 9, bg="375623")
    alloc = profil.get("allocation_cible_bogleheads", {})
    patrimoine = profil.get("patrimoine_financier_total", 0)
    headers = ["Classe", "Allocation (%)", "Montant (€)", "ETF suggéré", "Enveloppe prioritaire"]
    for i, h in enumerate(headers, 1):
        style_subheader(ws.cell(row=row, column=i, value=h))
    row += 1

    classe_map = {
        "actions": ("Actions", "CW8 (PEA) / IWDA (CTO)", "PEA → CTO → PER"),
        "obligations": ("Obligations", "GOVS / AGGH", "PER → Contrat Cap IS"),
        "immobilier_cote": ("Immobilier coté", "IWDP / EPRE", "PER → CTO"),
        "or": ("Or", "GOLD / IGLN", "CTO"),
        "liquidites": ("Liquidités", "CSH / XEON", "CTO IS → CTO"),
    }
    total_alloc = 0.0
    for key, (label, etf_ref, env_prio) in classe_map.items():
        pct = alloc.get(key, 0.0)
        if not pct:
            continue
        total_alloc += pct
        montant = pct * patrimoine
        bg = COULEURS_CLASSES.get(label.split()[0], "FFFFFF")
        for j, val in enumerate([label, pct, montant, etf_ref, env_prio], 1):
            cell = ws.cell(row=row, column=j, value=val)
            cell.fill = _fill(bg)
            cell.border = _thin_border()
            if j == 2:
                cell.number_format = "0.0%"
                cell.alignment = _align("center")
            elif j == 3:
                cell.number_format = "#,##0 €"
        row += 1
    ws.cell(row=row, column=1, value="TOTAL").font = Font(bold=True, color="FFFFFF")
    ws.cell(row=row, column=1).fill = _fill(COULEUR_HEADER)
    ws.cell(row=row, column=2, value=total_alloc).number_format = "0.0%"
    ws.cell(row=row, column=2).font = _font(bold=True)
    ws.cell(row=row, column=3, value=patrimoine).number_format = "#,##0 €"
    ws.cell(row=row, column=3).font = _font(bold=True)
    row += 2

    # ── Enveloppes ──
    row = titre_section(ws, row, "🏦 ENVELOPPES DISPONIBLES ET ENCOURS", 1, 9, bg="843C0C")
    headers = ["Enveloppe", "Encours actuel (€)", "Plafond (€)", "Plafond restant (€)", "Versements prévus/an", "Avantage fiscal", "", "", ""]
    for i, h in enumerate(headers, 1):
        style_subheader(ws.cell(row=row, column=i, value=h))
    row += 1

    env_dispo = profil.get("enveloppes_disponibles", {})
    env_labels_map = {
        "PEA": "Exonération IR après 5 ans (18,6% PS seulement)",
        "PER": "Déduction TMI actuelle à l'entrée",
        "PEE": f"Abondement {env_dispo.get('PEE', {}).get('abondement_employeur_pct', 0)*100 if env_dispo.get('PEE') else 0:.0f}% + exonération IR",
        "CTO_perso": "Liquidité totale — PFU 31,4%",
        "CTO_IS": "IS 15/25% — attention MTM annuel",
        "Contrat_Cap_IS": "Pas de MTM — base forfaitaire IS × TME",
    }
    env_plafonds = {"PEA": 150000, "PER": None, "PEE": None, "CTO_perso": None, "CTO_IS": None, "Contrat_Cap_IS": None}
    for env_key, avantage in env_labels_map.items():
        env_data = env_dispo.get(env_key)
        if env_data is None:
            continue
        encours = env_data.get("encours_actuel", 0) or 0
        versements = env_data.get("versement_annuel_prevu", 0) or 0
        plafond = env_plafonds.get(env_key)
        plafond_restant = max(0, plafond - encours) if plafond else "—"

        row_data = [env_key, encours, plafond or "—", plafond_restant, versements, avantage, "", "", ""]
        for j, val in enumerate(row_data, 1):
            cell = ws.cell(row=row, column=j, value=val)
            cell.border = _thin_border()
            cell.font = _font(size=9)
            if j == 2 and isinstance(val, (int, float)):
                cell.number_format = "#,##0 €"
            elif j == 3 and isinstance(val, (int, float)):
                cell.number_format = "#,##0 €"
            elif j == 4 and isinstance(val, (int, float)):
                cell.number_format = "#,##0 €"
            elif j == 5 and isinstance(val, (int, float)):
                cell.number_format = "#,##0 €"
        row += 1

    row += 1
    # ── Calculs fiscaux ──
    row = titre_section(ws, row, "💡 CALCULS FISCAUX ILLUSTRATIFS", 1, 9, bg="7030A0")
    from src.fiscalite import calculer_pfu, avantage_fiscal_pea, calculer_avantage_per, calculer_is

    # PFU sur 10 000€ gain
    gain_exemple = 10000
    pfu = calculer_pfu(gain_exemple, params_fiscaux)
    ws.cell(row=row, column=1, value=f"PFU sur {gain_exemple:,}€ de gain (CTO)").font = _font(bold=True)
    ws.cell(row=row, column=2, value=f"IR: {pfu['ir']:.0f}€ + PS: {pfu['ps']:.0f}€ = {pfu['total_impots']:.0f}€")
    ws.cell(row=row, column=3, value=f"Net: {pfu['net']:.0f}€ ({pfu['taux_effectif']*100:.1f}%)")
    row += 1

    # PEA après 5 ans
    pea_avantage = avantage_fiscal_pea(gain_exemple, params_fiscaux, apres_5_ans=True)
    ws.cell(row=row, column=1, value="Avantage PEA après 5 ans (vs CTO)").font = _font(bold=True)
    ws.cell(row=row, column=2, value=f"Économie: {pea_avantage['economie']:.0f}€ par {gain_exemple:,}€ de gain")
    ws.cell(row=row, column=3, value=f"PS seulement: {pea_avantage['taux_effectif_pea']*100:.1f}%")
    row += 1

    # Avantage PER
    tmi = profil.get("tmi", 0.30)
    horizon = profil.get("horizon_placement_ans", 20)
    per_res = calculer_avantage_per(10000, tmi, 0.30, 0.06, horizon, params_fiscaux)
    ws.cell(row=row, column=1, value=f"Avantage PER (TMI {tmi*100:.0f}% → 30% à retraite)").font = _font(bold=True)
    ws.cell(row=row, column=2, value=f"PER net sur {horizon}ans: {per_res['capital_per_net']:.0f}€")
    ws.cell(row=row, column=3, value=f"vs CTO net: {per_res['capital_cto_net']:.0f}€")
    ws.cell(row=row, column=4, value=f"Avantage: {per_res['avantage_per']:.0f}€")
    row += 2

    ws.cell(row=row, column=1, value=f"💬 {alloc.get('commentaire', '')}").font = _font(italic=True, size=9)
    ws.cell(row=row, column=1).fill = _fill("FFF2CC")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=9)
    ws.row_dimensions[row].height = 30

    widths = [30, 20, 18, 18, 22, 40, 12, 12, 12]
    for i, w in enumerate(widths, 1):
        set_col_width(ws, i, w)
    ws.freeze_panes = "A4"


# ─── Onglet 11 : Comparatif Profils ─────────────────────────────────
def creer_onglet_comparatif_profils(wb: openpyxl.Workbook, profils: dict, params_fiscaux: dict):
    ws = wb.create_sheet("Comparatif_Profils")
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:J1")
    c = ws["A1"]
    c.value = "📊 COMPARATIF FISCAL — 6 PROFILS vs SCÉNARIO NAÏF CTO"
    style_header(c, size=14)
    ws.row_dimensions[1].height = 30
    ajouter_disclaimer(ws, 2, 1, 10)

    row = 4
    row = titre_section(ws, row, "🔢 GAIN FISCAL ESTIMÉ PAR PROFIL (HORIZON COMPLET)", 1, 10)

    headers = [
        "Profil", "Nom", "Patrimoine (€)", "Horizon (ans)", "TMI",
        "Capital naïf CTO (€)", "Capital optimisé (€)", "Gain fiscal (€)",
        "Gain (%)", "Enveloppe clé"
    ]
    for i, h in enumerate(headers, 1):
        style_subheader(ws.cell(row=row, column=i, value=h))
    row += 1

    from src.fiscalite import calculer_pfu, avantage_fiscal_pea
    rendement = 0.06  # 6% hypothèse

    profil_colors = ["BDD7EE", "C6EFCE", "FFEB9C", "FCE4D6", "E2EFDA", "F2F2F2"]

    for idx, profil in enumerate(profils.get("profils", [])):
        patrimoine = profil.get("patrimoine_financier_total", 0)
        horizon = profil.get("horizon_placement_ans", 20)
        tmi = profil.get("tmi", 0.30)
        taux_ps = params_fiscaux["prelevements_sociaux"]["taux_global"]
        taux_pfu = params_fiscaux["pfu"]["taux_ir"]

        # Capital brut
        capital_brut = patrimoine * ((1 + rendement) ** horizon)
        gain_brut = capital_brut - patrimoine

        # Scénario naïf CTO : PFU 31.4% sur tous les gains
        impots_naive = gain_brut * (taux_pfu + taux_ps)
        capital_naive = capital_brut - impots_naive

        # Scénario optimisé : PEA (18.6% PS), PER (PS seulement simplifié), CTO reste
        # Pondération simplifiée selon les enveloppes disponibles
        env_dispo = profil.get("enveloppes_disponibles", {})
        pea_encours = (env_dispo.get("PEA") or {}).get("encours_actuel", 0) or 0
        per_encours = (env_dispo.get("PER") or {}).get("encours_actuel", 0) or 0
        pee_encours = (env_dispo.get("PEE") or {}).get("encours_actuel", 0) or 0
        is_encours = (
            (env_dispo.get("Contrat_Cap_IS") or {}).get("encours_actuel", 0) or 0
            + (env_dispo.get("CTO_IS") or {}).get("encours_actuel", 0) or 0
        )
        cto_encours = (env_dispo.get("CTO_perso") or {}).get("encours_actuel", 0) or 0
        total_env = pea_encours + per_encours + pee_encours + is_encours + cto_encours

        if total_env > 0:
            pct_pea = pea_encours / total_env
            pct_per = per_encours / total_env
            pct_pee = pee_encours / total_env
            pct_is = is_encours / total_env
            pct_cto = cto_encours / total_env
        else:
            pct_pea = pct_per = pct_pee = pct_is = 0.0
            pct_cto = 1.0

        # Taux effectif moyen pondéré (simplifié)
        taux_is_moy = params_fiscaux["is"]["taux_reduit"]
        taux_moyen = (
            pct_pea * taux_ps
            + pct_per * taux_ps
            + pct_pee * taux_ps
            + pct_is * taux_is_moy
            + pct_cto * (taux_pfu + taux_ps)
        )
        impots_optim = gain_brut * taux_moyen
        capital_optim = capital_brut - impots_optim

        gain_fiscal = capital_optim - capital_naive
        gain_pct = gain_fiscal / capital_naive if capital_naive > 0 else 0

        # Enveloppe clé
        holding_is = profil.get("particularites_fiscales", {}).get("holding_is", False)
        if holding_is:
            env_cle = "Contrat Cap IS"
        elif pea_encours > 0:
            env_cle = "PEA + PER"
        else:
            env_cle = "PER"

        bg = profil_colors[idx % len(profil_colors)]
        row_data = [
            profil.get("id"),
            profil.get("nom"),
            patrimoine,
            horizon,
            tmi,
            capital_naive,
            capital_optim,
            gain_fiscal,
            gain_pct,
            env_cle,
        ]
        for j, val in enumerate(row_data, 1):
            cell = ws.cell(row=row, column=j, value=val)
            cell.fill = _fill(bg)
            cell.font = _font(size=9, bold=(j <= 2))
            cell.border = _thin_border()
            cell.alignment = _align("center" if j in (1, 4, 5, 9) else "right" if j in (3, 6, 7, 8) else "left")
            if j in (3, 6, 7, 8):
                cell.number_format = "#,##0"
            elif j == 5:
                cell.number_format = "0%"
            elif j == 9:
                cell.number_format = "0.0%"
                if val > 0.05:
                    cell.fill = _fill("C6EFCE")
                    cell.font = Font(bold=True, color="375623", size=9)
        row += 1

    row += 1
    # Note méthodologique
    row = titre_section(ws, row, "📝 MÉTHODOLOGIE (SIMPLIFIÉE)", 1, 10)
    notes = [
        "Hypothèse : rendement annuel 6%, gains 100% en capital (pas de dividendes distribués).",
        "Scénario naïf CTO : PFU 31,4% (12,8% IR + 18,6% PS) sur la totalité des gains à la cession.",
        "Scénario optimisé : taux effectif moyen pondéré par enveloppe (PEA → 18,6% PS, PER → 18,6% PS, IS → 15%, CTO → 31,4%).",
        "⚠️ Calcul illustratif — ne prend pas en compte : CEHR, CDHR, versements futurs, MTM CTO IS, inflation.",
        "Pour un calcul précis, utiliser le solveur avec les contraintes réelles de chaque profil.",
    ]
    for note in notes:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=10)
        ws.cell(row=row, column=1, value=f"• {note}")
        ws.cell(row=row, column=1).font = _font(size=9, italic=True)
        ws.cell(row=row, column=1).fill = _fill(COULEUR_LIGHT_GREY if row % 2 == 0 else "FFFFFF")
        ws.row_dimensions[row].height = 18
        row += 1

    widths = [6, 30, 16, 10, 8, 16, 16, 14, 10, 18]
    for i, w in enumerate(widths, 1):
        set_col_width(ws, i, w)
    ws.freeze_panes = "A5"


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


# ─── Onglet Projection Monte-Carlo ──────────────────────────────────
def _creer_onglet_projection_monte_carlo(wb: openpyxl.Workbook, profil_ref: dict):
    """Crée l'onglet Projection_MonteCarlo avec simulation 10 000 tirages."""
    ws = wb.create_sheet("Projection_MonteCarlo")
    ws.sheet_view.showGridLines = False

    # Charger les paramètres de projection
    params_marche = charger_params_projection()
    sim_params = params_marche.get("simulation", {})
    nb_tirages = sim_params.get("nb_tirages", 10000)
    seed = sim_params.get("seed", 42)
    inflation = params_marche.get("inflation_annuelle", 0.02)
    horizons = [10, 20, 30]

    # Construire l'allocation depuis le profil de référence
    alloc_profil = profil_ref.get("allocation_cible_bogleheads", {})
    actions_total = float(alloc_profil.get("actions", 0.65))
    obligations = float(alloc_profil.get("obligations", 0.20))
    immobilier = float(alloc_profil.get("immobilier_cote", 0.05))
    or_val = float(alloc_profil.get("or", 0.05))
    liquidites = float(alloc_profil.get("liquidites", 0.05))
    # Répartir les actions entre monde/usa/europe/emergents
    allocation = AllocationClasses(
        actions_monde=round(actions_total * 0.50, 4),
        actions_usa=round(actions_total * 0.25, 4),
        actions_europe=round(actions_total * 0.15, 4),
        actions_emergents=round(actions_total * 0.10, 4),
        obligations=obligations,
        monetaire=liquidites,
        or_=or_val,
        immobilier=immobilier,
        matieres_premieres=0.0,
    )

    capital_initial = float(profil_ref.get("patrimoine_financier_total", 500_000))
    versement_annuel = float(profil_ref.get("capacite_epargne_annuelle", 40_000))
    objectif_capital = capital_initial * 3.0

    # Lancer les projections (10, 20, 30 ans)
    params_projection = {
        h: ParametresProjection(
            capital_initial=capital_initial,
            versement_annuel=versement_annuel,
            horizon_annees=h,
            allocation=allocation,
            nb_tirages=nb_tirages,
            seed=seed,
            objectif_capital=objectif_capital,
            rebalancement_annuel=True,
        )
        for h in horizons
    }
    from src.projection import simuler_monte_carlo
    resultats = {h: simuler_monte_carlo(params_projection[h], params_marche) for h in horizons}

    # ── Titre principal ──────────────────────────────────────────────
    row = 1
    ws.merge_cells(f"A{row}:I{row}")
    c = ws.cell(row=row, column=1, value="📈 PROJECTION PATRIMONIALE MONTE-CARLO — BOGLEHEAD FR 2026")
    style_header(c, size=14)
    ws.row_dimensions[row].height = 32
    row += 1

    ajouter_disclaimer(ws, row, 1, 9)
    row += 1

    # Description méthodologique
    ws.merge_cells(f"A{row}:I{row}")
    desc = (
        "Simulation de {:,} trajectoires sur 10, 20 et 30 ans. "
        "Rendements réels nets d'inflation (sources : Dimson-Marsh-Staunton, JST). "
        "Rebalancement annuel vers l'allocation cible. "
        "⚠️ Pour recalculer, relancer : python build_excel.py"
    ).format(nb_tirages)
    c = ws.cell(row=row, column=1, value=desc)
    c.fill = _fill(COULEUR_LIGHT_BLUE)
    c.font = _font(size=9, italic=True)
    c.alignment = _align("left", "center", wrap=True)
    ws.row_dimensions[row].height = 28
    row += 2

    # ── Section 1 — Hypothèses ────────────────────────────────────────
    row = titre_section(ws, row, "📊 SECTION 1 — HYPOTHÈSES DE RENDEMENT PAR CLASSE D'ACTIFS", 1, 9)

    headers_hyp = ["Classe d'actifs", "Rendement réel moyen", "Volatilité annualisée"]
    for j, h in enumerate(headers_hyp, 1):
        c = ws.cell(row=row, column=j, value=h)
        style_subheader(c)
    ws.row_dimensions[row].height = 18
    row += 1

    classes_actifs = params_marche.get("classes_actifs", {})
    labels_classes = {
        "actions_monde": "Actions Monde",
        "actions_usa": "Actions USA",
        "actions_europe": "Actions Europe",
        "actions_emergents": "Actions Émergents",
        "obligations": "Obligations",
        "monetaire": "Monétaire",
        "or": "Or",
        "immobilier": "Immobilier coté",
        "matieres_premieres": "Matières premières",
    }
    for yaml_key, label in labels_classes.items():
        data = classes_actifs.get(yaml_key, {})
        rendement = data.get("rendement_moyen", 0.0)
        vol = data.get("volatilite", 0.0)
        bg = COULEUR_LIGHT_GREY if (list(labels_classes.keys()).index(yaml_key) % 2 == 0) else None
        c1 = ws.cell(row=row, column=1, value=label)
        c2 = ws.cell(row=row, column=2, value=rendement)
        c3 = ws.cell(row=row, column=3, value=vol)
        style_data(c1, bg=bg, bold=False)
        style_data(c2, bg=bg, number_format="0.0%")
        style_data(c3, bg=bg, number_format="0.0%")
        c2.alignment = _align("center")
        c3.alignment = _align("center")
        ws.row_dimensions[row].height = 16
        row += 1
    row += 1

    # Paramètres de simulation
    sim_info = [
        ("Nombre de tirages Monte-Carlo", f"{nb_tirages:,}"),
        ("Seed (reproductibilité)", str(seed)),
        ("Horizons simulés", "10, 20 et 30 ans"),
        ("Inflation annuelle prévisionnelle", f"{inflation:.1%}"),
        ("Percentiles calculés", "P5, P10, P25, P50 (médiane), P75, P90, P95"),
    ]
    for label, val in sim_info:
        c1 = ws.cell(row=row, column=1, value=label)
        c2 = ws.cell(row=row, column=2, value=val)
        c1.font = _font(bold=True)
        c2.font = _font()
        ws.row_dimensions[row].height = 16
        row += 1
    row += 1

    # ── Section 2 — Paramètres client ────────────────────────────────
    row = titre_section(ws, row, "👤 SECTION 2 — PARAMÈTRES CLIENT (Profil de référence)", 1, 9)

    params_client = [
        ("Profil de référence", profil_ref.get("nom", "—")),
        ("Capital initial (€)", capital_initial),
        ("Versement annuel (€)", versement_annuel),
        ("Objectif de capital (€)", objectif_capital),
        ("Horizon de simulation (ans)", "10 / 20 / 30"),
        ("Rebalancement annuel", "Oui"),
    ]
    for label, val in params_client:
        c1 = ws.cell(row=row, column=1, value=label)
        c2 = ws.cell(row=row, column=2, value=val)
        c1.font = _font(bold=True)
        c1.fill = _fill(COULEUR_LIGHT_GREY)
        if isinstance(val, float) and val > 100:
            c2.number_format = "#,##0 €"
        ws.row_dimensions[row].height = 16
        row += 1

    # Allocation cible
    row += 1
    ws.cell(row=row, column=1, value="Allocation cible par classe").font = _font(bold=True, color=COULEUR_SUBHEADER)
    row += 1
    alloc_arr = allocation.as_array()
    for i, (cls_name, pct) in enumerate(zip(allocation.classes, alloc_arr)):
        if pct > 0:
            label_map = {
                "actions_monde": "Actions Monde",
                "actions_usa": "Actions USA",
                "actions_europe": "Actions Europe",
                "actions_emergents": "Actions Émergents",
                "obligations": "Obligations",
                "monetaire": "Monétaire",
                "or": "Or",
                "immobilier": "Immobilier coté",
                "matieres_premieres": "Matières premières",
            }
            bg = COULEUR_LIGHT_GREY if i % 2 == 0 else None
            c1 = ws.cell(row=row, column=1, value=f"  {label_map.get(cls_name, cls_name)}")
            c2 = ws.cell(row=row, column=2, value=pct)
            style_data(c1, bg=bg)
            style_data(c2, bg=bg, number_format="0.0%")
            c2.alignment = _align("center")
            ws.row_dimensions[row].height = 15
            row += 1
    row += 1

    # ── Section 3 — Résultats Monte-Carlo ────────────────────────────
    row = titre_section(ws, row, "📊 SECTION 3 — RÉSULTATS MONTE-CARLO PAR HORIZON", 1, 9)

    # Tableau des percentiles par horizon
    percentile_headers = ["Horizon", "P5", "P10", "P25", "Médiane (P50)", "P75", "P90", "P95"]
    for j, h in enumerate(percentile_headers, 1):
        c = ws.cell(row=row, column=j, value=h)
        style_subheader(c)
    ws.row_dimensions[row].height = 18
    row += 1

    percentiles_list = [5, 10, 25, 50, 75, 90, 95]
    for h in horizons:
        res = resultats[h]
        row_data = [f"{h} ans"] + [
            res.capital_final_percentiles.get(p, 0) for p in percentiles_list
        ]
        bg = COULEUR_LIGHT_GREY if horizons.index(h) % 2 == 0 else None
        for j, val in enumerate(row_data, 1):
            c = ws.cell(row=row, column=j, value=val)
            style_data(c, bg=bg)
            if j == 1:
                c.font = _font(bold=True)
                c.alignment = _align("center")
            else:
                c.number_format = "#,##0 €"
                c.alignment = _align("center")
        ws.row_dimensions[row].height = 18
        row += 1
    row += 1

    # Probabilité d'atteindre l'objectif
    ws.merge_cells(f"A{row}:C{row}")
    ws.cell(row=row, column=1, value="Objectif de capital").font = _font(bold=True)
    ws.cell(row=row, column=4, value=objectif_capital).number_format = "#,##0 €"
    ws.row_dimensions[row].height = 16
    row += 1

    for h in horizons:
        res = resultats[h]
        prob = res.probabilite_objectif
        annee = res.annee_mediane_atteinte_objectif
        c1 = ws.cell(row=row, column=1, value=f"Probabilité d'atteindre l'objectif à {h} ans")
        c2 = ws.cell(row=row, column=4, value=prob if prob is not None else 0.0)
        c3_val = f"Année {annee}" if annee is not None else "Non atteint (médiane)"
        c3 = ws.cell(row=row, column=5, value=c3_val)
        c1.font = _font(bold=True)
        c2.number_format = "0.0%"
        c2.alignment = _align("center")
        if prob is not None and prob >= 0.75:
            c2.font = _font(bold=True, color=COULEUR_OK)
        elif prob is not None and prob < 0.50:
            c2.font = _font(bold=True, color=COULEUR_DANGER)
        ws.row_dimensions[row].height = 16
        row += 1
    row += 1

    # ── Section 4 — Trajectoires synthétiques (horizon 30 ans) ───────
    row = titre_section(ws, row, "📈 SECTION 4 — TRAJECTOIRES SYNTHÉTIQUES (Horizon 30 ans)", 1, 9)

    headers_traj = ["Année", "P10", "Médiane (P50)", "P90"]
    for j, h in enumerate(headers_traj, 1):
        c = ws.cell(row=row, column=j, value=h)
        style_subheader(c)
    ws.row_dimensions[row].height = 18

    data_start_row = row + 1
    row += 1

    res30 = resultats[30]
    for annee in range(31):
        bg = COULEUR_LIGHT_GREY if annee % 2 == 0 else None
        vals = [
            annee,
            float(res30.capital_p10_par_annee[annee]),
            float(res30.capital_median_par_annee[annee]),
            float(res30.capital_p90_par_annee[annee]),
        ]
        for j, val in enumerate(vals, 1):
            c = ws.cell(row=row, column=j, value=val)
            style_data(c, bg=bg)
            if j == 1:
                c.alignment = _align("center")
            else:
                c.number_format = "#,##0 €"
                c.alignment = _align("right")
        ws.row_dimensions[row].height = 15
        row += 1

    data_end_row = row - 1

    # ── Section 5 — Graphique en éventail ────────────────────────────
    chart = LineChart()
    chart.title = "Projection Monte-Carlo (10 000 tirages) — percentiles 10 / 50 / 90"
    chart.style = 10
    chart.y_axis.title = "Capital (€)"
    chart.x_axis.title = "Années"
    chart.height = 14
    chart.width = 22

    # Colonnes B, C, D = P10, Médiane, P90
    for col_idx, label in [(2, "P10"), (3, "Médiane (P50)"), (4, "P90")]:
        data_ref = Reference(ws, min_col=col_idx, min_row=data_start_row - 1, max_row=data_end_row)
        chart.add_data(data_ref, titles_from_data=True)

    # Années en axe X
    cats = Reference(ws, min_col=1, min_row=data_start_row, max_row=data_end_row)
    chart.set_categories(cats)

    # Styles des séries : P10 rouge tireté, Médiane bleu, P90 vert
    from openpyxl.chart.series import SeriesLabel
    series_styles = [
        ("FF0000", False),  # P10 — rouge
        ("2E75B6", False),  # Médiane — bleu
        ("70AD47", False),  # P90 — vert
    ]
    for i, (color, dashed) in enumerate(series_styles):
        if i < len(chart.series):
            chart.series[i].graphicalProperties.line.solidFill = color
            chart.series[i].graphicalProperties.line.width = 20000  # ~1.5pt
            if dashed:
                chart.series[i].graphicalProperties.line.dashDot = "dash"

    # Placer le graphique 2 lignes sous le tableau
    chart_anchor = f"F{data_start_row - 1}"
    ws.add_chart(chart, chart_anchor)

    # ── Mise en forme colonnes ────────────────────────────────────────
    set_col_width(ws, 1, 40)
    set_col_width(ws, 2, 18)
    set_col_width(ws, 3, 18)
    set_col_width(ws, 4, 18)
    set_col_width(ws, 5, 22)
    set_col_width(ws, 6, 16)
    set_col_width(ws, 7, 16)
    set_col_width(ws, 8, 16)
    set_col_width(ws, 9, 16)

    ws.freeze_panes = "A4"


# ─── Fonction principale ─────────────────────────────────────────────
def generer_excel(chemin_sortie: str = None):
    """Génère le fichier Excel complet Boglehead FR."""
    if chemin_sortie is None:
        chemin_sortie = str(ROOT / "output" / "portefeuille_bogleheads.xlsx")

    # Chargement des données
    params_fiscaux = load_yaml("fiscalite_2026.yaml")
    enveloppes_data = load_yaml("enveloppes.yaml")["enveloppes"]
    etfs_data = load_yaml("univers_etf.yaml")["univers_etf"]
    profils_data = load_yaml("profils_clients.yaml")

    wb = openpyxl.Workbook()
    # Supprimer la feuille par défaut
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]

    # ── Création des onglets ──────────────────────────────────────────
    print("  → Onglet Paramètres_Client")
    creer_onglet_parametres_client(wb)

    print("  → Onglet Paramètres_Fiscalité_2026")
    creer_onglet_fiscalite(wb, params_fiscaux)

    print("  → Onglet Enveloppes")
    creer_onglet_enveloppes(wb, enveloppes_data)

    print("  → Onglet Univers_ETF")
    creer_onglet_univers_etf(wb, etfs_data)

    print("  → Onglet Allocation_Cible")
    creer_onglet_allocation_cible(wb)

    print("  → Onglet Asset_Location_Matrice")
    creer_onglet_asset_location(wb, etfs_data, enveloppes_data)

    print("  → Onglet Rebalancement")
    creer_onglet_rebalancement(wb)

    print("  → Onglet Reporting_Client")
    creer_onglet_reporting(wb)

    print("  → Onglet Profils_Types")
    creer_onglet_profils_types(wb, profils_data)

    for profil in profils_data.get("profils", []):
        nom_court = profil.get("nom", f"Profil_{profil['id']}")
        print(f"  → Onglet Profil {profil['id']} — {nom_court}")
        creer_onglet_profil_individuel(wb, profil, etfs_data, params_fiscaux)

    print("  → Onglet Comparatif_Profils")
    creer_onglet_comparatif_profils(wb, profils_data, params_fiscaux)

    print("  → Onglet Tuto_Solveur")
    creer_onglet_tuto_solveur(wb)

    print("  → Onglet Projection_MonteCarlo")
    profil_ref = profils_data.get("profils", [{}])[0]
    _creer_onglet_projection_monte_carlo(wb, profil_ref)

    # Mise en page générale — propriétés du classeur
    wb.properties.title = "Boglehead FR — Outil CGP Multi-Enveloppes 2026"
    wb.properties.subject = "Allocation Boglehead multi-enveloppes — France 2026"
    wb.properties.creator = "Boglehead FR — Outil CGP"
    wb.properties.description = (
        "Outil pédagogique de gestion de portefeuille Boglehead multi-enveloppes fiscales. "
        "Ne constitue pas un conseil en investissement."
    )

    # Sauvegarde
    Path(chemin_sortie).parent.mkdir(parents=True, exist_ok=True)
    wb.save(chemin_sortie)
    print(f"\n✅ Fichier sauvegardé : {chemin_sortie}")
    print(f"   Onglets créés : {len(wb.sheetnames)}")
    for name in wb.sheetnames:
        print(f"   • {name}")
