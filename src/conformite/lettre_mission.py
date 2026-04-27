"""Génération de la Lettre de Mission CIF — art. 325-3 RG AMF."""

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

_MODALITE_LABELS = {
    "forfait": "Forfait",
    "horaire": "Taux horaire",
    "pct_actifs": "Pourcentage des actifs sous conseil",
}

_DEFAULT_TEXTES: dict[str, str] = {
    "preambule": (
        "La présente lettre de mission est conclue conformément à l'article 325-3 du RG AMF "
        "et à l'article L.541-8-1 du CMF."
    ),
    "objet": (
        "Le Conseiller s'engage à fournir au Client des services de conseil en investissement "
        "personnalisés, adaptés à son profil de risque et à ses objectifs patrimoniaux."
    ),
    "duree_resiliation": (
        "La présente mission est conclue pour une durée indéterminée à compter de sa signature. "
        "Préavis de résiliation : 30 jours calendaires."
    ),
    "responsabilite": (
        "Le Conseiller est couvert par une assurance Responsabilité Civile Professionnelle. "
        "Le Client est seul décisionnaire de ses investissements."
    ),
    "mentions_cncif": ("Lettre de mission établie conformément aux clauses standard CNCIF."),
}


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


def generer_lettre_mission(
    profil: Any,
    cabinet: Any,
    conformite: Any,
    parametres: Any,
    sortie_path: Path,
) -> DocumentConformite:
    """Génère la Lettre de Mission CIF — art. 325-3 RG AMF.

    Parameters
    ----------
    profil:
        Profil client. Peut être None.
    cabinet:
        Configuration cabinet.
    conformite:
        Configuration conformité. Peut être None.
    parametres:
        ParametresMission ou dict avec objet, perimetre, honoraires_eur, etc.
    sortie_path:
        Chemin de sortie du PDF.
    """
    sortie_path = Path(sortie_path)
    sortie_path.parent.mkdir(parents=True, exist_ok=True)

    textes = _DEFAULT_TEXTES.copy()
    if conformite is not None:
        try:
            raw = (
                conformite.get("textes_lettre_mission", {})
                if isinstance(conformite, dict)
                else getattr(conformite, "textes_lettre_mission", {})
            )
            if raw:
                textes.update(raw)
        except Exception:
            logger.warning(
                "LM: impossible de lire textes_lettre_mission, utilisation des textes par défaut."
            )

    cab_nom = _get(cabinet, "cabinet.nom") or _get(cabinet, "nom") or "Cabinet"
    cab_orias = _get(cabinet, "cabinet.numero_orias") or _get(cabinet, "numero_orias") or ""
    cab_email = _get(cabinet, "cabinet.email") or ""
    cab_adresse = _get(cabinet, "cabinet.adresse") or ""

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

    # Extraire paramètres mission
    if parametres is None:
        parametres = {}
    objet = _get(parametres, "objet") or "Conseil en investissements financiers"
    perimetre = _get(parametres, "perimetre") or []
    honoraires = _get(parametres, "honoraires_eur") or 0.0
    modalite = _get(parametres, "honoraires_modalite") or "forfait"
    duree_mois = _get(parametres, "duree_mois") or 12
    date_debut = _get(parametres, "date_debut") or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    date_gen = datetime.now(timezone.utc).isoformat()
    styles = build_styles()

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
        canvas.drawString(2 * cm, 1.2 * cm, f"Lettre de Mission — {client_nom} — Page {doc.page}")
        canvas.drawRightString(_W - 2 * cm, 1.2 * cm, f"Généré le {date_gen[:10]}")
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_header_footer)])

    story: list[Any] = []

    # ── Page 1 : Couverture ───────────────────────────────────────────────────
    story.append(Spacer(1, 2 * cm))
    story.append(Paragraph("LETTRE DE MISSION CIF", styles["cover_title"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph("Art. 325-3 RG AMF — Conseil en Investissements Financiers", styles["cover_sub"])
    )
    story.append(Spacer(1, 1 * cm))

    parties_data = [
        ["Partie", "Cabinet", "Client"],
        ["Dénomination", cab_nom, client_nom],
        ["N° ORIAS / Réf.", cab_orias or "—", f"Profil #{profil_id}"],
        ["Adresse", cab_adresse or "—", "—"],
        ["Email", cab_email or "—", client_email or "—"],
    ]
    parties_table = Table(
        parties_data, colWidths=[4 * cm, (doc.width - 4 * cm) / 2, (doc.width - 4 * cm) / 2]
    )
    parties_table.setStyle(TableStyle(TABLE_KEY_VALUE_STYLE))
    story.append(parties_table)
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(f"<b>Date de prise d'effet :</b> {date_debut}", styles["body"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(textes.get("preambule", _DEFAULT_TEXTES["preambule"]), styles["body"]))
    story.append(PageBreak())

    # ── Page 2 : Objet & Périmètre ───────────────────────────────────────────
    story.append(Paragraph("1. Objet de la mission", styles["h2"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(textes.get("objet", _DEFAULT_TEXTES["objet"]), styles["body"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(f"<b>Objet spécifique :</b> {objet}", styles["body"]))
    story.append(Spacer(1, 0.8 * cm))

    story.append(Paragraph("2. Périmètre de la mission", styles["h2"]))
    story.append(Spacer(1, 0.3 * cm))
    if perimetre:
        for item in perimetre:
            story.append(Paragraph(f"• {item}", styles["bullet"]))
    else:
        story.append(Paragraph("• Conseil en investissements financiers global", styles["bullet"]))
    story.append(PageBreak())

    # ── Page 3 : Honoraires ───────────────────────────────────────────────────
    story.append(Paragraph("3. Honoraires", styles["h2"]))
    story.append(Spacer(1, 0.3 * cm))

    modalite_label = _MODALITE_LABELS.get(modalite, modalite)
    if modalite == "pct_actifs":
        honoraires_str = f"{honoraires:.2f} % des actifs sous conseil par an"
    elif modalite == "horaire":
        honoraires_str = f"{honoraires:,.0f} € / heure"
    else:
        honoraires_str = f"{honoraires:,.0f} € (forfait)"

    honoraires_data = [
        ["Modalité", modalite_label],
        ["Montant", honoraires_str],
        ["Durée de la mission", f"{duree_mois} mois"],
        ["Date de début", date_debut],
    ]
    hon_table = Table(honoraires_data, colWidths=[6 * cm, doc.width - 6 * cm])
    hon_table.setStyle(TableStyle(TABLE_KEY_VALUE_STYLE))
    story.append(hon_table)
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            "Aucune rétrocession de commission de la part de producteurs de produits financiers n'est perçue "
            "(art. L.541-8-1 CMF).",
            styles["italic"],
        )
    )
    story.append(PageBreak())

    # ── Page 4 : Durée, résiliation, responsabilité ───────────────────────────
    story.append(Paragraph("4. Durée et résiliation", styles["h2"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            textes.get("duree_resiliation", _DEFAULT_TEXTES["duree_resiliation"]), styles["body"]
        )
    )
    story.append(Spacer(1, 0.8 * cm))

    story.append(Paragraph("5. Responsabilité et médiation", styles["h2"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(textes.get("responsabilite", _DEFAULT_TEXTES["responsabilite"]), styles["body"])
    )
    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(textes.get("mentions_cncif", _DEFAULT_TEXTES["mentions_cncif"]), styles["legal"])
    )
    story.append(PageBreak())

    # ── Page 5 : Signatures ───────────────────────────────────────────────────
    story.append(Paragraph("6. Signatures", styles["h2"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            "Les soussignés déclarent avoir pris connaissance et accepté les termes de la présente lettre de mission.",
            styles["body"],
        )
    )
    story.append(Spacer(1, 1 * cm))

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
            "Document établi conformément à l'art. 325-3 RG AMF. Conservé 5 ans minimum.",
            styles["legal"],
        )
    )

    doc.build(story)

    sha = _sha256(sortie_path)
    return DocumentConformite(
        type_doc="LETTRE_MISSION",
        profil_id=profil_id,
        client_nom=client_nom,
        client_email=client_email,
        date_generation=date_gen,
        chemin_pdf=str(sortie_path),
        sha256=sha,
        version_template="LM_v1.0",
    )
