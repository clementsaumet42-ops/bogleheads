import openpyxl
from openpyxl.chart import LineChart, Reference

from src.excel.styles import (
    COULEUR_DANGER,
    COULEUR_LIGHT_BLUE,
    COULEUR_LIGHT_GREY,
    COULEUR_OK,
    COULEUR_SUBHEADER,
    _align,
    _fill,
    _font,
    ajouter_disclaimer,
    set_col_width,
    style_data,
    style_header,
    style_subheader,
    titre_section,
)
from src.projection import (
    AllocationClasses,
    ParametresProjection,
    simuler_monte_carlo,
)
from src.projection import (
    charger_params as charger_params_projection,
)


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
    resultats = {h: simuler_monte_carlo(params_projection[h], params_marche) for h in horizons}

    # ── Titre principal ──────────────────────────────────────────────
    row = 1
    ws.merge_cells(f"A{row}:I{row}")
    c = ws.cell(
        row=row, column=1, value="📈 PROJECTION PATRIMONIALE MONTE-CARLO — BOGLEHEAD FR 2026"
    )
    style_header(c, size=14)
    ws.row_dimensions[row].height = 32
    row += 1

    ajouter_disclaimer(ws, row, 1, 9)
    row += 1

    # Description méthodologique
    ws.merge_cells(f"A{row}:I{row}")
    desc = (
        f"Simulation de {nb_tirages:,} trajectoires sur 10, 20 et 30 ans. "
        "Rendements réels nets d'inflation (sources : Dimson-Marsh-Staunton, JST). "
        "Rebalancement annuel vers l'allocation cible. "
        "⚠️ Pour recalculer, relancer : python build_excel.py"
    )
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
    ws.cell(row=row, column=1, value="Allocation cible par classe").font = _font(
        bold=True, color=COULEUR_SUBHEADER
    )
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
    for col_idx, _label in [(2, "P10"), (3, "Médiane (P50)"), (4, "P90")]:
        data_ref = Reference(ws, min_col=col_idx, min_row=data_start_row - 1, max_row=data_end_row)
        chart.add_data(data_ref, titles_from_data=True)

    # Années en axe X
    cats = Reference(ws, min_col=1, min_row=data_start_row, max_row=data_end_row)
    chart.set_categories(cats)

    # Styles des séries : P10 rouge tireté, Médiane bleu, P90 vert
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
