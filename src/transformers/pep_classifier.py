"""
T7: PEP Classification Enrichment for WorldCheck data.

This module derives PEP classification from source fields.

Logic:
    IF sub_category = "PEP" THEN "PEP"
    ELSE IF category = "POLITICAL INDIVIDUAL" THEN "PEP - Review Required"
    ELSE NULL

This enrichment is important because:
    - PEPs require enhanced due diligence
    - PEP status triggers ongoing monitoring
    - Different PEP levels have different review requirements
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from .base import BaseTransformer, TransformationResult, TransformationSeverity


@dataclass
class PEPInfo:
    """Information about PEP classification."""

    is_pep: bool
    classification: Optional[str]
    level: Optional[int] = None
    requires_review: bool = True
    reason: Optional[str] = None


class PEPClassifier(BaseTransformer):
    """
    Derives and enriches PEP classification from WorldCheck data.

    WorldCheck may have PEP information in:
    - sub_category field ("PEP")
    - category field ("POLITICAL INDIVIDUAL")

    This transformer normalizes the classification for the target schema.
    """

    # PEP-related keywords in category
    PEP_KEYWORDS = {
        "POLITICAL",
        "GOVERNMENT",
        "MINISTER",
        "PRESIDENT",
        "PARLIAMENT",
        "CONGRESS",
        "DIPLOMAT",
        "AMBASSADOR",
        "GENERAL",
        "ADMIRAL",
        "GOVERNOR",
        "MAYOR",
    }

    # Allowed classification values
    ALLOWED_CLASSIFICATIONS = {
        "PEP",
        "PEP - Level 1",
        "PEP - Level 2",
        "PEP - Level 3",
        "PEP - Level 4",
        "PEP - Review Required",
        "PEP - Associate",
        "PEP - Family Member",
        None,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.transformation_name = "T7-PEPClassifier"

    def transform(self, source_record: Dict[str, Any]) -> TransformationResult:
        """
        Derive PEP classification from source fields.

        Args:
            source_record: Dict with 'category' and 'sub-category' fields

        Returns:
            TransformationResult with PEP classification
        """
        category = self._safe_get(source_record, "category")
        sub_category = self._safe_get(source_record, "sub-category")

        result = TransformationResult(
            success=True, data={}, confidence=1.0, transformation_applied=self.transformation_name
        )

        # Derive PEP classification
        pep_info = self._derive_pep_classification(category, sub_category)

        result.data = {
            "PEPclassification": pep_info.classification,
            "IsPEP": pep_info.is_pep,
            "PEPLevel": pep_info.level,
            "Reason": pep_info.reason,
            "SourceSubCategory": str(sub_category) if sub_category else None,
            "SourceCategory": str(category) if category else None,
        }

        result.confidence = 0.95 if pep_info.is_pep else 1.0
        result.requires_review = pep_info.requires_review

        # Add warnings for review-required cases
        if pep_info.requires_review and not pep_info.is_pep:
            result.add_issue(
                code="PEP_001",
                message="Record may be PEP-related, requires review",
                severity=TransformationSeverity.WARNING,
                field="category",
                source_value=category,
            )

        return result

    def _derive_pep_classification(self, category: Any, sub_category: Any) -> PEPInfo:
        """
        Derive PEP classification from category and sub-category.

        Args:
            category: Category field value
            sub_category: Sub-category field value

        Returns:
            PEPInfo with classification details
        """
        category_clean = str(category).strip().upper() if category else ""
        sub_clean = str(sub_category).strip().upper() if sub_category else ""

        # Explicit PEP sub-category
        if sub_clean == "PEP":
            return PEPInfo(
                is_pep=True,
                classification="PEP",
                level=self._estimate_pep_level(category_clean),
                requires_review=True,
                reason="Explicit PEP sub-category",
            )

        # Political individual category
        if "POLITICAL" in category_clean and "INDIVIDUAL" in category_clean:
            return PEPInfo(
                is_pep=True,
                classification="PEP - Review Required",
                level=None,
                requires_review=True,
                reason="Political Individual category",
            )

        # Check for PEP keywords
        if self._contains_pep_keyword(category_clean):
            return PEPInfo(
                is_pep=True,
                classification="PEP - Review Required",
                level=None,
                requires_review=True,
                reason=f"PEP keyword detected in category: {category}",
            )

        # Not PEP
        return PEPInfo(is_pep=False, classification=None, level=None, requires_review=False, reason=None)

    def _estimate_pep_level(self, category: str) -> int:
        """
            Estimate PEP level from category.

        Args:
                category: Category string

            Returns:
                Estimated PEP level (1-4) or None
        """
        category_upper = category.upper()

        # Level 1: Heads of State/Government
        if any(kw in category_upper for kw in ["PRESIDENT", "PRIME MINISTER", "KING", "QUEEN", "EMIR"]):
            return 1

        # Level 2: Senior Government Officials
        if any(kw in category_upper for kw in ["MINISTER", "AMBASSADOR", "SENATOR", "GOVERNOR"]):
            return 2

        # Level 3: Mid-level Officials
        if any(kw in category_upper for kw in ["MAYOR", "GENERAL", "PARLIAMENT", "CONGRESS"]):
            return 3

        # Level 4: Associates/Other
        return 4

    def _contains_pep_keyword(self, category: str) -> bool:
        """
        Check if category contains PEP-related keywords.

        Args:
            category: Category string to check

        Returns:
            True if contains PEP keyword
        """
        for keyword in self.PEP_KEYWORDS:
            if keyword in category:
                return True
        return False

    def classify_batch(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Classify PEP status for a batch of records.

        Args:
            records: List of source records

        Returns:
            Batch summary with PEP statistics
        """
        pep_count = 0
        review_required_count = 0
        level_distribution = {1: 0, 2: 0, 3: 0, 4: 0, "Unknown": 0}

        for record in records:
            result = self.transform(record)
            is_pep = result.data.get("IsPEP", False)
            level = result.data.get("PEPLevel")
            requires_review = result.requires_review

            if is_pep:
                pep_count += 1
                if level in level_distribution:
                    level_distribution[level] += 1
                else:
                    level_distribution["Unknown"] += 1

            if requires_review:
                review_required_count += 1

        return {
            "total_records": len(records),
            "pep_count": pep_count,
            "pep_percentage": (pep_count / len(records) * 100) if records else 0,
            "review_required_count": review_required_count,
            "level_distribution": level_distribution,
        }

    def get_pep_keywords(self) -> Set[str]:
        """
        Get the set of PEP keywords used for detection.

        Returns:
            Set of keyword strings
        """
        return self.PEP_KEYWORDS.copy()

    def add_pep_keyword(self, keyword: str) -> None:
        """
        Add a custom PEP keyword.

        Args:
            keyword: Keyword to add
        """
        self.PEP_KEYWORDS.add(keyword.upper())
