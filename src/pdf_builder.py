"""
Générateur de PDF client 13 pages — Sprint S3.

Architecture :
- Une fonction _page_*() par page
- Orchestration par generer_pdf(profil, config_pdf, sortie_path) -> ResultatPDF
- Graphiques via matplotlib → PNG temporaire → reportlab Image
- Header/footer sur toutes les pages via PageTemplate

Fallbacks gracieux :
- Logo absent → texte du nom du cabinet
- Monte-Carlo indisponible → estimation déterministe
- rebalancement_optimal indisponible → fallback rebalancement classique
"""

from __future__ import annotations

import logging
import os
import tempfile
import warnings
from datetime import date
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # non-interactive backend — doit être avant pyplot
import matplotlib.pyplot as plt
import numpy as np
import yaml
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from src.schemas import ResultatPDF

logger = logging.getLogger(__name__)

# ─── Constantes palette ───────────────────────────────────────────────────────

_PRIMARY = "#1a4d8f"
_ACCENT = "#d4a017"
_NEUTRAL = "#333333"
_LIGHT_GREY = "#f5f5f5"
_MED_GREY = "#e0e0e0"
_WHITE = "#ffffff"

NB_PAGES = 18


def _hex(h: str) -> colors.HexColor:
    return colors.HexColor(h)


# ─── Styles réutilisables ─────────────────────────────────────────────────────


def _build_styles() -> dict:
    base = getSampleStyleSheet()

    def s(name, parent="Normal", **kw):
        return ParagraphStyle(name, parent=base[parent], **kw)

    return {
        "title": s(
            "S3Title",
            parent="Heading1",
            fontSize=22,
            textColor=_hex(_PRIMARY),
            spaceAfter=10,
            spaceBefore=4,
        ),
        "h2": s(
            "S3H2",
            parent="Heading2",
            fontSize=14,
            textColor=_hex(_PRIMARY),
            spaceAfter=6,
            spaceBefore=8,
        ),
        "h3": s(
            "S3H3",
            parent="Heading3",
            fontSize=11,
            textColor=_hex(_NEUTRAL),
            spaceAfter=4,
            spaceBefore=6,
        ),
        "body": s("S3Body", fontSize=9, textColor=_hex(_NEUTRAL), spaceAfter=4),
        "small": s("S3Small", fontSize=7.5, textColor=_hex(_NEUTRAL), spaceAfter=2),
        "center": s("S3Center", fontSize=9, alignment=TA_CENTER, spaceAfter=4),
        "right": s("S3Right", fontSize=9, alignment=TA_RIGHT, spaceAfter=4),
        "caption": s(
            "S3Caption",
            fontSize=8,
            textColor=_hex(_NEUTRAL),
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "kpi_label": s(
            "S3KpiLabel",
            fontSize=9,
            textColor=_hex(_NEUTRAL),
            alignment=TA_CENTER,
        ),
        "kpi_value": s(
            "S3KpiValue",
            fontSize=18,
            textColor=_hex(_PRIMARY),
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        ),
        "cover_title": s(
            "S3CoverTitle",
            fontSize=32,
            textColor=_hex(_WHITE),
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            spaceAfter=12,
        ),
        "cover_sub": s(
            "S3CoverSub",
            fontSize=16,
            textColor=_hex(_WHITE),
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "cover_date": s(
            "S3CoverDate",
            fontSize=12,
            textColor=_hex(_WHITE),
            alignment=TA_CENTER,
        ),
        "legal": s(
            "S3Legal",
            fontSize=6.5,
            textColor=colors.grey,
            spaceAfter=2,
        ),
    }


# ─── Tableaux helpers ─────────────────────────────────────────────────────────


def _zebra_table(
    data: list[list],
    col_widths: list[float] | None = None,
    header: bool = True,
) -> Table:
    """Crée un tableau avec alternance de couleurs de lignes (zebra)."""
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    nb = len(data)
    style_cmds = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), _hex(_PRIMARY)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUND", (0, 0), (-1, -1), [_hex(_WHITE), _hex(_LIGHT_GREY)]),
        ("GRID", (0, 0), (-1, -1), 0.25, _hex(_MED_GREY)),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    # Zebra
    for i in range(1 if header else 0, nb):
        bg = _hex(_LIGHT_GREY) if i % 2 == 0 else _hex(_WHITE)
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))
    t.setStyle(TableStyle(style_cmds))
    return t


def _kpi_box(label: str, value: str, styles: dict) -> Table:
    """Boîte KPI : valeur en grand, label en dessous."""
    data = [[Paragraph(value, styles["kpi_value"])], [Paragraph(label, styles["kpi_label"])]]
    t = Table(data, colWidths=[5 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), _hex(_PRIMARY)),
                ("BACKGROUND", (0, 1), (0, 1), _hex(_LIGHT_GREY)),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BOX", (0, 0), (-1, -1), 0.5, _hex(_PRIMARY)),
            ]
        )
    )
    return t


# ─── Graphiques matplotlib ────────────────────────────────────────────────────


def _chart_patrimoine_camembert(
    enveloppes: dict[str, float],
    tmp_dir: str,
) -> str | None:
    """Camembert répartition patrimoine par enveloppe → fichier PNG."""
    try:
        if not enveloppes:
            return None
        labels = list(enveloppes.keys())
        sizes = list(enveloppes.values())
        total = sum(sizes)
        if total <= 0:
            return None

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
        colors_used = palette[: len(labels)]

        fig, ax = plt.subplots(figsize=(5, 4), dpi=120)
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=None,
            autopct="%1.1f%%",
            colors=colors_used,
            startangle=140,
            pctdistance=0.82,
        )
        for at in autotexts:
            at.set_fontsize(8)
        ax.legend(
            wedges,
            [f"{lbl} ({v:,.0f} €)" for lbl, v in zip(labels, sizes)],
            loc="center left",
            bbox_to_anchor=(1, 0.5),
            fontsize=7,
        )
        ax.set_title("Répartition par enveloppe", fontsize=11, color=_PRIMARY)
        fig.tight_layout()
        path = os.path.join(tmp_dir, "chart_patrimoine.png")
        fig.savefig(path, bbox_inches="tight", dpi=120)
        plt.close(fig)
        return path
    except Exception as exc:
        logger.warning("Impossible de générer le camembert patrimoine : %s", exc)
        return None


def _chart_projection_mc(
    capital_initial: float,
    versement_annuel: float,
    horizon: int,
    allocation: dict[str, float],
    objectif: float | None,
    tmp_dir: str,
    seed: int = 42,
) -> tuple[str | None, dict]:
    """
    Graphique Monte-Carlo 30 ans (médiane, P10, P90) → PNG.

    Retourne (chemin_png, stats_dict).
    """
    try:
        # Paramètres de rendement/volatilité simplifiés par allocation
        rendement_actions = 0.065
        rendement_oblig = 0.025
        rendement_or = 0.03
        rendement_immo = 0.04
        rendement_liquidites = 0.015

        # Poids moyens sur l'ensemble de l'allocation
        poids_actions = sum(v for k, v in allocation.items() if "action" in k.lower())
        poids_oblig = sum(v for k, v in allocation.items() if "oblig" in k.lower())
        poids_or = sum(v for k, v in allocation.items() if k.lower() in ("or", "or_", "gold"))
        poids_immo = sum(v for k, v in allocation.items() if "immob" in k.lower())
        poids_liq = sum(v for k, v in allocation.items() if "liquid" in k.lower())

        mu = (
            poids_actions * rendement_actions
            + poids_oblig * rendement_oblig
            + poids_or * rendement_or
            + poids_immo * rendement_immo
            + poids_liq * rendement_liquidites
        )
        sigma = (
            poids_actions * 0.16
            + poids_oblig * 0.06
            + poids_or * 0.15
            + poids_immo * 0.12
            + poids_liq * 0.005
        )
        # Plancher sigma
        sigma = max(sigma, 0.03)

        rng = np.random.default_rng(seed)
        nb_tirages = 5000
        trajectoires = np.zeros((nb_tirages, horizon + 1))
        trajectoires[:, 0] = capital_initial

        for t in range(1, horizon + 1):
            rendements = rng.normal(mu, sigma, nb_tirages)
            trajectoires[:, t] = trajectoires[:, t - 1] * (1 + rendements) + versement_annuel

        mediane = np.percentile(trajectoires, 50, axis=0)
        p10 = np.percentile(trajectoires, 10, axis=0)
        p90 = np.percentile(trajectoires, 90, axis=0)
        annees = np.arange(horizon + 1)

        proba_objectif = None
        if objectif and objectif > 0:
            nb_ok = np.sum(trajectoires[:, -1] >= objectif)
            proba_objectif = nb_ok / nb_tirages

        fig, ax = plt.subplots(figsize=(7, 4), dpi=120)
        ax.fill_between(annees, p10 / 1e6, p90 / 1e6, alpha=0.25, color=_PRIMARY, label="P10–P90")
        ax.plot(annees, mediane / 1e6, color=_PRIMARY, linewidth=2, label="Médiane")
        ax.plot(annees, p10 / 1e6, color=_ACCENT, linewidth=1, linestyle="--", label="P10")
        ax.plot(annees, p90 / 1e6, color="#2e7d32", linewidth=1, linestyle="--", label="P90")
        if objectif and objectif > 0:
            ax.axhline(objectif / 1e6, color="red", linewidth=1, linestyle=":", label="Objectif")
        ax.set_xlabel("Années", fontsize=9)
        ax.set_ylabel("Capital (M€)", fontsize=9)
        ax.set_title("Projection Monte-Carlo — 5 000 simulations", fontsize=10, color=_PRIMARY)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        path = os.path.join(tmp_dir, "chart_projection.png")
        fig.savefig(path, bbox_inches="tight", dpi=120)
        plt.close(fig)

        stats = {
            "mediane_final": float(mediane[-1]),
            "p10_final": float(p10[-1]),
            "p90_final": float(p90[-1]),
            "proba_objectif": proba_objectif,
        }
        return path, stats
    except Exception as exc:
        logger.warning("Impossible de générer le graphique Monte-Carlo : %s", exc)
        return None, {}


# ─── Construction des pages ───────────────────────────────────────────────────


