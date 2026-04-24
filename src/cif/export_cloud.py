from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def exporter_vers_s3(
    fichier: Path,
    bucket: str,
    cle_s3: str,
    config_aws: dict | None = None,
) -> bool:
    """
    Stub d'export vers AWS S3.

    Parameters
    ----------
    fichier : fichier local à uploader
    bucket : nom du bucket S3
    cle_s3 : clé (chemin) dans le bucket
    config_aws : configuration AWS (region, credentials, etc.)

    Returns
    -------
    bool — True si succès (stub retourne toujours False)
    """
    logger.warning(
        "export_cloud: stub S3 — boto3 non disponible. Fichier %s non uploadé vers s3://%s/%s",
        fichier,
        bucket,
        cle_s3,
    )
    return False


def exporter_vers_azure(
    fichier: Path,
    container: str,
    blob_name: str,
    connection_string: str | None = None,
) -> bool:
    """
    Stub d'export vers Azure Blob Storage.

    Returns
    -------
    bool — True si succès (stub retourne toujours False)
    """
    logger.warning(
        "export_cloud: stub Azure — azure-storage-blob non disponible. Fichier %s non uploadé.",
        fichier,
    )
    return False


def archiver_dossier_client(
    client_id: str,
    fichiers: list[Path],
    config: Any = None,
) -> dict[str, Any]:
    """
    Archive les fichiers d'un dossier client (stub).

    Returns
    -------
    dict avec statut et liste des fichiers
    """
    return {
        "statut": "stub",
        "client_id": client_id,
        "nb_fichiers": len(fichiers),
        "message": "Export cloud non configuré — stub S5",
    }
