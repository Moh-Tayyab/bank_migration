from typing import Dict, Any, List, Optional, Iterator
import copy
from datetime import datetime

class TransactionManager:
    def __init__(self):
        self._in_transaction = False
        self._savepoints: Dict[str, Any] = {}
        self._committed: List[Dict[str, Any]] = []
        self._failed_records: Dict[str, Any] = {}
        self._rolled_back = False

    def begin(self):
        self._in_transaction = True
        self._savepoints = {}
        self._committed = []
        self._failed_records = {}
        self._rolled_back = False

    def savepoint(self, record_id: str, data: Optional[Dict] = None):
        if not self._in_transaction:
            raise RuntimeError("No active transaction")
        self._savepoints[record_id] = copy.deepcopy(data) if data else None

    def mark_failed(self, record_id: str, error: str):
        """Dead Letter Queue (DLQ) implementation: track failures without aborting."""
        self._failed_records[record_id] = {"error": error, "timestamp": datetime.utcnow().isoformat()}

    def commit(self) -> List[Dict[str, Any]]:
        if not self._in_transaction:
            raise RuntimeError("No active transaction")
        self._committed = [v for v in self._savepoints.values() if v is not None]
        self._in_transaction = False
        return self._committed

    def rollback(self, to_savepoint: Optional[str] = None):
        if not self._in_transaction:
            return
        if to_savepoint:
            keys_to_remove = []
            for key in self._savepoints:
                if key == to_savepoint:
                    break
                keys_to_remove.append(key)
            for key in keys_to_remove:
                del self._savepoints[key]
        else:
            self._savepoints = {}
            self._rolled_back = True
            self._in_transaction = False

    @property
    def is_active(self) -> bool:
        return self._in_transaction

    @property
    def is_rolled_back(self) -> bool:
        return self._rolled_back

    def get_savepoint(self, record_id: str) -> Optional[Dict]:
        return self._savepoints.get(record_id)

    def get_failed_records(self) -> Dict[str, Any]:
        return self._failed_records
