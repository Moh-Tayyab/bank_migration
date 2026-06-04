"""
T2: Risk Scoring Engine for WorldCheck data.

This module calculates risk scores based on WorldCheck category and sub-category.
Risk scores range from 0-100 where 100 = highest risk.

Risk Matrix:
    CRIME - TERROR: 100
    NONCONVICTION TERROR: 95
    CRIME - WAR: 90
    CRIME - FINANCIAL: 85
    POLITICAL INDIVIDUAL: 70 (with PEP boost to 80)
    INDIVIDUAL: 50
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .base import BaseTransformer, TransformationResult, TransformationSeverity


@dataclass
class RiskScoreConfig:
    """Configuration for risk scoring matrix."""

    base_scores: Dict[str, int]
    pep_boost: int = 10
    default_score: int = 50
    min_score: int = 0
    max_score: int = 100

    def get_base_score(self, category: str) -> int:
        """Get base score for a category."""
        return self.base_scores.get(category, self.default_score)


# Default risk scoring configuration based on WorldCheck categories
DEFAULT_RISK_CONFIG = RiskScoreConfig(
    base_scores={
        "CRIME - TERROR": 100,
        "NONCONVICTION TERROR": 95,
        "CRIME - WAR": 90,
        "CRIME - FINANCIAL": 85,
        "POLITICAL INDIVIDUAL": 70,
        "INDIVIDUAL": 50,
    },
    pep_boost=10,
    default_score=50,
    min_score=0,
    max_score=100,
)


class RiskScoringEngine(BaseTransformer):
    """
    Calculates risk scores based on WorldCheck category and sub-category.

    Risk scoring is critical for:
    - Prioritizing screening alerts
    - Determining review depth
    - Compliance reporting
    - Risk-based monitoring
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.transformation_name = "T2-RiskScoringEngine"

        # Load risk config from provided config or use default
        risk_config = config.get("risk_scores") if config else None
        self.risk_config = self._load_risk_config(risk_config)

    def _load_risk_config(self, risk_config: Optional[Dict[str, Any]]) -> RiskScoreConfig:
        """Load risk configuration from dict or use default."""
        if risk_config:
            return RiskScoreConfig(
                base_scores=risk_config.get("base_scores", DEFAULT_RISK_CONFIG.base_scores),
                pep_boost=risk_config.get("pep_boost", DEFAULT_RISK_CONFIG.pep_boost),
                default_score=risk_config.get("default_score", DEFAULT_RISK_CONFIG.default_score),
                min_score=risk_config.get("min_score", DEFAULT_RISK_CONFIG.min_score),
                max_score=risk_config.get("max_score", DEFAULT_RISK_CONFIG.max_score),
            )
        return DEFAULT_RISK_CONFIG

    def transform(self, source_record: Dict[str, Any]) -> TransformationResult:
        """
        Calculate risk score for the source record.

        Args:
            source_record: Dict with 'category' and optionally 'sub-category' fields

        Returns:
            TransformationResult with risk score
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
                code="RISK_001",
                message="category is required for risk scoring",
                severity=TransformationSeverity.CRITICAL,
                field="category",
                source_value=category,
            )
            result.requires_review = True
            result.data = {"RiskScore": self.risk_config.default_score}
            return result

        # Calculate base score
        base_score = self.risk_config.get_base_score(str(category).strip())

        # Apply PEP boost if applicable
        final_score = self._apply_pep_boost(base_score, sub_category)

        # Validate score is within range
        final_score = max(self.risk_config.min_score, min(self.risk_config.max_score, final_score))

        result.data = {
            "RiskScore": final_score,
            "BaseScore": base_score,
            "PEPBoostApplied": sub_category == "PEP",
            "RiskCategory": self._get_risk_category(final_score),
            "Category": str(category).strip(),
            "SubCategory": str(sub_category) if sub_category else None,
        }

        # Add warning if using default score
        if base_score == self.risk_config.default_score and str(category).strip() not in self.risk_config.base_scores:
            result.add_issue(
                code="RISK_002",
                message=f"Category '{category}' not in risk matrix, using default score",
                severity=TransformationSeverity.WARNING,
                field="category",
                source_value=category,
            )
            result.confidence = 0.70
            result.requires_review = True

        return result

    def _apply_pep_boost(self, base_score: int, sub_category: Optional[str]) -> int:
        """
        Apply PEP boost to risk score if applicable.

        Args:
            base_score: Current base score
            sub_category: Sub-category value

        Returns:
            Adjusted risk score
        """
        if not self._is_null_or_empty(sub_category):
            if str(sub_category).strip().upper() == "PEP":
                boosted = base_score + self.risk_config.pep_boost
                return min(self.risk_config.max_score, boosted)
        return base_score

    def _get_risk_category(self, score: int) -> str:
        """
        Get risk category label for a numeric score.

        Args:
            score: Numeric risk score

        Returns:
            Risk category label
        """
        if score >= 90:
            return "CRITICAL"
        elif score >= 75:
            return "HIGH"
        elif score >= 50:
            return "MEDIUM"
        elif score >= 25:
            return "LOW"
        else:
            return "VERY_LOW"

    def get_all_base_scores(self) -> Dict[str, int]:
        """
        Get all configured base scores.

        Returns:
            Dict of category to base score mapping
        """
        return self.risk_config.base_scores.copy()

    def update_base_score(self, category: str, score: int) -> None:
        """
        Update or add a base score for a category.

        Args:
            category: Category name
            score: Risk score (0-100)
        """
        if not 0 <= score <= 100:
            raise ValueError(f"Score must be between 0 and 100, got {score}")

        self.risk_config.base_scores[category] = score

    def validate_risk_matrix(self) -> Dict[str, Any]:
        """
        Validate the risk scoring matrix.

        Returns:
            Validation results
        """
        issues = []

        for category, score in self.risk_config.base_scores.items():
            if not isinstance(score, int):
                issues.append({"category": category, "issue": "Score must be integer", "value": score})
            if not 0 <= score <= 100:
                issues.append({"category": category, "issue": "Score out of range (0-100)", "value": score})

        if not 0 <= self.risk_config.default_score <= 100:
            issues.append(
                {
                    "category": "DEFAULT",
                    "issue": "Default score out of range (0-100)",
                    "value": self.risk_config.default_score,
                }
            )

        return {"valid": len(issues) == 0, "issues": issues, "matrix_size": len(self.risk_config.base_scores)}
