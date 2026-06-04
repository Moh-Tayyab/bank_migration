"""
T5: Date Validator for WorldCheck data.

This module validates and formats dates to ISO 8601 standard (YYYY-MM-DD).

Supported Input Formats:
    - YYYY-MM-DD (ISO 8601)
    - DD/MM/YYYY (European)
    - MM-DD-YYYY (US)
    - YYYY/MM/DD

Validations:
    - Date must be valid (not invalid like Feb 30)
    - Date must not be in the future (unless configured otherwise)
    - For LastUpdatedDate: must be >= AddedDate

Output Format:
    - ISO 8601: YYYY-MM-DD
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseTransformer, TransformationResult, TransformationSeverity


@dataclass
class DateValidationResult:
    """Result of date validation."""

    is_valid: bool
    formatted_date: Optional[str]
    original_value: Any
    error_message: Optional[str] = None
    is_future: bool = False


class DateValidator(BaseTransformer):
    """
    Validates and formats dates to ISO 8601 standard.

    WorldCheck dates can be in various formats. This validator:
    1. Parses the date from multiple possible formats
    2. Validates the date is real (e.g., not Feb 30)
    3. Ensures date is not in the future (configurable)
    4. Returns ISO 8601 formatted date
    """

    # Supported date formats
    DATE_FORMATS = [
        "%Y-%m-%d",  # ISO 8601
        "%d/%m/%Y",  # European
        "%m-%d-%Y",  # US
        "%Y/%m/%d",  # Alternative ISO
        "%d-%m-%Y",  # European with hyphens
        "%m/%d/%Y",  # US with slashes
        "%Y%m%d",  # Compact
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.transformation_name = "T5-DateValidator"

        # Configuration options
        self.allow_future = config.get("allow_future", False) if config else False
        self.max_past_years = config.get("max_past_years", 100) if config else 100

    def transform(self, source_record: Dict[str, Any]) -> TransformationResult:
        """
        Validate and format dates from source record.

        This validates both 'entered' (AddedDate) and 'updated' (LastUpdatedDate) fields.

        Args:
            source_record: Dict with 'entered' and 'updated' fields

        Returns:
            TransformationResult with formatted dates
        """
        entered = self._safe_get(source_record, "entered")
        updated = self._safe_get(source_record, "updated")

        result = TransformationResult(
            success=True, data={}, confidence=1.0, transformation_applied=self.transformation_name
        )

        # Validate entered date
        entered_result = self.validate_and_format_date(entered, "entered")
        if not entered_result.is_valid:
            result.success = False
            result.add_issue(
                code="DATE_001",
                message=f"Invalid entered date: {entered_result.error_message}",
                severity=TransformationSeverity.CRITICAL,
                field="entered",
                source_value=entered,
            )
            result.requires_review = True

        # Validate updated date
        updated_result = self.validate_and_format_date(updated, "updated")
        if not updated_result.is_valid:
            result.success = False
            result.add_issue(
                code="DATE_002",
                message=f"Invalid updated date: {updated_result.error_message}",
                severity=TransformationSeverity.CRITICAL,
                field="updated",
                source_value=updated,
            )
            result.requires_review = True

        # Cross-field validation: updated >= entered
        if entered_result.is_valid and updated_result.is_valid:
            entered_dt = datetime.strptime(entered_result.formatted_date, "%Y-%m-%d")
            updated_dt = datetime.strptime(updated_result.formatted_date, "%Y-%m-%d")

            if updated_dt < entered_dt:
                result.add_issue(
                    code="DATE_003",
                    message="LastUpdatedDate cannot be before AddedDate",
                    severity=TransformationSeverity.CRITICAL,
                    field="updated",
                    source_value=updated,
                )
                result.requires_review = True
                result.confidence = 0.70

            # Warn if dates are too far in the past
            years_old = (datetime.now() - entered_dt).days / 365.25
            if years_old > self.max_past_years:
                result.add_issue(
                    code="DATE_004",
                    message=f"AddedDate is very old ({years_old:.0f} years)",
                    severity=TransformationSeverity.WARNING,
                    field="entered",
                    source_value=entered,
                )

        result.data = {
            "AddedDate": entered_result.formatted_date if entered_result.is_valid else None,
            "LastUpdatedDate": updated_result.formatted_date if updated_result.is_valid else None,
            "EnteredValid": entered_result.is_valid,
            "UpdatedValid": updated_result.is_valid,
        }

        return result

    def validate_and_format_date(self, date_value: Any, field_name: str) -> DateValidationResult:
        """
        Validate and format a single date value.

        Args:
            date_value: Date value to validate
            field_name: Name of the field (for error messages)

        Returns:
            DateValidationResult with validation outcome
        """
        original_value = date_value

        if self._is_null_or_empty(date_value):
            return DateValidationResult(
                is_valid=False,
                formatted_date=None,
                original_value=original_value,
                error_message=f"{field_name} is required and cannot be empty",
            )

        date_str = str(date_value).strip()

        # Try parsing with each format
        for fmt in self.DATE_FORMATS:
            try:
                parsed = datetime.strptime(date_str, fmt)

                # Validate not in future
                if not self.allow_future and parsed.date() > datetime.now().date():
                    return DateValidationResult(
                        is_valid=False,
                        formatted_date=None,
                        original_value=original_value,
                        error_message=f"{field_name} cannot be in the future",
                        is_future=True,
                    )

                # Return ISO formatted date
                return DateValidationResult(
                    is_valid=True, formatted_date=parsed.strftime("%Y-%m-%d"), original_value=original_value
                )

            except ValueError:
                continue

        # No format matched
        return DateValidationResult(
            is_valid=False,
            formatted_date=None,
            original_value=original_value,
            error_message=f"{field_name} has invalid format, expected formats: {', '.join(self.DATE_FORMATS)}",
        )

    def validate_date_range(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Validate that end_date >= start_date.

        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format

        Returns:
            Validation result
        """
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")

            return {
                "valid": end >= start,
                "days_difference": (end - start).days,
                "message": "Valid" if end >= start else "End date before start date",
            }
        except ValueError as e:
            return {"valid": False, "error": str(e)}

    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported date formats.

        Returns:
            List of format strings
        """
        return self.DATE_FORMATS.copy()

    def add_custom_format(self, format_string: str) -> None:
        """
        Add a custom date format.

        Args:
            format_string: Python strptime format string
        """
        self.DATE_FORMATS.append(format_string)
