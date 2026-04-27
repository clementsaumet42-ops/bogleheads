"""Sprint S15 Lot B — Plan d'exécution chiffré.

Convertit l'allocation finale validée (output optimiseur + screener)
en liste d'ordres ligne par ligne avec quantités, frais et reliquats.
"""

from __future__ import annotations

import csv
import io
import logging
import math
from typing import Any

logger = logging.getLogger(__name__)

# Montant minimum pour un ordre (sécurité)
_MONTANT_MIN_ORDRE_EUR = 1.0


def _estimer_frais_courtage(montant_eur: float, prix_unitaire: float, broker: Any) -> float:
    """Estime les frais de courtage pour un ordre donné."""
    if broker is None:
        return 0.0

    # Frais fixe en € (Euronext)
    frais_fixe = getattr(broker, "frais_courtage_actions_euronext_eur", None)
    # Frais en % (Euronext)
    frais_pct = getattr(broker, "frais_courtage_actions_euronext_pct", None)
    # Minimum d'ordre
    min_ordre = getattr(broker, "minimum_ordre_eur", 0.0) or 0.0

    frais = 0.0
    if frais_fixe is not None:
        frais = float(frais_fixe)
    elif frais_pct is not None:
        frais = float(frais_pct) * montant_eur
    else:
        frais = 0.0

    # Appliquer le minimum d'ordre
    frais = max(frais, min_ordre * 0.0 if min_ordre else frais)
    return round(frais, 2)


def _calculer_quantite(
    montant_eur: float,
    prix_unitaire: float,
    enveloppe: str,
) -> tuple[float, float]:
    """
    Calcule la quantité de parts et le reliquat cash.

    AV en UC permet les fractions. Les autres enveloppes arrondissent à l'entier.

    Returns
    -------
    (quantite, reliquat_eur)
    """
    if prix_unitaire <= 0:
        return 0.0, montant_eur

    enveloppe_up = enveloppe.upper()
    if enveloppe_up in ("AV", "AV_UC"):
        # UC fractionnées : on arrondit à 6 décimales
        quantite = round(montant_eur / prix_unitaire, 6)
        reliquat = 0.0
    else:
        # Entier strict (PEA, CTO, PER)
        quantite = math.floor(montant_eur / prix_unitaire)
        reliquat = round(montant_eur - quantite * prix_unitaire, 2)

    return quantite, reliquat


def generer_ordres(
    allocation_finale: dict[str, dict[str, float]],
    prix_reference: dict[str, float],
    contexte: dict,
    tolerance_prix: float = 0.02,
) -> dict:
    """
    Convertit l'allocation finale en liste d'ordres.

    Parameters
    ----------
    allocation_finale : dict
        Format : {enveloppe: {isin: montant_eur}}.
        Ex : {"PEA": {"IE0031442068": 30000}, "CTO": {"IE00B4L5Y983": 20000}}.
    prix_reference : dict
        Format : {isin: prix_eur}. Dernier cours de clôture.
    contexte : dict
        Informations contextuelles : brokers (dict {enveloppe: Broker}),
        contrats, noms ETF optionnels ({isin: nom}).
    tolerance_prix : float
        Tolérance pour l'ordre limité (défaut ±2%).

    Returns
    -------
    dict
        {
            'ordres': [liste d'ordres],
            'reliquats': {enveloppe: montant_reliquat_eur},
            'frais_total': float,
        }

    Chaque ordre contient :
        enveloppe, isin, ticker, nom, montant_cible_eur, prix_reference_eur,
        quantite, type_ordre, prix_limite_eur, frais_courtage_eur,
        montant_reel_eur.
    """
    ordres: list[dict] = []
    reliquats: dict[str, float] = {}
    frais_total = 0.0

    brokers_ctx: dict[str, Any] = contexte.get("brokers", {}) or {}
    noms_etf: dict[str, str] = contexte.get("noms_etf", {}) or {}
    tickers_etf: dict[str, str] = contexte.get("tickers_etf", {}) or {}

    for enveloppe, positions in allocation_finale.items():
        if not positions:
            continue

        # Récupérer le broker pour cette enveloppe
        broker = brokers_ctx.get(enveloppe) or brokers_ctx.get(enveloppe.lower())
        reliquat_env = 0.0

        for isin, montant_eur in positions.items():
            if montant_eur < _MONTANT_MIN_ORDRE_EUR:
                continue

            prix_ref = prix_reference.get(isin)
            if prix_ref is None or prix_ref <= 0:
                logger.warning("Prix manquant pour ISIN %s — ordre ignoré", isin)
                continue

            quantite, reliquat = _calculer_quantite(montant_eur, prix_ref, enveloppe)

            if quantite <= 0:
                reliquat_env += montant_eur
                continue

            # Ordre limité : prix max d'achat = prix_ref × (1 + tolerance)
            prix_limite = round(prix_ref * (1.0 + tolerance_prix), 4)
            montant_reel = round(quantite * prix_ref, 2)

            # Frais de courtage
            frais = _estimer_frais_courtage(montant_reel, prix_ref, broker)
            frais_total += frais

            reliquat_env += reliquat

            ordres.append(
                {
                    "enveloppe": enveloppe,
                    "isin": isin,
                    "ticker": tickers_etf.get(isin, ""),
                    "nom": noms_etf.get(isin, isin),
                    "montant_cible_eur": round(montant_eur, 2),
                    "prix_reference_eur": round(prix_ref, 4),
                    "quantite": quantite,
                    "type_ordre": "limité",
                    "prix_limite_eur": prix_limite,
                    "frais_courtage_eur": frais,
                    "montant_reel_eur": montant_reel,
                }
            )

        if reliquat_env > 0:
            reliquats[enveloppe] = round(reliquat_env, 2)

    return {
        "ordres": ordres,
        "reliquats": reliquats,
        "frais_total": round(frais_total, 2),
    }