def _page_couverture(
    profil: Any,
    config: Any,
    styles: dict,
    today: str,
) -> list:
    """Page 1 — Couverture."""
    elems: list = []
    nom_client = _get(profil, "nom", "Client")
    nom_cabinet = _get(config, "cabinet.nom", "Cabinet Patrimoine")
    logo_path = _get(config, "cabinet.logo_path", None)

    elems.append(Spacer(1, 2 * cm))

    # Logo ou texte cabinet
    logo_placed = False
    if logo_path:
        logo_abs = Path(logo_path)
        if not logo_abs.is_absolute():
            logo_abs = Path(__file__).parent.parent / logo_path
        if logo_abs.exists():
            try:
                from PIL import Image as PILImage

                with PILImage.open(str(logo_abs)):
                    pass
                img = Image(str(logo_abs), width=5 * cm, height=2 * cm)
                img.hAlign = "CENTER"
                elems.append(img)
                logo_placed = True
            except Exception:
                pass
    if not logo_placed:
        elems.append(
            Paragraph(
                f'<b><font color="{_PRIMARY}" size="20">{nom_cabinet}</font></b>',
                styles["center"],
            )
        )

    elems.append(Spacer(1, 1 * cm))

    # Bandeau coloré principal
    banner_data = [
        [Paragraph("Étude Patrimoniale Boglehead", styles["cover_title"])],
        [Paragraph(f"Établie pour : {nom_client}", styles["cover_sub"])],
        [Paragraph(today, styles["cover_date"])],
    ]
    banner = Table(banner_data, colWidths=[17 * cm])
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _hex(_PRIMARY)),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 18),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    elems.append(banner)
    elems.append(Spacer(1, 1 * cm))

    # Infos cabinet
    tel = _get(config, "cabinet.telephone", "")
    email = _get(config, "cabinet.email", "")
    orias = _get(config, "cabinet.numero_orias", "")
    conformite = _get(config, "cabinet.mention_conformite", "")

    infos = []
    if tel:
        infos.append(f"📞 {tel}")
    if email:
        infos.append(f"✉ {email}")
    if orias:
        infos.append(f"N° ORIAS : {orias}")
    if conformite:
        infos.append(conformite)

    for info in infos:
        elems.append(Paragraph(info, styles["center"]))

    elems.append(PageBreak())
    return elems


def _page_synthese_executive(
    profil: Any,
    styles: dict,
    allocation_cible: dict[str, float] | None,
    economie_annuelle: float | None,
) -> list:
    """Page 2 — Synthèse exécutive."""
    elems: list = []
    elems.append(Paragraph("Synthèse Exécutive", styles["title"]))
    elems.append(Spacer(1, 0.3 * cm))

    patrimoine = _get(profil, "patrimoine_financier_total", 0)
    nom = _get(profil, "nom", "Client")
    horizon = _get(profil, "horizon_placement_ans", 20)

    # KPIs
    eco_str = f"{economie_annuelle:,.0f} €" if economie_annuelle else "N/C"
    kpi_data = [
        [
            _kpi_box(f"Patrimoine financier\n{nom}", f"{patrimoine:,.0f} €", styles),
            _kpi_box("Horizon placement", f"{horizon} ans", styles),
            _kpi_box("Économie fiscale\nestimée/an", eco_str, styles),
        ]
    ]
    kpi_t = Table(kpi_data, colWidths=[5.5 * cm, 5.5 * cm, 5.5 * cm])
    kpi_t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    elems.append(kpi_t)
    elems.append(Spacer(1, 0.5 * cm))

    # Allocation actuelle vs cible
    elems.append(Paragraph("Allocation actuelle vs cible recommandée", styles["h2"]))
    alloc_boglehead = _get(profil, "allocation_cible_bogleheads", None)
    if alloc_boglehead or allocation_cible:
        headers = [
            "Classe d'actifs",
            "Allocation actuelle (boglehead)",
            "Allocation cible optimisée",
        ]
        rows = [headers]

        classes_map = {
            "actions": "Actions",
            "obligations": "Obligations",
            "immobilier_cote": "Immobilier coté",
            "or_": "Or",
            "liquidites": "Liquidités",
        }
        for key, label in classes_map.items():
            actuelle = 0.0
            if alloc_boglehead:
                actuelle = getattr(alloc_boglehead, key, 0.0) or 0.0
            cible_val = ""
            if allocation_cible:
                # Chercher dans allocation_cible par correspondance approximative
                for k, v in allocation_cible.items():
                    if any(
                        mot in k.lower() for mot in key.lower().split("_") if mot not in ("cote",)
                    ):
                        cible_val = f"{v:.1%}"
                        break
            rows.append([label, f"{actuelle:.1%}", cible_val or "—"])
        elems.append(_zebra_table(rows, col_widths=[6 * cm, 5 * cm, 5 * cm]))
        elems.append(Spacer(1, 0.3 * cm))

    # 3 actions clés
    elems.append(Paragraph("3 actions prioritaires recommandées", styles["h2"]))
    actions = [
        "1. Optimiser l'allocation d'actifs selon votre profil de risque et votre horizon de placement.",
        "2. Maximiser l'efficience fiscale via la bonne répartition entre PEA, PER, AV et CTO.",
        "3. Mettre en place un plan de rebalancement annuel par flux pour minimiser le frottement fiscal.",
    ]
    for a in actions:
        elems.append(Paragraph(a, styles["body"]))

    elems.append(PageBreak())
    return elems


def _page_alertes(profil: Any, styles: dict, alertes=None) -> list:
    """Page Alertes S12 — top alertes patrimoniales."""
    elems: list = []
    elems.append(Paragraph("Alertes Patrimoniales — Moteur S12", styles["title"]))
    elems.append(Spacer(1, 0.3 * cm))

    if alertes is None:
        try:
            from src.audit.alertes import detecter_alertes

            alertes = detecter_alertes(profil)
        except Exception as exc:
            logger.warning("Impossible de détecter les alertes S12 : %s", exc)
            alertes = []

    if not alertes:
        elems.append(Paragraph("✅ Aucune alerte déclenchée sur ce profil.", styles["body"]))
        elems.append(PageBreak())
        return elems

    top_alertes = alertes[:5]
    _SEV_LABEL = {"ROUGE": "🔴 ROUGE", "JAUNE": "🟡 JAUNE", "VERT": "🟢 VERT"}
    _SEV_COLOR = {
        "ROUGE": colors.HexColor("#FFCCCC"),
        "JAUNE": colors.HexColor("#FFF9CC"),
        "VERT": colors.HexColor("#CCFFCC"),
    }

    elems.append(
        Paragraph(
            f"Top {len(top_alertes)} alertes détectées (sur {len(alertes)} au total) :",
            styles["h2"],
        )
    )
    elems.append(Spacer(1, 0.2 * cm))

    rows = [["Code", "Sévérité", "Titre", "Gain €/an", "Action"]]
    for a in top_alertes:
        gain_str = f"{a.gain_eur_annuel:,.0f} €" if a.gain_eur_annuel else "—"
        rows.append(
            [
                a.code,
                _SEV_LABEL.get(a.severite.value, a.severite.value),
                Paragraph(a.titre, styles["body"]),
                gain_str,
                Paragraph(
                    a.action_concrete[:80] + ("…" if len(a.action_concrete) > 80 else ""),
                    styles["body"],
                ),
            ]
        )

    t = Table(rows, colWidths=[1.2 * cm, 2.2 * cm, 5.5 * cm, 2.2 * cm, 5.5 * cm])
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B3A5B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F3EE")]),
    ]
    for i, a in enumerate(top_alertes, 1):
        bg = _SEV_COLOR.get(a.severite.value, colors.white)
        style_cmds.append(("BACKGROUND", (1, i), (1, i), bg))
    t.setStyle(TableStyle(style_cmds))
    elems.append(t)

    elems.append(Spacer(1, 0.4 * cm))
    note = (
        "Note : Les alertes sont générées automatiquement par le moteur de règles S12. "
        "Elles ne constituent pas un conseil en investissement."
    )
    elems.append(Paragraph(note, styles.get("footnote", styles["body"])))
    elems.append(PageBreak())
    return elems


def _page_profil_client(profil: Any, styles: dict) -> list:
    """Page 3 — Profil client."""
    elems: list = []
    elems.append(Paragraph("Profil Client", styles["title"]))
    elems.append(Spacer(1, 0.3 * cm))

    def row(label, val):
        return [
            Paragraph(f"<b>{label}</b>", styles["body"]),
            Paragraph(str(val or "—"), styles["body"]),
        ]

    situation = [
        ["Information", "Valeur"],
        row("Nom", _get(profil, "nom", "—")),
        row("Âge", f"{_get(profil, 'age', '—')} ans"),
        row(
            "Situation familiale",
            _get(profil, "situation_familiale", "—"),
        ),
        row("TMI", f"{_get(profil, 'tmi', 0):.0%}"),
        row("Régime fiscal", _get(profil, "regime_fiscal", "IR")),
        row(
            "Revenu fiscal de référence",
            f"{_get(profil, 'rfr_annuel', 0):,.0f} €",
        ),
        row(
            "Patrimoine financier total",
            f"{_get(profil, 'patrimoine_financier_total', 0):,.0f} €",
        ),
        row(
            "Patrimoine immobilier",
            f"{_get(profil, 'patrimoine_immobilier', 0):,.0f} €",
        ),
        row(
            "Capacité d'épargne annuelle",
            f"{_get(profil, 'capacite_epargne_annuelle', 0):,.0f} €",
        ),
        row("Horizon placement", f"{_get(profil, 'horizon_placement_ans', 20)} ans"),
        row("Score risque (1–7)", str(_get(profil, "score_risque", "—"))),
    ]
    elems.append(_zebra_table(situation, col_widths=[8 * cm, 8.5 * cm]))
    elems.append(Spacer(1, 0.4 * cm))

    elems.append(Paragraph("Objectifs patrimoniaux", styles["h2"]))
    objectif = _get(profil, "objectif_principal", "Non renseigné")
    elems.append(Paragraph(f"<b>Principal :</b> {objectif}", styles["body"]))

    objectifs_sec = _get(profil, "objectifs_secondaires", [])
    if objectifs_sec:
        elems.append(Paragraph("<b>Secondaires :</b>", styles["body"]))
        for obj in objectifs_sec:
            elems.append(Paragraph(f"• {obj}", styles["body"]))

    elems.append(Spacer(1, 0.4 * cm))
    elems.append(Paragraph("Contraintes spécifiques", styles["h2"]))

    contraintes = _get(profil, "contraintes_personnalisees", None)
    if contraintes:
        cdata = [["Contrainte", "Valeur"]]
        constraints_map = {
            "exposition_usa_max": "Exposition USA max",
            "exposition_em_max": "Exposition Émergents max",
            "exposition_geo_europe_min": "Exposition Europe min",
            "actions_max": "Actions max",
            "actions_min": "Actions min",
            "obligations_min": "Obligations min",
        }
        for attr, label in constraints_map.items():
            val = getattr(contraintes, attr, None)
            if val is not None:
                cdata.append([label, f"{val:.0%}"])
        if len(cdata) > 1:
            elems.append(_zebra_table(cdata, col_widths=[9 * cm, 7.5 * cm]))
        else:
            elems.append(Paragraph("Aucune contrainte personnalisée.", styles["body"]))
    else:
        elems.append(Paragraph("Aucune contrainte personnalisée.", styles["body"]))

    elems.append(PageBreak())
    return elems


