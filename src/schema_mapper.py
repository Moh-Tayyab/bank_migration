from typing import Any, Dict, Optional

from .models import Record
from .registry import BankRegistry


class SchemaMapper:
    def __init__(self, registry: Optional[BankRegistry] = None):
        self._registry = registry or BankRegistry()

    def map_record(
        self,
        record: Record,
        target_bank: str,
        version: str = "latest",
    ) -> Record:
        mappings = self._registry.get_mappings(record.source_bank, target_bank)
        if not mappings:
            return record
        mapped_data: Dict[str, Any] = {}
        for mapping in mappings:
            value = record.data.get(mapping.source_field, mapping.default)
            if mapping.transform:
                value = self._apply_transform(value, mapping.transform)
            mapped_data[mapping.target_field] = value
        record.data = mapped_data
        record.target_bank = target_bank
        return record

    def _apply_transform(self, value: Any, transform: str) -> Any:
        if value is None:
            return value
        str_value = str(value)
        transforms = {
            "upper": lambda v: str(v).upper(),
            "lower": lambda v: str(v).lower(),
            "strip": lambda v: str(v).strip(),
            "title": lambda v: str(v).title(),
            "reverse": lambda v: str(v)[::-1],
        }
        handler = transforms.get(transform)
        if handler:
            return handler(value)
        if transform.startswith("prefix:"):
            return transform.split(":", 1)[1] + str(value)
        if transform.startswith("suffix:"):
            return str(value) + transform.split(":", 1)[1]
        if transform.startswith("substring:"):
            parts = transform.split(":")[1].split(",")
            start, end = int(parts[0]), int(parts[1])
            return str_value[start:end]
        return value
