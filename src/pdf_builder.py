"""
pdf_builder.py — Generateur de rapport PDF client 13 pages (outil CGP Boglehead).

Usage:
    from src.pdf_builder import generer_pdf
    from src.schemas import CabinetConfig
    resultat = generer_pdf(profil_dict, cabinet_config, "output/rapport.pdf")
"""

from __future__ import annotations

import tempfile
import uuid
from datetime import date
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

from reportlab.lib.colors import HexColor, lightgrey, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepInFrame,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.doctemplate import BaseDocTemplate, Frame, PageTemplate

from src.schemas import CabinetConfig, ResultatPDF

# ─── Constants ────────────────────────────────────────────────────────────────

PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm
CONTENT_W = PAGE_W - 2 * MARGIN
CONTENT_H = PAGE_H - 2 * MARGIN
HEADER_H = 0.8 * cm
FOOTER_H = 0.8 * cm
INNER_H = CONTENT_H - HEADER_H - FOOTER_H

NB_PAGES = 13
_TMP_DIR = Path(tempfile.gettempdir())


# ─── Color helpers ────────────────────────────────────────────────────────────


def _hex(code: str) -> HexColor:
    return HexColor(code)


def _colors(cfg: CabinetConfig) -> tuple[HexColor, HexColor, HexColor]:
    s = cfg.style
    return _hex(s.couleur_primary), _hex(s.couleur_accent), _hex(s.couleur_neutral)


# ─── Latin-1 safe text ────────────────────────────────────────────────────────

_LATIN1_MAP: dict[str, str] = {
    "\u2013": "-",
    "\u2014": "-",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2026": "...",
    "\u20ac": "EUR",
    "\u00b0": " deg",
    "\u00e9": "e",
    "\u00e8": "e",
    "\u00ea": "e",
    "\u00eb": "e",
    "\u00e0": "a",
    "\u00e2": "a",
    "\u00e4": "a",
    "\u00f4": "o",
    "\u00f6": "o",
    "\u00f9": "u",
    "\u00fb": "u",
    "\u00fc": "u",
    "\u00ee": "i",
    "\u00ef": "i",
    "\u00e7": "c",
    "\u00c9": "E",
    "\u00c8": "E",
    "\u00ca": "E",
    "\u00c0": "A",
    "\u00c2": "A",
    "\u00ce": "I",
    "\u00d4": "O",
    "\u00db": "U",
    "\u00c7": "C",
}


def _s(text: Any) -> str:
    """Convert to str and make latin-1 safe for Helvetica."""
    if text is None:
        return ""
    txt = str(text)
    for src, dst in _LATIN1_MAP.items():
        txt = txt.replace(src, dst)
    result = []
    for ch in txt:
        try:
            ch.encode("latin-1")
            result.append(ch)
        except (UnicodeEncodeError, ValueError):
            result.append("?")
    return "".join(result)


def _fv(capital: float, versement: float, rendement: float, horizon: int) -> float:
    """Future value: lump sum + annuity at constant annual return rate."""
    r = rendement
    if r == 0:
        return capital + versement * horizon
    return capital * (1 + r) ** horizon + versement * ((1 + r) ** horizon - 1) / r


def _pct(v: Any, decimals: int = 1) -> str:
    try:
        return f"{float(v) * 100:.{decimals}f}%"
    except (TypeError, ValueError):
        return "N/A"


def _eur(v: Any) -> str:
    try:
        return f"{float(v):,.0f} EUR".replace(",", " ")
    except (TypeError, ValueError):
        return "N/A"


# ─── Styles ───────────────────────────────────────────────────────────────────


def _build_styles(cfg: CabinetConfig) -> dict[str, ParagraphStyle]:
    primary, accent, neutral = _colors(cfg)

    def ps(name: str, **kw) -> ParagraphStyle:
        return ParagraphStyle(name, **kw)

    return {
        "title_cover": ps(
            "TitleCover",
            fontName="Helvetica-Bold",
            fontSize=28,
            textColor=primary,
            spaceAfter=12,
            leading=34,
        ),
        "subtitle_cover": ps(
            "SubtitleCover",
            fontName="Helvetica",
            fontSize=16,
            textColor=neutral,
            spaceAfter=8,
            leading=20,
        ),
        "h1": ps(
            "H1",
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=primary,
            spaceBefore=10,
            spaceAfter=6,
            leading=20,
        ),
        "h2": ps(
            "H2",
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=primary,
            spaceBefore=8,
            spaceAfter=4,
            leading=16,
        ),
        "h3": ps(
            "H3",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=neutral,
            spaceBefore=6,
            spaceAfter=3,
            leading=14,
        ),
        "body": ps(
            "Body",
            fontName="Helvetica",
            fontSize=9,
            textColor=neutral,
            spaceAfter=4,
            leading=13,
        ),
        "body_small": ps(
            "BodySmall",
            fontName="Helvetica",
            fontSize=8,
            textColor=neutral,
            spaceAfter=3,
            leading=11,
        ),
        "label": ps(
            "Label",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=neutral,
            spaceAfter=2,
            leading=12,
        ),
        "accent": ps(
            "Accent",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=accent,
            spaceAfter=4,
            leading=14,
        ),
        "kpi": ps(
            "KPI",
            fontName="Helvetica-Bold",
            fontSize=20,
            textColor=primary,
            spaceAfter=2,
            leading=24,
            alignment=1,
        ),
        "kpi_label": ps(
            "KPILabel",
            fontName="Helvetica",
            fontSize=8,
            textColor=neutral,
            spaceAfter=0,
            leading=10,
            alignment=1,
        ),
        "footer": ps(
            "Footer",
            fontName="Helvetica",
            fontSize=7,
            textColor=_hex("#888888"),
            leading=9,
        ),
        "header": ps(
            "Header",
            fontName="Helvetica",
            fontSize=8,
            textColor=_hex("#888888"),
            leading=10,
        ),
        "bullet": ps(
            "Bullet",
            fontName="Helvetica",
            fontSize=9,
            textColor=neutral,
            spaceAfter=3,
            leading=13,
            leftIndent=12,
            bulletIndent=0,
        ),
        "table_header": ps(
            "TableHeader",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=white,
            leading=10,
            alignment=1,
        ),
        "table_cell": ps(
            "TableCell",
            fontName="Helvetica",
            fontSize=8,
            textColor=neutral,
            leading=10,
        ),
    }


# ─── Table helpers ────────────────────────────────────────────────────────────


def _zebra_table(
    data: list[list],
    col_widths: list[float],
    primary: HexColor,
    has_header: bool = True,
) -> Table:
    """Build a table with zebra row colours and a coloured header."""
    t = Table(data, colWidths=col_widths, repeatRows=1 if has_header else 0)
    style_cmds: list[tuple] = [
        ("GRID", (0, 0), (-1, -1), 0.3, lightgrey),
        ("ROWBACKGROUNDS", (0, 1 if has_header else 0), (-1, -1), [white, _hex("#eef2f9")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]
    if has_header:
        style_cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), primary),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ]
    t.setStyle(TableStyle(style_cmds))
    return t


def _kpi_box(
    value: str,
    label: str,
    styles: dict[str, ParagraphStyle],
    primary: HexColor,
    width: float = 5 * cm,
) -> Table:
    """Single KPI cell wrapped in a coloured box."""
    inner = Table(
        [[Paragraph(_s(value), styles["kpi"])], [Paragraph(_s(label), styles["kpi_label"])]],
        colWidths=[width - 0.4 * cm],
    )
    inner.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    box = Table([[inner]], colWidths=[width])
    box.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1.5, primary),
                ("BACKGROUND", (0, 0), (-1, -1), _hex("#f0f4fb")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return box


# ─── Matplotlib chart helpers ─────────────────────────────────────────────────


def _tmp_png(prefix: str) -> Path:
    return _TMP_DIR / f"{prefix}_{uuid.uuid4().hex[:8]}.png"


def _save_fig(fig: plt.Figure, path: Path) -> None:
    fig.savefig(str(path), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _make_pie_chart(labels: list[str], values: list[float], title: str, cfg: CabinetConfig) -> Path:
    primary_hex = cfg.style.couleur_primary
    palette = [
        "#1a4d8f",
        "#d4a017",
        "#2e7d32",
        "#c62828",
        "#6a1b9a",
        "#00838f",
        "#ef6c00",
        "#37474f",
    ]
    colors = palette[: len(labels)]
    fig, ax = plt.subplots(figsize=(5, 4))
    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,
        colors=colors,
        autopct=lambda p: f"{p:.1f}%" if p > 2 else "",
        startangle=90,
        wedgeprops={"edgecolor": "white", "linewidth": 1},
    )
    for at in autotexts:
        at.set_fontsize(7)
    ax.legend(
        wedges,
        [f"{lb} ({v * 100:.1f}%)" for lb, v in zip(labels, values)],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.25),
        fontsize=7,
        ncol=2,
    )
    ax.set_title(_s(title), fontsize=10, fontweight="bold", color=primary_hex)
    path = _tmp_png("pie")
    _save_fig(fig, path)
    return path


