import os
from datetime import datetime
from typing import List

from .config import settings
from .models import AuditEntry, AuditEvent


class AuditLogger:
    def __init__(self, migration_id: str = ""):
        self.migration_id = migration_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self._entries: List[AuditEntry] = []
        self._log_path = settings.log_dir / f"audit_{self.migration_id}.jsonl"
        os.makedirs(settings.log_dir, exist_ok=True)

    def log(
        self,
        event: AuditEvent,
        record_id: str = "",
        bank_pair: str = "",
        details: str = "",
    ) -> AuditEntry:
        entry = AuditEntry(
            event=event,
            record_id=record_id,
            bank_pair=bank_pair,
            details=details,
        )
        self._entries.append(entry)
        self._write_entry(entry)
        return entry

    def _write_entry(self, entry: AuditEntry) -> None:
        with open(self._log_path, "a") as f:
            f.write(entry.model_dump_json() + "\n")

    def get_trail(self) -> List[AuditEntry]:
        return self._entries

    def get_log_path(self) -> str:
        return str(self._log_path)

    @staticmethod
    def read_trail(log_path: str) -> List[AuditEntry]:
        entries = []
        if os.path.exists(log_path):
            with open(log_path) as f:
                for line in f:
                    if line.strip():
                        entries.append(AuditEntry.model_validate_json(line))
        return entries
