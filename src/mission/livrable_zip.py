"""Assemblage du ZIP final de mission.

Le livrable final est un fichier ZIP contenant :
- Le diagnostic PDF (8 pages)
- L'allocation PDF (1 page)
- Le plan d'action PDF (3 pages)
- Le RAA MIF II signé eIDAS
- Le DER + LM signés eIDAS
- Le journal d'audit JSON
"""

from __future__ import annotations

from pathlib import Path


def assembler_zip_mission(chemin_dossier: Path) -> Path:
    """Assemble le ZIP complet d'une mission. À implémenter S+1."""
    raise NotImplementedError("Sprint S+1")