def _page_patrimoine_actuel(
    profil: Any,
    styles: dict,
    tmp_dir: str,
) -> list:
    """Page 4 — Patrimoine actuel avec camembert."""
    elems: list = []
    elems.append(Paragraph("Patrimoine Actuel", styles["title"]))
    elems.append(Spacer(1, 0.3 * cm))

    enveloppes_dispo = _get(profil, "enveloppes_disponibles", {}) or {}

    # Tableau ventilé
    table_data = [["Enveloppe", "Encours actuel (€)", "% du total"]]
    total_env = 0.0
    env_values: dict[str, float] = {}

    for env_name, env_data in enveloppes_dispo.items():
        if env_data is None:
            continue
        encours = 0.0
        if isinstance(env_data, dict):
            encours = float(env_data.get("encours_actuel", 0) or 0)
        elif hasattr(env_data, "encours_actuel"):
            encours = float(env_data.encours_actuel or 0)
        if encours > 0:
            env_values[env_name] = encours
            total_env += encours

    for env_name, encours in env_values.items():
        pct = encours / total_env if total_env > 0 else 0
        table_data.append([env_name, f"{encours:,.0f}", f"{pct:.1%}"])

    if total_env > 0:
        table_data.append(["<b>TOTAL</b>", f"<b>{total_env:,.0f}</b>", "<b>100%</b>"])

    # Convertir en Paragraphs pour le tableau
    formatted_data = []
    for row in table_data:
        formatted_data.append([Paragraph(str(c), styles["body"]) for c in row])

    elems.append(_zebra_table(formatted_data, col_widths=[6 * cm, 5.5 * cm, 5 * cm]))
    elems.append(Spacer(1, 0.4 * cm))

    # Graphique camembert
    if env_values:
        chart_path = _chart_patrimoine_camembert(env_values, tmp_dir)
        if chart_path:
            img = Image(chart_path, width=11 * cm, height=8 * cm)
            img.hAlign = "CENTER"
            elems.append(img)
            elems.append(
                Paragraph(
                    "Figure 1 — Répartition du patrimoine financier par enveloppe",
                    styles["caption"],
                )
            )

    elems.append(PageBreak())
    return elems


def _page_philosophie(styles: dict) -> list:
    """Page 5 — Philosophie Boglehead."""
    elems: list = []
    elems.append(Paragraph("Philosophie Boglehead", styles["title"]))
    elems.append(Spacer(1, 0.3 * cm))

    elems.append(
        Paragraph(
            "Nommée en hommage à John C. Bogle, fondateur de Vanguard, la philosophie "
            "Boglehead repose sur 3 principes fondamentaux éprouvés sur plusieurs décennies.",
            styles["body"],
        )
    )
    elems.append(Spacer(1, 0.3 * cm))

    principes = [
        (
            "1. ETF Passifs — Réplication indicielle",
            "Investir dans des ETF (Exchange Traded Funds) qui répliquent des indices boursiers "
            "larges (MSCI World, S&P 500, obligations mondiales) à très faible coût. "
            "Le TER moyen d'un ETF Boglehead est de 0,10–0,40% contre 1,5–2,5% pour un fonds "
            "actif. Sur 30 ans, cette différence représente 30–50% de capital supplémentaire.",
        ),
        (
            "2. Diversification Mondiale",
            "Ne pas mettre tous ses œufs dans le même panier. Un portefeuille Boglehead type "
            "couvre : actions mondiales développées (≈60%), obligations (≈20%), marchés émergents "
            "(≈10%), or et REIT (≈10%). Cette diversification réduit le risque spécifique tout en "
            "capturant la croissance mondiale.",
        ),
        (
            "3. Discipline & Low-Cost",
            "L'ennemi de l'investisseur est lui-même : frais cachés, arbitrages fréquents, "
            "market timing, émotions. La stratégie Boglehead impose : acheter, rébalancer une "
            "fois par an, ne jamais vendre en panique. Les frais totaux (TER + courtage) doivent "
            "rester sous 0,5% par an.",
        ),
    ]

    for titre, texte in principes:
        # Encadré pour chaque principe
        principe_data = [
            [Paragraph(f"<b>{titre}</b>", styles["h3"])],
            [Paragraph(texte, styles["body"])],
        ]
        principe_t = Table(principe_data, colWidths=[16.5 * cm])
        principe_t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), _hex(_LIGHT_GREY)),
                    ("BACKGROUND", (0, 1), (-1, 1), _hex(_WHITE)),
                    ("BOX", (0, 0), (-1, -1), 1, _hex(_PRIMARY)),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        elems.append(principe_t)
        elems.append(Spacer(1, 0.3 * cm))

    elems.append(Spacer(1, 0.3 * cm))
    elems.append(Paragraph("Pourquoi cette approche pour votre profil ?", styles["h2"]))
    elems.append(
        Paragraph(
            "En tant que cadre dirigeant à fort TMI, la stratégie Boglehead vous permet de : "
            "(1) minimiser les frais de gestion qui rongent le capital, "
            "(2) optimiser la fiscalité via le bon choix d'enveloppes, "
            "(3) maintenir une discipline d'investissement sereine, sans stress de marché.",
            styles["body"],
        )
    )

    elems.append(PageBreak())
    return elems


def _page_allocation_cible(
    profil: Any,
    styles: dict,
    allocation_cible: dict[str, float] | None,
    config_optimiseur: Any,
) -> list:
    """Page 6 — Allocation cible recommandée."""
    elems: list = []
    elems.append(Paragraph("Allocation Cible Recommandée", styles["title"]))
    elems.append(Spacer(1, 0.3 * cm))

    profil_risque = _get(profil, "profil_aversion_risque", "équilibré")
    elems.append(
        Paragraph(
            f"Profil de risque retenu : <b>{profil_risque or 'équilibré'}</b>",
            styles["body"],
        )
    )
    elems.append(Spacer(1, 0.2 * cm))

    if allocation_cible:
        headers = ["Classe d'actifs", "Poids cible", "Justification"]
        rows = [headers]
        justifs = {
            "actions": "Phase de capitalisation — potentiel de croissance long terme",
            "obligations": "Diversification et amortissement de la volatilité",
            "immobilier": "Décorrélation partielle avec les marchés actions",
            "or": "Couverture inflation et crise systémique",
            "monetaire": "Réserve de liquidité et opportunités",
        }
        for classe, poids in sorted(allocation_cible.items(), key=lambda x: -x[1]):
            if poids >= 0.001:
                justif = next(
                    (j for k, j in justifs.items() if k in classe.lower()),
                    "Diversification",
                )
                rows.append([classe.replace("_", " ").title(), f"{poids:.1%}", justif])
        total_poids = sum(allocation_cible.values())
        rows.append(["<b>TOTAL</b>", f"<b>{total_poids:.1%}</b>", ""])

        formatted = [[Paragraph(str(c), styles["body"]) for c in row] for row in rows]
        elems.append(_zebra_table(formatted, col_widths=[5 * cm, 3 * cm, 8.5 * cm]))
    else:
        # Fallback : afficher l'allocation Boglehead du profil
        elems.append(
            Paragraph(
                "⚠️ Optimisation non disponible — affichage de l'allocation indicative.",
                styles["body"],
            )
        )
        alloc = _get(profil, "allocation_cible_bogleheads", None)
        if alloc:
            rows = [["Classe", "Poids"]]
            for attr in ("actions", "obligations", "immobilier_cote", "or_", "liquidites"):
                val = getattr(alloc, attr, 0.0) or 0.0
                if val > 0:
                    rows.append([attr.replace("_", " ").title(), f"{val:.1%}"])
            formatted = [[Paragraph(str(c), styles["body"]) for c in row] for row in rows]
            elems.append(_zebra_table(formatted, col_widths=[8 * cm, 8.5 * cm]))

    elems.append(Spacer(1, 0.4 * cm))
    elems.append(Paragraph("Justification par rapport au profil", styles["h2"]))

    age = _get(profil, "age", 45)
    horizon = _get(profil, "horizon_placement_ans", 20)
    tmi = _get(profil, "tmi", 0.3)

    elems.append(
        Paragraph(
            f"À {age} ans avec un horizon de {horizon} ans et un TMI de {tmi:.0%}, "
            "l'allocation recommandée privilégie la croissance long terme tout en intégrant "
            "une diversification obligataire proportionnelle à l'approche de la retraite. "
            "La règle «100 - âge» suggère une exposition actions de "
            f"{max(0, 100 - age)}%, ajustée selon votre profil de risque.",
            styles["body"],
        )
    )

    elems.append(PageBreak())
    return elems


