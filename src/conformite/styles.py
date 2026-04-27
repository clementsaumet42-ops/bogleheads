"""Styles ReportLab partagés pour les PDFs conformité CIF."""

from __future__ import annotations

from typing import Any

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

_PRIMARY = colors.HexColor("#1a4d8f")
_ACCENT = colors.HexColor("#d4a017")
_NEUTRAL = colors.HexColor("#333333")
_LIGHT_GREY = colors.HexColor("#f5f5f5")
_BLUE_LIGHT = colors.HexColor("#e8f0fb")
_ROW_ALT = colors.HexColor("#f9f9f9")
_GRID_COLOR = colors.HexColor("#cccccc")


def build_styles() -> dict[str, ParagraphStyle]:
    """Construit les styles partagés pour les PDFs conformité."""
    base = getSampleStyleSheet()

    def s(name: str, parent: str = "Normal", **kw: Any) -> ParagraphStyle:
        return ParagraphStyle(name, parent=base[parent], **kw)

    return {
        "title": s(
            "ConfTitle",
            parent="Heading1",
            fontSize=20,
            textColor=_PRIMARY,
            spaceAfter=12,
            spaceBefore=6,
        ),
        "h2": s(
            "ConfH2",
            parent="Heading2",
            fontSize=13,
            textColor=_PRIMARY,
            spaceAfter=8,
            spaceBefore=10,
        ),
        "h3": s("ConfH3", parent="Heading3", fontSize=11, textColor=_NEUTRAL, spaceAfter=6),
        "body": s("ConfBody", fontSize=10, leading=14, textColor=_NEUTRAL),
        "small": s("ConfSmall", fontSize=8, leading=11, textColor=_NEUTRAL),
        "bold": s(
            "ConfBold", fontSize=10, leading=14, fontName="Helvetica-Bold", textColor=_NEUTRAL
        ),
        "center": s("ConfCenter", fontSize=10, alignment=1, textColor=_NEUTRAL),
        "italic": s("ConfItalic", fontSize=9, leading=13, textColor=_NEUTRAL),
        "legal": s("ConfLegal", fontSize=7.5, leading=10, textColor=_NEUTRAL),
        "cover_title": s(
            "ConfCoverTitle",
            fontSize=24,
            textColor=_PRIMARY,
            alignment=1,
            fontName="Helvetica-Bold",
        ),
        "cover_sub": s("ConfCoverSub", fontSize=14, textColor=_NEUTRAL, alignment=1),
        "bullet": s("ConfBullet", fontSize=10, leading=14, textColor=_NEUTRAL, leftIndent=12),
    }


TABLE_HEADER_STYLE = [
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("BACKGROUND", (0, 0), (-1, 0), _BLUE_LIGHT),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _ROW_ALT]),
    ("GRID", (0, 0), (-1, -1), 0.5, _GRID_COLOR),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
]

TABLE_KEY_VALUE_STYLE = [
    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("BACKGROUND", (0, 0), (-1, 0), _BLUE_LIGHT),
    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [_ROW_ALT, colors.white]),
    ("GRID", (0, 0), (-1, -1), 0.5, _GRID_COLOR),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
]

SIGNATURE_TABLE_STYLE = [
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ("BOX", (0, 0), (0, -1), 0.5, colors.grey),
    ("BOX", (1, 0), (1, -1), 0.5, colors.grey),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]
