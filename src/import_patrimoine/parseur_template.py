"""Parseur de templates YAML pour l'extraction de lignes patrimoine depuis PDF."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from src.import_patrimoine.modele import LignePatrimoine


def charger_template(nom_template: str) -> dict[str, Any]:
    """Charge un template YAML par son nom de fichier (sans .yaml)."""
    chemin = Path(__file__).parent / "templates" / f"{nom_template}.yaml"
    if not chemin.exists():
        raise FileNotFoundError(f"Template introuvable : {nom_template}")
    with chemin.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _detecter_enveloppe(texte_contexte: str, tpl: dict[str, Any]) -> str:
    """Détecte l'enveloppe financière à partir du contexte textuel et du template."""
    detection = tpl.get("extraction", {}).get("detection_enveloppe", {})
    texte_up = texte_contexte.upper()
    for env_key, patterns in detection.items():
        for pat in patterns:
            if pat.upper() in texte_up:
                return env_key.upper()
    enveloppe_defaut = tpl.get("emetteur", {}).get("enveloppe_par_defaut_si_indetectable", "CTO")
    return enveloppe_defaut


def _parse_montant(valeur_brute: str, regex_montant: str) -> float | None:
    """Parse un montant depuis une chaîne brute.

    Essaie d'abord le regex configuré. Si le résultat semble incomplet
    (ex : "123" au lieu de "1234.56"), tente aussi une extraction directe
    du nombre le plus long dans la chaîne.
    """
    texte = valeur_brute.replace("\xa0", " ").replace("\u202f", " ").strip()

    def _to_float(s: str) -> float | None:
        s = s.strip().replace(" ", "")
        if s.count(",") == 1 and s.count(".") == 0:
            s = s.replace(",", ".")
        elif s.count(".") >= 1 and s.count(",") == 1:
            s = s.replace(".", "").replace(",", ".")
        elif s.count(",") > 1:
            s = s.replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None

    # Tente le regex configuré
    m = re.search(regex_montant, texte)
    valeur_regex = None
    if m:
        valeur_regex = _to_float(m.group(1))

    # Tente un fallback plus simple (nombre décimal ou entier)
    candidats = re.findall(r"\d[\d\s.,]*\d|\d", texte)
    valeur_fallback = None
    for c in reversed(candidats):
        v = _to_float(c.strip())
        if v is not None and v > 0:
            valeur_fallback = v
            break

    # Préfère la valeur la plus grande/précise entre les deux
    if valeur_regex is not None and valeur_fallback is not None:
        # Si le fallback est significativement plus grand, préférer le fallback
        return valeur_fallback if valeur_fallback > valeur_regex * 2 else valeur_regex
    return valeur_regex if valeur_regex is not None else valeur_fallback


def _index_colonne(headers: list[str], patterns: list[str]) -> int | None:
    """Retourne l'index de la colonne correspondant aux patterns, ou None."""
    for i, h in enumerate(headers):
        for pat in patterns:
            if pat.lower() in h.lower():
                return i
    return None


def _extraire_isin_texte(texte: str, regex_isin: str) -> str | None:
    """Extrait le premier ISIN valide d'une chaîne."""
    m = re.search(regex_isin, texte)
    if m:
        return m.group(1)
    return None


