from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    parts = key.split(".")
    for part in parts:
        if obj is None:
            return default
        if isinstance(obj, dict):
            obj = obj.get(part)
        else:
            obj = getattr(obj, part, None)
    return obj if obj is not None else default


def generer_lettre_mission(
    config_cabinet: Any,
    client_info: dict,
    sortie_path: str | Path,
) -> Path:
    """
    Génère la Lettre de Mission CIF.

    Conforme à l'Art. L.541-8-1 CMF — Contrat formalisant la relation
    conseiller / client.

    Parameters
    ----------
    config_cabinet : dict ou objet avec les infos du cabinet
    client_info : dict avec nom, prenom, adresse, etc.
    sortie_path : chemin de sortie PDF

    Returns
    -------
    Path du PDF généré
    """
    sortie_path = Path(sortie_path)
    sortie_path.parent.mkdir(parents=True, exist_ok=True)
    today = date.today().strftime("%d/%m/%Y")

    base = getSampleStyleSheet()
    primary = colors.HexColor("#1a4d8f")
    neutral = colors.HexColor("#333333")

    def s(name: str, parent: str = "Normal", **kw: Any) -> ParagraphStyle:
        return ParagraphStyle(name, parent=base[parent], **kw)

    styles = {
        "title": s("LmTitle", parent="Heading1", fontSize=18, textColor=primary, spaceAfter=10),
        "h2": s("LmH2", parent="Heading2", fontSize=12, textColor=primary, spaceAfter=6),
        "body": s("LmBody", fontSize=10, leading=14, textColor=neutral),
        "small": s("LmSmall", fontSize=8, leading=11, textColor=neutral),
        "bold": s("LmBold", fontSize=10, leading=14, fontName="Helvetica-Bold"),
    }

    nom_cabinet = _get(config_cabinet, "cabinet.nom", "[Cabinet]")
    prenom_ec = _get(config_cabinet, "cabinet.prenom_ec", "")
    nom_ec = _get(config_cabinet, "cabinet.nom_ec", "[Conseiller]")
    adresse_cabinet = _get(config_cabinet, "cabinet.adresse", "[Adresse]")
    email_cabinet = _get(config_cabinet, "cabinet.email", "[Email]")
    orias = _get(config_cabinet, "cabinet.numero_orias", "[N° ORIAS]")
    mode_remun = _get(config_cabinet, "remuneration.mode", "honoraires")
    forfait_init = _get(config_cabinet, "tarifs.mission_initiale_forfait_eur", 3000)
    suivi_annuel = _get(config_cabinet, "tarifs.suivi_annuel_forfait_eur", 1200)
    taux_horaire = _get(config_cabinet, "tarifs.taux_horaire_eur", 250)
    mention_retro = _get(
        config_cabinet,
        "remuneration.mention_retrocessions",
        "Aucune rétrocession perçue (Art. L.541-8-1 CMF)",
    )

    client_nom = client_info.get("nom", "[Nom client]")
    client_prenom = client_info.get("prenom", "")
    client_adresse = client_info.get("adresse", "[Adresse client]")

    story: list = []

    # ── Page 1 — Parties et objet ──────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("LETTRE DE MISSION", styles["title"]))
    story.append(
        Paragraph(
            f"Établie le {today} — Conforme à l'Art. L.541-8-1 CMF",
            styles["small"],
        )
    )
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("1. Identification des parties", styles["h2"]))
    data_parties = [
        ["", "Le Conseiller", "Le Client"],
        ["Nom / Dénomination", f"{nom_cabinet}", f"{client_prenom} {client_nom}"],
        ["Adresse", adresse_cabinet, client_adresse],
        ["Représentant", f"{prenom_ec} {nom_ec}", "Le soussigné"],
        ["N° ORIAS", orias, "—"],
        ["Contact", email_cabinet, client_info.get("email", "—")],
    ]
    tbl = Table(data_parties, colWidths=[4.5 * cm, 7 * cm, 5.5 * cm])
    tbl.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0fb")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9f9f9")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(tbl)
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("2. Objet de la mission", styles["h2"]))
    story.append(
        Paragraph(
            "La présente lettre de mission définit les conditions dans lesquelles le Conseiller "
            "en Investissements Financiers (CIF) fournit ses services au Client dans le cadre "
            "des dispositions de l'Art. L.541-8-1 du Code Monétaire et Financier.",
            styles["body"],
        )
    )
    story.append(Spacer(1, 0.2 * cm))
    prestations = [
        "Analyse patrimoniale complète (actif, passif, fiscal)",
        "Élaboration d'une stratégie d'allocation d'actifs personnalisée",
        "Recommandations d'instruments financiers adaptés au profil client",
        "Suivi annuel du portefeuille et recommandations de rebalancement",
        "Optimisation fiscale multi-enveloppes (PEA, AV, CTO, PER)",
        "Accompagnement sur la stratégie de transmission patrimoniale",
    ]
    for p in prestations:
        story.append(Paragraph(f"• {p}", styles["body"]))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("3. Rémunération et honoraires", styles["h2"]))
    story.append(
        Paragraph(
            f"Mode de rémunération : <b>{mode_remun.upper()}</b>",
            styles["body"],
        )
    )
    story.append(Paragraph(mention_retro, styles["body"]))
    story.append(Spacer(1, 0.2 * cm))
    data_tarifs = [
        ["Prestation", "Tarif"],
        ["Mission initiale (bilan + stratégie)", f"{forfait_init:,} € HT".replace(",", " ")],
        ["Suivi annuel", f"{suivi_annuel:,} € HT / an".replace(",", " ")],
        ["Conseil ponctuel", f"{taux_horaire} € HT / heure"],
    ]
    tbl_tarifs = Table(data_tarifs, colWidths=[11 * cm, 6 * cm])
    tbl_tarifs.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0fb")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9f9f9")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(tbl_tarifs)

    # ── Page 2 — Durée, résiliation, obligations ───────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("LETTRE DE MISSION — Suite", styles["title"]))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("4. Durée et conditions de résiliation", styles["h2"]))
    story.append(
        Paragraph(
            "La présente mission est conclue pour une durée indéterminée à compter de sa signature. "
            "Chaque partie peut y mettre fin par lettre recommandée avec accusé de réception "
            "moyennant un préavis de 30 jours calendaires.",
            styles["body"],
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("5. Obligations du Conseiller", styles["h2"]))
    obligations_conseil = [
        "Fournir des conseils personnalisés adaptés au profil et aux objectifs du Client",
        "Mettre à jour l'évaluation du profil client a minima annuellement",
        "Informer le Client de tout changement réglementaire impactant ses investissements",
        "Agir dans le seul intérêt du Client (devoir fiduciaire)",
        "Conserver les enregistrements conformément à la réglementation (5 ans minimum)",
    ]
    for o in obligations_conseil:
        story.append(Paragraph(f"• {o}", styles["body"]))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("6. Obligations du Client", styles["h2"]))
    obligations_client = [
        "Fournir des informations exactes et complètes sur sa situation patrimoniale",
        "Informer le Conseiller de tout changement significatif de situation",
        "Régler les honoraires selon les modalités convenues",
        "Ne pas prendre de décisions contraires aux recommandations sans en informer le Conseiller",
    ]
    for o in obligations_client:
        story.append(Paragraph(f"• {o}", styles["body"]))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("7. Responsabilité et litiges", styles["h2"]))
    story.append(
        Paragraph(
            "Le Conseiller est couvert par une assurance Responsabilité Civile Professionnelle. "
            "En cas de litige, les parties s'engagent à recourir à la médiation avant toute action "
            "judiciaire. Le droit applicable est le droit français.",
            styles["body"],
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("8. Références légales", styles["h2"]))
    refs = [
        "Art. L.541-8-1 CMF — Obligations d'information et de conseil du CIF",
        "Art. 325-3 RG AMF — Évaluation de l'adéquation",
        "Art. 325-8 RG AMF — Profil de risque et adéquation",
        "Directive MIF II 2014/65/UE",
        "Art. L.222-7 Code consommation — Droit de rétractation",
    ]
    for r in refs:
        story.append(Paragraph(f"• {r}", styles["small"]))
    story.append(Spacer(1, 0.5 * cm))

    # ── Page 3 — Signatures ────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("LETTRE DE MISSION — Signatures", styles["title"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            "Les soussignés reconnaissent avoir pris connaissance de l'ensemble des dispositions "
            "de la présente lettre de mission et en acceptent les termes.",
            styles["body"],
        )
    )
    story.append(Spacer(1, 1 * cm))

    sig_data = [
        ["Pour le Cabinet", "Le Client"],
        [f"{prenom_ec} {nom_ec}", f"{client_prenom} {client_nom}"],
        [f"Fait à _______, le {today}", "Fait à _______, le ____/____/______"],
        ["", ""],
        ["Signature :", "Signature :"],
        ["", ""],
        ["", ""],
        ["", ""],
    ]
    tbl_sig = Table(sig_data, colWidths=[8.5 * cm, 8.5 * cm])
    tbl_sig.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOX", (0, 0), (0, -1), 0.5, colors.grey),
                ("BOX", (1, 0), (1, -1), 0.5, colors.grey),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(tbl_sig)
    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            "Document confidentiel — Usage exclusif du cabinet et du client.",
            styles["small"],
        )
    )

    # ── Build ──────────────────────────────────────────────────────────────────
    doc = BaseDocTemplate(
        str(sortie_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.0 * cm,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="main", frames=frame)])
    doc.build(story)

    logger.info("Lettre de mission générée : %s", sortie_path)
    return sortie_path
