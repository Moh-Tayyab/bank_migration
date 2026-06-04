"""
T6: Data Confidence Calculator for WorldCheck data.

This module calculates data confidence scores based on field completeness and validity.

Scoring Logic:
    Base Score: 50
    + Name completeness: +35 (if first_name present), -20 (if NULL)
    + Classification present: +10 (if sub_category present), -5 (if NULL)
    + Dates valid: +5 each
    + All fields present: +10 bonus

Final Score Range: 0-100
    85-100: High confidence (all key fields present)
    60-84: Medium confidence (some fields missing)
    30-59: Low confidence (significant gaps)
    0-29: Very low confidence (minimal data)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import BaseTransformer, TransformationResult, TransformationSeverity


@dataclass
class ConfidenceConfig:
    """Configuration for confidence scoring."""

    base_score: int = 50
    name_present_bonus: int = 35
    name_missing_penalty: int = 20
    classification_present_bonus: int = 10
    classification_missing_penalty: int = 5
    date_valid_bonus: int = 5
    all_fields_bonus: int = 10
    min_score: int = 0
    max_score: int = 100


class ConfidenceCalculator(BaseTransformer):
    """
    Calculates data confidence score based on field completeness.

    Confidence scoring is important for:
    - Identifying records needing manual review
    - Prioritizing data enrichment efforts
    - Flagging low-quality source data
    - Migration reporting
    """

    # Fields to check for completeness
    KEY_FIELDS = ["first_name", "last_name", "category", "sub-category", "entered", "updated"]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.transformation_name = "T6-ConfidenceCalculator"

        # Load config
        self.confidence_config = self._load_config(config)

    def _load_config(self, config: Optional[Dict[str, Any]]) -> ConfidenceConfig:
        """Load confidence configuration."""
        if config:
            return ConfidenceConfig(
                base_score=config.get("base_score", 50),
                name_present_bonus=config.get("name_present_bonus", 35),
                name_missing_penalty=config.get("name_missing_penalty", 20),
                classification_present_bonus=config.get("classification_present_bonus", 10),
                classification_missing_penalty=config.get("classification_missing_penalty", 5),
                date_valid_bonus=config.get("date_valid_bonus", 5),
                all_fields_bonus=config.get("all_fields_bonus", 10),
                min_score=config.get("min_score", 0),
                max_score=config.get("max_score", 100),
            )
        return ConfidenceConfig()

    def transform(self, source_record: Dict[str, Any]) -> TransformationResult:
        """
        Calculate data confidence score for the source record.

        Args:
            source_record: Source data record

        Returns:
            TransformationResult with confidence score
        """
        result = TransformationResult(
            success=True, data={}, confidence=1.0, transformation_applied=self.transformation_name
        )

        # Calculate score
        score, breakdown = self._calculate_score(source_record)

        # Determine confidence category
        category = self._get_confidence_category(score)

        result.data = {
            "DataConfidenceScore": score,
            "ConfidenceCategory": category,
            "Breakdown": breakdown,
            "RequiresReview": score < 70,
        }

        # Set requires_review flag
        result.requires_review = score < 70
        result.confidence = score / 100.0  # Normalize to 0-1

        # Add warning for low confidence
        if score < 60:
            result.add_issue(
                code="CONF_001",
                message=f"Low data confidence score ({score}): significant data gaps",
                severity=TransformationSeverity.WARNING if score >= 40 else TransformationSeverity.ERROR,
            )

        return result

    def _calculate_score(self, record: Dict[str, Any]) -> tuple[int, Dict[str, Any]]:
        """
        Calculate confidence score and breakdown.

        Args:
            record: Source record

        Returns:
            Tuple of (score, breakdown dict)
        """
        cfg = self.confidence_config
        score = cfg.base_score
        breakdown = {"base_score": cfg.base_score, "adjustments": []}

        # Check name completeness
        first_name = self._safe_get(record, "first_name")
        last_name = self._safe_get(record, "last_name")

        has_first_name = not self._is_null_or_empty(first_name)
        has_last_name = not self._is_null_or_empty(last_name)

        if has_first_name and has_last_name:
            score += cfg.name_present_bonus
            breakdown["adjustments"].append(
                {"field": "names", "change": f"+{cfg.name_present_bonus}", "reason": "Both first and last name present"}
            )
        elif has_last_name and not has_first_name:
            # Entity name scenario
            score -= cfg.name_missing_penalty
            breakdown["adjustments"].append(
                {
                    "field": "first_name",
                    "change": f"-{cfg.name_missing_penalty}",
                    "reason": "First name missing (entity name?)",
                }
            )

        # Check classification
        sub_category = self._safe_get(record, "sub-category")
        if not self._is_null_or_empty(sub_category):
            score += cfg.classification_present_bonus
            breakdown["adjustments"].append(
                {
                    "field": "sub-category",
                    "change": f"+{cfg.classification_present_bonus}",
                    "reason": "Classification present",
                }
            )
        else:
            score -= cfg.classification_missing_penalty
            breakdown["adjustments"].append(
                {
                    "field": "sub-category",
                    "change": f"-{cfg.classification_missing_penalty}",
                    "reason": "Classification missing",
                }
            )

        # Check dates
        for field in ["entered", "updated"]:
            value = self._safe_get(record, field)
            if not self._is_null_or_empty(value):
                if self._is_valid_date_format(str(value)):
                    score += cfg.date_valid_bonus
                    breakdown["adjustments"].append(
                        {"field": field, "change": f"+{cfg.date_valid_bonus}", "reason": "Date valid"}
                    )

        # Check all key fields present
        all_present = all(not self._is_null_or_empty(self._safe_get(record, field)) for field in self.KEY_FIELDS)

        if all_present:
            score += cfg.all_fields_bonus
            breakdown["adjustments"].append(
                {"field": "all", "change": f"+{cfg.all_fields_bonus}", "reason": "All key fields present"}
            )

        # Clamp score to range
        final_score = max(cfg.min_score, min(cfg.max_score, score))
        breakdown["final_score"] = final_score

        return final_score, breakdown

    def _get_confidence_category(self, score: int) -> str:
        """
        Get confidence category for a score.

        Args:
            score: Numeric score

        Returns:
            Category label
        """
        if score >= 85:
            return "HIGH"
        elif score >= 60:
            return "MEDIUM"
        elif score >= 30:
            return "LOW"
        else:
            return "VERY_LOW"

    def _is_valid_date_format(self, date_str: str) -> bool:
        """
        Quick check if date string appears valid.

        Args:
            date_str: Date string to check

        Returns:
            True if appears valid
        """
        try:
            # Try common formats
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y"]:
                try:
                    from datetime import datetime

                    datetime.strptime(date_str, fmt)
                    return True
                except ValueError:
                    continue
            return False
        except Exception:
            return False

    def calculate_batch_scores(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate confidence scores for a batch of records.

        Args:
            records: List of source records

        Returns:
            Batch summary with statistics
        """
        scores = []
        categories = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "VERY_LOW": 0}

        for record in records:
            result = self.transform(record)
            score = result.data.get("DataConfidenceScore", 0)
            category = result.data.get("ConfidenceCategory", "UNKNOWN")

            scores.append(score)
            if category in categories:
                categories[category] += 1

        return {
            "total_records": len(records),
            "average_score": sum(scores) / len(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "category_distribution": categories,
            "records_requiring_review": sum(1 for s in scores if s < 70),
        }