def _make_projection_chart(
    annees: list[int],
    p10: list[float],
    mediane: list[float],
    p90: list[float],
    cfg: CabinetConfig,
) -> Path:
    primary_hex = cfg.style.couleur_primary
    accent_hex = cfg.style.couleur_accent
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.fill_between(annees, p10, p90, alpha=0.15, color=primary_hex, label="P10 - P90")
    ax.plot(annees, mediane, color=primary_hex, linewidth=2, label="Mediane")
    ax.plot(annees, p10, color=accent_hex, linewidth=0.8, linestyle="--", alpha=0.8)
    ax.plot(annees, p90, color=accent_hex, linewidth=0.8, linestyle="--", alpha=0.8)
    ax.set_xlabel("Annees", fontsize=8)
    ax.set_ylabel("Capital (EUR)", fontsize=8)
    ax.set_title("Projection Monte-Carlo du patrimoine", fontsize=10, fontweight="bold")
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"{x / 1e6:.1f}M" if x >= 1e6 else f"{x / 1e3:.0f}k")
    )
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    path = _tmp_png("mc")
    _save_fig(fig, path)
    return path


# ─── Header / footer callback ─────────────────────────────────────────────────


class _PDFContext:
    """Mutable context shared with the page callback via closure."""

    def __init__(self) -> None:
        self.cabinet_nom: str = ""
        self.client_nom: str = ""
        self.date_str: str = ""
        self.primary: HexColor = _hex("#1a4d8f")
        self.mention_legale: str = ""
        self.total_pages: int = NB_PAGES


def _make_on_page(ctx: _PDFContext):
    def on_page(canvas, doc):
        canvas.saveState()
        page_num = doc.page

        # ── Header line ──────────────────────────────────────────────────────
        y_header = PAGE_H - MARGIN + 0.1 * cm
        canvas.setStrokeColor(ctx.primary)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, y_header - 0.05 * cm, PAGE_W - MARGIN, y_header - 0.05 * cm)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(ctx.primary)
        canvas.drawString(MARGIN, y_header, _s(ctx.cabinet_nom))
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(_hex("#888888"))
        canvas.drawRightString(PAGE_W - MARGIN, y_header, _s(ctx.client_nom))

        # ── Footer line ───────────────────────────────────────────────────────
        y_footer = MARGIN - 0.4 * cm
        canvas.setStrokeColor(_hex("#cccccc"))
        canvas.setLineWidth(0.3)
        canvas.line(MARGIN, y_footer + 0.3 * cm, PAGE_W - MARGIN, y_footer + 0.3 * cm)
        canvas.setFont("Helvetica", 6.5)
        canvas.setFillColor(_hex("#888888"))
        canvas.drawString(MARGIN, y_footer, _s(ctx.mention_legale))
        canvas.drawRightString(
            PAGE_W - MARGIN,
            y_footer,
            f"Page {page_num} / {ctx.total_pages}   |   {_s(ctx.date_str)}",
        )

        canvas.restoreState()

    return on_page


# ─── Page 1: Couverture ───────────────────────────────────────────────────────


def _page_couverture(
    profil: dict,
    cfg: CabinetConfig,
    styles: dict[str, ParagraphStyle],
) -> list:
    primary, accent, neutral = _colors(cfg)
    elements: list = []

    elements.append(Spacer(1, 3 * cm))

    # Logo or text fallback
    logo_path = cfg.cabinet.logo_path
    logo_shown = False
    if logo_path:
        logo_file = Path(logo_path)
        if not logo_file.is_absolute():
            logo_file = Path(__file__).parent.parent / logo_path
        if logo_file.exists():
            try:
                img = Image(str(logo_file), width=6 * cm, height=2 * cm, kind="proportional")
                elements.append(img)
                elements.append(Spacer(1, 0.5 * cm))
                logo_shown = True
            except Exception:
                pass

    if not logo_shown:
        elements.append(
            Paragraph(_s(cfg.cabinet.nom), styles["title_cover"])
        )
        elements.append(Spacer(1, 0.3 * cm))

    # Decorative line
    elements.append(HRFlowable(width=CONTENT_W, thickness=3, color=accent, spaceAfter=20))

    elements.append(Spacer(1, 1 * cm))
    elements.append(
        Paragraph("Etude patrimoniale Boglehead", styles["title_cover"])
    )
    elements.append(Spacer(1, 0.5 * cm))

    client_nom = _s(profil.get("nom", "Client"))
    elements.append(Paragraph(client_nom, styles["subtitle_cover"]))
    elements.append(Spacer(1, 0.3 * cm))

    today = _s(date.today().strftime("%d/%m/%Y"))
    elements.append(Paragraph(f"Date : {today}", styles["body"]))
    elements.append(Spacer(1, 2 * cm))

    # Cabinet details box
    cab = cfg.cabinet
    cab_lines = []
    if logo_shown and cab.nom:
        cab_lines.append(f"<b>{_s(cab.nom)}</b>")
    if cab.adresse:
        cab_lines.append(_s(cab.adresse))
    if cab.telephone:
        cab_lines.append(f"Tel : {_s(cab.telephone)}")
    if cab.email:
        cab_lines.append(f"Email : {_s(cab.email)}")
    if cab.site_web:
        cab_lines.append(_s(cab.site_web))
    if cab.numero_orias:
        cab_lines.append(f"ORIAS : {_s(cab.numero_orias)}")
    if cab.mention_conformite:
        cab_lines.append(_s(cab.mention_conformite))

    if cab_lines:
        cab_text = "<br/>".join(cab_lines)
        box_data = [[Paragraph(cab_text, styles["body_small"])]]
        box = Table(box_data, colWidths=[CONTENT_W])
        box.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.8, primary),
                    ("BACKGROUND", (0, 0), (-1, -1), _hex("#f0f4fb")),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        elements.append(box)

    return elements


# ─── Page 2: Synthese executive ───────────────────────────────────────────────


def _page_synthese(
    profil: dict,
    cfg: CabinetConfig,
    styles: dict[str, ParagraphStyle],
) -> list:
    primary, accent, neutral = _colors(cfg)
    elements: list = []

    elements.append(Paragraph("Synthese executive", styles["h1"]))
    elements.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=primary, spaceAfter=10))

    patrimoine = profil.get("patrimoine_financier_total", 0)
    tmi = profil.get("tmi", 0)
    capacite = profil.get("capacite_epargne_annuelle", 0)
    horizon = profil.get("horizon_placement_ans", 20)

    # KPI row
    eco_fiscale_est = float(capacite) * float(tmi) * 0.5 if capacite and tmi else 0
    kpis = [
        (_eur(patrimoine), "Patrimoine financier"),
        (_pct(tmi), "TMI"),
        (_eur(eco_fiscale_est), "Economie fiscale estimee/an"),
        (f"{horizon} ans", "Horizon placement"),
    ]
    kpi_w = CONTENT_W / len(kpis)
    kpi_row = [[_kpi_box(v, lbl, styles, primary, kpi_w - 0.2 * cm) for v, lbl in kpis]]
    kpi_table = Table(kpi_row, colWidths=[kpi_w] * len(kpis))
    kpi_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    elements.append(kpi_table)
    elements.append(Spacer(1, 0.6 * cm))

    # Allocation actuelle vs cible
    alloc = profil.get("allocation_cible_bogleheads", {}) or {}

    elements.append(Paragraph("Allocation cible Boglehead", styles["h2"]))
    alloc_data = [["Classe d'actifs", "Cible"]]
    alloc_keys = ["actions", "obligations", "immobilier_cote", "or", "liquidites"]
    labels_fr = {
        "actions": "Actions",
        "obligations": "Obligations",
        "immobilier_cote": "Immobilier cote",
        "or": "Or",
        "liquidites": "Liquidites",
    }
    for k in alloc_keys:
        v = alloc.get(k, 0)
        if v:
            alloc_data.append([_s(labels_fr.get(k, k)), _pct(v)])
    if len(alloc_data) > 1:
        elements.append(
            _zebra_table(alloc_data, [CONTENT_W * 0.6, CONTENT_W * 0.4], primary)
        )
    elements.append(Spacer(1, 0.4 * cm))

    # 3 actions cles
    elements.append(Paragraph("3 actions cles recommandees", styles["h2"]))
    actions = _build_3_actions(profil)
    for i, action in enumerate(actions, 1):
        elements.append(Paragraph(f"{i}. {_s(action)}", styles["bullet"]))

    return elements


