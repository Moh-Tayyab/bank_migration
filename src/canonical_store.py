
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import json
import os
from typing import Dict, Optional, List
from datetime import datetime
from .config import settings
from .models import CanonicalRecord
from .infrastructure.db import DatabaseManager

class CanonicalStore:
    def __init__(self, encryption_key: str = "", db_manager: DatabaseManager = None):
        key = encryption_key or settings.canonical_encryption_key or self._generate_key()
        self._fernet = Fernet(self._derive_key(key))
        self.db = db_manager or DatabaseManager()
        
        # Initialize Table
        self._init_db()

    def _init_db(self):
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

    def _generate_key(self) -> str:
        return base64.urlsafe_b64encode(os.urandom(32)).decode()

    def _derive_key(self, key: str) -> bytes:
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b"un_bank_migration", iterations=480000)
        return base64.urlsafe_b64encode(kdf.derive(key.encode()))

    def store(self, record: CanonicalRecord) -> str:
        # Encrypt data
        data = record.model_dump_json().encode()
        encrypted = self._fernet.encrypt(data)
        
        # Store in Postgres
        query = "INSERT INTO canonical_records (record_id, encrypted_data, source_bank) VALUES (%s, %s, %s) ON CONFLICT (record_id) DO UPDATE SET encrypted_data = EXCLUDED.encrypted_data"
        self.db.execute(query, (record.record_id, encrypted, record.source_bank))
        
        record.encrypted = True
        return record.record_id # Now returns ID instead of path

    def retrieve(self, record_id: str) -> Optional[CanonicalRecord]:
        query = "SELECT encrypted_data FROM canonical_records WHERE record_id = %s"
        res = self.db.execute(query, (record_id,))
        
        if not res:
            return None
            
        encrypted = res[0]['encrypted_data']
        decrypted = self._fernet.decrypt(encrypted)
        return CanonicalRecord.model_validate_json(decrypted)

    def delete(self, record_id: str) -> bool:
        query = "DELETE FROM canonical_records WHERE record_id = %s"
        self.db.execute(query, (record_id,))
        return True

    def list_records(self) -> List[str]:
        query = "SELECT record_id FROM canonical_records"
        res = self.db.execute(query)
        return [r['record_id'] for r in res] if res else []
