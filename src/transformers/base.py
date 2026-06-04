"""
Base transformer classes for WorldCheck transformation engine.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class TransformationSeverity(Enum):
    """Severity level for transformation issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class TransformationIssue:
    """Represents an issue detected during transformation."""

    code: str
    message: str
    severity: TransformationSeverity = TransformationSeverity.WARNING
    field: Optional[str] = None
    source_value: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "field": self.field,
            "source_value": str(self.source_value) if self.source_value is not None else None,
        }


@dataclass
class TransformationResult:
    """Result of a transformation operation."""

    success: bool
    data: Dict[str, Any]
    issues: List[TransformationIssue] = field(default_factory=list)
    confidence: float = 1.0
    requires_review: bool = False
    transformation_applied: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "issues": [issue.to_dict() for issue in self.issues],
            "confidence": self.confidence,
            "requires_review": self.requires_review,
            "transformation_applied": self.transformation_applied,
        }

    def add_issue(
        self,
        code: str,
        message: str,
        severity: TransformationSeverity = TransformationSeverity.WARNING,
        field: Optional[str] = None,
        source_value: Optional[Any] = None,
    ) -> None:
        """Add an issue to the transformation result."""
        self.issues.append(
            TransformationIssue(code=code, message=message, severity=severity, field=field, source_value=source_value)
        )


class BaseTransformer(ABC):
    """
    Abstract base class for all transformers.

    All transformers must implement the transform method which takes
    a source record and returns a TransformationResult.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the transformer.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.transformation_name = self.__class__.__name__

    @abstractmethod
    def transform(self, source_record: Dict[str, Any]) -> TransformationResult:
        """
        Transform the source record.

        Args:
            source_record: The source data record

        Returns:
            TransformationResult with transformed data and any issues
        """
        pass

    def _safe_get(self, record: Dict[str, Any], field: str, default: Any = None) -> Any:
        """
        Safely get a value from a record, returning default if not found or None.

        Args:
            record: Source record
            field: Field name to retrieve
            default: Default value if field is missing or None

        Returns:
            Field value or default
        """
        value = record.get(field)
        if value is None:
            return default
        return value

    def _is_null_or_empty(self, value: Any) -> bool:
        """
        Check if a value is None or empty string.

        Args:
            value: Value to check

        Returns:
            True if value is None or empty
        """
        if value is None:
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        return False

    def _log_transformation(
        self,
        source_record: Dict[str, Any],
        result: TransformationResult,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a log entry for the transformation.

        Args:
            source_record: Original source record
            result: Transformation result
            additional_info: Additional information to log

        Returns:
            Log entry dictionary
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "transformation": self.transformation_name,
            "success": result.success,
            "confidence": result.confidence,
            "requires_review": result.requires_review,
            "issues_count": len(result.issues),
            "input": {k: str(v) if v is not None else None for k, v in source_record.items()},
            "output": result.data,
            "issues": [issue.to_dict() for issue in result.issues],
        }

        if additional_info:
            log_entry["additional_info"] = additional_info

        return log_entry