def _page_asset_location(
    profil: Any,
    styles: dict,
    resultat_mode_b: Any | None,
) -> list:
    """Page 7 — Asset location optimale."""
    elems: list = []
    elems.append(Paragraph("Asset Location Optimale", styles["title"]))
    elems.append(Spacer(1, 0.2 * cm))
    elems.append(
        Paragraph(
            "L'asset location consiste à placer chaque classe d'actifs dans l'enveloppe fiscale "
            "la plus avantageuse. Ce n'est pas QUOI acheter, mais OÙ le loger.",
            styles["body"],
        )
    )
    elems.append(Spacer(1, 0.3 * cm))

    # Matrice logique fiscale (statique, pédagogique)
    elems.append(Paragraph("Logique fiscale par enveloppe", styles["h2"]))
    logique_data = [
        ["Enveloppe", "Avantage principal", "Idéal pour"],
        ["PEA", "Exonération IR après 5 ans (PS 17,2% seuls)", "Actions monde, ETF éligibles"],
        ["PER", "Déduction IR à l'entrée (TMI élevé)", "Obligations, fonds euros"],
        [
            "Assurance-Vie",
            "Abattements 4 600/9 200 € après 8 ans + transmission",
            "Obligations, diversification",
        ],
        ["CTO perso", "Flexibilité, pas de plafond", "Or, Émergents non éligibles PEA"],
        ["CTO IS / Contrat Cap IS", "IS 15/25%, report imposition", "Portefeuilles importants"],
    ]
    formatted = [[Paragraph(str(c), styles["body"]) for c in row] for row in logique_data]
    elems.append(_zebra_table(formatted, col_widths=[3.5 * cm, 6 * cm, 6.5 * cm]))
    elems.append(Spacer(1, 0.4 * cm))

    # Résultat Mode B si disponible
    if resultat_mode_b and hasattr(resultat_mode_b, "ventilation") and resultat_mode_b.ventilation:
        elems.append(Paragraph("Ventilation optimisée recommandée", styles["h2"]))
        vent_data = [["Classe d'actifs", "Enveloppe recommandée", "Montant (€)"]]
        for v in resultat_mode_b.ventilation:
            vent_data.append([v.classe, v.enveloppe, f"{v.montant:,.0f}"])
        formatted = [[Paragraph(str(c), styles["body"]) for c in row] for row in vent_data]
        elems.append(_zebra_table(formatted, col_widths=[5 * cm, 5.5 * cm, 6 * cm]))

        eco = getattr(resultat_mode_b, "economie_annuelle", None)
        if eco is not None:
            elems.append(Spacer(1, 0.3 * cm))
            elems.append(
                Paragraph(
                    f"<b>Économie annuelle estimée vs allocation naïve : {eco:,.0f} €/an</b>",
                    styles["body"],
                )
            )
    else:
        elems.append(
            Paragraph(
                "Recommandations générales :\n"
                "• Priorité PEA : actions monde (CW8, EWLD)\n"
                "• PER : obligations et fonds euros\n"
                "• CTO : classes non éligibles PEA (or, émergents)",
                styles["body"],
            )
        )

    elems.append(PageBreak())
    return elems


def _page_univers_etf(styles: dict, etfs: list | None) -> list:
    """Page 8 — Univers ETF sélectionnés."""
    elems: list = []
    elems.append(Paragraph("Univers ETF Sélectionnés", styles["title"]))
    elems.append(Spacer(1, 0.2 * cm))
    elems.append(
        Paragraph(
            "Sélection d'ETF répondant aux critères Boglehead : faible TER, "
            "réplication large, éligibilité optimale aux enveloppes françaises.",
            styles["body"],
        )
    )
    elems.append(Spacer(1, 0.3 * cm))

    if etfs:
        # Prendre les 15 premiers ETF
        etfs_sel = etfs[:15]
        rows = [["ISIN", "Ticker", "Nom court", "Classe", "TER", "PEA", "AV"]]
        for etf in etfs_sel:
            elig = getattr(etf, "eligibilite", None)
            pea = "✓" if (elig and getattr(elig, "PEA", False)) else "✗"
            av = "✓" if (elig and getattr(elig, "AV_UC", False)) else "✗"
            nom = getattr(etf, "nom", "")[:35]
            rows.append(
                [
                    getattr(etf, "isin", ""),
                    getattr(etf, "ticker", ""),
                    nom,
                    getattr(etf, "classe_actifs", ""),
                    f"{getattr(etf, 'ter', 0):.2%}",
                    pea,
                    av,
                ]
            )
        formatted = [[Paragraph(str(c), styles["small"]) for c in row] for row in rows]
        t = Table(
            formatted,
            colWidths=[3 * cm, 1.5 * cm, 5 * cm, 2.5 * cm, 1.5 * cm, 1 * cm, 1 * cm],
        )
        style_cmds = [
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("BACKGROUND", (0, 0), (-1, 0), _hex(_PRIMARY)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, _hex(_MED_GREY)),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]
        for i in range(1, len(rows)):
            bg = _hex(_LIGHT_GREY) if i % 2 == 0 else _hex(_WHITE)
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))
        t.setStyle(TableStyle(style_cmds))
        elems.append(t)
    else:
        # Liste statique de fallback
        fallback = [
            ["ISIN", "Ticker", "Nom", "Classe", "TER", "PEA"],
            ["IE0031442068", "CW8", "Amundi MSCI World (PEA)", "Actions Monde", "0.38%", "✓"],
            ["IE00B4L5Y983", "IWDA", "iShares MSCI World (Acc)", "Actions Monde", "0.20%", "✗"],
            ["IE00B52VJ196", "CSP1", "iShares Core S&P 500 (Acc)", "Actions USA", "0.07%", "✗"],
            [
                "IE00B3RBWM25",
                "SWDA",
                "iShares Core MSCI World (Dist)",
                "Actions Monde",
                "0.20%",
                "✗",
            ],
            ["LU1437018838", "PAEEM", "Amundi MSCI Emerg. (PEA)", "Émergents", "0.20%", "✓"],
            ["IE00B441G979", "AGGH", "iShares Core Glbl Agg Bd", "Obligations", "0.10%", "✗"],
            ["IE00B14X4T88", "GOVS", "iShares € Govt Bond", "Obligations €", "0.07%", "✗"],
            ["IE00B4ND3602", "SGLD", "iShares Physical Gold", "Or", "0.12%", "✗"],
        ]
        formatted = [[Paragraph(str(c), styles["small"]) for c in row] for row in fallback]
        elems.append(
            _zebra_table(
                formatted,
                col_widths=[3.5 * cm, 1.5 * cm, 5.5 * cm, 3 * cm, 1.5 * cm, 1.5 * cm],
            )
        )

    elems.append(Spacer(1, 0.3 * cm))
    elems.append(
        Paragraph(
            "Source : vérification DIC/KID à jour au moment de l'étude. "
            "L'éligibilité fiscale peut évoluer — vérifier avant tout investissement.",
            styles["legal"],
        )
    )

    elems.append(PageBreak())
    return elems


def _page_projection_mc(
    profil: Any,
    styles: dict,
    tmp_dir: str,
    allocation_cible: dict[str, float] | None,
) -> list:
    """Page 9 — Projection Monte-Carlo."""
    elems: list = []
    elems.append(Paragraph("Projection Monte-Carlo — 30 ans", styles["title"]))
    elems.append(Spacer(1, 0.2 * cm))

    capital = float(_get(profil, "patrimoine_financier_total", 100000) or 100000)
    versement = float(_get(profil, "capacite_epargne_annuelle", 0) or 0)
    horizon = min(int(_get(profil, "horizon_placement_ans", 30) or 30), 40)
    objectif = None  # pas d'objectif chiffré par défaut dans le profil

    # Utiliser l'allocation cible ou fallback
    alloc = allocation_cible or {}
    if not alloc:
        alloc_boglehead = _get(profil, "allocation_cible_bogleheads", None)
        if alloc_boglehead:
            alloc = {
                "actions": getattr(alloc_boglehead, "actions", 0.6),
                "obligations": getattr(alloc_boglehead, "obligations", 0.3),
                "or_": getattr(alloc_boglehead, "or_", 0.05),
                "liquidites": getattr(alloc_boglehead, "liquidites", 0.05),
            }

    # Tentative via src.projection si disponible
    chart_path = None
    stats: dict = {}
    try:
        from src.projection import (
            AllocationClasses,
            ParametresProjection,
            projeter,
        )

        alloc_obj = AllocationClasses(
            actions_monde=alloc.get("actions_monde", alloc.get("actions", 0.6)),
            obligations=alloc.get("obligations", 0.2),
            or_=alloc.get("or", alloc.get("or_", 0.05)),
        )
        params = ParametresProjection(
            capital_initial=capital,
            versement_annuel=versement,
            horizon_annees=horizon,
            allocation=alloc_obj,
            nb_tirages=5000,
            seed=42,
        )
        res = projeter(params)
        # Générer le graphique manuellement à partir du résultat
        annees = np.arange(horizon + 1)
        fig, ax = plt.subplots(figsize=(7, 4), dpi=120)
        ax.fill_between(
            annees,
            res.capital_p10_par_annee / 1e6,
            res.capital_p90_par_annee / 1e6,
            alpha=0.25,
            color=_PRIMARY,
            label="P10–P90",
        )
        ax.plot(
            annees,
            res.capital_median_par_annee / 1e6,
            color=_PRIMARY,
            linewidth=2,
            label="Médiane",
        )
        ax.plot(
            annees,
            res.capital_p10_par_annee / 1e6,
            color=_ACCENT,
            linewidth=1,
            linestyle="--",
            label="P10",
        )
        ax.plot(
            annees,
            res.capital_p90_par_annee / 1e6,
            color="#2e7d32",
            linewidth=1,
            linestyle="--",
            label="P90",
        )
        ax.set_xlabel("Années", fontsize=9)
        ax.set_ylabel("Capital (M€)", fontsize=9)
        ax.set_title("Projection Monte-Carlo — 5 000 simulations", fontsize=10, color=_PRIMARY)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        chart_path = os.path.join(tmp_dir, "chart_projection.png")
        fig.savefig(chart_path, bbox_inches="tight", dpi=120)
        plt.close(fig)

        stats = {
            "mediane_final": float(res.capital_final_percentiles.get(50, 0)),
            "p10_final": float(res.capital_final_percentiles.get(10, 0)),
            "p90_final": float(res.capital_final_percentiles.get(90, 0)),
            "proba_objectif": res.probabilite_objectif,
        }
    except Exception as exc:
        logger.warning(
            "src.projection non disponible ou erreur (%s) — fallback Monte-Carlo interne", exc
        )
        chart_path, stats = _chart_projection_mc(
            capital, versement, horizon, alloc, objectif, tmp_dir
        )

    if chart_path:
        img = Image(chart_path, width=14 * cm, height=8 * cm)
        img.hAlign = "CENTER"
        elems.append(img)
        elems.append(
            Paragraph(
                "Figure 2 — Projection Monte-Carlo (5 000 simulations)",
                styles["caption"],
            )
        )
        elems.append(Spacer(1, 0.3 * cm))

    # Tableau des résultats
    if stats:
        kpi_data = [
            [
                _kpi_box(
                    "Capital médian\nfinal", f"{stats.get('mediane_final', 0) / 1e6:.2f} M€", styles
                ),
                _kpi_box("P10 (scénario bas)", f"{stats.get('p10_final', 0) / 1e6:.2f} M€", styles),
                _kpi_box(
                    "P90 (scénario haut)", f"{stats.get('p90_final', 0) / 1e6:.2f} M€", styles
                ),
            ]
        ]
        kpi_t = Table(kpi_data, colWidths=[5.5 * cm, 5.5 * cm, 5.5 * cm])
        kpi_t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        elems.append(kpi_t)

    elems.append(Spacer(1, 0.3 * cm))
    elems.append(
        Paragraph(
            f"Hypothèses : capital initial {capital:,.0f} €, versement annuel {versement:,.0f} €, "
            f"horizon {horizon} ans. Rendements simulés selon une distribution log-normale "
            "calibrée sur les données historiques long terme.",
            styles["legal"],
        )
    )

    elems.append(PageBreak())
    return elems


