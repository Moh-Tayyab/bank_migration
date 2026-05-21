from typing import Dict, Optional, List
from pydantic import BaseModel
from datetime import datetime
import json
import os


class SchemaVersion(BaseModel):
    bank_name: str
    version: str
    parent_version: Optional[str] = None
    changelog: str = ""
    created_at: datetime = datetime.utcnow()
    fields: Dict[str, dict] = {}
    is_active: bool = True


class SchemaVersionManager:
    def __init__(self, registry_path: str = "config/bank_schemas"):
        self._registry_path = registry_path
        os.makedirs(registry_path, exist_ok=True)

    def _version_path(self, bank: str, version: str) -> str:
        filename = f"{version}.json" if version.endswith(".json") else f"{version}.json"
        return os.path.join(self._registry_path, bank, filename)

    def save_schema(self, bank: str, version: str, schema: Dict) -> str:
        bank_dir = os.path.join(self._registry_path, bank)
        os.makedirs(bank_dir, exist_ok=True)
        path = self._version_path(bank, version)
        with open(path, "w") as f:
            json.dump(schema, f, indent=2)
        return path

    def load_schema(self, bank: str, version: str) -> Optional[Dict]:
        path = self._version_path(bank, version)
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return None

    def list_versions(self, bank: str) -> List[str]:
        bank_dir = os.path.join(self._registry_path, bank)
        if not os.path.exists(bank_dir):
            return []
        return sorted(
            f.replace(".json", "").lstrip("v")
            for f in os.listdir(bank_dir)
            if f.endswith(".json")
        )

    def migrate_schema(
        self, bank: str, from_version: str, to_version: str, record: Dict
    ) -> Dict:
        from_schema = self.load_schema(bank, from_version)
        to_schema = self.load_schema(bank, to_version)
        if not from_schema or not to_schema:
            raise ValueError(f"Schema versions {from_version} -> {to_version} not found")
        migrated = {}
        for field, config in to_schema.get("fields", {}).items():
            source_field = config.get("migrated_from", field)
            migrated[field] = record.get(source_field, config.get("default"))
        return migrated