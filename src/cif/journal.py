from __future__ import annotations

import base64
import hashlib
import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

SALT_FIXE = b"bogleheads_cif_v1"
VERSION_APP = "0.8.0"


def _derive_key(passphrase: str) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT_FIXE,
        iterations=100000,
    )
    key = kdf.derive(passphrase.encode())
    return base64.urlsafe_b64encode(key)


class JournalConseils:
    """Journal d'audit des conseils — sqlite3 + Fernet (AES-256)."""

    def __init__(self, db_path: Path, passphrase: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(_derive_key(passphrase))
        logger.info("JournalConseils: backend sqlite3+Fernet (chiffrement AES-256)")
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conseils (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    date_heure TEXT NOT NULL,
                    type_conseil TEXT NOT NULL,
                    contenu_json_chiffre BLOB NOT NULL,
                    contenu_hash TEXT NOT NULL,
                    supports_remis TEXT,
                    signature_client TEXT,
                    signature_ec TEXT,
                    version_app TEXT DEFAULT '0.8.0'
                )
            """)
            conn.commit()

    def ajouter_conseil(
        self,
        client_id: str,
        type_conseil: str,
        contenu: dict,
        supports_remis: str | None = None,
        signature_client: str | None = None,
        signature_ec: str | None = None,
    ) -> str:
        conseil_id = str(uuid.uuid4())
        date_heure = datetime.utcnow().isoformat()
        contenu_json = json.dumps(contenu, ensure_ascii=False)
        contenu_hash = hashlib.sha256(contenu_json.encode()).hexdigest()
        contenu_chiffre = self._fernet.encrypt(contenu_json.encode())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO conseils
                    (id, client_id, date_heure, type_conseil, contenu_json_chiffre,
                     contenu_hash, supports_remis, signature_client, signature_ec, version_app)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conseil_id,
                    client_id,
                    date_heure,
                    type_conseil,
                    contenu_chiffre,
                    contenu_hash,
                    supports_remis,
                    signature_client,
                    signature_ec,
                    VERSION_APP,
                ),
            )
            conn.commit()
        return conseil_id

    def lire_conseils(self, client_id: str | None = None) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            if client_id:
                rows = conn.execute(
                    "SELECT * FROM conseils WHERE client_id = ? ORDER BY date_heure DESC",
                    (client_id,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM conseils ORDER BY date_heure DESC").fetchall()
        result = []
        for row in rows:
            try:
                contenu_json = self._fernet.decrypt(row[4]).decode()
                contenu = json.loads(contenu_json)
            except Exception:
                contenu = {}
            result.append(
                {
                    "id": row[0],
                    "client_id": row[1],
                    "date_heure": row[2],
                    "type_conseil": row[3],
                    "contenu": contenu,
                    "contenu_hash": row[5],
                    "supports_remis": row[6],
                    "signature_client": row[7],
                    "signature_ec": row[8],
                    "version_app": row[9],
                }
            )
        return result

    def purger_client(self, client_id: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM conseils WHERE client_id = ?", (client_id,))
            conn.commit()
            return cursor.rowcount

    def __len__(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM conseils").fetchone()
            return row[0] if row else 0


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 3 and sys.argv[1] == "purge":
        client_id = sys.argv[2]
        db = sys.argv[3] if len(sys.argv) > 3 else "data/journal_cif.db"
        passphrase = sys.argv[4] if len(sys.argv) > 4 else "changeme"
        journal = JournalConseils(Path(db), passphrase)
        n = journal.purger_client(client_id)
        print(f"Purge client {client_id}: {n} enregistrement(s) supprimé(s)")
