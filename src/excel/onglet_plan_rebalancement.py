"""
Onglet Excel Plan_Rebalancement — Sprint S3.6.

Génère un plan d'action chiffré pour le CGP, structuré en 3 étapes :
  Étape 1 : arbitrages gratuits (intra-enveloppe exonérée)
  Étape 2 : flux entrants (réorientation des versements)
  Étape 3 : ventes optimisées fiscalement

Affiche l'économie fiscale réalisée vs scénario naïf.
"""

from __future__ import annotations

from typing import Any

import openpyxl
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
    ajouter_disclaimer,
    set_col_width,
    titre_section,
)
from src.rebalancement_optimal import (
    ABATTEMENT_AV_CELIBATAIRE,
    Lot,
    PlanRebalancement,
    Position,
    optimiser_rebalancement,
)

VERT_OK = "C6EFCE"
ROUGE_NOK = "FFC7CE"
ORANGE_WARN = "FFEB9C"
BLEU_ETAPE = "BDD7EE"
NB_COLS = 9


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _cell_merge(ws, row: int, col_start: int, col_end: int, value, bg=None, bold=False, size=10):
    ws.merge_cells(start_row=row, start_column=col_start, end_row=row, end_column=col_end)
    c = ws.cell(row=row, column=col_start, value=value)
    c.font = _font(bold=bold, size=size)
    c.alignment = _align("left", "center", wrap=True)
    if bg:
        c.fill = _fill(bg)
    return c


def _ligne_donnee(ws, row: int, cols_vals: list[tuple[int, Any]], bg=None, bold=False):
    for col, val in cols_vals:
        c = ws.cell(row=row, column=col, value=val)
        c.font = _font(bold=bold)
        c.alignment = _align("left", "center")
        c.border = _thin_border()
        if bg:
            c.fill = _fill(bg)


def _derive_emoji(derive_pp: float) -> str:
    if abs(derive_pp) <= 2.0:
        return "✅"
    if abs(derive_pp) <= 5.0:
        return "🟡"
    return "🔴"


# ─── Création de l'onglet ────────────────────────────────────────────────────


