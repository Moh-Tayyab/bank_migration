"""
T1: Conditional Name Parser for WorldCheck data.

This module handles the complex name parsing logic where:
- When first_name is NULL, last_name contains the FULL ENTITY NAME
- When first_name is present, it's split across first_name and last_name

Example:
    first_name=NULL, last_name="REVOLUTIONARY ORGANIZATION 17 NOVEMBER"
    → FullName="REVOLUTIONARY ORGANIZATION 17 NOVEMBER", IsEntity=True

    first_name="Bashar", last_name="AL-ASSAD"
    → FullName="Bashar AL-ASSAD", GivenNames="Bashar", FamilyName="AL-ASSAD"
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .base import BaseTransformer, TransformationResult, TransformationSeverity


@dataclass
class NameResult:
    """Result of name parsing transformation."""

    FullName: str
    GivenNames: Optional[str]
    FamilyName: str
    NameType: str
    PrimaryName: str
    Title: Optional[str] = None
    IsEntity: bool = False
    OriginalFirstName: Optional[str] = None
    OriginalLastName: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "FullName": self.FullName,
            "GivenNames": self.GivenNames,
            "FamilyName": self.FamilyName,
            "NameType": self.NameType,
            "PrimaryName": self.PrimaryName,
            "Title": self.Title,
            "IsEntity": self.IsEntity,
            "OriginalFirstName": self.OriginalFirstName,
            "OriginalLastName": self.OriginalLastName,
        }


class ConditionalNameParser(BaseTransformer):
    """
    Parses names from WorldCheck format, handling entity names stored in last_name field.

    WorldCheck stores names inconsistently:
    - Person names: first_name and last_name contain name parts
    - Entity names: first_name is NULL, last_name contains full entity name

    This transformer detects the pattern and parses accordingly.
    """

    # Entity detection keywords
    ENTITY_KEYWORDS = [
        "organization",
        "organisation",
        "group",
        "movement",
        "party",
        "front",
        "brigade",
        "battalion",
        "forces",
        "army",
        "corps",
        "command",
        "council",
        "committee",
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.transformation_name = "T1-ConditionalNameParser"

    def transform(self, source_record: Dict[str, Any]) -> TransformationResult:
        """
        Transform WorldCheck name fields to target schema.

        Args:
            source_record: Dict with 'first_name' and 'last_name' fields

        Returns:
            TransformationResult with NameResult data
        """
        first_name = self._safe_get(source_record, "first_name")
        last_name = self._safe_get(source_record, "last_name")

        result = TransformationResult(
            success=True, data={}, confidence=1.0, transformation_applied=self.transformation_name
        )

        # Validate required fields
        if self._is_null_or_empty(last_name):
            result.success = False
            result.add_issue(
                code="NAME_001",
                message="last_name is required and cannot be empty",
                severity=TransformationSeverity.CRITICAL,
                field="last_name",
                source_value=last_name,
            )
            result.requires_review = True
            return result

        # Detect if this is an entity name (first_name is NULL)
        if self._is_null_or_empty(first_name):
            return self._parse_entity_name(last_name, result)
        else:
            return self._parse_person_name(first_name, last_name, result)

    def _parse_entity_name(self, last_name: str, result: TransformationResult) -> TransformationResult:
        """
        Parse an entity name stored in the last_name field.

        Args:
            last_name: Full entity name
            result: Transformation result to populate

        Returns:
            Updated TransformationResult
        """
        entity_name = str(last_name).strip()
        is_entity = self._detect_entity(entity_name)

        name_result = NameResult(
            FullName=entity_name,
            GivenNames=None,
            FamilyName=entity_name,
            NameType="Entity Name" if is_entity else "Primary Name",
            PrimaryName=entity_name,
            Title=None,
            IsEntity=is_entity,
            OriginalFirstName=None,
            OriginalLastName=entity_name,
        )

        result.data = name_result.to_dict()
        result.confidence = 0.85 if is_entity else 0.70
        result.transformation_applied = f"{self.transformation_name}-Entity"

        if not is_entity:
            result.add_issue(
                code="NAME_002",
                message="first_name is NULL but last_name doesn't appear to be an entity name",
                severity=TransformationSeverity.WARNING,
                field="first_name",
                source_value=None,
            )
            result.requires_review = True

        return result

    def _parse_person_name(self, first_name: str, last_name: str, result: TransformationResult) -> TransformationResult:
        """
        Parse a person name split across first_name and last_name fields.

        Args:
            first_name: First name(s)
            last_name: Last name(s)
            result: Transformation result to populate

        Returns:
            Updated TransformationResult
        """
        first_clean = str(first_name).strip()
        last_clean = str(last_name).strip()
        full_name = f"{first_clean} {last_clean}"

        # Check if first_name actually contains full name (common issue)
        if " " in first_clean and len(first_clean) > len(last_clean):
            result.add_issue(
                code="NAME_003",
                message="first_name may contain full name, consider concatenating both fields",
                severity=TransformationSeverity.INFO,
                field="first_name",
                source_value=first_name,
            )

        name_result = NameResult(
            FullName=full_name,
            GivenNames=first_clean,
            FamilyName=last_clean,
            NameType="Primary Name",
            PrimaryName=full_name,
            Title=None,
            IsEntity=False,
            OriginalFirstName=first_clean,
            OriginalLastName=last_clean,
        )

        result.data = name_result.to_dict()
        result.confidence = 0.95
        result.transformation_applied = f"{self.transformation_name}-Person"

        return result

    def _detect_entity(self, name: str) -> bool:
        """
        Detect if a name appears to be an entity/organization.

        Args:
            name: Name to check

        Returns:
            True if name appears to be an entity
        """
        name_lower = name.lower()

        # Check for entity keywords
        for keyword in self.ENTITY_KEYWORDS:
            if keyword in name_lower:
                return True

        # Check for all uppercase (common for entity names)
        if name.isupper() and len(name.split()) >= 3:
            return True

        # Check for numbers in name (organizations often have numbers)
        if any(char.isdigit() for char in name):
            return True

        return False

    def validate_source_fields(self, source_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate source fields before transformation.

        Args:
            source_record: Source record to validate

        Returns:
            Dict with validation results
        """
        issues = []

        first_name = self._safe_get(source_record, "first_name")
        last_name = self._safe_get(source_record, "last_name")

        if self._is_null_or_empty(last_name):
            issues.append({"field": "last_name", "code": "REQUIRED", "message": "last_name is required"})

        if not self._is_null_or_empty(first_name):
            # Validate first_name doesn't contain suspicious patterns
            if "," in str(first_name):
                issues.append(
                    {
                        "field": "first_name",
                        "code": "SUSPICIOUS_PATTERN",
                        "message": "first_name contains comma - may be formatted incorrectly",
                    }
                )

        return {"valid": len(issues) == 0, "issues": issues}
