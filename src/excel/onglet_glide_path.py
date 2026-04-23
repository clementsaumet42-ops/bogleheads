import openpyxl
from openpyxl.styles import Font
from openpyxl.chart import AreaChart, Reference as _Ref
from openpyxl.drawing.fill import PatternFillProperties  # noqa: F401 (imported for side-effects in chart rendering)
from openpyxl.utils import get_column_letter
from src.projection import (
    AllocationClasses,
    ParametresProjection,
    charger_params as charger_params_projection,
    simuler_monte_carlo,
    simuler_monte_carlo_glide_path,
)
from src.glide_path import charger_glide_paths, glide_path_pour_profil
from src.excel.styles import (
    COULEUR_HEADER, COULEUR_SUBHEADER, COULEUR_LIGHT_GREY,
    _fill, _font, _align,
    style_subheader,
    set_col_width,
)


# ─── Onglet Glide Path ──────────────────────────────────────────────
def _creer_onglet_glide_path(wb: openpyxl.Workbook, profil_ref: dict):
    """Crée l'onglet Glide_Path avec trajectoire, graphique et comparaison MC."""
    ws = wb.create_sheet("Glide_Path")
    ws.sheet_view.showGridLines = False

    # ── Trouver l'id profil et charger le glide path ──────────────────
    profil_id_num = profil_ref.get("id", 1)
    _id_to_gp_key = {
        1: "profil_1_cadre",
        2: "profil_2_dirigeant",
        3: "profil_3_dirigeant_pme",
        4: "profil_4_profession",
        5: "profil_5_jeune",
        6: "profil_6_pre_retraite",
    }
    profil_id = _id_to_gp_key.get(profil_id_num, "profil_1_cadre")
    gps = charger_glide_paths()
    try:
        gp = glide_path_pour_profil(profil_id)
    except KeyError:
        gp = gps["bogle_classique"]

    age_actuel = int(profil_ref.get("age", 45))
    age_fin = 90
    horizons_mc = [10, 20, 30]

    capital_initial = float(profil_ref.get("patrimoine_financier_total", 500_000))
    versement_annuel = float(profil_ref.get("capacite_epargne_annuelle", 40_000))

    params_marche = charger_params_projection()
    sim_params = params_marche.get("simulation", {})
    nb_tirages = min(sim_params.get("nb_tirages", 10000), 2000)
    seed = sim_params.get("seed", 42)

    # ── Section 1 — Titre & Description ──────────────────────────────
    row = 1
    c = ws.cell(row=row, column=1, value="🔄 Glide Path — Trajectoire d'allocation dans le temps")
    c.font = Font(bold=True, color="FFFFFF", size=14)
    c.fill = _fill(COULEUR_HEADER)
    c.alignment = _align("center", "center")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=12)
    ws.row_dimensions[row].height = 28
    row += 1

    desc_lines = [
        "Le lifecycle investing (glide path) adapte l'allocation d'actifs à l'âge de l'investisseur.",
        "Jeune : forte exposition actions (croissance). À l'approche de la retraite : désensibilisation progressive.",
        f"Glide path utilisé : {gp.nom} — {gp.description}",
    ]
    for line in desc_lines:
        c = ws.cell(row=row, column=1, value=line)
        c.font = _font(italic=True, size=9)
        c.alignment = _align("left", "center", wrap=True)
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=12)
        ws.row_dimensions[row].height = 16
        row += 1
    row += 1

    # ── Section 2 — Paramètres ────────────────────────────────────────
    c = ws.cell(row=row, column=1, value="⚙️ PARAMÈTRES DU GLIDE PATH")
    c.font = Font(bold=True, color="FFFFFF", size=11)
    c.fill = _fill(COULEUR_SUBHEADER)
    c.alignment = _align("left", "center")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=12)
    ws.row_dimensions[row].height = 20
    row += 1

    params_info = [
        ("Glide path", gp.nom),
        ("Description", gp.description),
        ("Type", gp.type),
        ("Règle", gp.formule if gp.formule else f"{len(gp.points)} points d'ancrage"),
        ("Âge de départ (profil)", age_actuel),
        ("Âge de fin de projection", age_fin),
    ]
    for label, val in params_info:
        c1 = ws.cell(row=row, column=1, value=label)
        c2 = ws.cell(row=row, column=2, value=val)
        c1.font = _font(bold=True)
        c1.fill = _fill(COULEUR_LIGHT_GREY)
        c2.alignment = _align("left", "center", wrap=True)
        ws.row_dimensions[row].height = 16
        row += 1
    row += 1

    # ── Section 3 — Trajectoire ───────────────────────────────────────
    c = ws.cell(row=row, column=1, value="📊 TRAJECTOIRE ANNÉE PAR ANNÉE")
    c.font = Font(bold=True, color="FFFFFF", size=11)
    c.fill = _fill(COULEUR_SUBHEADER)
    c.alignment = _align("left", "center")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=12)
    ws.row_dimensions[row].height = 20
    row += 1

    headers = [
        "Année", "Âge",
        "Actions %", "Obligations %", "Monétaire %", "Immobilier %",
        "Actions Monde %", "Actions USA %", "Actions Europe %", "Actions Émergents %",
        "Défensif total %", "Offensif total %",
    ]
    for j, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=j, value=h)
        style_subheader(c)
        ws.column_dimensions[get_column_letter(j)].width = 14
    ws.row_dimensions[row].height = 18

    traj_data_start = row + 1
    row += 1

    trajectoire = gp.trajectoire(age_actuel, age_fin)
    annee_base = 2026

    for idx, (age, alloc) in enumerate(trajectoire):
        bg = COULEUR_LIGHT_GREY if idx % 2 == 0 else None
        actions_pct = (alloc.actions_monde + alloc.actions_usa + alloc.actions_europe + alloc.actions_emergents) * 100
        vals = [
            annee_base + idx,
            age,
            round(actions_pct, 1),
            round(alloc.obligations * 100, 1),
            round(alloc.monetaire * 100, 1),
            round(alloc.immobilier * 100, 1),
            round(alloc.actions_monde * 100, 1),
            round(alloc.actions_usa * 100, 1),
            round(alloc.actions_europe * 100, 1),
            round(alloc.actions_emergents * 100, 1),
            round((alloc.obligations + alloc.monetaire + alloc.immobilier + alloc.or_ + alloc.matieres_premieres) * 100, 1),
            round(actions_pct, 1),
        ]
        for j, val in enumerate(vals, 1):
            c = ws.cell(row=row, column=j, value=val)
            c.alignment = _align("center")
            if bg:
                c.fill = _fill(bg)
            if j in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
                c.number_format = "0.0\"%\""
        ws.row_dimensions[row].height = 14
        row += 1

    traj_data_end = row - 1
    row += 2

    # ── Section 4 — Graphique empilé ─────────────────────────────────
    chart = AreaChart()
    chart.title = f"Évolution de l'allocation dans le temps — {gp.nom}"
    chart.grouping = "percentStacked"
    chart.style = 10
    chart.y_axis.title = "Allocation (%)"
    chart.x_axis.title = "Âge"
    chart.height = 14
    chart.width = 24

    col_labels = {3: "Actions", 4: "Obligations", 5: "Monétaire", 6: "Immobilier"}
    for col_idx, label in col_labels.items():
        data_ref = _Ref(ws, min_col=col_idx, min_row=traj_data_start - 1, max_row=traj_data_end)
        chart.add_data(data_ref, titles_from_data=True)

    cats = _Ref(ws, min_col=2, min_row=traj_data_start, max_row=traj_data_end)
    chart.set_categories(cats)

    series_colors = ["4472C4", "ED7D31", "70AD47", "A9D18E"]
    for i, color in enumerate(series_colors):
        if i < len(chart.series):
            chart.series[i].graphicalProperties.solidFill = color

    chart_anchor_col = get_column_letter(14)
    ws.add_chart(chart, f"{chart_anchor_col}{traj_data_start}")

    # ── Section 5 — Comparaison Monte-Carlo fixe vs glide path ───────
    c = ws.cell(row=row, column=1, value="📈 COMPARAISON MONTE-CARLO : ALLOCATION FIXE vs GLIDE PATH")
    c.font = Font(bold=True, color="FFFFFF", size=11)
    c.fill = _fill(COULEUR_HEADER)
    c.alignment = _align("left", "center")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=12)
    ws.row_dimensions[row].height = 20
    row += 1

    alloc_profil = profil_ref.get("allocation_cible_bogleheads", {})
    actions_total = float(alloc_profil.get("actions", 0.65))
    alloc_fixe = AllocationClasses(
        actions_monde=round(actions_total * 0.50, 4),
        actions_usa=round(actions_total * 0.25, 4),
        actions_europe=round(actions_total * 0.15, 4),
        actions_emergents=round(actions_total * 0.10, 4),
        obligations=float(alloc_profil.get("obligations", 0.20)),
        monetaire=float(alloc_profil.get("liquidites", 0.05)),
        or_=float(alloc_profil.get("or", 0.05)),
        immobilier=float(alloc_profil.get("immobilier_cote", 0.05)),
    )

    headers_mc = ["Horizon", "Approche", "Médiane (€)", "P10 (€)", "P90 (€)", "Prob. objectif"]
    for j, h in enumerate(headers_mc, 1):
        c = ws.cell(row=row, column=j, value=h)
        style_subheader(c)
    ws.row_dimensions[row].height = 18
    row += 1

    objectif = capital_initial * 3.0

    for horizon in horizons_mc:
        p_fixe = ParametresProjection(
            capital_initial=capital_initial,
            versement_annuel=versement_annuel,
            horizon_annees=horizon,
            allocation=alloc_fixe,
            nb_tirages=nb_tirages,
            seed=seed,
            objectif_capital=objectif,
        )
        res_fixe = simuler_monte_carlo(p_fixe, params_marche)

        res_gp = simuler_monte_carlo_glide_path(
            capital_initial=capital_initial,
            versement_annuel=versement_annuel,
            age_debut=age_actuel,
            horizon_annees=horizon,
            glide_path=gp,
            nb_tirages=nb_tirages,
            seed=seed,
            params_marche=params_marche,
            objectif_capital=objectif,
        )

        for approche, res in [("Allocation fixe", res_fixe), ("Glide path", res_gp)]:
            bg = COULEUR_LIGHT_GREY if approche == "Glide path" else None
            prob = res.probabilite_objectif
            vals = [
                f"{horizon} ans",
                approche,
                res.capital_final_percentiles.get(50, 0),
                res.capital_final_percentiles.get(10, 0),
                res.capital_final_percentiles.get(90, 0),
                f"{prob * 100:.1f}%" if prob is not None else "—",
            ]
            for j, val in enumerate(vals, 1):
                c = ws.cell(row=row, column=j, value=val)
                c.alignment = _align("center")
                if bg:
                    c.fill = _fill(bg)
                if j in (3, 4, 5) and isinstance(val, float):
                    c.number_format = "#,##0 €"
            ws.row_dimensions[row].height = 15
            row += 1
        row += 1

    # ── Largeurs de colonnes ──────────────────────────────────────────
    set_col_width(ws, 1, 12)
    set_col_width(ws, 2, 8)
    set_col_width(ws, 3, 12)
    set_col_width(ws, 4, 14)
    set_col_width(ws, 5, 13)
    set_col_width(ws, 6, 13)
    set_col_width(ws, 7, 15)
    set_col_width(ws, 8, 13)
    set_col_width(ws, 9, 15)
    set_col_width(ws, 10, 17)
    set_col_width(ws, 11, 16)
    set_col_width(ws, 12, 16)

    ws.freeze_panes = "A5"