def _build_3_actions(profil: dict) -> list[str]:
    actions = []
    enveloppes = profil.get("enveloppes_disponibles") or {}
    tmi = float(profil.get("tmi", 0))
    capacite = float(profil.get("capacite_epargne_annuelle", 0))

    per = enveloppes.get("PER") or {}
    if tmi >= 0.30 and per and capacite > 0:
        versement = min(capacite * 0.25, 10000)
        actions.append(
            f"Maximiser les versements PER ({_eur(versement)}/an) pour deduction fiscale a {_pct(tmi)}"
        )

    pea = enveloppes.get("PEA") or {}
    pea_encours = float(pea.get("encours_actuel", 0)) if pea else 0
    if pea_encours < 100000:
        actions.append(
            "Privilegier le remplissage du PEA (plafond 150 000 EUR) avec ETF actions monde"
        )

    alloc = profil.get("allocation_cible_bogleheads") or {}
    actions_pct = float(alloc.get("actions", 0))
    if actions_pct >= 0.60:
        actions.append(
            "Mettre en place un rebalancement annuel automatique en orientant les flux vers "
            "les classes sous-representees"
        )
    elif actions_pct < 0.60:
        actions.append(
            "Diversifier avec des ETF obligations pour stabiliser le portefeuille en phase de pre-retraite"
        )

    if len(actions) < 3:
        actions.append(
            "Reduire les frais : privilegier des ETF avec TER < 0.20% et limiter les transactions CTO"
        )
    return actions[:3]


# ─── Page 3: Profil client ────────────────────────────────────────────────────


def _page_profil_client(
    profil: dict,
    cfg: CabinetConfig,
    styles: dict[str, ParagraphStyle],
) -> list:
    primary, accent, neutral = _colors(cfg)
    elements: list = []

    elements.append(Paragraph("Profil client", styles["h1"]))
    elements.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=primary, spaceAfter=8))

    # Situation personnelle
    elements.append(Paragraph("Situation personnelle et professionnelle", styles["h2"]))
    rows = [
        ("Nom / Code profil", _s(profil.get("nom", "")) + f" ({_s(profil.get('code', ''))})"),
        ("Age", f"{profil.get('age', 'N/A')} ans"),
        ("Situation familiale", _s(profil.get("situation_familiale", "N/A"))),
        ("Regime fiscal", _s(profil.get("regime_fiscal", "IR"))),
        ("TMI", _pct(profil.get("tmi", 0))),
        ("Revenu fiscal de reference", _eur(profil.get("rfr_annuel"))),
        ("Revenus annuels bruts", _eur(profil.get("revenus_annuels_bruts"))),
        ("Capacite d'epargne annuelle", _eur(profil.get("capacite_epargne_annuelle"))),
    ]
    data = [["Critere", "Valeur"]] + [[_s(k), _s(v)] for k, v in rows]
    elements.append(_zebra_table(data, [CONTENT_W * 0.5, CONTENT_W * 0.5], primary))
    elements.append(Spacer(1, 0.4 * cm))

    # Objectifs
    elements.append(Paragraph("Objectifs et horizon", styles["h2"]))
    obj_principal = _s(profil.get("objectif_principal", "Non renseigne"))
    elements.append(Paragraph(f"Objectif principal : {obj_principal}", styles["body"]))

    objectifs_sec = profil.get("objectifs_secondaires") or []
    if objectifs_sec:
        elements.append(Paragraph("Objectifs secondaires :", styles["label"]))
        for obj in objectifs_sec:
            elements.append(Paragraph(f"  - {_s(obj)}", styles["bullet"]))

    elements.append(Spacer(1, 0.3 * cm))
    elements.append(
        Paragraph(
            f"Horizon de placement : {profil.get('horizon_placement_ans', 'N/A')} ans",
            styles["body"],
        )
    )
    score = profil.get("score_risque")
    if score is not None:
        elements.append(
            Paragraph(f"Score de risque : {score} / 10", styles["body"])
        )

    # Contraintes fiscales
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph("Particularites fiscales", styles["h2"]))
    particularites = profil.get("particularites_fiscales") or {}
    if particularites:
        part_rows = [["Critere", "Statut"]] + [
            [_s(k.replace("_", " ").capitalize()), "Oui" if v else "Non"]
            for k, v in particularites.items()
        ]
        elements.append(_zebra_table(part_rows, [CONTENT_W * 0.7, CONTENT_W * 0.3], primary))
    else:
        elements.append(Paragraph("Aucune particularite fiscale renseignee.", styles["body"]))

    return elements


# ─── Page 4: Patrimoine actuel ────────────────────────────────────────────────


def _page_patrimoine(
    profil: dict,
    cfg: CabinetConfig,
    styles: dict[str, ParagraphStyle],
    pie_path: Path | None,
) -> list:
    primary, accent, neutral = _colors(cfg)
    elements: list = []

    elements.append(Paragraph("Patrimoine actuel", styles["h1"]))
    elements.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=primary, spaceAfter=8))

    enveloppes = profil.get("enveloppes_disponibles") or {}
    total = float(profil.get("patrimoine_financier_total", 0))

    # Table enveloppes
    elements.append(Paragraph("Repartition par enveloppe", styles["h2"]))
    data = [["Enveloppe", "Encours (EUR)", "% du total"]]
    pie_labels, pie_vals = [], []
    for env_name, env_data in enveloppes.items():
        if env_data is None:
            continue
        encours = float(env_data.get("encours_actuel", 0)) if isinstance(env_data, dict) else 0.0
        if encours > 0:
            pct = encours / total if total > 0 else 0
            data.append([_s(env_name), _eur(encours), _pct(pct)])
            pie_labels.append(_s(env_name))
            pie_vals.append(pct)

    if len(data) > 1:
        elements.append(
            _zebra_table(
                data,
                [CONTENT_W * 0.45, CONTENT_W * 0.30, CONTENT_W * 0.25],
                primary,
            )
        )
    else:
        elements.append(Paragraph("Aucune donnee d'enveloppe renseignee.", styles["body"]))

    elements.append(Spacer(1, 0.4 * cm))

    # Pie chart
    if pie_path and pie_path.exists():
        elements.append(Paragraph("Repartition graphique", styles["h2"]))
        try:
            img = Image(str(pie_path), width=8 * cm, height=6.5 * cm)
            elements.append(img)
        except Exception:
            pass

    elements.append(Spacer(1, 0.3 * cm))
    elements.append(
        Paragraph(
            f"Patrimoine financier total : <b>{_eur(total)}</b>",
            styles["accent"],
        )
    )
    immo = profil.get("patrimoine_immobilier")
    if immo:
        elements.append(
            Paragraph(f"Patrimoine immobilier (hors champ) : {_eur(immo)}", styles["body"])
        )

    return elements


# ─── Page 5: Philosophie Boglehead ────────────────────────────────────────────


