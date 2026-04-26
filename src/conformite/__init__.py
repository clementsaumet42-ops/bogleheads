"""Sous-package conformité CIF — Sprint S14.

Génération automatique des documents réglementaires CIF :
- DER (Document d'Entrée en Relation) — art. 325-5 RG AMF
- Lettre de Mission CIF — art. 325-3 RG AMF
- Rapport d'Adéquation MIF II — art. 25(6) MIF II

Signature simple eIDAS (checkbox + horodatage UTC + SHA256).
Archivage horodaté + manifest JSON append-only.
"""

from __future__ import annotations

from src.conformite.archivage import (
    archiver_document,
    lister_documents_client,
    verifier_integrite_dossier,
)
from src.conformite.der import generer_der
from src.conformite.lettre_mission import generer_lettre_mission
from src.conformite.rapport_adequation import generer_rapport_adequation
from src.conformite.signature import signer_document

__all__ = [
    "generer_der",
    "generer_lettre_mission",
    "generer_rapport_adequation",
    "signer_document",
    "archiver_document",
    "lister_documents_client",
    "verifier_integrite_dossier",
]
