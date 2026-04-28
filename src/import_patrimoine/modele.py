"""Modèles Pydantic pour l'import patrimoine depuis PDF."""

from __future__ import annotations

import re

from pydantic import BaseModel, field_validator


class LignePatrimoine(BaseModel):
    isin: str | None = None
    nom_actif: str
    quantite: float | None = None
    valorisation_eur: float
    enveloppe: str  # "PEA" | "AV" | "PER" | "CTO" | "Livret" | "Compte courant" | ...
    broker_emetteur: str
    contrat_av: str | None = None
    type_actif: str  # "Action" | "ETF" | "OPCVM" | "Fonds €" | "UC" | "Cash" | ...
    devise: str = "EUR"
    confiance: int = 0  # 0-100
    source_pdf: str
    source_page: int = 1
    methode_extraction: str  # "template:bourse_direct" | "ocr" | "manuel"

    @field_validator("isin")
    @classmethod
    def valider_isin(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not re.match(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$", v):
            return None
        return v

    @field_validator("confiance")
    @classmethod
    def valider_confiance(cls, v: int) -> int:
        return max(0, min(100, v))


class ImportPDF(BaseModel):
    pdf_nom: str
    pdf_hash: str
    timestamp_import: str
    emetteur_detecte: str | None = None
    template_utilise: str | None = None
    lignes_validees: list[LignePatrimoine] = []
    lignes_rejetees: list[LignePatrimoine] = []


class ResultatExtraction(BaseModel):
    pdf_nom: str
    pdf_hash: str
    emetteur_detecte: str | None = None
    template_utilise: str | None = None
    lignes: list[LignePatrimoine] = []
    avertissements: list[str] = []
    texte_brut: str = ""
    tableaux_bruts: list[list[list[str]]] = []