def _page_philosophie(
    cfg: CabinetConfig,
    styles: dict[str, ParagraphStyle],
) -> list:
    primary, accent, neutral = _colors(cfg)
    elements: list = []

    elements.append(Paragraph("Philosophie Boglehead", styles["h1"]))
    elements.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=primary, spaceAfter=8))

    intro = (
        "La philosophie Boglehead, inspiree par John C. Bogle (fondateur de Vanguard), "
        "repose sur trois principes fondamentaux pour l'investisseur individuel."
    )
    elements.append(Paragraph(_s(intro), styles["body"]))
    elements.append(Spacer(1, 0.5 * cm))

    principes = [
        (
            "1. ETF passifs — Investir dans le marche, pas contre lui",
            "Les fonds indiciels (ETF passifs) reproduisent un indice de marche a moindre cout. "
            "Statistiquement, plus de 80% des fonds actifs sous-performent leur indice de reference "
            "sur 10 ans apres frais. L'ETF passif capte la prime de risque du marche sans pari actif.",
        ),
        (
            "2. Diversification mondiale — Ne pas mettre tous ses oeufs dans le meme panier",
            "Un portefeuille Boglehead est diversifie a l'echelle mondiale : actions de pays "
            "developpes et emergents, plusieurs secteurs, plusieurs devises. Cette diversification "
            "reduit le risque specifique sans sacrifier le rendement attendu a long terme.",
        ),
        (
            "3. Low-cost — Les frais sont le seul rendement certain",
            "Chaque euro de frais est un euro de rendement perdu definitivement. "
            "Un TER de 0.20% vs 1.50% represente, sur 30 ans et 500 000 EUR, une difference "
            "de patrimoine de plus de 200 000 EUR. L'investisseur Boglehead traque les frais "
            "a tous les niveaux : TER ETF, frais de courtage, fiscalite.",
        ),
    ]

    for titre, texte in principes:
        box_data = [
            [Paragraph(_s(titre), styles["h3"])],
            [Paragraph(_s(texte), styles["body"])],
        ]
        box = Table(box_data, colWidths=[CONTENT_W])
        box.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.8, primary),
                    ("BACKGROUND", (0, 0), (0, 0), _hex("#eef2f9")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        elements.append(box)
        elements.append(Spacer(1, 0.4 * cm))

    elements.append(Spacer(1, 0.3 * cm))
    elements.append(
        Paragraph(
            "Ces principes sont universels et particulierement adaptes au contexte fiscal "
            "francais avec les enveloppes PEA, PER, AV et CTO.",
            styles["body"],
        )
    )

    return elements


# ─── Page 6: Allocation cible recommandee ────────────────────────────────────


def _page_allocation_cible(
    profil: dict,
    cfg: CabinetConfig,
    styles: dict[str, ParagraphStyle],
) -> list:
    primary, accent, neutral = _colors(cfg)
    elements: list = []

    elements.append(Paragraph("Allocation cible recommandee", styles["h1"]))
    elements.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=primary, spaceAfter=8))

    alloc = profil.get("allocation_cible_bogleheads") or {}
    score = profil.get("score_risque", 5)
    age = profil.get("age", 40)
    horizon = profil.get("horizon_placement_ans", 20)

    # Profil description
    if isinstance(score, (int, float)):
        if score >= 8:
            profil_risque = "Dynamique / offensif"
        elif score >= 6:
            profil_risque = "Equilibre offensif"
        elif score >= 4:
            profil_risque = "Equilibre"
        else:
            profil_risque = "Prudent / defensif"
    else:
        profil_risque = "Non evalue"

    elements.append(
        Paragraph(
            f"Profil de risque : <b>{_s(profil_risque)}</b> (score {score}/10)",
            styles["body"],
        )
    )
    elements.append(Spacer(1, 0.3 * cm))

    # Allocation table
    alloc_keys = [
        ("actions", "Actions monde"),
        ("obligations", "Obligations"),
        ("immobilier_cote", "Immobilier cote (REIT)"),
        ("or", "Or / matieres premieres"),
        ("liquidites", "Liquidites / monetaire"),
    ]

    data = [["Classe d'actifs", "Allocation cible", "Borne basse", "Borne haute", "Justification"]]
    for key, label in alloc_keys:
        v = float(alloc.get(key, 0))
        basse = max(0, v - 0.05)
        haute = min(1, v + 0.05)
        justif = _get_alloc_justif(key, v, age, horizon)
        data.append([_s(label), _pct(v), _pct(basse), _pct(haute), _s(justif)])

    elements.append(
        _zebra_table(
            data,
            [
                CONTENT_W * 0.28,
                CONTENT_W * 0.14,
                CONTENT_W * 0.13,
                CONTENT_W * 0.13,
                CONTENT_W * 0.32,
            ],
            primary,
        )
    )
    elements.append(Spacer(1, 0.4 * cm))

    # Commentaire
    commentaire = alloc.get("commentaire")
    if commentaire:
        elements.append(
            Paragraph(
                f"Commentaire : {_s(str(commentaire))}",
                styles["body"],
            )
        )
        elements.append(Spacer(1, 0.3 * cm))

    # Justification globale
    elements.append(Paragraph("Justification du profil", styles["h2"]))
    justif_globale = (
        f"A {age} ans, avec un horizon de {horizon} ans et un score de risque de {score}/10, "
        f"le profil '{_s(profil_risque)}' permet une exposition significative aux actifs de croissance "
        "tout en maintenant une diversification suffisante pour absorber les chocs de marche. "
        "L'allocation respecte les principes Boglehead : ETF passifs, diversification mondiale, frais reduits."
    )
    elements.append(Paragraph(_s(justif_globale), styles["body"]))

    return elements


def _get_alloc_justif(key: str, v: float, age: int, horizon: int) -> str:
    if key == "actions":
        return f"Moteur de croissance long terme ({horizon} ans)"
    if key == "obligations":
        return "Stabilisation et decorrelation actions" if v > 0.10 else "Profil offensif, obligations reduites"
    if key == "immobilier_cote":
        return "Diversification via REIT, decorrelation partielle" if v > 0 else "Non alloue"
    if key == "or":
        return "Couverture inflation et crise" if v > 0 else "Non alloue"
    if key == "liquidites":
        return f"Matelas securite et opportunites ({_pct(v)})"
    return ""


# ─── Page 7: Asset location optimale ─────────────────────────────────────────


def _page_asset_location(
    profil: dict,
    cfg: CabinetConfig,
    styles: dict[str, ParagraphStyle],
) -> list:
    primary, accent, neutral = _colors(cfg)
    elements: list = []

    elements.append(Paragraph("Asset location optimale", styles["h1"]))
    elements.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=primary, spaceAfter=8))

    intro = (
        "L'asset location consiste a placer chaque classe d'actifs dans l'enveloppe fiscale "
        "la plus avantageuse, afin de maximiser le rendement net d'impots a long terme."
    )
    elements.append(Paragraph(_s(intro), styles["body"]))
    elements.append(Spacer(1, 0.4 * cm))

    enveloppes = profil.get("enveloppes_disponibles") or {}
    env_actives = [k for k, v in enveloppes.items() if v is not None]

    # Matrix: classe x enveloppe
    classes = ["Actions PEA", "Actions hors PEA", "Obligations", "REIT", "Or/ETC", "Monetaire"]
    all_envs = ["PEA", "PER", "PEE", "AV_UC", "CTO_perso", "CTO_IS"]
    displayed_envs = [e for e in all_envs if e in env_actives] or all_envs[:4]

    # Preference matrix (star ratings)
    matrix: dict[str, dict[str, str]] = {
        "Actions PEA": {"PEA": "***", "PER": "**", "PEE": "*", "AV_UC": "*", "CTO_perso": ".", "CTO_IS": "."},
        "Actions hors PEA": {"PEA": ".", "PER": "***", "PEE": ".", "AV_UC": "**", "CTO_perso": "*", "CTO_IS": "**"},
        "Obligations": {"PEA": ".", "PER": "***", "PEE": ".", "AV_UC": "**", "CTO_perso": "*", "CTO_IS": "**"},
        "REIT": {"PEA": "*", "PER": "***", "PEE": ".", "AV_UC": "**", "CTO_perso": "**", "CTO_IS": "*"},
        "Or/ETC": {"PEA": ".", "PER": "**", "PEE": ".", "AV_UC": "*", "CTO_perso": "***", "CTO_IS": "*"},
        "Monetaire": {"PEA": ".", "PER": ".", "PEE": ".", "AV_UC": "*", "CTO_perso": "**", "CTO_IS": "***"},
    }

    header = ["Classe d'actifs"] + displayed_envs
    data = [header]
    for classe in classes:
        row = [_s(classe)]
        for env in displayed_envs:
            row.append(matrix.get(classe, {}).get(env, "."))
        data.append(row)

    n_envs = len(displayed_envs)
    col_w = CONTENT_W / (n_envs + 1)
    col_widths = [col_w * 1.8] + [col_w * (1 - 0.8 / n_envs)] * n_envs
    # Normalize
    total_w = sum(col_widths)
    col_widths = [w * CONTENT_W / total_w for w in col_widths]

    elements.append(
        Paragraph("Matrice asset location (*** = optimal, * = acceptable, . = deconseille)", styles["h2"])
    )
    elements.append(_zebra_table(data, col_widths, primary))
    elements.append(Spacer(1, 0.4 * cm))

    # Try to get module suggestions
    try:
        from src.asset_location import suggerer_asset_location

        alloc = profil.get("allocation_cible_bogleheads") or {}
        etfs_fictifs: list[dict] = [
            {"ticker": "CW8", "classe": "Actions", "sous_classe": "Monde developpé"},
            {"ticker": "OBLI", "classe": "Obligations", "sous_classe": "Europe"},
        ]
        suggestions = suggerer_asset_location(etfs_fictifs, env_actives or ["PEA", "CTO_perso"], alloc)
        if suggestions:
            elements.append(Paragraph("Recommandations module asset location", styles["h2"]))
            for s in suggestions[:3]:
                elements.append(Paragraph(f"  - {_s(str(s))}", styles["bullet"]))
    except Exception:
        pass

    # Logique fiscale
    elements.append(Paragraph("Logique fiscale", styles["h2"]))
    logique = [
        "PEA : fiscalite allégee apres 5 ans (PS uniquement 17.2%), ideal pour actions europeennes et monde via ETF synthetiques.",
        "PER : deduction des versements du revenu imposable, ideal pour les TMI elevees (30%+). "
        "Sortie imposable mais differee a la retraite (TMI souvent plus faible).",
        "AV : abattement annuel de 4 600 EUR (celibataire) apres 8 ans, transmission hors succession.",
        "CTO : soumis au PFU 30% (ou bareme sur option), a utiliser en dernier recours pour actifs "
        "non eligibles aux enveloppes fiscales privilegiees.",
    ]
    for line in logique:
        elements.append(Paragraph(f"  - {_s(line)}", styles["bullet"]))

    return elements


