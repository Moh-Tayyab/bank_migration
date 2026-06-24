import base64
import logging
import os
from typing import Dict, List, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .config import settings
from .infrastructure.db import DatabaseManager
from .models import CanonicalRecord

logger = logging.getLogger(__name__)


class _MemoryStore:
    def __init__(self):
        self._records: Dict[str, CanonicalRecord] = {}

    def store(self, record: CanonicalRecord) -> str:
        self._records[record.record_id] = record
        return record.record_id

    def retrieve(self, record_id: str) -> Optional[CanonicalRecord]:
        return self._records.get(record_id)

    def delete(self, record_id: str) -> bool:
        return self._records.pop(record_id, None) is not None

    def list_records(self) -> List[str]:
        return list(self._records.keys())


class CanonicalStore:
    _KEY_FILE = settings.canonical_store_dir / ".encryption_key"
    _SALT_FILE = settings.canonical_store_dir / ".salt"

    def __init__(self, encryption_key: str = "", db_manager: DatabaseManager = None):
        self._memory_store = _MemoryStore()
        self._db_available = False
        key = encryption_key or settings.canonical_encryption_key or self._load_or_create_key()
        salt = self._load_or_create_salt()
        self._fernet = Fernet(self._derive_key(key, salt))

        if db_manager is not None:
            self.db = db_manager
            self._init_db()
        else:
            self.db = DatabaseManager()
            if self.db.available:
                try:
                    self._init_db()
                    self._db_available = True
                except Exception as e:
                    logger.info("Database unavailable, using in-memory store: %s", e)
                    self.db = None
                    self._db_available = False
            else:
                self.db = None
                self._db_available = False

    def _init_db(self):
        if self.db is None:
            return
        query = """
        CREATE TABLE IF NOT EXISTS canonical_records (
            record_id VARCHAR(255) PRIMARY KEY,
            encrypted_data BYTEA,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_bank VARCHAR(100)
        );
        CREATE INDEX IF NOT EXISTS idx_record_id ON canonical_records(record_id);
        """
        self.db.execute(query)

    @staticmethod
    def _restrict_perms(path) -> None:
        """Best-effort restriction of secret file perms to owner-only.

        Some filesystems (e.g. Windows drives mounted via WSL DrvFs) cannot
        apply POSIX permission bits and raise PermissionError on os.chmod.
        The chmod is hardening only — ignore the failure there rather than
        aborting startup, since perms are governed by the mount in that case.
        """
        try:
            os.chmod(path, 0o600)
        except (PermissionError, OSError):
            logger.warning("Could not chmod %s (filesystem may not support it)", path)

    def _generate_key(self) -> str:
        return base64.urlsafe_b64encode(os.urandom(32)).decode()

    def _load_or_create_key(self) -> str:
        settings.canonical_store_dir.mkdir(parents=True, exist_ok=True)
        if self._KEY_FILE.exists():
            self._restrict_perms(self._KEY_FILE)
            return self._KEY_FILE.read_text().strip()
        logger.warning("Auto-generating encryption key — set CANONICAL_ENCRYPTION_KEY env var for production use")
        key = self._generate_key()
        self._KEY_FILE.write_text(key)
        self._restrict_perms(self._KEY_FILE)
        return key

    def _load_or_create_salt(self) -> bytes:
        settings.canonical_store_dir.mkdir(parents=True, exist_ok=True)
        if self._SALT_FILE.exists():
            self._restrict_perms(self._SALT_FILE)
            return base64.urlsafe_b64decode(self._SALT_FILE.read_text().strip())
        salt = os.urandom(16)
        self._SALT_FILE.write_text(base64.urlsafe_b64encode(salt).decode())
        self._restrict_perms(self._SALT_FILE)
        return salt

    def _derive_key(self, key: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600000)
        return base64.urlsafe_b64encode(kdf.derive(key.encode()))

    def store(self, record: CanonicalRecord) -> str:
        if not self._db_available:
            return self._memory_store.store(record)
        data = record.model_dump_json().encode()
        encrypted = self._fernet.encrypt(data)
        query = (
            "INSERT INTO canonical_records (record_id, encrypted_data, source_bank) "
            "VALUES (%s, %s, %s) ON CONFLICT (record_id) DO UPDATE SET "
            "encrypted_data = EXCLUDED.encrypted_data"
        )
        self.db.execute(query, (record.record_id, encrypted, record.source_bank))
        record.encrypted = True
        return record.record_id

    def retrieve(self, record_id: str) -> Optional[CanonicalRecord]:
        if not self._db_available:
            return self._memory_store.retrieve(record_id)
        query = "SELECT encrypted_data FROM canonical_records WHERE record_id = %s"
        res = self.db.execute(query, (record_id,))
        if not res:
            return None
        encrypted = bytes(res[0]["encrypted_data"])
        decrypted = self._fernet.decrypt(encrypted)
        return CanonicalRecord.model_validate_json(decrypted)

    def delete(self, record_id: str) -> bool:
        if not self._db_available:
            return self._memory_store.delete(record_id)
        query = "DELETE FROM canonical_records WHERE record_id = %s"
        self.db.execute(query, (record_id,))
        return True

    def list_records(self) -> List[str]:
        if not self._db_available:
            return self._memory_store.list_records()
        query = "SELECT record_id FROM canonical_records"
        res = self.db.execute(query)
        return [r["record_id"] for r in res] if res else []
