"""
T4: Record Type Classifier for WorldCheck data.

This module derives ListRecordType from WorldCheck category and sub-category.

Derivation Logic:
    IF sub-category = "PEP" THEN "PEP" (Politically Exposed Person)
    ELSE IF category contains "CRIME" OR "TERROR" THEN "SAN" (Sanctions)
    ELSE IF category = "POLITICAL INDIVIDUAL" AND sub-category != "PEP" THEN "SIP"
    ELSE IF category = "INDIVIDUAL" THEN "SIP"
    ELSE "SIP" (Special Interest Person - default)

Target Values:
    SAN - Sanctions
    PEP - Politically Exposed Person
    SIP - Special Interest Person
    SOE - State-Owned Enterprise
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .base import BaseTransformer, TransformationResult, TransformationSeverity


@dataclass
class ClassificationRule:
    """Represents a single classification rule."""

    name: str
    target_value: str
    condition: str  # Description of condition
    priority: int = 0


class RecordTypeClassifier(BaseTransformer):
    """
    Derives ListRecordType from WorldCheck category and sub-category.

    This is critical for AML/KYC screening as the record type determines:
    - Which screening lists to check
    - Review requirements
    - Monitoring frequency
    - Alert routing
    """

    # Allowed target values
    ALLOWED_RECORD_TYPES = {"SAN", "PEP", "SIP", "SOE"}

    # Default classification rules (in priority order)
    DEFAULT_RULES = [
        ClassificationRule(
            name="PEP Detection", target_value="PEP", condition="sub_category equals 'PEP'", priority=100
        ),
        ClassificationRule(
            name="Terror/Crime Detection",
            target_value="SAN",
            condition="category contains 'TERROR' or 'CRIME'",
            priority=90,
        ),
        ClassificationRule(
            name="Political Individual",
            target_value="SIP",
            condition="category equals 'POLITICAL INDIVIDUAL'",
            priority=70,
        ),
        ClassificationRule(
            name="Individual Default", target_value="SIP", condition="category equals 'INDIVIDUAL'", priority=50
        ),
        ClassificationRule(name="Default Fallback", target_value="SIP", condition="No matching rule", priority=0),
    ]

    # Keywords for sanctions detection
    SANCTIONS_KEYWORDS = {"TERROR", "CRIME", "WAR", "FINANCIAL", "FRAUD", "LAUNDERING", "NARCOTICS", "WEAPONS"}

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.transformation_name = "T4-RecordTypeClassifier"

        # Load custom rules from config or use defaults
        self.rules = self._load_rules(config.get("classification_rules") if config else None)

    def _load_rules(self, custom_rules: Optional[list]) -> list:
        """Load classification rules from config or use defaults."""
        if custom_rules:
            return [ClassificationRule(**rule) for rule in custom_rules]
        return self.DEFAULT_RULES.copy()

    def transform(self, source_record: Dict[str, Any]) -> TransformationResult:
        """
        Derive ListRecordType from category and sub-category.

        Args:
            source_record: Dict with 'category' and 'sub-category' fields

        Returns:
            TransformationResult with ListRecordType
        """
        category = self._safe_get(source_record, "category")
        sub_category = self._safe_get(source_record, "sub-category")

        result = TransformationResult(
            success=True, data={}, confidence=1.0, transformation_applied=self.transformation_name
        )

        # Validate category
        if self._is_null_or_empty(category):
            result.success = False
            result.add_issue(
                code="TYPE_001",
                message="category is required for record type classification",
                severity=TransformationSeverity.CRITICAL,
                field="category",
                source_value=category,
            )
            result.requires_review = True
            result.data = {"ListRecordType": "SIP", "RuleApplied": "Default Fallback"}
            return result

        # Apply classification rules
        classification = self._apply_rules(category, sub_category)

        result.data = {
            "ListRecordType": classification.record_type,
            "RuleApplied": classification.rule_name,
            "Confidence": classification.confidence,
            "RequiresReview": classification.requires_review,
            "Category": str(category).strip(),
            "SubCategory": str(sub_category) if sub_category else None,
        }

        result.confidence = classification.confidence
        result.requires_review = classification.requires_review

        # Add warning if using default rule
        if classification.rule_name == "Default Fallback":
            result.add_issue(
                code="TYPE_002",
                message=f"No specific rule matched for category '{category}', using default",
                severity=TransformationSeverity.WARNING,
                field="category",
                source_value=category,
            )

        return result

    def _apply_rules(self, category: str, sub_category: Optional[str]) -> "ClassificationResult":
        """
        Apply classification rules in priority order.

        Args:
            category: Category value
            sub_category: Sub-category value

        Returns:
            ClassificationResult with record type and metadata
        """
        category_clean = str(category).strip().upper() if category else ""
        sub_clean = str(sub_category).strip().upper() if sub_category else ""

        # Rule: PEP Detection (highest priority)
        if sub_clean == "PEP":
            return ClassificationResult(
                record_type="PEP", rule_name="PEP Detection", confidence=0.95, requires_review=False
            )

        # Rule: Terror/Crime Detection
        if self._contains_sanctions_keyword(category_clean):
            return ClassificationResult(
                record_type="SAN", rule_name="Terror/Crime Detection", confidence=0.90, requires_review=False
            )

        # Rule: Political Individual
        if "POLITICAL" in category_clean and "INDIVIDUAL" in category_clean:
            return ClassificationResult(
                record_type="SIP", rule_name="Political Individual", confidence=0.85, requires_review=False
            )

        # Rule: Individual
        if "INDIVIDUAL" in category_clean:
            return ClassificationResult(
                record_type="SIP", rule_name="Individual", confidence=0.80, requires_review=False
            )

        # Default fallback
        return ClassificationResult(
            record_type="SIP", rule_name="Default Fallback", confidence=0.50, requires_review=True
        )

    def _contains_sanctions_keyword(self, category: str) -> bool:
        """
        Check if category contains sanctions-related keywords.

        Args:
            category: Category string to check

        Returns:
            True if contains sanctions keyword
        """
        for keyword in self.SANCTIONS_KEYWORDS:
            if keyword in category:
                return True
        return False

    def validate_record_type(self, record_type: str) -> bool:
        """
        Validate a record type value.

        Args:
            record_type: Record type to validate

        Returns:
            True if valid
        """
        return record_type in self.ALLOWED_RECORD_TYPES

    def get_all_rules(self) -> list:
        """
        Get all configured rules.

        Returns:
            List of ClassificationRule objects
        """
        return self.rules.copy()

    def add_custom_rule(self, rule: ClassificationRule) -> None:
        """
        Add a custom classification rule.

        Args:
            rule: ClassificationRule to add
        """
        self.rules.append(rule)
        # Sort by priority
        self.rules.sort(key=lambda r: r.priority, reverse=True)


class ClassificationResult:
    """Result of record type classification."""

    def __init__(self, record_type: str, rule_name: str, confidence: float, requires_review: bool = False):
        self.record_type = record_type
        self.rule_name = rule_name
        self.confidence = confidence
        self.requires_review = requires_review