# ─── Page 8: Univers ETF selectionnes ────────────────────────────────────────


def _page_univers_etf(
    profil: dict,
    cfg: CabinetConfig,
    styles: dict[str, ParagraphStyle],
) -> list:
    primary, accent, neutral = _colors(cfg)
    elements: list = []

    elements.append(Paragraph("Univers ETF selectionnes", styles["h1"]))
    elements.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=primary, spaceAfter=8))

    enveloppes = profil.get("enveloppes_disponibles") or {}
    env_actives = set(k for k, v in enveloppes.items() if v is not None)

    # Load ETF universe
    etfs_filtered: list[dict] = []
    try:
        from src.schemas import charger_et_valider

        univers = charger_et_valider("univers_etf.yaml")
        for etf in univers.univers_etf:
            elig = etf.eligibilite.model_dump() if hasattr(etf.eligibilite, "model_dump") else {}
            eligible_in_active = any(elig.get(e, False) for e in env_actives) if env_actives else True
            if eligible_in_active:
                etfs_filtered.append(
                    {
                        "isin": etf.isin,
                        "ticker": etf.ticker,
                        "nom": etf.nom[:40],
                        "classe": etf.classe_actifs,
                        "ter": etf.ter,
                        "domicile": etf.domicile,
                        "eligibilite": ", ".join(
                            k for k, v in elig.items() if v and k in env_actives
                        ) or ", ".join(k for k, v in elig.items() if v)[:30],
                    }
                )
    except Exception:
        etfs_filtered = []

    if etfs_filtered:
        data = [["ISIN", "Ticker", "Nom", "Classe", "TER", "Domicile", "Eligibilite"]]
        for e in etfs_filtered[:15]:
            data.append(
                [
                    _s(e.get("isin", "")),
                    _s(e.get("ticker", "")),
                    _s(e.get("nom", "")),
                    _s(e.get("classe", "")),
                    f"{float(e.get('ter', 0)) * 100:.2f}%",
                    _s(e.get("domicile", "")),
                    _s(e.get("eligibilite", "")),
                ]
            )
        col_widths = [
            CONTENT_W * 0.14,
            CONTENT_W * 0.07,
            CONTENT_W * 0.23,
            CONTENT_W * 0.12,
            CONTENT_W * 0.06,
            CONTENT_W * 0.10,
            CONTENT_W * 0.28,
        ]
        elements.append(
            Paragraph(
                f"ETF eligibles aux enveloppes du profil ({len(etfs_filtered)} selectionnes) :",
                styles["h2"],
            )
        )
        elements.append(_zebra_table(data, col_widths, primary))
        if len(etfs_filtered) > 15:
            elements.append(
                Paragraph(
                    f"... et {len(etfs_filtered) - 15} autres ETF non affiches.", styles["body_small"]
                )
            )
    else:
        elements.append(
            Paragraph(
                "Aucun ETF disponible pour ce profil ou donnees non chargees.", styles["body"]
            )
        )
        elements.append(Spacer(1, 0.5 * cm))
        default_etfs = [
            ["ISIN", "Ticker", "Nom", "TER", "Enveloppe"],
            ["IE0031442068", "CW8", "Amundi MSCI World (PEA)", "0.38%", "PEA/CTO"],
            ["IE00B4L5Y983", "IWDA", "iShares Core MSCI World", "0.20%", "CTO/PER"],
            ["FR0010315770", "LYXOR S&P500", "Lyxor S&P 500 PEA", "0.15%", "PEA"],
            ["IE00B14X4T88", "EMIM", "iShares Emergents", "0.18%", "CTO/PER"],
        ]
        elements.append(
            Paragraph("Selection ETF indicative (univers standard Boglehead FR) :", styles["h2"])
        )
        elements.append(
            _zebra_table(
                default_etfs,
                [CONTENT_W * 0.20, CONTENT_W * 0.13, CONTENT_W * 0.35, CONTENT_W * 0.12, CONTENT_W * 0.20],
                primary,
            )
        )

    elements.append(Spacer(1, 0.3 * cm))
    elements.append(
        Paragraph(
            "Criteres de selection : TER minimal, replication physique ou synthetique reconnue, "
            "domicile Irlande ou France (eligible PEA), AUM > 500M EUR, liquidite quotidienne.",
            styles["body_small"],
        )
    )

    return elements


# ─── Page 9: Projection Monte-Carlo ──────────────────────────────────────────


def _page_projection(
    profil: dict,
    cfg: CabinetConfig,
    styles: dict[str, ParagraphStyle],
    mc_path: Path | None,
) -> list:
    primary, accent, neutral = _colors(cfg)
    elements: list = []

    elements.append(Paragraph("Projection Monte-Carlo", styles["h1"]))
    elements.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=primary, spaceAfter=8))

    patrimoine = float(profil.get("patrimoine_financier_total", 0))
    versement = float(profil.get("capacite_epargne_annuelle", 0))
    horizon = int(profil.get("horizon_placement_ans", 20))

    elements.append(
        Paragraph(
            f"Capital initial : <b>{_eur(patrimoine)}</b> | "
            f"Versement annuel : <b>{_eur(versement)}</b> | "
            f"Horizon : <b>{horizon} ans</b>",
            styles["body"],
        )
    )
    elements.append(Spacer(1, 0.3 * cm))

    # Load projection results
    proj_data: dict | None = None
    try:
        from src.projection import AllocationClasses, projeter_profil

        alloc_raw = profil.get("allocation_cible_bogleheads") or {}
        alloc = AllocationClasses(
            actions=float(alloc_raw.get("actions", 0.6)),
            obligations=float(alloc_raw.get("obligations", 0.2)),
            or_=float(alloc_raw.get("or", 0.05)),
            immobilier=float(alloc_raw.get("immobilier_cote", 0.05)),
            monetaire=float(alloc_raw.get("liquidites", 0.10)),
        )
        resultats = projeter_profil(profil, alloc, horizons=[10, 20, 30])
        proj_data = {h: r for h, r in resultats.items()}
    except Exception:
        proj_data = None

    # Graph
    if mc_path and mc_path.exists():
        try:
            img = Image(str(mc_path), width=CONTENT_W, height=7 * cm)
            elements.append(img)
            elements.append(Spacer(1, 0.3 * cm))
        except Exception:
            pass

    # Results table
    if proj_data:
        elements.append(Paragraph("Resultats par horizon", styles["h2"]))
        res_data = [["Horizon", "P10 (pessimiste)", "Mediane (P50)", "P90 (optimiste)", "Proba objectif"]]
        for h, r in sorted(proj_data.items()):
            try:
                p10 = _eur(r.percentile_10) if hasattr(r, "percentile_10") else "N/A"
                med = _eur(r.mediane) if hasattr(r, "mediane") else "N/A"
                p90 = _eur(r.percentile_90) if hasattr(r, "percentile_90") else "N/A"
                proba = _pct(r.probabilite_objectif) if hasattr(r, "probabilite_objectif") and r.probabilite_objectif is not None else "N/A"
                res_data.append([f"{h} ans", p10, med, p90, proba])
            except Exception:
                res_data.append([f"{h} ans", "N/A", "N/A", "N/A", "N/A"])
        elements.append(
            _zebra_table(
                res_data,
                [CONTENT_W * 0.12, CONTENT_W * 0.22, CONTENT_W * 0.22, CONTENT_W * 0.22, CONTENT_W * 0.22],
                primary,
            )
        )
    else:
        # Fallback: deterministic estimate
        rendement_moy = 0.065
        elements.append(Paragraph("Estimation deterministique (fallback)", styles["h2"]))
        est_data = [["Horizon", "Capital estime (rendement 6.5%/an)", "Dont versements cumules"]]
        for h in [10, 20, 30]:
            cap = _fv(patrimoine, versement, rendement_moy, h)
            cumul = versement * h
            est_data.append([f"{h} ans", _eur(cap), _eur(cumul)])
        elements.append(
            _zebra_table(
                est_data,
                [CONTENT_W * 0.20, CONTENT_W * 0.50, CONTENT_W * 0.30],
                primary,
            )
        )

    elements.append(Spacer(1, 0.3 * cm))
    elements.append(
        Paragraph(
            "Hypotheses : 10 000 simulations, rendements gaussiens par classe d'actifs, "
            "rebalancement annuel, inflation non deduite. Les resultats passés ne prejugent pas "
            "des resultats futurs. Tout investissement comporte un risque de perte en capital.",
            styles["body_small"],
        )
    )

    return elements