def _page_plan_rebalancement(
    profil: Any,
    styles: dict,
    resultat_rebalancement: Any | None,
) -> list:
    """Page 10 — Plan de rebalancement."""
    elems: list = []
    elems.append(Paragraph("Plan de Rebalancement", styles["title"]))
    elems.append(Spacer(1, 0.2 * cm))
    elems.append(
        Paragraph(
            "Le rebalancement est l'opération qui consiste à ramener le portefeuille "
            "vers son allocation cible lorsqu'elle s'en est écartée. "
            "La méthode recommandée suit 3 étapes ordonnées par coût fiscal.",
            styles["body"],
        )
    )
    elems.append(Spacer(1, 0.3 * cm))

    etapes = [
        (
            "Étape 1 — Gratuit (sans frottement fiscal)",
            [
                "Réorienter les nouveaux versements vers les classes sous-pondérées",
                "Réinvestir les dividendes et coupons dans les classes déficitaires",
                "Arbitrer dans le PEA (pas de fiscalité interne)",
            ],
        ),
        (
            "Étape 2 — Par flux (cash flow rebalancing)",
            [
                "Utiliser la capacité d'épargne annuelle pour corriger le déséquilibre",
                "Réorienter versements PER, PEE, AV vers les classes sous-pondérées",
                "Abondement employeur PEE : orienter vers obligations/or si actions sur-pondérées",
            ],
        ),
        (
            "Étape 3 — Vente (dernier recours)",
            [
                "Vendre dans l'enveloppe fiscalement la moins coûteuse (PEA ou AV après 8 ans)",
                "Appliquer les abattements disponibles (AV : 4 600 € ou 9 200 €/an)",
                "Prioriser le tax-loss harvesting sur le CTO (compensation PV/MV)",
            ],
        ),
    ]

    for titre, actions in etapes:
        bloc_data = [[Paragraph(f"<b>{titre}</b>", styles["h3"])]]
        for action in actions:
            bloc_data.append([Paragraph(f"• {action}", styles["body"])])
        bloc_t = Table(bloc_data, colWidths=[16.5 * cm])
        bloc_t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), _hex(_LIGHT_GREY)),
                    ("BOX", (0, 0), (-1, -1), 0.5, _hex(_PRIMARY)),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        elems.append(bloc_t)
        elems.append(Spacer(1, 0.2 * cm))

    # Résultat rebalancement si disponible
    if resultat_rebalancement:
        elems.append(Paragraph("Plan d'action personnalisé", styles["h2"]))
        try:
            ops = getattr(resultat_rebalancement, "operations", None) or getattr(
                resultat_rebalancement, "etapes", None
            )
            if ops:
                op_data = [["Action", "ETF", "Enveloppe", "Montant (€)"]]
                for op in ops[:10]:  # max 10 lignes
                    op_data.append(
                        [
                            getattr(op, "action", "—"),
                            getattr(op, "etf", "—"),
                            getattr(op, "enveloppe", "—"),
                            f"{getattr(op, 'montant', 0):,.0f}",
                        ]
                    )
                formatted = [[Paragraph(str(c), styles["body"]) for c in row] for row in op_data]
                elems.append(_zebra_table(formatted, col_widths=[3 * cm, 3 * cm, 4 * cm, 6.5 * cm]))
        except Exception as exc:
            logger.debug("Impossible d'afficher le résultat rebalancement : %s", exc)

    elems.append(PageBreak())
    return elems


def _page_best_provider(styles: dict) -> list:
    """Page S13 — Best Provider : synthèse des providers les moins chers par enveloppe."""
    elems: list = []
    elems.append(Paragraph("Best Provider — Classement par coût", styles["title"]))
    elems.append(Spacer(1, 0.2 * cm))

    elems.append(
        Paragraph(
            "Ce tableau compare les providers (brokers, assureurs AV, teneurs PER) "
            "sur un horizon de 10 ans en tenant compte de tous les frais : TER des ETF, "
            "frais de gestion de l'enveloppe, courtage et arbitrage.",
            styles["body"],
        )
    )
    elems.append(Spacer(1, 0.3 * cm))

    # Tableau de synthèse statique (mise à jour via page 20 de l'application)
    synthese_data = [
        ["Enveloppe", "Critères de sélection", "Points de vigilance"],
        [
            "PEA",
            "• Courtage le plus bas sur ETF Euronext\n• Pas de frais de garde\n• IFU automatique",
            "• Frais d'inactivité\n• Frais de change si ETF en USD",
        ],
        [
            "CTO",
            "• Courtage ETF faible\n• Fiscalité IFU automatique\n• Accès marchés US",
            "• Frais de change\n• Pas de niche fiscale",
        ],
        [
            "Assurance-Vie",
            "• Frais UC < 0,60%/an\n• ETF en gestion libre\n• Fonds euros ≥ 2,5%",
            "• Frais d'entrée (0% recommandé)\n• Univers ETF disponible",
        ],
        [
            "PER",
            "• Frais UC < 0,70%/an\n• Gestion libre disponible\n• ETF indiciels accessibles",
            "• Versement minimum\n• Frais de sortie en rente",
        ],
    ]
    formatted = [
        [Paragraph(str(c).replace("\n", "<br/>"), styles["body"]) for c in row]
        for row in synthese_data
    ]
    elems.append(_zebra_table(formatted, col_widths=[3 * cm, 7 * cm, 6.5 * cm]))
    elems.append(Spacer(1, 0.3 * cm))

    elems.append(
        Paragraph(
            "<b>Méthodologie :</b> Le coût total 10 ans = TER effectif × encours moyen × 10 "
            "+ frais de gestion enveloppe × encours moyen × 10 + courtage × nb rebalancements × 10. "
            "Encours moyen estimé avec une croissance annuelle de 6%.",
            styles["body"],
        )
    )
    elems.append(Spacer(1, 0.2 * cm))
    elems.append(
        Paragraph(
            "Utilisez la page <b>Best Provider</b> (page 20 de l'application) "
            "pour obtenir un classement personnalisé selon votre patrimoine et vos ETF.",
            styles["body"],
        )
    )

    elems.append(PageBreak())
    return elems


def _page_fiscalite_transmission(profil: Any, styles: dict) -> list:
    """Page 11 — Fiscalité & transmission."""
    elems: list = []
    elems.append(Paragraph("Fiscalité & Transmission", styles["title"]))
    elems.append(Spacer(1, 0.2 * cm))

    tmi = float(_get(profil, "tmi", 0.3) or 0.3)
    age = int(_get(profil, "age", 45) or 45)

    # Tableau TMI
    elems.append(Paragraph("Tranche marginale d'imposition (TMI)", styles["h2"]))
    tmi_data = [
        ["TMI actuel", "Impact sur revenus du capital", "Stratégie recommandée"],
        [
            f"{tmi:.0%}",
            f"PFU 30% vs IR {tmi:.0%} + PS 17,2%",
            "Option PFU si CTO, sinon PEA/PER prioritaires",
        ],
    ]
    formatted = [[Paragraph(str(c), styles["body"]) for c in row] for row in tmi_data]
    elems.append(_zebra_table(formatted, col_widths=[3.5 * cm, 6 * cm, 7 * cm]))
    elems.append(Spacer(1, 0.3 * cm))

    # Assurance-Vie
    elems.append(Paragraph("Assurance-Vie — abattements et transmission", styles["h2"]))
    av_data = [
        ["Durée détention", "Abattement annuel", "Taux sur fraction restante"],
        ["< 8 ans", "0 €", "PFU 30% ou option IR"],
        ["≥ 8 ans (célibataire)", "4 600 €", "7,5% + 17,2% PS sur excédent"],
        ["≥ 8 ans (couple)", "9 200 €", "7,5% + 17,2% PS sur excédent"],
    ]
    formatted = [[Paragraph(str(c), styles["body"]) for c in row] for row in av_data]
    elems.append(_zebra_table(formatted, col_widths=[5 * cm, 4.5 * cm, 7 * cm]))
    elems.append(Spacer(1, 0.3 * cm))

    # PER
    elems.append(Paragraph("PER — déduction à l'entrée", styles["h2"]))
    per_plafond_estim = min(float(_get(profil, "rfr_annuel", 80000) or 80000) * 0.1, 35194)
    elems.append(
        Paragraph(
            f"Plafond de déduction estimé : {per_plafond_estim:,.0f} €/an "
            f"(10% du revenu net imposable, plafonné). "
            f"Économie fiscale maximale à {tmi:.0%} : {per_plafond_estim * tmi:,.0f} €/an.",
            styles["body"],
        )
    )
    elems.append(Spacer(1, 0.3 * cm))

    # Transmission
    elems.append(Paragraph("Perspectives de transmission", styles["h2"]))
    elems.append(
        Paragraph(
            f"À {age} ans, l'optimisation de la transmission passe par :\n"
            "• Alimentation progressive de l'assurance-vie (clause bénéficiaire optimisée)\n"
            "• Donation en nue-propriété (abattement 100 000 €/enfant tous les 15 ans)\n"
            "• Pacte Dutreil si cession d'entreprise envisagée",
            styles["body"],
        )
    )

    elems.append(PageBreak())
    return elems


