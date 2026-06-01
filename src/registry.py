import json
import os
from typing import Dict, List, Optional

from .models import BankSchema, MappingRule
from .schema_version import SchemaVersionManager


class BankRegistry:
    def __init__(self, config_dir: str = "config/bank_schemas"):
        self._config_dir = config_dir
        self._version_manager = SchemaVersionManager(config_dir)
        self._schemas: Dict[str, Dict[str, BankSchema]] = {}
        self._load_all()

    def _load_all(self):
        os.makedirs(self._config_dir, exist_ok=True)
        for bank in os.listdir(self._config_dir):
            bank_dir = os.path.join(self._config_dir, bank)
            if not os.path.isdir(bank_dir):
                continue
            for version_file in os.listdir(bank_dir):
                if not version_file.endswith(".json"):
                    continue
                version = version_file.replace(".json", "")
                filepath = os.path.join(bank_dir, version_file)
                with open(filepath) as f:
                    data = json.load(f)
                schema = BankSchema(
                    bank_name=bank,
                    version=version,
                    fields=data.get("fields", {}),
                    mappings=[MappingRule(**m) for m in data.get("mappings", [])],
                    masking_rules=data.get("masking_rules", {}),
                )
                if bank not in self._schemas:
                    self._schemas[bank] = {}
                self._schemas[bank][version] = schema

    def register_bank(self, bank: str, schema: BankSchema) -> str:
        path = self._version_manager.save_schema(
            bank,
            schema.version,
            {
                "fields": schema.fields,
                "mappings": [m.model_dump() for m in schema.mappings],
                "masking_rules": schema.masking_rules,
            },
        )
        if bank not in self._schemas:
            self._schemas[bank] = {}
        self._schemas[bank][schema.version] = schema
        return path

    def get_schema(self, bank: str, version: str = "latest") -> Optional[BankSchema]:
        versions = self._schemas.get(bank, {})
        if not versions:
            return None
        if version == "latest":
            sorted_keys = sorted(versions.keys(), key=self._version_sort_key)
            return versions[sorted_keys[-1]] if sorted_keys else None
        return versions.get(version)

    @staticmethod
    def _version_sort_key(v: str) -> list:
        try:
            return [int(x) for x in v.lstrip("v").split(".")]
        except (ValueError, AttributeError):
            return [0]

    def get_mappings(self, source_bank: str, target_bank: str) -> List[MappingRule]:
        target = self.get_schema(target_bank)
        if not target:
            return []
        return target.mappings

    def list_banks(self) -> List[str]:
        return list(self._schemas.keys())

    def get_masking_rules(self, bank: str, version: str = "latest") -> Dict[str, str]:
        schema = self.get_schema(bank, version)
        if not schema:
            return {}
        return schema.masking_rules

    def detect_target_bank(self, columns: List[str], exclude_banks: Optional[List[str]] = None) -> Optional[str]:
        """
        Detect the best matching target bank based on column overlap.

        Args:
            columns: List of column names from the uploaded file
            exclude_banks: Banks to exclude from detection (e.g., source bank)

        Returns:
            The bank name with the highest field overlap, or None if no match found
        """
        exclude = set(exclude_banks or [])
        column_set = set(col.lower() for col in columns)

        best_match = None
        best_score = 0

        for bank in self._schemas:
            if bank in exclude:
                continue
            schema = self.get_schema(bank, "latest")
            if not schema:
                continue

            schema_fields = set(f.lower() for f in schema.fields.keys())
            overlap = column_set & schema_fields
            score = len(overlap)

            if score > best_score:
                best_score = score
                best_match = bank

        # Only return a match if there's at least some overlap
        if best_score > 0:
            return best_match
        return None