def export_ordres_csv(plan: dict, path: str | None = None) -> str:
    """
    Exporte le plan d'ordres en CSV.

    Parameters
    ----------
    plan : dict
        Résultat de generer_ordres().
    path : str | None
        Chemin de sortie. Si None, retourne le CSV comme chaîne.

    Returns
    -------
    str
        Contenu CSV (ou chemin si path est fourni).
    """
    ordres = plan.get("ordres", [])
    reliquats = plan.get("reliquats", {})
    frais_total = plan.get("frais_total", 0.0)

    colonnes = [
        "enveloppe",
        "isin",
        "ticker",
        "nom",
        "montant_cible_eur",
        "prix_reference_eur",
        "quantite",
        "type_ordre",
        "prix_limite_eur",
        "frais_courtage_eur",
        "montant_reel_eur",
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=colonnes, extrasaction="ignore")
    writer.writeheader()
    for ordre in ordres:
        writer.writerow(ordre)

    # Ligne vide + synthèse
    output.write("\n")
    output.write(f"FRAIS TOTAL;{frais_total:.2f}\n")
    for env, rel in reliquats.items():
        output.write(f"RELIQUAT {env};{rel:.2f}\n")

    csv_content = output.getvalue()

    if path is not None:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(csv_content)
        return path

    return csv_content


def export_ordres_pdf(plan: dict) -> list:
    """
    Génère les éléments ReportLab pour la page PDF du plan d'ordres.

    Returns
    -------
    list
        Liste d'éléments ReportLab (Paragraph, Table, Spacer…).
        Peut être intégré dans _page_plan_execution().
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    except ImportError:
        logger.warning("ReportLab non disponible — export PDF désactivé")
        return []

    styles = getSampleStyleSheet()
    body_style = styles["Normal"]
    elems: list = []

    ordres = plan.get("ordres", [])
    reliquats = plan.get("reliquats", {})
    frais_total = plan.get("frais_total", 0.0)

    if not ordres:
        elems.append(Paragraph("Aucun ordre généré.", body_style))
        return elems

    # En-tête tableau
    header = ["Enveloppe", "Ticker", "Qté", "Montant (€)", "Limite (€)", "Frais (€)"]
    data = [header]
    for o in ordres:
        qte = o["quantite"]
        qte_str = f"{qte:.6g}"
        data.append(
            [
                o.get("enveloppe", ""),
                o.get("ticker", o.get("isin", "")),
                qte_str,
                f"{o.get('montant_cible_eur', 0):,.2f}",
                f"{o.get('prix_limite_eur', 0):,.4f}",
                f"{o.get('frais_courtage_eur', 0):,.2f}",
            ]
        )

    col_widths = [2.5 * cm, 2.5 * cm, 2 * cm, 3.5 * cm, 3.5 * cm, 2.5 * cm]
    t = Table(data, colWidths=col_widths)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a4d8f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e0e0e0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elems.append(t)
    elems.append(Spacer(1, 0.3 * cm))

    # Synthèse frais + reliquats
    elems.append(Paragraph(f"<b>Frais totaux estimés :</b> {frais_total:,.2f} €", body_style))
    for env, rel in reliquats.items():
        elems.append(Paragraph(f"Reliquat {env} : {rel:,.2f} €", body_style))

    return elems