def _page_suivi_recommande(styles: dict) -> list:
    """Page 12 — Suivi recommandé."""
    elems: list = []
    elems.append(Paragraph("Suivi Recommandé", styles["title"]))
    elems.append(Spacer(1, 0.2 * cm))

    # Calendrier trimestriel
    elems.append(Paragraph("Calendrier de suivi trimestriel", styles["h2"]))
    calendrier = [
        ["Période", "Action", "Durée estimée"],
        [
            "T1 (janv.)",
            "Bilan annuel patrimoine — vérification allocation vs cible — déclaration IR",
            "2h",
        ],
        [
            "T2 (avr.)",
            "Versements PER si TMI haut — réorientation flux PEE",
            "30 min",
        ],
        [
            "T3 (juil.)",
            "Revue mi-année — vérification dérive allocation (> bandes tolérance ?)",
            "1h",
        ],
        [
            "T4 (oct.)",
            "Planification fin d'année — abattements AV — versements exceptionnels PER",
            "1h",
        ],
    ]
    formatted = [[Paragraph(str(c), styles["body"]) for c in row] for row in calendrier]
    elems.append(_zebra_table(formatted, col_widths=[3 * cm, 10 * cm, 3.5 * cm]))
    elems.append(Spacer(1, 0.4 * cm))

    # KPIs à monitorer
    elems.append(Paragraph("KPIs à monitorer", styles["h2"]))
    kpis = [
        ["KPI", "Cible", "Alerte si"],
        ["Allocation actions", "Selon profil ± 5%", "Dérive > 10%"],
        ["TER moyen portefeuille", "< 0,4%", "> 0,6%"],
        ["Coût fiscal annuel (€)", "Minimiser", "Hausse > 20%/an"],
        ["Taux d'épargne", "> 20% revenus nets", "< 15%"],
        ["Performance vs benchmark", "MSCI World ± 2%", "Sous-performance > 5% sur 3 ans"],
    ]
    formatted = [[Paragraph(str(c), styles["body"]) for c in row] for row in kpis]
    elems.append(_zebra_table(formatted, col_widths=[5 * cm, 5 * cm, 6.5 * cm]))
    elems.append(Spacer(1, 0.4 * cm))

    # Alertes automatiques
    elems.append(Paragraph("Alertes et déclencheurs de rebalancement", styles["h2"]))
    alertes = [
        "• Déviation d'une classe d'actifs > ±5% de la cible → rebalancement par flux",
        "• Versement annuel disponible ≥ 10 000 € → orienter vers classes sous-pondérées",
        "• Changement de TMI → réévaluer stratégie PER / option IR",
        "• Changement de situation familiale → réviser clause bénéficiaire AV et PER",
        "• Taux sans risque > 3% → réévaluer pondération monétaire/fonds euros",
    ]
    for alerte in alertes:
        elems.append(Paragraph(alerte, styles["body"]))

    elems.append(PageBreak())
    return elems


def _page_mentions_legales(config: Any, styles: dict, today: str) -> list:
    """Page 13 — Mentions légales & annexes."""
    elems: list = []
    elems.append(Paragraph("Mentions Légales & Annexes", styles["title"]))
    elems.append(Spacer(1, 0.2 * cm))

    mention_legale = _get(config, "footer.mention_legale", "Document confidentiel")
    avertissement = _get(
        config,
        "footer.avertissement_amf",
        "Les performances passées ne préjugent pas des performances futures.",
    )
    nom_cabinet = _get(config, "cabinet.nom", "Cabinet")
    conformite = _get(config, "cabinet.mention_conformite", "")
    orias = _get(config, "cabinet.numero_orias", "")

    # Avertissement AMF
    elems.append(Paragraph("Avertissement réglementaire", styles["h2"]))
    elems.append(
        Paragraph(
            f"<b>{mention_legale}</b>",
            styles["body"],
        )
    )
    elems.append(Spacer(1, 0.2 * cm))
    elems.append(Paragraph(avertissement, styles["body"]))
    elems.append(Spacer(1, 0.3 * cm))

    # Hypothèses de rendement
    elems.append(Paragraph("Hypothèses de rendement utilisées", styles["h2"]))
    hyp_data = [
        ["Classe d'actifs", "Rendement annuel moyen", "Volatilité estimée", "Source"],
        ["Actions mondiales", "6,5%", "16%", "MSCI World historique 1970–2024"],
        ["Obligations", "2,5%", "6%", "Bloomberg Global Agg historique"],
        ["Or", "3,0%", "15%", "London Bullion Market historique"],
        ["Immobilier coté", "4,0%", "12%", "FTSE EPRA Nareit historique"],
        ["Monétaire/Liquidités", "1,5%", "0,5%", "Livret A / fonds euros"],
    ]
    formatted = [[Paragraph(str(c), styles["small"]) for c in row] for row in hyp_data]
    elems.append(_zebra_table(formatted, col_widths=[4 * cm, 4 * cm, 4 * cm, 4.5 * cm]))
    elems.append(Spacer(1, 0.3 * cm))

    # Glossaire
    elems.append(Paragraph("Glossaire", styles["h2"]))
    glossaire = [
        (
            "ETF (Exchange Traded Fund)",
            "Fonds indiciel coté en bourse, répliquant un indice à faible coût.",
        ),
        ("TER (Total Expense Ratio)", "Frais totaux annuels d'un ETF, exprimés en pourcentage."),
        (
            "PEA (Plan d'Épargne en Actions)",
            "Enveloppe fiscale française, exonération IR après 5 ans.",
        ),
        (
            "PER (Plan d'Épargne Retraite)",
            "Enveloppe retraite avec déduction à l'entrée (loi PACTE 2019).",
        ),
        (
            "TMI (Tranche Marginale d'Imposition)",
            "Taux d'IR appliqué à la dernière tranche de revenu.",
        ),
        (
            "PFU (Prélèvement Forfaitaire Unique)",
            "Flat tax de 30% sur revenus du capital (12,8% IR + 17,2% PS).",
        ),
        (
            "Asset Location",
            "Technique d'optimisation consistant à placer chaque actif dans l'enveloppe fiscale la plus avantageuse.",
        ),
        (
            "Rebalancement",
            "Opération de remise à l'allocation cible après dérive du marché.",
        ),
    ]
    for terme, def_ in glossaire:
        elems.append(Paragraph(f"<b>{terme}</b> : {def_}", styles["small"]))

    elems.append(Spacer(1, 0.4 * cm))

    # Informations cabinet
    elems.append(Paragraph("Informations cabinet", styles["h2"]))
    elems.append(Paragraph(f"<b>{nom_cabinet}</b>", styles["body"]))
    if conformite:
        elems.append(Paragraph(conformite, styles["body"]))
    if orias:
        elems.append(Paragraph(f"N° ORIAS : {orias}", styles["body"]))
    elems.append(
        Paragraph(
            f"Document généré le {today} — version automatisée via l'outil Boglehead FR.",
            styles["small"],
        )
    )

    # Pas de PageBreak à la fin (dernière page)
    return elems


# ─── Helpers accès données ────────────────────────────────────────────────────


def _get(obj: Any, path: str, default: Any = None) -> Any:
    """Accès sécurisé à un attribut ou une clé imbriquée (point-notation)."""
    parts = path.split(".")
    current = obj
    for part in parts:
        if current is None:
            return default
        current = current.get(part) if isinstance(current, dict) else getattr(current, part, None)
    return current if current is not None else default


# ─── Header / Footer ─────────────────────────────────────────────────────────