def creer_onglet_plan_rebalancement(wb: openpyxl.Workbook, profil_ref: dict | None = None):
    """
    Crée l'onglet Plan_Rebalancement dans le classeur wb.

    Parameters
    ----------
    wb
        Classeur openpyxl cible.
    profil_ref
        Dict du profil client (issu de profils_clients.yaml). Si None, utilise
        des données de démonstration.
    """
    ws = wb.create_sheet("Plan_Rebalancement")

    # Largeurs de colonnes
    for col, width in enumerate([4, 20, 18, 18, 14, 14, 14, 20, 18], start=1):
        set_col_width(ws, col, width)

    # ── Calcul du plan ────────────────────────────────────────────────────────
    plan = _calculer_plan_depuis_profil(profil_ref)

    # ── En-tête principal ─────────────────────────────────────────────────────
    row = 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=NB_COLS)
    c = ws.cell(
        row=row,
        column=1,
        value=f"🎯 PLAN DE REBALANCEMENT — GÉNÉRÉ LE {plan.date_generation}",
    )
    c.font = Font(bold=True, color="FFFFFF", size=14)
    c.fill = _fill(COULEUR_HEADER)
    c.alignment = _align("center", "center")
    ws.row_dimensions[row].height = 30
    row += 1

    # Sous-titre profil
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=NB_COLS)
    c = ws.cell(row=row, column=1, value=f"Profil : {plan.profil_code}")
    c.font = _font(italic=True, size=10, color="444444")
    c.alignment = _align("center", "center")
    row += 2

    # ── Section : Dérive constatée ────────────────────────────────────────────
    row = titre_section(ws, row, "📊 DÉRIVE CONSTATÉE", 1, NB_COLS)

    # En-têtes
    headers = ["Classe", "Dérive (pp)", "Statut", "Action suggérée"]
    for i, h in enumerate(headers, start=2):
        c = ws.cell(row=row, column=i, value=h)
        c.font = _font(bold=True, color="FFFFFF")
        c.fill = _fill(COULEUR_SUBHEADER)
        c.alignment = _align("center", "center")
        c.border = _thin_border()
    row += 1

    for classe, derive_pp in plan.derive_par_classe.items():
        emoji = _derive_emoji(derive_pp)
        if derive_pp > 2.0:
            action = "RÉDUIRE (surpondéré)"
            bg = ROUGE_NOK
        elif derive_pp < -2.0:
            action = "AUGMENTER (sous-pondéré)"
            bg = ORANGE_WARN
        else:
            action = "Dans les bandes ✅"
            bg = VERT_OK
        _ligne_donnee(
            ws,
            row,
            [
                (2, classe),
                (3, f"{derive_pp:+.1f} pp"),
                (4, emoji),
                (5, action),
            ],
            bg=bg,
        )
        row += 1
    row += 1

    # ── Étape 1 : Arbitrages gratuits ─────────────────────────────────────────
    row = titre_section(ws, row, "ÉTAPE 1 — ARBITRAGES GRATUITS (0 €)", 1, NB_COLS, BLEU_ETAPE)

    if plan.arbitrages_gratuits:
        headers2 = [
            "Enveloppe",
            "Vendre ETF",
            "Acheter classe",
            "Montant (€)",
            "Coût fiscal",
            "Impact (pp)",
        ]
        for i, h in enumerate(headers2, start=2):
            c = ws.cell(row=row, column=i, value=h)
            c.font = _font(bold=True)
            c.fill = _fill(COULEUR_LIGHT_GREY)
            c.alignment = _align("center", "center")
            c.border = _thin_border()
        row += 1

        for arb in plan.arbitrages_gratuits:
            _ligne_donnee(
                ws,
                row,
                [
                    (2, arb.get("enveloppe", "")),
                    (3, arb.get("vendre_etf", "")),
                    (4, arb.get("acheter_classe", "")),
                    (5, arb.get("montant", 0.0)),
                    (6, "0 €"),
                    (7, f"{arb.get('impact_pp', 0.0):.2f} pp"),
                ],
                bg=VERT_OK,
            )
            row += 1
    else:
        _cell_merge(
            ws, row, 2, NB_COLS, "ℹ️ Aucun arbitrage gratuit nécessaire", bg=COULEUR_LIGHT_GREY
        )
        row += 1
    row += 1

    # ── Étape 2 : Flux entrants ───────────────────────────────────────────────
    row = titre_section(ws, row, "ÉTAPE 2 — FLUX ENTRANTS (0 €)", 1, NB_COLS, BLEU_ETAPE)

    if plan.flux_recommandes:
        headers3 = ["Classe", "Montant (€)", "Horizon (mois)", "Coût fiscal"]
        for i, h in enumerate(headers3, start=2):
            c = ws.cell(row=row, column=i, value=h)
            c.font = _font(bold=True)
            c.fill = _fill(COULEUR_LIGHT_GREY)
            c.alignment = _align("center", "center")
            c.border = _thin_border()
        row += 1

        for flux in plan.flux_recommandes:
            _ligne_donnee(
                ws,
                row,
                [
                    (2, flux.get("classe", "")),
                    (3, flux.get("montant", 0.0)),
                    (4, flux.get("horizon_mois", 3)),
                    (5, "0 €"),
                ],
                bg=COULEUR_LIGHT_BLUE,
            )
            row += 1
    else:
        _cell_merge(
            ws,
            row,
            2,
            NB_COLS,
            "ℹ️ Pas de versements prévus (étape 2 ignorée)",
            bg=COULEUR_LIGHT_GREY,
        )
        row += 1
    row += 1

    # ── Étape 3 : Ventes ─────────────────────────────────────────────────────
    row = titre_section(ws, row, "ÉTAPE 3 — VENTES OPTIMISÉES", 1, NB_COLS, "F4B942")

    if plan.ventes:
        headers4 = [
            "Enveloppe",
            "ETF",
            "Montant (€)",
            "PV réalisée (€)",
            "Coût fiscal (€)",
            "Frais (€)",
            "Méthode",
        ]
        for i, h in enumerate(headers4, start=2):
            c = ws.cell(row=row, column=i, value=h)
            c.font = _font(bold=True, color="FFFFFF")
            c.fill = _fill("ED7D31")
            c.alignment = _align("center", "center")
            c.border = _thin_border()
        row += 1

        for vente in plan.ventes:
            bg = VERT_OK if vente.cout_fiscal == 0 else ORANGE_WARN
            _ligne_donnee(
                ws,
                row,
                [
                    (2, vente.enveloppe),
                    (3, vente.etf),
                    (4, round(vente.montant, 2)),
                    (5, round(vente.plus_value_realisee, 2)),
                    (6, round(vente.cout_fiscal, 2)),
                    (7, round(vente.frais_courtage, 2)),
                    (8, vente.methode),
                ],
                bg=bg,
            )
            row += 1
    else:
        _cell_merge(ws, row, 2, NB_COLS, "✅ Aucune vente nécessaire à cette étape", bg=VERT_OK)
        row += 1
    row += 1

    # ── Résultats ─────────────────────────────────────────────────────────────
    row = titre_section(ws, row, "═══ RÉSULTATS ═══", 1, NB_COLS)

    resultats = [
        ("Allocation cible atteinte", "✅" if plan.allocation_atteinte else "⚠️ Partielle"),
        ("Coût fiscal total optimisé", f"{plan.cout_fiscal_total:.2f} €"),
        ("Coût fiscal sans optimisation (naïf)", f"{plan.cout_fiscal_naif:.2f} €"),
        ("⭐ Économie fiscale réalisée", f"{plan.economie_fiscale:.2f} €"),
        (
            "Horizon de mise en œuvre",
            f"{plan.horizon_mois} mois" if plan.horizon_mois > 0 else "Immédiat",
        ),
    ]

    for label, val in resultats:
        is_economie = "Économie" in label
        bg = VERT_OK if is_economie and plan.economie_fiscale > 0 else COULEUR_LIGHT_GREY
        _ligne_donnee(
            ws,
            row,
            [(2, label), (4, val)],
            bg=bg,
            bold=is_economie,
        )
        row += 1

    row += 1
    row = ajouter_disclaimer(ws, row, col_start=1, col_end=NB_COLS)

    return ws


