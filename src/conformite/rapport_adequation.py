"""Génération du Rapport d'Adéquation MIF II — art. 25(6) MIF II."""

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

from src.conformite.styles import TABLE_HEADER_STYLE, TABLE_KEY_VALUE_STYLE, build_styles
from src.schemas import DocumentConformite

logger = logging.getLogger(__name__)

_W, _H = A4

_DEFAULT_TEXTES: dict[str, str] = {
    "introduction": (
        "Le présent rapport d'adéquation est établi conformément à l'article 25(6) de la "
        "directive MIF II (2014/65/UE) et à l'article 325-5 du RG AMF."
    ),
    "avertissements": (
        "Les recommandations sont basées sur les informations déclarées par le Client. "
        "Tout investissement comporte un risque de perte en capital. "
        "Les performances passées ne préjugent pas des performances futures."
    ),
    "obligation_maj": (
        "Conformément à l'article 325-5 RG AMF, le Conseiller procèdera à une mise à jour "
        "annuelle du présent rapport d'adéquation."
    ),
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


def generer_rapport_adequation(
    profil: Any,
    cabinet: Any,
    conformite: Any,
    allocation_cible: dict,
    etfs_retenus: list,
    sortie_path: Path,
) -> DocumentConformite:
    """Génère le Rapport d'Adéquation MIF II — art. 25(6) MIF II.

    Parameters
    ----------
    profil:
        Profil client. Peut être None.
    cabinet:
        Configuration cabinet.
    conformite:
        Configuration conformité. Peut être None.
    allocation_cible:
        Dict {classe: pct} ex. {"Actions": 0.7, "Obligations": 0.3}.
    etfs_retenus:
        Liste de dicts ou objets ETF retenus.
    sortie_path:
        Chemin de sortie du PDF.
    """
    sortie_path = Path(sortie_path)
    sortie_path.parent.mkdir(parents=True, exist_ok=True)

    textes = _DEFAULT_TEXTES.copy()
    if conformite is not None:
        try:
            raw = (
                conformite.get("textes_rapport_adequation", {})
                if isinstance(conformite, dict)
                else getattr(conformite, "textes_rapport_adequation", {})
            )
            if raw:
                textes.update(raw)
        except Exception:
            logger.warning(
                "RA: impossible de lire textes_rapport_adequation, utilisation des textes par défaut."
            )

    cab_nom = _get(cabinet, "cabinet.nom") or _get(cabinet, "nom") or "Cabinet"
    cab_orias = _get(cabinet, "cabinet.numero_orias") or _get(cabinet, "numero_orias") or ""

    client_nom = "Client"
    profil_id = 0
    client_email: str | None = None
    age = None
    tmi = None
    patrimoine = None
    score_risque = None
    horizon = None

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
            age = _get(profil, "age")
            tmi = _get(profil, "tmi")
            patrimoine = _get(profil, "patrimoine_financier_total")
            score_risque = _get(profil, "score_risque") or _get(profil, "profil_risque")
            horizon = _get(profil, "horizon_placement") or _get(profil, "horizon_ans")
        except Exception:
            pass

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
        canvas.drawString(
            2 * cm, 1.2 * cm, f"Rapport d'Adéquation MIF II — {client_nom} — Page {doc.page}"
        )
        canvas.drawRightString(_W - 2 * cm, 1.2 * cm, f"Généré le {date_gen[:10]}")
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_header_footer)])

    story: list[Any] = []

    # ── Page 1 : Couverture ───────────────────────────────────────────────────
    story.append(Spacer(1, 2 * cm))
    story.append(Paragraph("RAPPORT D'ADÉQUATION", styles["cover_title"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph("Art. 25(6) MIF II (2014/65/UE) — Art. 325-5 RG AMF", styles["cover_sub"])
    )
    story.append(Spacer(1, 1 * cm))

    cover_data = [
        ["Cabinet", cab_nom],
        ["N° ORIAS", cab_orias or "—"],
        ["Client", client_nom],
        ["Profil #", str(profil_id)],
        ["Date", date_gen[:10]],
    ]
    cover_table = Table(cover_data, colWidths=[5 * cm, doc.width - 5 * cm])
    cover_table.setStyle(TableStyle(TABLE_KEY_VALUE_STYLE))
    story.append(cover_table)
    story.append(Spacer(1, 0.8 * cm))
    story.append(
        Paragraph(textes.get("introduction", _DEFAULT_TEXTES["introduction"]), styles["body"])
    )
    story.append(PageBreak())

    # ── Page 2 : Profil client — 5 critères MIF II ───────────────────────────
    story.append(Paragraph("1. Profil du client — Critères MIF II", styles["h2"]))
    story.append(Spacer(1, 0.3 * cm))

    profil_data = [
        ["Critère MIF II", "Information client", "Valeur"],
        [
            "Objectifs d'investissement",
            "Horizon de placement",
            str(horizon) + " ans" if horizon else "—",
        ],
        [
            "Tolérance au risque",
            "Score de risque / Profil",
            str(score_risque) if score_risque else "—",
        ],
        [
            "Capacité à subir des pertes",
            "Patrimoine financier total",
            f"{patrimoine:,.0f} €" if patrimoine else "—",
        ],
        ["Connaissances & expérience", "Âge client", str(age) + " ans" if age else "—"],
        [
            "Situation financière",
            "Tranche marginale d'imposition",
            f"{int(tmi * 100) if isinstance(tmi, float) and tmi < 1 else tmi} %" if tmi else "—",
        ],
    ]
    profil_table = Table(profil_data, colWidths=[5 * cm, 6 * cm, doc.width - 11 * cm])
    profil_table.setStyle(TableStyle(TABLE_HEADER_STYLE))
    story.append(profil_table)
    story.append(PageBreak())

    # ── Page 3 : Recommandation principale — Allocation cible ────────────────
    story.append(Paragraph("2. Recommandation principale — Allocation cible", styles["h2"]))
    story.append(Spacer(1, 0.3 * cm))

    if allocation_cible:
        alloc_data = [["Classe d'actifs", "Pondération cible"]]
        for classe, pct in allocation_cible.items():
            pct_val = pct * 100 if isinstance(pct, float) and pct <= 1 else pct
            alloc_data.append([str(classe), f"{pct_val:.1f} %"])
        alloc_table = Table(alloc_data, colWidths=[doc.width * 0.6, doc.width * 0.4])
        alloc_table.setStyle(TableStyle(TABLE_HEADER_STYLE))
        story.append(alloc_table)
    else:
        story.append(Paragraph("Aucune allocation cible définie.", styles["body"]))

    story.append(Spacer(1, 0.8 * cm))
    story.append(
        Paragraph(
            "Justification : L'allocation recommandée est adaptée au profil de risque du client, "
            "à son horizon de placement et à ses objectifs patrimoniaux, conformément aux critères MIF II.",
            styles["body"],
        )
    )
    story.append(PageBreak())

    # ── Page 4 : Tableau d'adéquation par ETF ────────────────────────────────
    story.append(Paragraph("3. Tableau d'adéquation — ETFs / Produits retenus", styles["h2"]))
    story.append(Spacer(1, 0.3 * cm))

    if etfs_retenus:
        etf_data = [["Ticker / ISIN", "Nom", "Classe", "TER (%)", "Adéquation"]]
        for etf in etfs_retenus:
            ticker = _get(etf, "ticker") or "—"
            nom = _get(etf, "nom") or "—"
            classe = _get(etf, "classe_actifs") or "—"
            ter = _get(etf, "ter")
            ter_str = f"{ter:.2f}" if ter is not None else "—"
            etf_data.append([ticker, nom, classe, ter_str, "✓"])
        etf_table = Table(
            etf_data,
            colWidths=[3 * cm, 6 * cm, 3.5 * cm, 2 * cm, doc.width - 14.5 * cm],
        )
        etf_table.setStyle(TableStyle(TABLE_HEADER_STYLE))
        story.append(etf_table)
    else:
        story.append(Paragraph("Aucun ETF/produit spécifié.", styles["body"]))

    story.append(PageBreak())

    # ── Page 5 : Risques & Avertissements ─────────────────────────────────────
    story.append(Paragraph("4. Risques identifiés", styles["h2"]))
    story.append(Spacer(1, 0.3 * cm))

    risques = [
        "Risque de marché : fluctuation des cours des actifs financiers.",
        "Risque de liquidité : difficulté à céder certains instruments dans des délais courts.",
        "Risque de change : pour les actifs libellés en devises étrangères.",
        "Risque d'inflation : érosion du pouvoir d'achat du capital.",
        "Risque de taux : impact des variations de taux sur les obligations.",
    ]
    for r in risques:
        story.append(Paragraph(f"• {r}", styles["bullet"]))

    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph("5. Avertissements et limites", styles["h2"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(textes.get("avertissements", _DEFAULT_TEXTES["avertissements"]), styles["body"])
    )
    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(textes.get("obligation_maj", _DEFAULT_TEXTES["obligation_maj"]), styles["body"])
    )
    story.append(Spacer(1, 1 * cm))
    story.append(
        Paragraph(
            "Document établi conformément à l'art. 25(6) MIF II et art. 325-5 RG AMF. "
            "Conservé 5 ans minimum.",
            styles["legal"],
        )
    )

    doc.build(story)

    sha = _sha256(sortie_path)
    return DocumentConformite(
        type_doc="RAPPORT_ADEQUATION",
        profil_id=profil_id,
        client_nom=client_nom,
        client_email=client_email,
        date_generation=date_gen,
        chemin_pdf=str(sortie_path),
        sha256=sha,
        version_template="RA_v1.0",
    )
