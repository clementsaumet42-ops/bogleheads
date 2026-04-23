import openpyxl
from openpyxl.styles import Font
from openpyxl.worksheet.table import Table, TableStyleInfo
from src.fiscalite import calculer_pfu, avantage_fiscal_pea, calculer_avantage_per, calculer_is
from src.excel.styles import (
    COULEURS_CLASSES, COULEUR_HEADER, COULEUR_SUBHEADER, COULEUR_AVERTISSEMENT, COULEUR_OK,
    COULEUR_DANGER, COULEUR_LIGHT_GREY,
    _fill, _font, _align, _thin_border,
    style_header, style_subheader, style_data,
    set_col_width, ajouter_disclaimer, titre_section,
)


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
