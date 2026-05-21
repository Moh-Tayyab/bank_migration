from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from .models import Record


class ValidationError(Exception):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class ValidationResult:
    def __init__(self):
        self.errors: List[ValidationError] = []
        self.warnings: List[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, field: str, message: str):
        self.errors.append(ValidationError(field, message))

    def add_warning(self, message: str):
        self.warnings.append(message)


class Validator:
    def __init__(self, rules: Optional[Dict[str, Dict]] = None):
        self._rules = rules or {}

    def validate(self, record: Record) -> ValidationResult:
        result = ValidationResult()
        data = record.data

        all_fields = set(data.keys()) | set(self._rules.keys())
        for field in all_fields:
            value = data.get(field)
            rules = self._rules.get(field, {})
            field_rules = FieldRules(rules)
            field_rules.validate(field, value, result, data)

        return result

    def validate_batch(self, records: List[Record]) -> List[ValidationResult]:
        return [self.validate(r) for r in records]


class FieldRules:
    def __init__(self, rules: Dict):
        self.required = rules.get("required", False)
        self.field_type = rules.get("type")
        self.min_length = rules.get("min_length")
        self.max_length = rules.get("max_length")
        self.pattern = rules.get("pattern")
        self.min_value = rules.get("min_value")
        self.max_value = rules.get("max_value")
        allowed = rules.get("allowed_values")
        self.allowed_values = set(allowed) if allowed else None

    def validate(self, field: str, value: Any, result: ValidationResult, data: Dict):
        if self.required and (value is None or str(value).strip() == ""):
            result.add_error(field, f"Required field '{field}' is empty")
            return

        if value is None or str(value).strip() == "":
            return

        if self.field_type:
            type_ok = self._check_type(value, self.field_type)
            if not type_ok:
                result.add_error(field, f"Field '{field}' expected {self.field_type}, got {type(value).__name__}")

        if self.min_length is not None and len(str(value)) < self.min_length:
            result.add_error(field, f"Field '{field}' below minimum length {self.min_length}")

        if self.max_length is not None and len(str(value)) > self.max_length:
            result.add_error(field, f"Field '{field}' exceeds maximum length {self.max_length}")

        if self.allowed_values is not None and value not in self.allowed_values:
            result.add_error(field, f"Field '{field}' value '{value}' not in allowed set")

    def _check_type(self, value: Any, expected: str) -> bool:
        type_map = {
            "str": str,
            "int": int,
            "float": float,
            "number": (int, float),
            "email": str,
            "date": str,
            "phone": str,
        }
        py_type = type_map.get(expected)
        if py_type is None:
            return True
        if expected == "email":
            return isinstance(value, str) and "@" in value
        if expected == "date":
            if not isinstance(value, str):
                return False
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y"):
                try:
                    datetime.strptime(value, fmt)
                    return True
                except ValueError:
                    continue
            return False
        if expected == "phone":
            return isinstance(value, str) and len(value) >= 7
        return isinstance(value, py_type)