# ─── Calcul du plan depuis le profil YAML ─────────────────────────────────────


def _calculer_plan_depuis_profil(profil_ref: dict | None) -> PlanRebalancement:
    """
    Construit un PlanRebalancement depuis le dict profil_ref (YAML).

    Utilisé par l'onglet Excel.
    """
    if profil_ref is None:
        return _plan_demonstration()

    # Positions détaillées
    positions: list[Position] = []
    for pos_dict in profil_ref.get("positions_detaillees", []):
        lots = [
            Lot(
                date_acquisition=lot["date_acquisition"],
                quantite=float(lot["quantite"]),
                prix_unitaire=float(lot["prix_unitaire"]),
            )
            for lot in pos_dict.get("lots", [])
        ]
        positions.append(
            Position(
                etf=pos_dict["etf"],
                enveloppe=pos_dict["enveloppe"],
                quantite=float(pos_dict["quantite"]),
                prix_revient_moyen=float(pos_dict["prix_revient_moyen"]),
                montant_actuel=float(pos_dict["montant_actuel"]),
                lots=lots,
                date_ouverture_enveloppe=pos_dict.get("date_ouverture_enveloppe"),
            )
        )

    # Allocation actuelle
    patrimoine_total = float(profil_ref.get("patrimoine_financier_total", 500_000))
    allocation_cible_raw = profil_ref.get("allocation_cible_bogleheads", {})
    allocation_cible = {
        k: float(v)
        for k, v in allocation_cible_raw.items()
        if k != "commentaire" and isinstance(v, (int, float))
    }

    # Allocation actuelle estimée depuis les positions
    if positions:
        total_pos = sum(p.montant_actuel for p in positions)
        allocation_actuelle = {}
        # Mapping enveloppe → classe (simplifié)
        for pos in positions:
            classe = _etf_to_classe(pos.etf)
            allocation_actuelle[classe] = (
                allocation_actuelle.get(classe, 0.0) + pos.montant_actuel / total_pos
            )
    else:
        # Utiliser l'allocation cible comme allocation actuelle (0 dérive)
        allocation_actuelle = dict(allocation_cible)

    # Paramètres de rebalancement
    regime_fiscal = profil_ref.get("regime_fiscal_detenteur", "IR")
    abattements = profil_ref.get("abattements_utilises", {})
    abattement_av = float(
        abattements.get("av_abattement_annuel_restant", ABATTEMENT_AV_CELIBATAIRE)
    )
    frais_courtage = float(profil_ref.get("frais_courtier_par_transaction", 0.0))
    versement_mensuel = float(
        (profil_ref.get("enveloppes_disponibles") or {})
        .get("PEA", {})
        .get("versement_mensuel_prevu", 0)
        or 0
    )
    capacite_epargne = float(profil_ref.get("capacite_epargne_annuelle", 0))
    if versement_mensuel == 0 and capacite_epargne > 0:
        versement_mensuel = capacite_epargne / 12

    return optimiser_rebalancement(
        positions=positions,
        allocation_actuelle=allocation_actuelle,
        allocation_cible=allocation_cible,
        patrimoine_total=patrimoine_total,
        versement_mensuel=versement_mensuel,
        regime_fiscal=regime_fiscal,
        abattement_av_restant=abattement_av,
        frais_courtage=frais_courtage,
        profil_code=profil_ref.get("code", "INCONNU"),
    )