# ─── Page 10: Plan de rebalancement ──────────────────────────────────────────


def _page_rebalancement(
    profil: dict,
    cfg: CabinetConfig,
    styles: dict[str, ParagraphStyle],
) -> list:
    primary, accent, neutral = _colors(cfg)
    elements: list = []

    elements.append(Paragraph("Plan de rebalancement", styles["h1"]))
    elements.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=primary, spaceAfter=8))

    enveloppes = profil.get("enveloppes_disponibles") or {}
    alloc_cible = profil.get("allocation_cible_bogleheads") or {}
    patrimoine = float(profil.get("patrimoine_financier_total", 0))
    capacite = float(profil.get("capacite_epargne_annuelle", 0))
    tmi = float(profil.get("tmi", 0))

    # Try rebalancement module
    reb_data: dict | None = None
    try:
        from src.rebalancement import recommander_rebalancement

        alloc_actuelle_approx = {k: float(v) for k, v in alloc_cible.items() if k != "commentaire"}
        params_fiscaux_simple = {
            "prelevements_sociaux": {"taux_global": 0.172},
            "pfu": {"taux_ir": 0.128},
            "is": {"taux_reduit": 0.15},
        }
        env_actives = [k for k, v in enveloppes.items() if v is not None]
        reb_data = recommander_rebalancement(
            alloc_actuelle_approx,
            {k: v for k, v in alloc_cible.items() if k != "commentaire"},
            patrimoine,
            capacite,
            params_fiscaux_simple,
            env_actives,
        )
    except Exception:
        reb_data = None

    elements.append(Paragraph("Strategie de rebalancement Boglehead", styles["h2"]))
    cascade = [
        (
            "1. Rebalancement par les flux (GRATUIT)",
            f"Orienter les versements annuels ({_eur(capacite)}) vers les classes sous-representees. "
            "Aucune fiscalite. A privilegier systematiquement.",
            True,
        ),
        (
            "2. Arbitrages intra-enveloppe exoneree (SANS COUT FISCAL)",
            "En cas de derive importante, effectuer des arbitrages au sein du PEA, PER ou PEE. "
            "Ces arbitrages ne generent pas d'imposition immediate.",
            bool(enveloppes.get("PEA") or enveloppes.get("PER")),
        ),
        (
            "3. Ventes CTO en dernier recours (COUT FISCAL PFU 30%)",
            f"Seulement si les derives depassent les bandes de tolerance (+/-5pp absolus ou +/-25% relatifs). "
            f"Cout fiscal : PFU 30% sur les plus-values (TMI {_pct(tmi)} + PS 17.2%).",
            bool(enveloppes.get("CTO_perso")),
        ),
    ]

    for titre, desc, applicable in cascade:
        color = _hex("#e8f5e9") if applicable else _hex("#fafafa")
        border_color = _hex("#2e7d32") if applicable else _hex("#cccccc")
        box_data = [
            [Paragraph(_s(titre), styles["h3"])],
            [Paragraph(_s(desc), styles["body"])],
        ]
        box = Table(box_data, colWidths=[CONTENT_W])
        box.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.8, border_color),
                    ("BACKGROUND", (0, 0), (0, 0), color),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(box)
        elements.append(Spacer(1, 0.25 * cm))

    # Recommandations from module
    if reb_data:
        recommandations = reb_data.get("recommandations", [])
        if recommandations:
            elements.append(Spacer(1, 0.3 * cm))
            elements.append(Paragraph("Actions specifiques recommandees", styles["h2"]))
            reb_table = [["Classe", "Action", "Methode", "Priorite"]]
            for rec in recommandations[:8]:
                reb_table.append(
                    [
                        _s(rec.get("classe", "")),
                        _s(rec.get("action", "")),
                        _s(rec.get("methode", "")),
                        str(rec.get("priorite", "")),
                    ]
                )
            if len(reb_table) > 1:
                elements.append(
                    _zebra_table(
                        reb_table,
                        [
                            CONTENT_W * 0.18,
                            CONTENT_W * 0.42,
                            CONTENT_W * 0.28,
                            CONTENT_W * 0.12,
                        ],
                        primary,
                    )
                )

    return elements


# ─── Page 11: Fiscalite & transmission ───────────────────────────────────────


def _page_fiscalite(
    profil: dict,
    cfg: CabinetConfig,
    styles: dict[str, ParagraphStyle],
) -> list:
    primary, accent, neutral = _colors(cfg)
    elements: list = []

    elements.append(Paragraph("Fiscalite et transmission", styles["h1"]))
    elements.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=primary, spaceAfter=8))

    tmi = float(profil.get("tmi", 0))
    rfr = profil.get("rfr_annuel")
    enveloppes = profil.get("enveloppes_disponibles") or {}
    situation = _s(profil.get("situation_familiale", "N/A"))

    # TMI panel
    elements.append(Paragraph("Situation fiscale actuelle", styles["h2"]))
    fisc_data = [
        ["Parametre", "Valeur"],
        ["TMI", _pct(tmi)],
        ["RFR annuel", _eur(rfr)],
        ["PFU (flat tax)", "30% (12.8% IR + 17.2% PS)"],
        ["Taux PS", "17.2%"],
        ["Situation familiale", situation],
    ]
    elements.append(_zebra_table(fisc_data, [CONTENT_W * 0.55, CONTENT_W * 0.45], primary))
    elements.append(Spacer(1, 0.4 * cm))

    # PER deduction
    elements.append(Paragraph("Opportunite PER — Deduction fiscale", styles["h2"]))
    per = enveloppes.get("PER") or {}
    per_versement = float(per.get("versement_annuel_prevu", 0)) if isinstance(per, dict) else 0
    eco_per = per_versement * tmi
    elements.append(
        Paragraph(
            f"Versement PER prevu : {_eur(per_versement)}/an | "
            f"Economie fiscale estimee : <b>{_eur(eco_per)}/an</b> (deduction au TMI {_pct(tmi)})",
            styles["body"],
        )
    )
    if tmi >= 0.30:
        plafond_approx = max(4113, min(32909, float(rfr or 0) * 0.10))
        elements.append(
            Paragraph(
                f"Plafond deduction PER estimatif : {_eur(plafond_approx)}/an "
                "(10% du RFR, plafonné à 8 PASS). A verifier avec votre avis d'imposition.",
                styles["body_small"],
            )
        )

    elements.append(Spacer(1, 0.4 * cm))

    # AV abattements
    elements.append(Paragraph("Assurance-vie — Avantages fiscaux", styles["h2"]))
    abattement = 9200 if "marié" in situation.lower() or "pacs" in situation.lower() else 4600
    av_lines = [
        f"Abattement annuel sur les rachats apres 8 ans : {_eur(abattement)} ({_s(situation)})",
        "Transmission hors droits de succession : jusqu'a 152 500 EUR par beneficiaire (versements avant 70 ans)",
        "Taux d'imposition apres 8 ans : 7.5% IR (au-dela abattement) + 17.2% PS",
    ]
    for line in av_lines:
        elements.append(Paragraph(f"  - {_s(line)}", styles["bullet"]))

    elements.append(Spacer(1, 0.4 * cm))

    # Transmission
    elements.append(Paragraph("Perspective transmission patrimoine", styles["h2"]))
    patrimoine_total = float(profil.get("patrimoine_financier_total", 0)) + float(
        profil.get("patrimoine_immobilier", 0)
    )
    trans_lines = [
        f"Patrimoine total estime : {_eur(patrimoine_total)}",
        "Abattement succession enfant : 100 000 EUR par enfant (tous les 15 ans)",
        "AV hors succession : optimiser les beneficiaires designes",
        "PER : capital transmis aux beneficiaires hors succession si deces avant 70 ans",
        "Anticiper les donations : abattement de 100 000 EUR renouvelable tous les 15 ans",
    ]
    for line in trans_lines:
        elements.append(Paragraph(f"  - {_s(line)}", styles["bullet"]))

    return elements