def appliquer_template(
    tpl: dict[str, Any],
    texte_brut: str,
    tableaux_bruts: list[list[list[str]]],
    nom_pdf: str,
    via_ocr: bool = False,
) -> list[LignePatrimoine]:
    """Applique un template YAML aux données extraites d'un PDF.

    Retourne la liste des lignes patrimoine extraites.
    """
    from src.import_patrimoine.confiance import calculer_confiance

    nom_emetteur = tpl.get("emetteur", {}).get("nom", "Inconnu")
    nom_template = tpl.get("_fichier", "inconnu")
    methode = tpl.get("extraction", {}).get("methode", "tableau")
    regex_isin = tpl.get("regex_isin", r"\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b")
    regex_montant = tpl.get("regex_montant_eur", r"(\d[\d\s.,]*)\s*€?")
    colonnes_cfg = tpl.get("extraction", {}).get("colonnes_attendues", [])
    filtres = tpl.get("extraction", {}).get("filtres_lignes", {})
    exclure_si = [s.upper() for s in filtres.get("exclure_si_contient", [])]
    inclure_si_isin = filtres.get("inclure_si_isin", False)

    lignes: list[LignePatrimoine] = []

    if methode in ("tableau", "hybride") and tableaux_bruts:
        for tableau in tableaux_bruts:
            if not tableau:
                continue
            headers = tableau[0]
            col_map = {}
            for col_cfg in colonnes_cfg:
                idx = _index_colonne(headers, col_cfg["patterns"])
                if idx is not None:
                    col_map[col_cfg["nom"]] = idx

            enveloppe = _detecter_enveloppe(texte_brut, tpl)

            for row in tableau[1:]:
                if not any(cell.strip() for cell in row):
                    continue

                row_text = " ".join(row)
                row_up = row_text.upper()

                if any(exc in row_up for exc in exclure_si):
                    continue

                isin = None
                if "isin" in col_map and col_map["isin"] < len(row):
                    isin = _extraire_isin_texte(row[col_map["isin"]], regex_isin)
                if isin is None:
                    isin = _extraire_isin_texte(row_text, regex_isin)

                if inclure_si_isin and isin is None:
                    continue

                libelle = ""
                if "libelle" in col_map and col_map["libelle"] < len(row):
                    libelle = row[col_map["libelle"]].strip()
                if not libelle:
                    libelle = row_text[:80].strip()

                quantite = None
                if "quantite" in col_map and col_map["quantite"] < len(row):
                    quantite = _parse_montant(row[col_map["quantite"]], regex_montant)

                valorisation = None
                if "valorisation" in col_map and col_map["valorisation"] < len(row):
                    valorisation = _parse_montant(row[col_map["valorisation"]], regex_montant)
                if valorisation is None:
                    for cell in reversed(row):
                        v = _parse_montant(cell, regex_montant)
                        if v is not None and v > 0:
                            valorisation = v
                            break

                if valorisation is None or valorisation <= 0:
                    continue

                ligne = LignePatrimoine(
                    isin=isin,
                    nom_actif=libelle or "Inconnu",
                    quantite=quantite,
                    valorisation_eur=valorisation,
                    enveloppe=enveloppe,
                    broker_emetteur=nom_emetteur,
                    type_actif="ETF" if isin else "UC",
                    source_pdf=nom_pdf,
                    source_page=1,
                    methode_extraction=f"template:{nom_template}",
                    confiance=0,
                )
                score = calculer_confiance(
                    ligne,
                    template_matche=True,
                    valorisation_ambigue=False,
                    via_ocr=via_ocr,
                )
                lignes.append(ligne.model_copy(update={"confiance": score}))

    elif methode == "regex":
        enveloppe = _detecter_enveloppe(texte_brut, tpl)
        for m in re.finditer(regex_isin, texte_brut):
            isin = m.group(1)
            contexte = texte_brut[max(0, m.start() - 200) : m.end() + 200]
            valorisation = None
            for vm in re.finditer(regex_montant, contexte):
                v = _parse_montant(vm.group(0), regex_montant)
                if v and v > 0:
                    valorisation = v
                    break
            if valorisation is None:
                continue
            ligne = LignePatrimoine(
                isin=isin,
                nom_actif=isin,
                quantite=None,
                valorisation_eur=valorisation,
                enveloppe=enveloppe,
                broker_emetteur=nom_emetteur,
                type_actif="ETF",
                source_pdf=nom_pdf,
                source_page=1,
                methode_extraction=f"template:{nom_template}",
                confiance=0,
            )
            from src.import_patrimoine.confiance import calculer_confiance

            score = calculer_confiance(ligne, template_matche=True, via_ocr=via_ocr)
            lignes.append(ligne.model_copy(update={"confiance": score}))

    return lignes
