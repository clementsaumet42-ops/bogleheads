import openpyxl
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Font

from src.excel.styles import (
    COULEUR_HEADER,
    COULEUR_LIGHT_BLUE,
    COULEUR_LIGHT_GREY,
    COULEUR_SUBHEADER,
    _align,
    _fill,
    _font,
    _thin_border,
    set_col_width,
    style_header,
    titre_section,
)
from src.rebalancement_flux import (
    EtatPortefeuille,
    comparer_cout_fiscal,
    repartir_versement,
    simuler_versements_recurrents,
)
from src.rebalancement_flux import (
    charger_config as charger_cfg_flux,
)


# ─── Onglet Rebalancement_Flux ────────────────────────────────────────
def _creer_onglet_rebalancement_flux(wb: openpyxl.Workbook, profil_ref: dict):
    """Crée l'onglet Rebalancement_Flux avec outil de rebalancement par flux."""
    ws = wb.create_sheet("Rebalancement_Flux")
    cfg = charger_cfg_flux()

    JAUNE_SAISIE = "FFFF99"
    VERT_OK = "C6EFCE"
    ROUGE_NOK = "FFC7CE"
    ORANGE_WARN = "FFEB9C"

    NB_COLS = 8

    # ── Section 1 — Titre & Description ──────────────────────────────
    row = 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=NB_COLS)
    c = ws.cell(row=row, column=1, value="💸 Rebalancement par flux — zéro fiscalité")
    c.font = Font(bold=True, color="FFFFFF", size=14)
    c.fill = _fill(COULEUR_HEADER)
    c.alignment = _align("center", "center")
    ws.row_dimensions[row].height = 28
    row += 1

    desc_lines = [
        "Au lieu de vendre les positions surpondérées pour rééquilibrer (ce qui déclenche l'imposition des plus-values),",
        "on oriente les nouveaux versements vers les classes sous-pondérées.",
        "Résultat : même effet de rebalancement, zéro impôt.",
        "Quand l'utiliser : en phase d'accumulation avec versements réguliers.",
        "Quand passer par une vente : si la dérive dépasse 15 pp ou si le rattrapage prend > 24 mois.",
    ]
    for line in desc_lines:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=NB_COLS)
        c = ws.cell(row=row, column=1, value=line)
        c.font = _font(italic=True, size=9)
        c.alignment = _align("left", "center", wrap=True)
        ws.row_dimensions[row].height = 16
        row += 1
    row += 1

    # ── Section 2 — Saisie du portefeuille actuel ─────────────────────
    row = titre_section(
        ws,
        row,
        "📋 SECTION 2 — PORTEFEUILLE ACTUEL (cellules jaunes = saisissables)",
        col_end=NB_COLS,
    )

    headers_s2 = [
        "Classe d'actifs",
        "Montant actuel (€)",
        "Poids actuel %",
        "Poids cible %",
        "Écart %",
        "Écart €",
    ]
    for j, h in enumerate(headers_s2, 1):
        c = ws.cell(row=row, column=j, value=h)
        style_header(c, bg=COULEUR_HEADER)
    ws.row_dimensions[row].height = 18
    row += 1

    alloc_profil = profil_ref.get("allocation_cible_bogleheads", {})
    patrimoine = float(profil_ref.get("patrimoine_financier_eur", 100_000))
    actions_total = float(alloc_profil.get("actions", 0.65))
    obligs_total = float(alloc_profil.get("obligations", 0.15))
    immo_total = float(alloc_profil.get("immobilier", 0.05))
    or_total = float(alloc_profil.get("or", 0.05))
    monetaire_total = float(alloc_profil.get("monetaire", 0.05))
    matieres = float(alloc_profil.get("matieres_premieres", 0.02))

    classes_info = [
        (
            "Actions Monde",
            "actions_monde",
            round(patrimoine * actions_total * 0.50),
            round(actions_total * 0.50, 4),
        ),
        (
            "Actions USA",
            "actions_usa",
            round(patrimoine * actions_total * 0.25),
            round(actions_total * 0.25, 4),
        ),
        (
            "Actions Europe",
            "actions_europe",
            round(patrimoine * actions_total * 0.15),
            round(actions_total * 0.15, 4),
        ),
        (
            "Actions Émergents",
            "actions_emergents",
            round(patrimoine * actions_total * 0.10),
            round(actions_total * 0.10, 4),
        ),
        ("Obligations", "obligations", round(patrimoine * obligs_total), round(obligs_total, 4)),
        ("Monétaire", "monetaire", round(patrimoine * monetaire_total), round(monetaire_total, 4)),
        ("Or", "or_", round(patrimoine * or_total), round(or_total, 4)),
        ("Immobilier", "immobilier", round(patrimoine * immo_total), round(immo_total, 4)),
        (
            "Matières premières",
            "matieres_premieres",
            round(patrimoine * matieres),
            round(matieres, 4),
        ),
    ]

    data_start_row = row
    col_montant = "B"
    col_poids_act = "C"
    col_cible = "D"
    col_ecart_pct = "E"

    for i, (label, _key, montant_def, cible_def) in enumerate(classes_info):
        r = row + i
        total_ref = f"SUM({col_montant}{data_start_row}:{col_montant}{data_start_row + len(classes_info) - 1})"

        c_label = ws.cell(row=r, column=1, value=label)
        c_label.font = _font(bold=True)
        c_label.fill = _fill(COULEUR_LIGHT_GREY)
        c_label.border = _thin_border()

        c_montant = ws.cell(row=r, column=2, value=montant_def)
        c_montant.fill = _fill(JAUNE_SAISIE)
        c_montant.number_format = "#,##0 €"
        c_montant.border = _thin_border()
        c_montant.alignment = _align("right")

        c_poids = ws.cell(row=r, column=3, value=f"={col_montant}{r}/({total_ref})")
        c_poids.number_format = "0.0%"
        c_poids.border = _thin_border()
        c_poids.alignment = _align("center")

        c_cible = ws.cell(row=r, column=4, value=cible_def)
        c_cible.fill = _fill(JAUNE_SAISIE)
        c_cible.number_format = "0.0%"
        c_cible.border = _thin_border()
        c_cible.alignment = _align("center")

        c_ecart = ws.cell(row=r, column=5, value=f"={col_cible}{r}-{col_poids_act}{r}")
        c_ecart.number_format = "+0.0%;-0.0%;0.0%"
        c_ecart.border = _thin_border()
        c_ecart.alignment = _align("center")

        c_ecart_e = ws.cell(
            row=r, column=6, value=f"=({col_cible}{r}-{col_poids_act}{r})*({total_ref})"
        )
        c_ecart_e.number_format = "#,##0 €"
        c_ecart_e.border = _thin_border()
        c_ecart_e.alignment = _align("right")

        ws.row_dimensions[r].height = 16

    row += len(classes_info)

    # Ligne TOTAL
    c_tot_lbl = ws.cell(row=row, column=1, value="TOTAL")
    c_tot_lbl.font = _font(bold=True)
    c_tot_lbl.fill = _fill(COULEUR_LIGHT_GREY)
    c_tot_lbl.border = _thin_border()

    c_tot_montant = ws.cell(
        row=row, column=2, value=f"=SUM({col_montant}{data_start_row}:{col_montant}{row - 1})"
    )
    c_tot_montant.number_format = "#,##0 €"
    c_tot_montant.font = _font(bold=True)
    c_tot_montant.border = _thin_border()
    c_tot_montant.alignment = _align("right")

    c_tot_pct = ws.cell(row=row, column=3, value="100 %")
    c_tot_pct.font = _font(bold=True)
    c_tot_pct.border = _thin_border()
    c_tot_pct.alignment = _align("center")

    c_tot_cible = ws.cell(
        row=row, column=4, value=f"=SUM({col_cible}{data_start_row}:{col_cible}{row - 1})"
    )
    c_tot_cible.number_format = "0.0%"
    c_tot_cible.font = _font(bold=True)
    c_tot_cible.border = _thin_border()
    c_tot_cible.alignment = _align("center")

    for col in (5, 6):
        c = ws.cell(row=row, column=col, value="—")
        c.font = _font(bold=True)
        c.border = _thin_border()
        c.alignment = _align("center")

    ws.row_dimensions[row].height = 16
    row += 2

    # Mise en forme conditionnelle sur la colonne Écart %
    ecart_range = (
        f"{col_ecart_pct}{data_start_row}:{col_ecart_pct}{data_start_row + len(classes_info) - 1}"
    )
    ws.conditional_formatting.add(
        ecart_range, CellIsRule(operator="greaterThan", formula=["0.05"], fill=_fill(ROUGE_NOK))
    )
    ws.conditional_formatting.add(
        ecart_range, CellIsRule(operator="lessThan", formula=["-0.05"], fill=_fill(ROUGE_NOK))
    )
    ws.conditional_formatting.add(
        ecart_range, CellIsRule(operator="between", formula=["-0.05", "0.05"], fill=_fill(VERT_OK))
    )

    # ── Section 3 — Versement disponible ─────────────────────────────
    row = titre_section(ws, row, "💶 SECTION 3 — VERSEMENT À RÉPARTIR", col_end=NB_COLS)
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    c_lbl = ws.cell(row=row, column=1, value="Versement à répartir (€) :")
    c_lbl.font = _font(bold=True)
    c_lbl.alignment = _align("right")
    c_vers = ws.cell(row=row, column=5, value=1_000)
    c_vers.fill = _fill(JAUNE_SAISIE)
    c_vers.number_format = "#,##0 €"
    c_vers.border = _thin_border()
    c_vers.alignment = _align("right")
    ws.row_dimensions[row].height = 18
    row += 2

    # ── Section 4 — Répartition recommandée (calculée en Python) ──────
    row = titre_section(
        ws, row, "📊 SECTION 4 — RÉPARTITION RECOMMANDÉE (calculée au build)", col_end=NB_COLS
    )

    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=NB_COLS)
    c_note = ws.cell(
        row=row,
        column=1,
        value=(
            "ℹ️ Cette répartition est calculée en Python au build. "
            "Pour recalculer après avoir modifié vos données, relancez python build_excel.py."
        ),
    )
    c_note.font = _font(italic=True, size=9)
    c_note.fill = _fill(COULEUR_LIGHT_BLUE)
    c_note.alignment = _align("left", "center", wrap=True)
    ws.row_dimensions[row].height = 20
    row += 1

    portef_kwargs = {key: float(montant) for _, key, montant, _ in classes_info}
    portefeuille = EtatPortefeuille(**portef_kwargs)
    allocation_cible_dict = {key: float(cible) for _, key, _, cible in classes_info}
    versement_defaut = 1_000.0

    rep = repartir_versement(portefeuille, allocation_cible_dict, versement_defaut, cfg)

    headers_s4 = [
        "Classe d'actifs",
        "Montant à verser (€)",
        "Nouveau poids %",
        "Nouvel écart %",
        "Statut",
    ]
    for j, h in enumerate(headers_s4, 1):
        c = ws.cell(row=row, column=j, value=h)
        style_header(c, bg=COULEUR_SUBHEADER)
    ws.row_dimensions[row].height = 18
    row += 1

    label_map = {key: label for label, key, _, _ in classes_info}
    for _key, montant_vers in rep.repartition.items():
        label = label_map.get(_key, _key)
        poids_final = rep.allocation_finale.get(_key, 0.0)
        cible = allocation_cible_dict.get(_key, 0.0)
        ecart_final = poids_final - cible
        statut = "✅" if abs(ecart_final) <= 0.05 else "⚠️"

        vals = [label, montant_vers, poids_final, ecart_final, statut]
        bg = VERT_OK if statut == "✅" else ORANGE_WARN
        for j, val in enumerate(vals, 1):
            c = ws.cell(row=row, column=j, value=val)
            c.border = _thin_border()
            c.alignment = _align("center" if j > 1 else "left")
            if j == 2 and isinstance(val, float):
                c.number_format = "#,##0 €"
            elif j in (3, 4) and isinstance(val, float):
                c.number_format = "+0.0%;-0.0%;0.0%"
            if j == 5:
                c.fill = _fill(bg)
        ws.row_dimensions[row].height = 15
        row += 1
    row += 1

    # ── Section 5 — Comparaison fiscale ──────────────────────────────
    row = titre_section(
        ws, row, "💰 SECTION 5 — COMPARAISON FISCALE (vente vs flux)", col_end=NB_COLS
    )

    headers_s5 = [
        "Enveloppe",
        "Montant à arbitrer",
        "Coût fiscal VENTE",
        "Coût fiscal FLUX",
        "Économie",
    ]
    for j, h in enumerate(headers_s5, 1):
        c = ws.cell(row=row, column=j, value=h)
        style_header(c, bg=COULEUR_SUBHEADER)
    ws.row_dimensions[row].height = 18
    row += 1

    enveloppes_fiscales = ["CTO_perso", "PEA", "PER", "AV_UC", "PEE", "CTO_IS", "Contrat_Cap_IS"]
    montant_arb = 5_000.0
    for env in enveloppes_fiscales:
        cmp = comparer_cout_fiscal(montant_arb, env, cfg)
        vals = [env, montant_arb, cmp.cout_fiscal_vente, 0.0, cmp.economie_fiscale]
        for j, val in enumerate(vals, 1):
            c = ws.cell(row=row, column=j, value=val)
            c.border = _thin_border()
            c.alignment = _align("right" if j > 1 else "left")
            if j in (2, 3, 4, 5) and isinstance(val, float):
                c.number_format = "#,##0 €"
            if j == 5 and isinstance(val, float) and val > 0:
                c.font = _font(bold=True, color="375623")
                c.fill = _fill(VERT_OK)
        ws.row_dimensions[row].height = 15
        row += 1
    row += 1

    # ── Section 6 — Horizon de rattrapage ─────────────────────────────
    row = titre_section(ws, row, "📅 SECTION 6 — HORIZON DE RATTRAPAGE", col_end=NB_COLS)

    versement_mensuel = 500.0
    nb_mois_max = 60
    historique = simuler_versements_recurrents(
        portefeuille, allocation_cible_dict, versement_mensuel, nb_mois_max, cfg
    )

    mois_rattrapage = None
    for i, r_hist in enumerate(historique, 1):
        if not r_hist.classes_encore_hors_bandes:
            mois_rattrapage = i
            break

    if mois_rattrapage is not None:
        msg_horizon = (
            f"Avec un versement mensuel de {versement_mensuel:,.0f} €, "
            f"toutes les classes reviennent dans les bandes en {mois_rattrapage} mois "
            f"({mois_rattrapage / 12:.1f} ans)."
        )
    else:
        msg_horizon = (
            f"Avec un versement mensuel de {versement_mensuel:,.0f} €, "
            f"les bandes ne sont pas toutes atteintes en {nb_mois_max} mois. "
            "Envisager un rebalancement partiel par vente."
        )

    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=NB_COLS)
    c_horizon = ws.cell(row=row, column=1, value=msg_horizon)
    c_horizon.font = _font(italic=True, size=9)
    c_horizon.fill = _fill(COULEUR_LIGHT_BLUE)
    c_horizon.alignment = _align("left", "center", wrap=True)
    ws.row_dimensions[row].height = 24
    row += 2

    # ── Section 7 — Recommandation ────────────────────────────────────
    row = titre_section(ws, row, "💡 SECTION 7 — RECOMMANDATION", col_end=NB_COLS)

    reco_bg = (
        VERT_OK
        if "✅" in rep.recommandation
        else (ROUGE_NOK if "⚠️" in rep.recommandation else ORANGE_WARN)
    )
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=NB_COLS)
    c_reco = ws.cell(row=row, column=1, value=rep.recommandation)
    c_reco.font = _font(bold=True, size=11)
    c_reco.fill = _fill(reco_bg)
    c_reco.alignment = _align("center", "center", wrap=True)
    ws.row_dimensions[row].height = 30
    row += 2

    # ── Largeurs de colonnes ──────────────────────────────────────────
    set_col_width(ws, 1, 22)
    set_col_width(ws, 2, 22)
    set_col_width(ws, 3, 16)
    set_col_width(ws, 4, 16)
    set_col_width(ws, 5, 14)
    set_col_width(ws, 6, 16)
    set_col_width(ws, 7, 16)
    set_col_width(ws, 8, 16)

    ws.freeze_panes = "A8"
