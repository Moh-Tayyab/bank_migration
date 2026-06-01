import json
from typing import Any, Dict, List
from ..models import MigrationResult


class JSONWriter:
    def write(self, result: MigrationResult, output_path: str):
        data = {
            "migration_result": {
                "success": result.success,
                "total_records": result.total_records,
                "processed": result.processed,
                "failed": result.failed,
                "output_path": result.output_path,
                "started_at": result.started_at.isoformat() if result.started_at else None,
                "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                "error": result.error,
            },
            "records": result.records,
            "audit_trail": [e.model_dump() for e in result.audit_trail],
        }
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)