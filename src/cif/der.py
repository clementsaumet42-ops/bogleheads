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
        obj = obj.get(part) if isinstance(obj, dict) else getattr(obj, part, None)
    return obj if obj is not None else default


def generer_der(config_cabinet: Any, sortie_path: str | Path) -> Path:
    """
    Génère le Document d'Entrée en Relation (DER).

    Conforme à l'Art. 325-3 RG AMF — Identification du conseiller,
    rémunération, réclamations, conflits d'intérêts.

    Parameters
    ----------
    config_cabinet : dict ou objet avec les infos du cabinet
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
        "title": s("DerTitle", parent="Heading1", fontSize=20, textColor=primary, spaceAfter=12),
        "h2": s("DerH2", parent="Heading2", fontSize=13, textColor=primary, spaceAfter=8),
        "body": s("DerBody", fontSize=10, leading=14, textColor=neutral),
        "small": s("DerSmall", fontSize=8, leading=11, textColor=neutral),
        "bold": s("DerBold", fontSize=10, leading=14, fontName="Helvetica-Bold"),
        "center": s("DerCenter", fontSize=10, alignment=1, textColor=neutral),
    }

    nom_cabinet = _get(config_cabinet, "cabinet.nom", "[Cabinet]")
    nom_ec = _get(config_cabinet, "cabinet.nom_ec", "[Conseiller]")
    prenom_ec = _get(config_cabinet, "cabinet.prenom_ec", "")
    adresse = _get(config_cabinet, "cabinet.adresse", "[Adresse]")
    telephone = _get(config_cabinet, "cabinet.telephone", "[Téléphone]")
    email = _get(config_cabinet, "cabinet.email", "[Email]")
    orias = _get(config_cabinet, "cabinet.numero_orias", "[N° ORIAS]")
    rc_assureur = _get(config_cabinet, "cabinet.rc_pro_assureur", "[Assureur]")
    rc_numero = _get(config_cabinet, "cabinet.rc_pro_numero", "[N° Police]")
    rc_montant = _get(config_cabinet, "cabinet.rc_pro_montant_eur", 1500000)
    mediateur_nom = _get(config_cabinet, "cabinet.mediateur_nom", "Médiateur de l'AMF")
    mediateur_url = _get(config_cabinet, "cabinet.mediateur_url", "https://www.amf-france.org")
    conflits = _get(
        config_cabinet,
        "cabinet.conflits_interets",
        "Pas de rétrocession.",
    )
    mode_remun = _get(config_cabinet, "remuneration.mode", "honoraires")
    mention_retro = _get(
        config_cabinet,
        "remuneration.mention_retrocessions",
        "Aucune rétrocession perçue (Art. L.541-8-1 CMF)",
    )

    story: list = []

    # ── Page 1 — Identification ────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            "DOCUMENT D'ENTRÉE EN RELATION (DER)",
            styles["title"],
        )
    )
    story.append(
        Paragraph(
            f"Établi le {today} — Art. 325-3 Règlement Général AMF",
            styles["small"],
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    story.append(
        Paragraph("1. Identification du Conseiller en Investissements Financiers", styles["h2"])
    )
    data_id = [
        ["Dénomination", nom_cabinet],
        ["Conseiller référent", f"{prenom_ec} {nom_ec}"],
        ["Adresse", adresse],
        ["Téléphone", telephone],
        ["Email", email],
        ["N° ORIAS", orias],
        ["Statut réglementaire", "Conseiller en Investissements Financiers (CIF)"],
        ["Autorité de tutelle", "Autorité des Marchés Financiers (AMF)"],
        ["Association professionnelle", "ANACOFI-CIF ou CNCIF (selon agrément)"],
    ]
    tbl_id = Table(data_id, colWidths=[6 * cm, 11 * cm])
    tbl_id.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0fb")),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f9f9f9"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(tbl_id)
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("2. Assurance Responsabilité Civile Professionnelle", styles["h2"]))
    story.append(
        Paragraph(
            f"Assureur : <b>{rc_assureur}</b> — N° de police : <b>{rc_numero}</b>",
            styles["body"],
        )
    )
    story.append(
        Paragraph(
            f"Montant de garantie : <b>{rc_montant:,} €</b>".replace(",", " "),
            styles["body"],
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("3. Services proposés", styles["h2"]))
    services = [
        "Conseil en investissements financiers (Art. L.541-1 CMF)",
        "Analyse patrimoniale globale",
        "Recommandations d'allocation d'actifs",
        "Suivi et rebalancement périodique",
        "Optimisation fiscale (PEA, assurance-vie, CTO, PER)",
    ]
    for svc in services:
        story.append(Paragraph(f"• {svc}", styles["body"]))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("4. Rémunération", styles["h2"]))
    story.append(
        Paragraph(
            f"Mode de rémunération : <b>{mode_remun.upper()}</b>",
            styles["body"],
        )
    )
    story.append(Paragraph(mention_retro, styles["body"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            "Conformément à l'Art. L.541-8-1 CMF, le conseiller informe le client de tout conflit "
            "d'intérêts potentiel avant la fourniture d'un conseil.",
            styles["body"],
        )
    )

    # ── Page 2 — Conflits, réclamations, RGPD ─────────────────────────────────
    story.append(PageBreak())
    story.append(
        Paragraph(
            "DOCUMENT D'ENTRÉE EN RELATION (DER) — Suite",
            styles["title"],
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("5. Politique de gestion des conflits d'intérêts", styles["h2"]))
    story.append(
        Paragraph(
            "Conformément à l'Art. 313-48 RG AMF :",
            styles["body"],
        )
    )
    story.append(Paragraph(str(conflits), styles["body"]))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("6. Procédure de réclamation", styles["h2"]))
    story.append(
        Paragraph(
            "Toute réclamation doit être adressée par écrit (courrier ou email) au cabinet. "
            "Le cabinet dispose de 10 jours ouvrables pour en accuser réception et de 2 mois "
            "maximum pour y répondre.",
            styles["body"],
        )
    )
    story.append(
        Paragraph(
            f"En cas de désaccord persistant, le client peut saisir le médiateur compétent : "
            f"<b>{mediateur_nom}</b> — {mediateur_url}",
            styles["body"],
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("7. Protection des données personnelles (RGPD)", styles["h2"]))
    story.append(
        Paragraph(
            "Les données personnelles collectées sont traitées conformément au Règlement "
            "Général sur la Protection des Données (RGPD — Art. 17). "
            "Le client dispose d'un droit d'accès, de rectification et d'effacement de ses données. "
            "Pour exercer ces droits, contacter le cabinet par email.",
            styles["body"],
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("8. Références réglementaires", styles["h2"]))
    refs = [
        "Art. L.541-1 CMF — Définition du CIF",
        "Art. L.541-8-1 CMF — Obligations d'information et de conseil",
        "Art. 325-3 RG AMF — Évaluation de l'adéquation",
        "Art. 313-48 RG AMF — Conflits d'intérêts",
        "Directive MIF II 2014/65/UE",
        "Art. 17 RGPD — Droit à l'effacement",
    ]
    for ref in refs:
        story.append(Paragraph(f"• {ref}", styles["small"]))
    story.append(Spacer(1, 0.5 * cm))

    # Signature
    story.append(Paragraph("9. Accusé de réception", styles["h2"]))
    story.append(
        Paragraph(
            "Le client reconnaît avoir reçu et pris connaissance du présent Document d'Entrée "
            "en Relation avant tout conseil en investissement.",
            styles["body"],
        )
    )
    story.append(Spacer(1, 1 * cm))
    sig_data = [
        ["Le Conseiller", "Le Client"],
        [f"{prenom_ec} {nom_ec}", "Nom, Prénom"],
        ["Date et signature :", "Date et signature :"],
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

    # ── Build PDF ─────────────────────────────────────────────────────────────
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

    logger.info("DER généré : %s (%d octets)", sortie_path, sortie_path.stat().st_size)
    return sortie_path