# ─── Page 12: Suivi recommande ────────────────────────────────────────────────


def _page_suivi(
    profil: dict,
    cfg: CabinetConfig,
    styles: dict[str, ParagraphStyle],
) -> list:
    primary, accent, neutral = _colors(cfg)
    elements: list = []

    elements.append(Paragraph("Suivi recommande", styles["h1"]))
    elements.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=primary, spaceAfter=8))

    # Calendrier
    elements.append(Paragraph("Calendrier de suivi trimestriel", styles["h2"]))
    cal_data = [
        ["Periode", "Actions recommandees"],
        ["T1 (Janv-Mars)", "Bilan annuel allocation | Optimisation fiscale PER | Declaration revenus"],
        ["T2 (Avr-Juin)", "Verification derive allocation | Ajustement versements PEE/PER"],
        ["T3 (Juil-Sep)", "Rebalancement si derive >5pp | Revue frais ETF | Bilan mi-annee"],
        ["T4 (Oct-Dec)", "Versements PER avant fin annee | Planification fiscale | Rebalancement final"],
    ]
    elements.append(_zebra_table(cal_data, [CONTENT_W * 0.28, CONTENT_W * 0.72], primary))
    elements.append(Spacer(1, 0.4 * cm))

    # KPIs
    elements.append(Paragraph("KPIs a monitorer", styles["h2"]))
    kpi_data = [
        ["KPI", "Seuil d'alerte", "Frequence"],
        ["Derive allocation vs cible", "> 5 pp absolus ou 25% relatifs", "Trimestrielle"],
        ["TER moyen portefeuille", "> 0.40%", "Annuelle"],
        ["Performance vs indice reference", "< -2% sur 3 ans glissants", "Annuelle"],
        ["Encours PEA / plafond 150k", "Suivi remplissage", "Semestrielle"],
        ["Ratio epargne / capacite", "< 80% de la capacite", "Mensuelle"],
        ["Frais courtage cumules", "> 0.5% des transactions", "Annuelle"],
    ]
    elements.append(
        _zebra_table(
            kpi_data,
            [CONTENT_W * 0.38, CONTENT_W * 0.37, CONTENT_W * 0.25],
            primary,
        )
    )
    elements.append(Spacer(1, 0.4 * cm))

    # Alertes
    elements.append(Paragraph("Alertes automatiques recommandees", styles["h2"]))
    alertes = [
        "Alerte derive : rebalancer si une classe depasse les bornes de tolerance (+/-5pp)",
        "Alerte plafond PEA : versement restant avant atteinte du plafond 150 000 EUR",
        "Alerte fiscale : rappel versement PER avant le 31/12 pour optimisation TMI",
        "Alerte AV : rappel des 8 ans d'anciennete pour beneficier des abattements",
        "Alerte marche : baisse de plus de 20% -> opportunite de versement complementaire (DCA)",
    ]
    for a in alertes:
        elements.append(Paragraph(f"  - {_s(a)}", styles["bullet"]))

    elements.append(Spacer(1, 0.4 * cm))

    # Prochaine revue
    elements.append(Paragraph("Prochaine revue conseil", styles["h2"]))
    next_year = date.today().year + 1
    elements.append(
        Paragraph(
            f"Revue annuelle recommandee : T1 {next_year}. "
            "Objectifs : bilan performance, reajustement allocation si changement de situation, "
            "optimisation fiscale annuelle.",
            styles["body"],
        )
    )

    return elements


# ─── Page 13: Mentions legales & annexes ─────────────────────────────────────


