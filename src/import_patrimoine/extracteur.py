"""Pipeline principal d'extraction PDF pour l'import patrimoine."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from src.import_patrimoine.modele import LignePatrimoine, ResultatExtraction

logger = logging.getLogger(__name__)


def _sha256(chemin: Path) -> str:
    """Calcule le hash SHA-256 d'un fichier."""
    h = hashlib.sha256()
    with chemin.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _extraire_texte_pdfplumber(chemin: Path) -> tuple[str, list[list[list[str]]]]:
    """Extrait le texte et les tableaux d'un PDF via pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber non installé — pip install bogleheads-fr[pdf]")
        return "", []

    texte_pages: list[str] = []
    tableaux: list[list[list[str]]] = []

    try:
        with pdfplumber.open(str(chemin)) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                texte_pages.append(t)
                tbls = page.extract_tables() or []
                for tbl in tbls:
                    if tbl:
                        tableaux.append([[str(cell or "") for cell in row] for row in tbl])
    except Exception as exc:
        logger.warning("Erreur pdfplumber sur %s : %s", chemin, exc)

    return "\n".join(texte_pages), tableaux


def extraire_pdf(chemin: Path) -> ResultatExtraction:
    """Pipeline complet d'extraction patrimoine depuis un PDF.

    1. Tente extraction de texte via pdfplumber
    2. Si peu de texte (PDF scanné) → fallback OCR Tesseract
    3. Détecte l'émetteur (signatures)
    4. Applique le template correspondant si trouvé
    5. Sinon retourne texte + tableaux bruts pour revue manuelle
    """
    from src.import_patrimoine.detecteur_emetteur import detecter_emetteur
    from src.import_patrimoine.ocr import detecter_pdf_scanne, extraire_via_ocr
    from src.import_patrimoine.parseur_template import appliquer_template, charger_template

    nom_pdf = chemin.name
    pdf_hash = _sha256(chemin)
    avertissements: list[str] = []

    # 1. Extraction texte natif
    texte_brut, tableaux_bruts = _extraire_texte_pdfplumber(chemin)

    via_ocr = False

    # 2. Fallback OCR si PDF scanné
    if detecter_pdf_scanne(chemin):
        avertissements.append("PDF scanné détecté — fallback OCR activé.")
        texte_ocr = extraire_via_ocr(chemin)
        if texte_ocr:
            texte_brut = texte_ocr
            via_ocr = True
        else:
            avertissements.append("OCR indisponible ou a échoué — revue manuelle nécessaire.")

    # 3. Détection émetteur
    emetteur_detecte, template_utilise = detecter_emetteur(texte_brut)

    if emetteur_detecte is None:
        avertissements.append(
            "Émetteur non reconnu — aucun template appliqué. Revue manuelle recommandée."
        )

    # 4. Application du template
    lignes: list[LignePatrimoine] = []
    if template_utilise:
        try:
            tpl = charger_template(template_utilise)
            tpl["_fichier"] = template_utilise
            lignes = appliquer_template(tpl, texte_brut, tableaux_bruts, nom_pdf, via_ocr=via_ocr)
        except Exception as exc:
            logger.warning("Erreur application template %s : %s", template_utilise, exc)
            avertissements.append(f"Erreur template : {exc}")

    # 5. Si aucune ligne extraite via template, créer des lignes brutes depuis tableaux
    if not lignes and tableaux_bruts:
        avertissements.append("Aucune ligne extraite via template — tableaux bruts disponibles.")

    if not lignes and not tableaux_bruts and not texte_brut:
        avertissements.append("PDF vide ou illisible — aucune donnée extraite.")

    return ResultatExtraction(
        pdf_nom=nom_pdf,
        pdf_hash=pdf_hash,
        emetteur_detecte=emetteur_detecte,
        template_utilise=template_utilise,
        lignes=lignes,
        avertissements=avertissements,
        texte_brut=texte_brut,
        tableaux_bruts=tableaux_bruts,
    )
