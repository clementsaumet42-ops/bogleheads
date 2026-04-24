"""Modèle de données pour les explications pédagogiques."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Explication(BaseModel):
    """Unité d'explication pédagogique — texte court + long, source, formule, impact."""

    model_config = ConfigDict(extra="allow")

    section: str
    """Identifiant de section, ex: 'allocation.mode_simple'."""

    titre: str
    """Titre court affiché en en-tête d'expander, ex: 'Pourquoi 85 % ACWI ?'."""

    texte_court: str
    """1-2 phrases pour le titre d'expander ou le résumé."""

    texte_long: str
    """3-6 phrases pour l'expander ouvert ou le PDF."""

    formule: str | None = None
    """LaTeX ou texte lisible, ex: 'σ²_p = Σ w_i·w_j·σ_ij'."""

    source: str = ""
    """Référence académique ou réglementaire, ex: 'Art. 125-0 A CGI'."""

    alternative_ecartee: str | None = None
    """Description de l'option non retenue et de la raison."""

    gain_eur: float | None = None
    """Impact chiffré en euros si applicable."""

    variables_contexte: dict[str, str] = Field(default_factory=dict)
    """Données contextuelles utiles au rendu : nom_client, profil, patrimoine_total, etc."""