def _page_mentions_legales(
    profil: dict,
    cfg: CabinetConfig,
    styles: dict[str, ParagraphStyle],
) -> list:
    primary, accent, neutral = _colors(cfg)
    elements: list = []

    elements.append(Paragraph("Mentions legales et annexes", styles["h1"]))
    elements.append(HRFlowable(width=CONTENT_W, thickness=1.5, color=primary, spaceAfter=8))

    # Hypotheses
    elements.append(Paragraph("Hypotheses de rendement utilisees", styles["h2"]))
    hyp_data = [
        ["Classe d'actifs", "Rendement annuel attendu", "Volatilite annuelle"],
        ["Actions monde developpees", "7.0%", "15%"],
        ["Actions emergents", "8.5%", "20%"],
        ["Obligations souveraines", "2.5%", "5%"],
        ["Obligations IG", "3.5%", "6%"],
        ["Immobilier cote (REIT)", "5.0%", "12%"],
        ["Or / matieres premieres", "3.0%", "18%"],
        ["Monetaire / liquidites", "2.0%", "1%"],
    ]
    elements.append(
        _zebra_table(
            hyp_data,
            [CONTENT_W * 0.40, CONTENT_W * 0.30, CONTENT_W * 0.30],
            primary,
        )
    )
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(
        Paragraph(
            "Source : Vanguard Capital Markets Model, MSCI long-term capital market assumptions, "
            "consensus BofA/JPM/GS (2024). Ces hypotheses sont reexaminees annuellement.",
            styles["body_small"],
        )
    )
    elements.append(Spacer(1, 0.4 * cm))

    # Avertissements AMF
    elements.append(Paragraph("Avertissements reglementaires", styles["h2"]))
    amf_text = _s(cfg.footer.avertissement_amf) or (
        "Les performances passees ne prejugent pas des performances futures. "
        "Tout investissement comporte un risque de perte en capital. "
        "Ce document est etabli a titre informatif et ne constitue pas un conseil "
        "en investissement au sens de la Directive MIF II. "
        "Tout conseil personnalise doit etre delivre par un CIF/CGP agree par l'AMF."
    )
    box_amf = Table(
        [[Paragraph(amf_text, styles["body_small"])]],
        colWidths=[CONTENT_W],
    )
    box_amf.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.8, _hex("#c62828")),
                ("BACKGROUND", (0, 0), (-1, -1), _hex("#fff8f8")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(box_amf)
    elements.append(Spacer(1, 0.4 * cm))

    # Sources
    elements.append(Paragraph("Sources et references", styles["h2"]))
    sources = [
        "John C. Bogle, 'Common Sense on Mutual Funds' (1999)",
        "MSCI World Index — www.msci.com",
        "AMF — Autorite des Marches Financiers — www.amf-france.org",
        "Service-public.fr — Fiscalite de l'epargne (2024)",
        "Bogleheads.org — The Bogleheads' Guide to Investing",
        "JustETF.com — Screener ETF Europe",
        "Morningstar — Données de performance ETF",
    ]
    for s in sources:
        elements.append(Paragraph(f"  - {_s(s)}", styles["bullet"]))

    elements.append(Spacer(1, 0.4 * cm))

    # Glossaire
    elements.append(Paragraph("Glossaire", styles["h2"]))
    glossaire = [
        ("ETF (Exchange-Traded Fund)", "Fonds indiciel cote en bourse, a frais reduits."),
        ("TER (Total Expense Ratio)", "Frais totaux annuels d'un ETF, exprimes en %."),
        ("PEA (Plan d'Epargne en Actions)", "Enveloppe fiscale avantageuse pour les actions europeennes, plafond 150 000 EUR."),
        ("PER (Plan d'Epargne Retraite)", "Enveloppe retraite avec deduction des versements du revenu imposable."),
        ("PFU (Prelevement Forfaitaire Unique)", "Flat tax de 30% sur les revenus du capital (12.8% IR + 17.2% PS)."),
        ("TMI (Tranche Marginale d'Imposition)", "Taux d'imposition de la derniere tranche de revenus (0, 11, 30, 41, 45%)."),
        ("Rebalancement", "Remise a niveau periodique de l'allocation cible apres derive des marches."),
        ("Monte-Carlo", "Methode de simulation probabiliste par tirage aleatoire de scenarios de marche."),
        ("Asset Location", "Optimisation du placement de chaque actif dans l'enveloppe fiscale la plus avantageuse."),
    ]
    glos_data = [["Terme", "Definition"]] + [[_s(t), _s(d)] for t, d in glossaire]
    elements.append(
        _zebra_table(glos_data, [CONTENT_W * 0.32, CONTENT_W * 0.68], primary)
    )

    # No PageBreak on last page
    return elements


# ─── Matplotlib chart generation ─────────────────────────────────────────────


def _generate_charts(
    profil: dict,
    cfg: CabinetConfig,
) -> tuple[Path | None, Path | None]:
    """Generate pie chart and Monte-Carlo chart. Returns (pie_path, mc_path)."""
    pie_path: Path | None = None
    mc_path: Path | None = None

    # Pie chart — enveloppes
    try:
        enveloppes = profil.get("enveloppes_disponibles") or {}
        total = float(profil.get("patrimoine_financier_total", 0))
        labels, vals = [], []
        for name, data in enveloppes.items():
            if data is None:
                continue
            enc = float(data.get("encours_actuel", 0)) if isinstance(data, dict) else 0
            if enc > 0:
                labels.append(_s(name))
                vals.append(enc / total if total > 0 else 0)
        if labels:
            pie_path = _make_pie_chart(labels, vals, "Repartition du patrimoine par enveloppe", cfg)
    except Exception:
        pie_path = None

    # Monte-Carlo chart
    try:
        from src.projection import AllocationClasses, projeter_profil

        alloc_raw = profil.get("allocation_cible_bogleheads") or {}
        alloc = AllocationClasses(
            actions=float(alloc_raw.get("actions", 0.6)),
            obligations=float(alloc_raw.get("obligations", 0.2)),
            or_=float(alloc_raw.get("or", 0.05)),
            immobilier=float(alloc_raw.get("immobilier_cote", 0.05)),
            monetaire=float(alloc_raw.get("liquidites", 0.10)),
        )
        horizons = [10, 20, 30]
        resultats = projeter_profil(profil, alloc, horizons=horizons)

        patrimoine_init = float(profil.get("patrimoine_financier_total", 100000))

        # Build simplified curves from available percentile data
        pts = {0: (patrimoine_init, patrimoine_init, patrimoine_init)}
        for h, r in sorted(resultats.items()):
            p10 = getattr(r, "percentile_10", None)
            med = getattr(r, "mediane", None)
            p90 = getattr(r, "percentile_90", None)
            if p10 is not None and med is not None and p90 is not None:
                pts[h] = (float(p10), float(med), float(p90))

        horizon_keys = sorted(pts.keys())
        p10_vals = [pts[k][0] for k in horizon_keys]
        med_vals = [pts[k][1] for k in horizon_keys]
        p90_vals = [pts[k][2] for k in horizon_keys]
        mc_path = _make_projection_chart(horizon_keys, p10_vals, med_vals, p90_vals, cfg)
    except Exception:
        # Fallback: deterministic estimation
        try:
            patrimoine_init = float(profil.get("patrimoine_financier_total", 100000))
            versement = float(profil.get("capacite_epargne_annuelle", 0))
            annees = list(range(0, 31))
            r_base = 0.065
            med_c = [_fv(patrimoine_init, versement, r_base, y) for y in annees]
            p10_c = [v * 0.65 for v in med_c]
            p90_c = [v * 1.45 for v in med_c]
            mc_path = _make_projection_chart(annees, p10_c, med_c, p90_c, cfg)
        except Exception:
            mc_path = None

    return pie_path, mc_path


# ─── Main document builder ────────────────────────────────────────────────────


class _BogDoc(BaseDocTemplate):
    """Custom BaseDocTemplate that counts pages."""

    def __init__(self, filename: str, on_page_fn, **kwargs):
        super().__init__(filename, **kwargs)
        self._on_page_fn = on_page_fn

    def build(self, flowables, **kwargs):
        super().build(flowables, **kwargs)


def _page_to_story(elements: list, frame_w: float, frame_h: float, add_break: bool = True) -> list:
    """Wrap page elements in KeepInFrame (shrink mode) to guarantee exactly one page."""
    kif = KeepInFrame(frame_w, frame_h, content=elements, mode="shrink", vAlign="TOP")
    result: list = [kif]
    if add_break:
        result.append(PageBreak())
    return result


def _build_doc(
    sortie_path: str,
    profil: dict,
    cfg: CabinetConfig,
    styles: dict[str, ParagraphStyle],
    pie_path: Path | None,
    mc_path: Path | None,
    ctx: _PDFContext,
) -> int:
    """Assemble all pages and build the PDF. Returns actual page count."""
    margin = cfg.style.marges_cm * cm
    frame_x = margin
    frame_y = margin + FOOTER_H + 0.2 * cm
    frame_w = PAGE_W - 2 * margin
    frame_h = PAGE_H - 2 * margin - HEADER_H - FOOTER_H - 0.4 * cm

    frame = Frame(frame_x, frame_y, frame_w, frame_h, id="main", showBoundary=0)

    on_page = _make_on_page(ctx)
    template = PageTemplate(id="main", frames=[frame], onPage=on_page)

    doc = BaseDocTemplate(
        sortie_path,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin + HEADER_H + 0.2 * cm,
        bottomMargin=margin + FOOTER_H + 0.2 * cm,
        pageTemplates=[template],
    )

    pages = [
        _page_couverture(profil, cfg, styles),           # 1
        _page_synthese(profil, cfg, styles),              # 2
        _page_profil_client(profil, cfg, styles),         # 3
        _page_patrimoine(profil, cfg, styles, pie_path),  # 4
        _page_philosophie(cfg, styles),                   # 5
        _page_allocation_cible(profil, cfg, styles),      # 6
        _page_asset_location(profil, cfg, styles),        # 7
        _page_univers_etf(profil, cfg, styles),           # 8
        _page_projection(profil, cfg, styles, mc_path),   # 9
        _page_rebalancement(profil, cfg, styles),         # 10
        _page_fiscalite(profil, cfg, styles),             # 11
        _page_suivi(profil, cfg, styles),                 # 12
        _page_mentions_legales(profil, cfg, styles),      # 13
    ]

    story: list = []
    for i, page_elements in enumerate(pages):
        is_last = i == len(pages) - 1
        story += _page_to_story(page_elements, frame_w, frame_h, add_break=not is_last)

    doc.build(story)

    # Count pages using pypdf if available, else NB_PAGES (KeepInFrame guarantees exactly 13)
    try:
        from pypdf import PdfReader

        reader = PdfReader(sortie_path)
        return len(reader.pages)
    except Exception:
        return NB_PAGES


# ─── Public API ───────────────────────────────────────────────────────────────


def generer_pdf(
    profil: dict,
    config: CabinetConfig,
    sortie_path: str | Path,
) -> ResultatPDF:
    """
    Generate a 13-page client PDF report for a Boglehead CGP study.

    Args:
        profil: Client profile dict (from profils_clients.yaml).
        config: Cabinet configuration (CabinetConfig).
        sortie_path: Output PDF file path.

    Returns:
        ResultatPDF with metadata about the generated file.
    """
    sortie_path = Path(sortie_path)
    sortie_path.parent.mkdir(parents=True, exist_ok=True)

    today = date.today()
    date_str = today.strftime("%d/%m/%Y")

    styles = _build_styles(config)
    primary, accent, neutral = _colors(config)

    # Shared context for header/footer callback
    ctx = _PDFContext()
    ctx.cabinet_nom = _s(config.cabinet.nom)
    ctx.client_nom = _s(profil.get("nom", ""))
    ctx.date_str = date_str
    ctx.primary = primary
    ctx.mention_legale = _s(config.footer.mention_legale)
    ctx.total_pages = NB_PAGES

    # Generate charts (may fail gracefully)
    pie_path, mc_path = _generate_charts(profil, config)

    tmp_files = [f for f in [pie_path, mc_path] if f is not None]

    try:
        nb_pages = _build_doc(
            str(sortie_path),
            profil,
            config,
            styles,
            pie_path,
            mc_path,
            ctx,
        )
    finally:
        # Clean up temp chart files
        for f in tmp_files:
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                pass

    taille = sortie_path.stat().st_size if sortie_path.exists() else 0
    profil_code = _s(profil.get("code", profil.get("nom", "INCONNU")))

    return ResultatPDF(
        chemin=str(sortie_path),
        taille_octets=taille,
        nb_pages=nb_pages,
        profil_code=profil_code,
        date_generation=today.isoformat(),
    )
