"""
T3: Gender Transformer for WorldCheck data.

This module handles gender transformation from WorldCheck 'e-i' field to target Gender field.

Mapping:
    E → U (Entity/Unknown)
    M → M (Male)
    F → F (Female)
    NULL/other → U (Unknown)

Note: WorldCheck uses 'e-i' field where:
    E = Entity
    I = Individual (with M/F subcodes)
"""

from typing import Any, Dict, Optional

from .base import BaseTransformer, TransformationResult, TransformationSeverity


class GenderTransformer(BaseTransformer):
    """
    Transforms WorldCheck 'e-i' field to target Gender field.

    The 'e-i' field in WorldCheck represents:
    - E: Entity/Organization
    - I: Individual (with additional M/F coding)
    - M: Male
    - F: Female
    """

    # Mapping from WorldCheck e-i to target Gender
    GENDER_MAP = {
        "M": "M",  # Male
        "F": "F",  # Female
        "E": "U",  # Entity → Unknown
        "MALE": "M",
        "FEMALE": "F",
        "ENTITY": "U",
        "UNKNOWN": "U",
    }

    # Allowed target values
    ALLOWED_GENDERS = {"M", "F", "U", "E"}

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.transformation_name = "T3-GenderTransformer"

    def transform(self, source_record: Dict[str, Any]) -> TransformationResult:
        """
        Transform WorldCheck e-i field to target Gender.

        Args:
            source_record: Dict with 'e-i' field

        Returns:
            TransformationResult with Gender value
        """
        ei_value = self._safe_get(source_record, "e-i")
        entity_type = self._safe_get(source_record, "entity_type")

        result = TransformationResult(
            success=True, data={}, confidence=1.0, transformation_applied=self.transformation_name
        )

        # Transform the value
        gender = self._transform_gender(ei_value, entity_type)

        result.data = {"Gender": gender, "SourceValue": ei_value, "SourceEntityType": entity_type}

        # Add issues based on transformation
        if self._is_null_or_empty(ei_value):
            result.add_issue(
                code="GENDER_001",
                message="e-i field is NULL, defaulting to Unknown",
                severity=TransformationSeverity.INFO,
                field="e-i",
                source_value=ei_value,
            )
            result.confidence = 0.90

        elif gender == "U" and not self._is_entity_value(ei_value):
            result.add_issue(
                code="GENDER_002",
                message=f"Unrecognized e-i value '{ei_value}', mapped to Unknown",
                severity=TransformationSeverity.WARNING,
                field="e-i",
                source_value=ei_value,
            )
            result.confidence = 0.85

        return result

    def _transform_gender(self, ei_value: Any, entity_type: Any) -> str:
        """
        Transform e-i value to target Gender.

        Args:
            ei_value: e-i field value
            entity_type: entity_type field value (additional context)

        Returns:
            Target Gender value (M/F/U)
        """
        if self._is_null_or_empty(ei_value):
            # Check entity_type for additional context
            if not self._is_null_or_empty(entity_type):
                if "person" in str(entity_type).lower():
                    return "U"  # Person but gender unknown
                elif "entity" in str(entity_type).lower() or "org" in str(entity_type).lower():
                    return "U"  # Entity
            return "U"  # Default to Unknown

        # Normalize to uppercase and strip
        ei_normalized = str(ei_value).upper().strip()

        # Look up in map
        gender = self.GENDER_MAP.get(ei_normalized)

        if gender:
            return gender

        # Handle cases where e-i might be "I" (Individual)
        if ei_normalized == "I":
            # Individual but gender not specified
            return "U"

        # Default to Unknown for unrecognized values
        return "U"

    def _is_entity_value(self, ei_value: Any) -> bool:
        """
        Check if e-i value represents an entity.

        Args:
            ei_value: e-i field value

        Returns:
            True if value represents entity
        """
        if self._is_null_or_empty(ei_value):
            return False

        return str(ei_value).upper().strip() in ["E", "ENTITY"]

    def validate_gender_value(self, gender: str) -> bool:
        """
        Validate a gender value against allowed values.

        Args:
            gender: Gender value to validate

        Returns:
            True if valid
        """
        return gender in self.ALLOWED_GENDERS

    def get_mapping_table(self) -> Dict[str, str]:
        """
        Get the complete mapping table.

        Returns:
            Dict of source values to target values
        """
        return self.GENDER_MAP.copy()
