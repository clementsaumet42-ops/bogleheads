"""Génération du DER (Document d'Entrée en Relation) — art. 325-5 RG AMF."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
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

from src.conformite.styles import TABLE_KEY_VALUE_STYLE, build_styles
from src.schemas import DocumentConformite

logger = logging.getLogger(__name__)

_W, _H = A4


def _get(obj: Any, key: str, default: Any = None) -> Any:
    parts = key.split(".")
    for part in parts:
        if obj is None:
            return default
        obj = obj.get(part) if isinstance(obj, dict) else getattr(obj, part, None)
    return obj if obj is not None else default


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


_DEFAULT_TEXTES: dict[str, str] = {
    "identification": (
        "Conformément à l'article 325-5 du RG AMF, le présent Document d'Entrée en Relation "
        "(DER) vous est remis avant toute fourniture de conseil en investissement."
    ),
    "statuts_services": (
        "Le cabinet exerce l'activité de Conseil en Investissements Financiers (CIF) au sens "
        "de l'article L.541-1 du CMF."
    ),
    "remuneration": (
        "Conformément à l'article L.541-8-1 CMF, le cabinet vous informe de ses modalités de "
        "rémunération. Rémunération exclusivement par honoraires directs."
    ),
    "reclamations": (
        "Toute réclamation doit être adressée par écrit au cabinet. En l'absence de réponse "
        "satisfaisante, le client peut saisir le Médiateur de l'AMF."
    ),
    "rgpd": (
        "Vos données personnelles sont traitées conformément au RGPD (Règlement UE 2016/679). "
        "Durée de conservation : 5 ans. Droits d'accès, rectification, effacement disponibles."
    ),
    "conclusion": (
        "Le présent document ne constitue pas un engagement contractuel. "
        "La relation est formalisée par la lettre de mission signée par les deux parties."
    ),
}


def generer_der(
    profil: Any,
    cabinet: Any,
    conformite: Any,
    sortie_path: Path,
) -> DocumentConformite:
    """Génère le Document d'Entrée en Relation (DER) — art. 325-5 RG AMF.

    Parameters
    ----------
    profil:
        Profil client (objet ou dict). Peut être None.
    cabinet:
        Configuration cabinet (objet CabinetConfig ou dict).
    conformite:
        Configuration conformité (objet ConformiteConfig ou dict). Peut être None.
    sortie_path:
        Chemin de sortie du PDF.

    Returns
    -------
    DocumentConformite avec métadonnées du PDF généré.
    """
    sortie_path = Path(sortie_path)
    sortie_path.parent.mkdir(parents=True, exist_ok=True)

    # Extraire les textes depuis conformite
    textes = _DEFAULT_TEXTES.copy()
    if conformite is not None:
        try:
            raw = (
                conformite.get("textes_der", {})
                if isinstance(conformite, dict)
                else getattr(conformite, "textes_der", {})
            )
            if raw:
                textes.update(raw)
        except Exception:
            logger.warning(
                "DER: impossible de lire textes_der depuis conformite, utilisation des textes par défaut."
            )

    # Extraire infos cabinet
    cab_nom = _get(cabinet, "cabinet.nom") or _get(cabinet, "nom") or "Cabinet"
    cab_orias = _get(cabinet, "cabinet.numero_orias") or _get(cabinet, "numero_orias") or ""
    if conformite is not None:
        try:
            orias_conf = (
                conformite.get("cabinet_orias")
                if isinstance(conformite, dict)
                else getattr(conformite, "cabinet_orias", None)
            )
            if orias_conf:
                cab_orias = cab_orias or orias_conf
        except Exception:
            pass
    cab_email = _get(cabinet, "cabinet.email") or ""
    cab_adresse = _get(cabinet, "cabinet.adresse") or ""
    cab_telephone = _get(cabinet, "cabinet.telephone") or ""
    cab_rcp_assureur = _get(cabinet, "cabinet.rc_pro_assureur") or ""
    cab_rcp_numero = _get(cabinet, "cabinet.rc_pro_numero") or ""
    mediateur = _get(cabinet, "cabinet.mediateur_nom") or "Médiateur de l'AMF"

    associations: list[str] = []
    if conformite is not None:
        try:
            assoc = (
                conformite.get("cabinet_associations", [])
                if isinstance(conformite, dict)
                else getattr(conformite, "cabinet_associations", [])
            )
            associations = list(assoc) if assoc else []
        except Exception:
            pass
    if not associations:
        cncif = _get(cabinet, "cabinet.numero_cncif")
        associations = ["CNCIF"] if cncif else []

    # Extraire infos profil
    client_nom = "Client"
    profil_id = 0
    client_email: str | None = None
    if profil is not None:
        try:
            client_nom = (
                profil.get("nom", "Client")
                if isinstance(profil, dict)
                else getattr(profil, "nom", "Client")
            ) or "Client"
            profil_id = (
                profil.get("id", 0) if isinstance(profil, dict) else getattr(profil, "id", 0)
            ) or 0
            client_email = (
                profil.get("email") if isinstance(profil, dict) else getattr(profil, "email", None)
            )
        except Exception:
            pass

    date_gen = datetime.now(timezone.utc).isoformat()
    styles = build_styles()

    # ─── Build PDF ─────────────────────────────────────────────────────────────

    doc = BaseDocTemplate(
        str(sortie_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2 * cm,
    )

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")

    def _header_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#888888"))
        canvas.drawString(2 * cm, 1.2 * cm, f"DER — {client_nom} — Page {doc.page}")
        canvas.drawRightString(_W - 2 * cm, 1.2 * cm, f"Généré le {date_gen[:10]}")
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_header_footer)])

    story: list[Any] = []

    # ── Page 1 : Couverture ───────────────────────────────────────────────────
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph("DOCUMENT D'ENTRÉE EN RELATION", styles["cover_title"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph("Conformément à l'article 325-5 du Règlement Général AMF", styles["cover_sub"])
    )
    story.append(Spacer(1, 1 * cm))

    cover_data = [
        ["Cabinet", cab_nom],
        ["N° ORIAS", cab_orias or "—"],
        ["Adresse", cab_adresse or "—"],
        ["Téléphone", cab_telephone or "—"],
        ["Email", cab_email or "—"],
        ["Associations professionnelles", ", ".join(associations) if associations else "—"],
    ]
    cover_table = Table(cover_data, colWidths=[6 * cm, doc.width - 6 * cm])
    cover_table.setStyle(TableStyle(TABLE_KEY_VALUE_STYLE))
    story.append(cover_table)
    story.append(Spacer(1, 1 * cm))

    story.append(Paragraph(f"<b>Client :</b> {client_nom}", styles["body"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(f"<b>Date de remise :</b> {date_gen[:10]}", styles["body"]))
    story.append(PageBreak())

    # ── Page 2 : Identification du CIF ───────────────────────────────────────
    story.append(
        Paragraph("1. Identification du Conseiller en Investissements Financiers", styles["h2"])
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(textes.get("identification", _DEFAULT_TEXTES["identification"]), styles["body"])
    )
    story.append(Spacer(1, 0.5 * cm))

    id_data = [
        ["Information", "Détail"],
        ["Dénomination", cab_nom],
        ["N° ORIAS", cab_orias or "—"],
        ["Associations professionnelles", ", ".join(associations) if associations else "—"],
        ["Assurance RC Pro", cab_rcp_assureur or "—"],
        ["N° Police RC Pro", cab_rcp_numero or "—"],
        ["Médiateur compétent", mediateur],
    ]
    id_table = Table(id_data, colWidths=[6 * cm, doc.width - 6 * cm])
    id_table.setStyle(TableStyle(TABLE_KEY_VALUE_STYLE))
    story.append(id_table)
    story.append(PageBreak())

    # ── Page 3 : Statuts & services ──────────────────────────────────────────
    story.append(Paragraph("2. Statuts et services proposés", styles["h2"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            textes.get("statuts_services", _DEFAULT_TEXTES["statuts_services"]), styles["body"]
        )
    )
    story.append(Spacer(1, 1 * cm))

    # ── Section 3 : Rémunération ─────────────────────────────────────────────
    story.append(Paragraph("3. Modes de rémunération", styles["h2"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(textes.get("remuneration", _DEFAULT_TEXTES["remuneration"]), styles["body"])
    )
    story.append(PageBreak())

    # ── Page 4 : Réclamations & RGPD ─────────────────────────────────────────
    story.append(Paragraph("4. Réclamations & médiation", styles["h2"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(textes.get("reclamations", _DEFAULT_TEXTES["reclamations"]), styles["body"])
    )
    story.append(Spacer(1, 1 * cm))

    story.append(Paragraph("5. Cadre RGPD — Protection des données personnelles", styles["h2"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(textes.get("rgpd", _DEFAULT_TEXTES["rgpd"]), styles["body"]))
    story.append(PageBreak())

    # ── Page 5 : Conclusion & accusé de réception ─────────────────────────────
    story.append(Paragraph("6. Conclusion", styles["h2"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(textes.get("conclusion", _DEFAULT_TEXTES["conclusion"]), styles["body"]))
    story.append(Spacer(1, 1.5 * cm))

    story.append(Paragraph("Accusé de réception", styles["h3"]))
    story.append(Spacer(1, 0.5 * cm))

    sig_data = [
        ["Pour le Cabinet", "Le Client"],
        [
            f"{cab_nom}\n\nSignature :\n\n\n_______________________",
            f"{client_nom}\n\nSignature :\n\n\n_______________________",
        ],
        [f"Date : {date_gen[:10]}", "Date :"],
    ]
    sig_table = Table(sig_data, colWidths=[doc.width / 2, doc.width / 2])
    sig_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOX", (0, 0), (0, -1), 0.5, colors.grey),
                ("BOX", (1, 0), (1, -1), 0.5, colors.grey),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(sig_table)
    story.append(Spacer(1, 1 * cm))

    story.append(
        Paragraph(
            "Document remis conformément à l'art. 325-5 RG AMF. "
            "Conservé 5 ans minimum (art. 325-5 RG AMF, MIF II art. 25).",
            styles["legal"],
        )
    )

    doc.build(story)

    sha = _sha256(sortie_path)
    return DocumentConformite(
        type_doc="DER",
        profil_id=profil_id,
        client_nom=client_nom,
        client_email=client_email,
        date_generation=date_gen,
        chemin_pdf=str(sortie_path),
        sha256=sha,
        version_template="DER_v1.0",
    )