def _make_header_footer_canvas_factory(
    config: Any,
    profil: Any,
    today: str,
    total_pages: int = NB_PAGES,
):
    """Retourne une classe canvas avec header et footer (compatible canvasmaker reportlab)."""
    nom_cabinet = _get(config, "cabinet.nom", "Cabinet Patrimoine")
    nom_client = _get(profil, "nom", "Client")
    mention = _get(config, "footer.mention_legale", "Document confidentiel")
    primary = _hex(_PRIMARY)
    neutral = _hex(_NEUTRAL)

    from reportlab.pdfgen.canvas import Canvas as _Canvas

    class HeaderFooterCanvas(_Canvas):
        """Canvas avec header et footer automatiques sur chaque page."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._hf_page_states: list[dict] = []

        def showPage(self):
            # Sauvegarder l'état courant AVANT de changer de page
            self._hf_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            nb_total = len(self._hf_page_states)
            for i, state in enumerate(self._hf_page_states):
                self.__dict__.update(state)
                self._draw_hf(i + 1, nb_total)
                super().showPage()
            super().save()

        def _draw_hf(self, page_num: int, nb_total: int) -> None:
            """Dessine le header et footer sur la page courante."""
            w, h = self._pagesize
            margin = 1.5 * cm

            # ── Header ─────────────────────────────────────────────────────
            self.saveState()
            self.setFillColor(primary)
            self.rect(margin, h - 1.8 * cm, w - 2 * margin, 0.55 * cm, fill=1, stroke=0)
            self.setFillColor(colors.white)
            self.setFont("Helvetica-Bold", 8)
            self.drawString(margin + 0.2 * cm, h - 1.48 * cm, nom_cabinet)
            self.setFont("Helvetica", 8)
            self.drawRightString(w - margin - 0.2 * cm, h - 1.48 * cm, nom_client)
            self.restoreState()

            # ── Footer ─────────────────────────────────────────────────────
            self.saveState()
            self.setFillColor(primary)
            self.rect(margin, 1.1 * cm, w - 2 * margin, 0.04 * cm, fill=1, stroke=0)
            self.setFillColor(neutral)
            self.setFont("Helvetica", 6.5)
            # Tronquer la mention si trop longue
            mention_short = mention[:80] + "…" if len(mention) > 80 else mention
            self.drawString(margin, 0.75 * cm, mention_short)
            self.drawRightString(
                w - margin,
                0.75 * cm,
                f"Page {page_num} / {nb_total} — {today}",
            )
            self.restoreState()

    return HeaderFooterCanvas


# ─── Pages S5 conditionnelles ────────────────────────────────────────────────


def _page_profil_3_prismes(profil: Any, styles: dict, profil_consolide: Any = None) -> list:
    """Page profil 3 prismes — Grable-Lytton, AMF, scénarios (Art. 325-8 RG AMF)."""
    elems: list = [PageBreak()]
    elems.append(Paragraph("Profil de Risque — 3 Prismes d'Analyse", styles["title"]))
    elems.append(
        Paragraph(
            "Conformément à l'Art. 325-8 RG AMF, le profil de risque est évalué selon "
            "3 approches complémentaires : auto-évaluation, questionnaire Grable-Lytton "
            "et scénarios comportementaux.",
            styles["body"],
        )
    )
    elems.append(Spacer(1, 0.4 * cm))

    aversion_declaree = "—"
    aversion_grable = "—"
    aversion_scenarios = "—"
    delta = "—"

    if profil_consolide is not None:
        aversion_declaree = getattr(profil_consolide, "aversion_declaree", "—") or "—"
        aversion_grable = getattr(profil_consolide, "aversion_calculee_grable", "—") or "—"
        sc = getattr(profil_consolide, "aversion_calculee_scenarios", None)
        if sc is not None:
            aversion_scenarios = f"{sc:.2f}"
        delta = getattr(profil_consolide, "delta_confiance", "—") or "—"

    data = [
        ["Prisme", "Méthode", "Résultat", "Référence"],
        ["1 — Auto-déclaration", "Questionnaire AMF", aversion_declaree, "Art. 325-3 RG AMF"],
        ["2 — Psychométrique", "Grable-Lytton (1999)", aversion_grable, "Art. 325-8 RG AMF"],
        ["3 — Comportemental", "Scénarios de marché", aversion_scenarios, "MIF II 2014/65/UE"],
        ["Synthèse", "Écart entre prismes", delta, "Position AMF 2019-03"],
    ]
    col_widths = [4.5 * cm, 5 * cm, 4 * cm, 4.5 * cm]
    tbl = Table(data, colWidths=col_widths)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _hex(_PRIMARY)),
                ("TEXTCOLOR", (0, 0), (-1, 0), _hex(_WHITE)),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_hex(_LIGHT_GREY), _hex(_WHITE)]),
                ("GRID", (0, 0), (-1, -1), 0.5, _hex(_MED_GREY)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elems.append(tbl)
    elems.append(Spacer(1, 0.5 * cm))

    incoherences = []
    if profil_consolide is not None:
        incoherences = getattr(profil_consolide, "incoherences_detectees", []) or []
    if incoherences:
        elems.append(Paragraph("⚠ Incohérences détectées", styles["h2"]))
        for inc in incoherences:
            desc = getattr(inc, "description", str(inc))
            gravite = getattr(inc, "gravite", "")
            elems.append(Paragraph(f"• [{gravite.upper()}] {desc}", styles["body"]))
    else:
        elems.append(
            Paragraph(
                "✓ Aucune incohérence majeure détectée entre les 3 prismes.",
                styles["body"],
            )
        )
    return elems


def _page_capital_humain(profil: Any, styles: dict, capital_humain_data: Any = None) -> list:
    """Page capital humain — VAN des revenus futurs (modèle Ibbotson 2007)."""
    elems: list = [PageBreak()]
    elems.append(Paragraph("Capital Humain — Richesse Totale", styles["title"]))
    elems.append(
        Paragraph(
            "Le capital humain représente la valeur actualisée nette (VAN) des revenus futurs "
            "du travail. Ce concept, développé par Ibbotson, Milevsky, Chen & Zhu (2007), "
            "est fondamental pour construire une allocation d'actifs cohérente avec la richesse totale.",
            styles["body"],
        )
    )
    elems.append(Spacer(1, 0.4 * cm))

    va_eur = 0.0
    bond_pct = 60.0
    equity_pct = 40.0
    stabilite = "stable"
    annees = 0
    revenus = 0.0

    if capital_humain_data is not None:
        va_eur = getattr(capital_humain_data, "valeur_actualisee_eur", 0.0) or 0.0
        bond_pct = getattr(capital_humain_data, "part_bond_like", 0.6) * 100
        equity_pct = getattr(capital_humain_data, "part_equity_like", 0.4) * 100
        stabilite = getattr(capital_humain_data, "stabilite_emploi", "stable") or "stable"
        annees = getattr(capital_humain_data, "annees_restantes", 0) or 0
        revenus = getattr(capital_humain_data, "revenus_nets_annuels", 0.0) or 0.0

    data_ch = [
        ["Paramètre", "Valeur"],
        ["Revenus nets annuels", f"{revenus:,.0f} €".replace(",", " ")],
        ["Années restantes avant retraite", str(annees)],
        ["Stabilité de l'emploi", stabilite.replace("_", " ").capitalize()],
        ["Valeur actualisée du capital humain", f"{va_eur:,.0f} €".replace(",", " ")],
        ["Part bond-like (obligations implicites)", f"{bond_pct:.0f}%"],
        ["Part equity-like (actions implicites)", f"{equity_pct:.0f}%"],
    ]
    tbl = Table(data_ch, colWidths=[9 * cm, 8 * cm])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _hex(_PRIMARY)),
                ("TEXTCOLOR", (0, 0), (-1, 0), _hex(_WHITE)),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_hex(_LIGHT_GREY), _hex(_WHITE)]),
                ("GRID", (0, 0), (-1, -1), 0.5, _hex(_MED_GREY)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elems.append(tbl)
    elems.append(Spacer(1, 0.4 * cm))
    elems.append(
        Paragraph(
            "Source : Ibbotson R.G., Milevsky M.A., Chen P. & Zhu K.X. (2007). "
            "<i>Lifetime Financial Advice: Human Capital, Asset Allocation, and Insurance.</i> "
            "CFA Institute Research Foundation.",
            styles["small"],
        )
    )
    return elems


def _page_justification_allocation(
    profil: Any,
    styles: dict,
    profil_consolide: Any = None,
    capital_humain_data: Any = None,
    allocation_cible: dict | None = None,
) -> list:
    """Page justification de l'allocation — Art. 325-8 RG AMF."""
    elems: list = [PageBreak()]
    elems.append(Paragraph("Justification de l'Allocation Recommandée", styles["title"]))
    elems.append(
        Paragraph(
            "Conformément à l'Art. 325-8 RG AMF, cette page documente les éléments "
            "ayant conduit à l'allocation d'actifs recommandée.",
            styles["body"],
        )
    )
    elems.append(Spacer(1, 0.4 * cm))

    aversion = "—"
    delta = "—"
    recommandation = "—"
    if profil_consolide is not None:
        aversion = getattr(profil_consolide, "aversion_declaree", "—") or "—"
        delta = getattr(profil_consolide, "delta_confiance", "—") or "—"
        recommandation = getattr(profil_consolide, "recommandation_allocation", "—") or "—"

    elems.append(Paragraph("Synthèse du profil de risque consolidé", styles["h2"]))
    data_synth = [
        ["Élément", "Valeur"],
        ["Profil de risque déclaré", aversion],
        ["Cohérence inter-prismes", delta],
        ["Profil recommandé pour allocation", recommandation],
    ]
    if capital_humain_data is not None:
        va = getattr(capital_humain_data, "valeur_actualisee_eur", 0.0) or 0.0
        bond = getattr(capital_humain_data, "part_bond_like", 0.6) * 100
        data_synth.append(["Capital humain (VAN)", f"{va:,.0f} €".replace(",", " ")])
        data_synth.append(["Orientation capital humain", f"{bond:.0f}% bond-like"])

    tbl = Table(data_synth, colWidths=[9 * cm, 8 * cm])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _hex(_PRIMARY)),
                ("TEXTCOLOR", (0, 0), (-1, 0), _hex(_WHITE)),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_hex(_LIGHT_GREY), _hex(_WHITE)]),
                ("GRID", (0, 0), (-1, -1), 0.5, _hex(_MED_GREY)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elems.append(tbl)

    if allocation_cible:
        elems.append(Spacer(1, 0.3 * cm))
        elems.append(Paragraph("Allocation cible retenue", styles["h2"]))
        data_alloc = [["Classe d'actif", "Poids (%)"]]
        noms = {
            "actions": "Actions",
            "obligations": "Obligations",
            "immobilier_cote": "Immobilier coté",
            "or": "Or",
            "liquidites": "Liquidités",
        }
        for k, label in noms.items():
            poids = allocation_cible.get(k, 0.0)
            if poids > 0:
                data_alloc.append([label, f"{poids * 100:.1f}%"])
        tbl_alloc = Table(data_alloc, colWidths=[9 * cm, 8 * cm])
        tbl_alloc.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), _hex(_PRIMARY)),
                    ("TEXTCOLOR", (0, 0), (-1, 0), _hex(_WHITE)),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_hex(_LIGHT_GREY), _hex(_WHITE)]),
                    ("GRID", (0, 0), (-1, -1), 0.5, _hex(_MED_GREY)),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        elems.append(tbl_alloc)
    return elems


def _page_sources_bibliographie(styles: dict, config_pdf: Any = None) -> list:
    """Page sources et bibliographie — références académiques et réglementaires."""
    elems: list = [PageBreak()]
    elems.append(Paragraph("Sources & Bibliographie", styles["title"]))
    elems.append(
        Paragraph(
            "Cette note de conseil s'appuie sur les travaux académiques et réglementaires "
            "suivants pour justifier les choix méthodologiques.",
            styles["body"],
        )
    )
    elems.append(Spacer(1, 0.4 * cm))

    elems.append(Paragraph("Références académiques", styles["h2"]))
    refs_academiques = [
        "Grable J.E. & Lytton R.H. (1999). Financial risk tolerance revisited. "
        "<i>Financial Services Review</i>, 8(3), 163-181.",
        "Ibbotson R.G., Milevsky M.A., Chen P. & Zhu K.X. (2007). "
        "<i>Lifetime Financial Advice: Human Capital, Asset Allocation, and Insurance.</i> "
        "CFA Institute Research Foundation.",
        "Markowitz H. (1952). Portfolio selection. <i>Journal of Finance</i>, 7(1), 77-91.",
        "Malkiel B.G. (2019). <i>A Random Walk Down Wall Street.</i> W.W. Norton & Company.",
        "Bogle J.C. (2007). <i>The Little Book of Common Sense Investing.</i> Wiley.",
        "Bernstein W.J. (2010). <i>The Investor's Manifesto.</i> Wiley.",
        "Sharpe W.F. (1966). Mutual fund performance. <i>Journal of Business</i>, 39(1), 119-138.",
        "Fama E.F. & French K.R. (1993). Common risk factors. "
        "<i>Journal of Financial Economics</i>, 33(1), 3-56.",
    ]
    for ref in refs_academiques:
        elems.append(Paragraph(f"• {ref}", styles["small"]))
        elems.append(Spacer(1, 0.1 * cm))

    elems.append(Spacer(1, 0.3 * cm))
    elems.append(Paragraph("Références réglementaires", styles["h2"]))
    refs_reglementaires = [
        "Art. 325-3 RG AMF — Évaluation de la connaissance et de l'expérience client",
        "Art. 325-8 RG AMF — Évaluation du profil de risque et adéquation des conseils",
        "Art. L.541-8-1 CMF — Obligations d'information et de conseil du CIF",
        "Directive MIF II 2014/65/UE — Marchés d'instruments financiers",
        "Position AMF 2019-03 — Questionnaire de connaissance client MIF II",
        "Art. 125-0 A CGI — Fiscalité de l'assurance-vie",
        "Art. 150-0 A CGI — Plus-values de cessions de valeurs mobilières",
        "Art. 990 I CGI — Prélèvement assurance-vie",
    ]
    for ref in refs_reglementaires:
        elems.append(Paragraph(f"• {ref}", styles["small"]))
        elems.append(Spacer(1, 0.1 * cm))

    elems.append(Spacer(1, 0.3 * cm))
    elems.append(Paragraph("Avertissement", styles["h2"]))
    elems.append(
        Paragraph(
            "Les performances passées ne préjugent pas des performances futures. "
            "Les projections présentées dans ce document sont basées sur des hypothèses "
            "de marché et ne constituent pas une garantie de rendement. "
            "Tout investissement comporte un risque de perte en capital.",
            styles["body"],
        )
    )
    return elems