def _etf_to_classe(ticker: str) -> str:
    """Mapping ticker → classe d'actifs (simplifié pour l'onglet)."""
    actions = {"CW8", "CSP1", "IWDA", "LYPS", "PAEEM", "IEEM", "EXSA", "C50"}
    obligations = {"AGGH", "GOVS", "IEAA", "IBTM", "ITPS"}
    or_etfs = {"GOLD", "IGLN", "XGLD"}
    if ticker in actions:
        return "actions"
    if ticker in obligations:
        return "obligations"
    if ticker in or_etfs:
        return "or_"
    return "liquidites"


def _plan_demonstration() -> PlanRebalancement:
    """Plan de démonstration quand aucun profil n'est fourni."""
    positions = [
        Position(
            etf="CSP1",
            enveloppe="PEA",
            quantite=150,
            prix_revient_moyen=300.0,
            montant_actuel=65_000,
            lots=[Lot(date_acquisition="2019-03-15", quantite=150, prix_unitaire=300.0)],
            date_ouverture_enveloppe="2019-03-15",
        ),
        Position(
            etf="AGGH",
            enveloppe="PEA",
            quantite=500,
            prix_revient_moyen=48.0,
            montant_actuel=24_000,
            lots=[Lot(date_acquisition="2020-01-10", quantite=500, prix_unitaire=48.0)],
            date_ouverture_enveloppe="2019-03-15",
        ),
        Position(
            etf="IWDA",
            enveloppe="CTO_perso",
            quantite=300,
            prix_revient_moyen=82.30,
            montant_actuel=28_530,
            lots=[
                Lot(date_acquisition="2021-01-10", quantite=150, prix_unitaire=78.0),
                Lot(date_acquisition="2023-04-15", quantite=150, prix_unitaire=86.6),
            ],
        ),
    ]

    allocation_actuelle = {"actions": 0.736, "obligations": 0.20, "liquidites": 0.064}
    allocation_cible = {"actions": 0.65, "obligations": 0.30, "liquidites": 0.05}
    patrimoine_total = 117_530

    return optimiser_rebalancement(
        positions=positions,
        allocation_actuelle=allocation_actuelle,
        allocation_cible=allocation_cible,
        patrimoine_total=patrimoine_total,
        versement_mensuel=3_000,
        regime_fiscal="IR",
        abattement_av_restant=ABATTEMENT_AV_CELIBATAIRE,
        frais_courtage=0.0,
        profil_code="DEMO",
    )