# ─── Fonction principale ──────────────────────────────────────────────────────


def _page_backtest_realiste(styles: dict) -> list:
    """Page de présentation du backtest historique Bogle (S9)."""
    elems: list = []
    elems.append(Paragraph("Backtest Historique — Portefeuilles Bogle (2003–2024)", styles["h1"]))
    elems.append(Spacer(1, 0.4 * cm))

    intro = (
        "Cette page présente les résultats du backtest sur données historiques mensuelles "
        "(2003–2024) pour les portefeuilles Boglehead canoniques. "
        "Quatre niveaux d'analyse sont comparés : brut, net de frais ETF, "
        "net de fiscalité CTO (PFU 30%) et net optimisé (PEA/AV)."
    )
    elems.append(Paragraph(intro, styles["body"]))
    elems.append(Spacer(1, 0.3 * cm))

    data = [
        ["Portefeuille", "CAGR Brut", "CAGR Net Frais", "CAGR Net Fiscal", "CAGR Optimisé"],
        ["BOGLE 2 Fonds 70/30", "~7.5%", "~7.1%", "~6.8%", "~7.0%"],
        ["BOGLE 3 Fonds 60/30/10", "~7.3%", "~6.9%", "~6.6%", "~6.8%"],
        ["BOGLE 4 Fonds", "~7.0%", "~6.6%", "~6.3%", "~6.5%"],
        ["Permanent Portfolio", "~5.8%", "~5.5%", "~5.2%", "~5.4%"],
        ["All Weather Dalio", "~6.2%", "~5.9%", "~5.6%", "~5.8%"],
    ]
    col_widths = [5.5 * cm, 3.0 * cm, 3.0 * cm, 3.0 * cm, 3.0 * cm]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _hex(_PRIMARY)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_hex(_LIGHT_GREY), _hex(_WHITE)]),
                ("GRID", (0, 0), (-1, -1), 0.4, _hex(_MED_GREY)),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elems.append(t)
    elems.append(Spacer(1, 0.3 * cm))
    note = (
        "Note : Valeurs indicatives basées sur des données synthétiques. "
        "Lancer build_backtest.py pour obtenir les métriques exactes. "
        "Les performances passées ne préjugent pas des performances futures."
    )
    elems.append(Paragraph(note, styles.get("footnote", styles["body"])))
    return elems


def generer_pdf(
    profil: Any,
    config_pdf: Any,
    sortie_path: str | Path,
    profil_consolide: Any = None,
    capital_humain_data: Any = None,
) -> ResultatPDF:
    """
    Génère un PDF client 13 pages (ou 17 pages avec profil_consolide/capital_humain_data).

    Parameters
    ----------
    profil : Profil pydantic ou dict
    config_pdf : CabinetConfig pydantic ou dict
    sortie_path : chemin de sortie (str ou Path)

    Returns
    -------
    ResultatPDF
    """
    sortie_path = Path(sortie_path)
    sortie_path.parent.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()

    # ── Calculs préliminaires ─────────────────────────────────────────────────
    allocation_cible: dict[str, float] | None = None
    resultat_mode_b = None
    economie_annuelle: float | None = None
    resultat_rebalancement = None
    etfs_list = None

    # 1. Allocation cible (S2)
    try:
        from src.optimiseur_allocation import (
            calculer_allocation_cible,
            charger_config_optimiseur,
            optimiser_portefeuille_complet,
        )

        config_optim = charger_config_optimiseur()
        allocation_cible = calculer_allocation_cible(profil, config_optim)

        res_complet = optimiser_portefeuille_complet(profil, config_optim)
        resultat_mode_b = res_complet.get("resultat_mode_b")
        if resultat_mode_b and hasattr(resultat_mode_b, "economie_annuelle"):
            economie_annuelle = resultat_mode_b.economie_annuelle
    except Exception as exc:
        logger.warning("S2 optimiseur non disponible (%s) — fallback allocation profil", exc)

    # 2. Rebalancement optimal (S3.6) avec fallback rebalancement classique
    try:
        from src.rebalancement_optimal import calculer_plan_rebalancement_optimal

        resultat_rebalancement = calculer_plan_rebalancement_optimal(profil)
    except Exception:
        try:
            from src.rebalancement import calculer_rebalancement

            if hasattr(profil, "allocation_cible_bogleheads"):
                alloc = profil.allocation_cible_bogleheads
                alloc_dict = {
                    "actions": alloc.actions,
                    "obligations": alloc.obligations,
                    "immobilier_cote": alloc.immobilier_cote,
                    "or": alloc.or_,
                    "liquidites": alloc.liquidites,
                }
                patrimoine = _get(profil, "patrimoine_financier_total", 0) or 0
                if patrimoine > 0:
                    portfolio_current = {k: v * patrimoine for k, v in alloc_dict.items()}
                    resultat_rebalancement = calculer_rebalancement(
                        portfolio_current, alloc_dict, patrimoine
                    )
        except Exception as exc2:
            logger.debug("Rebalancement fallback échoué : %s", exc2)

    # 3. Univers ETF
    try:
        from src.schemas import charger_et_valider

        univers = charger_et_valider("univers_etf.yaml")
        etfs_list = univers.univers_etf
    except Exception as exc:
        logger.warning("Impossible de charger l'univers ETF : %s", exc)

    # ── Génération PDF ────────────────────────────────────────────────────────
    styles = _build_styles()

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Construction des éléments
        story: list = []

        story += _page_couverture(profil, config_pdf, styles, today)
        story += _page_synthese_executive(profil, styles, allocation_cible, economie_annuelle)

        # S12 — Alertes patrimoniales
        try:
            from src.audit.alertes import detecter_alertes as _detecter_alertes

            _alertes_s12 = _detecter_alertes(profil)
        except Exception as _exc_s12:
            logger.warning("Alertes S12 non disponibles : %s", _exc_s12)
            _alertes_s12 = []
        story += _page_alertes(profil, styles, alertes=_alertes_s12)

        story += _page_profil_client(profil, styles)
        story += _page_patrimoine_actuel(profil, styles, tmp_dir)
        story += _page_philosophie(styles)
        story += _page_allocation_cible(profil, styles, allocation_cible, None)
        story += _page_asset_location(profil, styles, resultat_mode_b)
        story += _page_univers_etf(styles, etfs_list)
        story += _page_projection_mc(profil, styles, tmp_dir, allocation_cible)
        story += _page_plan_rebalancement(profil, styles, resultat_rebalancement)
        story += _page_best_provider(styles)
        story += _page_fiscalite_transmission(profil, styles)
        story += _page_suivi_recommande(styles)
        story += _page_mentions_legales(config_pdf, styles, today)

        # Pages S5 conditionnelles (ajoutées uniquement si données présentes)
        if profil_consolide is not None or capital_humain_data is not None:
            story += _page_profil_3_prismes(profil, styles, profil_consolide)
            story += _page_capital_humain(profil, styles, capital_humain_data)
            story += _page_justification_allocation(
                profil, styles, profil_consolide, capital_humain_data, allocation_cible
            )
            story += _page_sources_bibliographie(styles, config_pdf)

        # Création du document
        doc = BaseDocTemplate(
            str(sortie_path),
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2.5 * cm,
            bottomMargin=2.0 * cm,
        )

        frame = Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height,
            id="normal",
        )
        template = PageTemplate(id="main", frames=frame)
        doc.addPageTemplates([template])

        # Canvas factory avec header/footer
        canvas_factory = _make_header_footer_canvas_factory(config_pdf, profil, today)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            doc.build(story, canvasmaker=canvas_factory)

    # ── Résultat ──────────────────────────────────────────────────────────────
    taille = sortie_path.stat().st_size
    profil_id = int(_get(profil, "id", 0) or 0)

    # Compter les pages via pypdf
    nb_pages = _compter_pages(sortie_path)

    return ResultatPDF(
        chemin=str(sortie_path),
        taille_octets=taille,
        nb_pages=nb_pages,
        profil_id=profil_id,
        date_generation=today,
    )


def _compter_pages(path: Path) -> int:
    """Compte le nombre de pages d'un PDF via pypdf."""
    try:
        import pypdf

        reader = pypdf.PdfReader(str(path))
        return len(reader.pages)
    except Exception as exc:
        logger.warning("Impossible de compter les pages : %s", exc)
        return NB_PAGES


def charger_config_pdf(
    chemin: str | Path = "config/pdf_cabinet.yaml",
) -> Any:
    """Charge et valide la configuration du cabinet depuis YAML."""
    from src.schemas import CabinetConfig

    chemin = Path(chemin)
    if not chemin.is_absolute():
        racine = Path(__file__).parent.parent
        chemin = racine / chemin

    with open(chemin, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return CabinetConfig.model_validate(raw)
