"""
WorldCheck Transformation Orchestrator

This module orchestrates all transformations for WorldCheck to Private Individuals migration.

Execution Order:
    1. Validate Dates (T5)
    2. Parse Names (T1)
    3. Derive Record Type (T4)
    4. Calculate Risk Score (T2)
    5. Transform Gender (T3)
    6. Derive PEP Classification (T7)
    7. Calculate Confidence Score (T6)
    8. Apply Default Values
    9. Validate Mandatory Fields
    10. Generate Transformation Log
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import BaseTransformer, TransformationResult
from .confidence_calculator import ConfidenceCalculator
from .date_validator import DateValidator
from .gender_transformer import GenderTransformer
from .name_parser import ConditionalNameParser
from .pep_classifier import PEPClassifier
from .record_type_classifier import RecordTypeClassifier
from .risk_scorer import RiskScoringEngine


@dataclass
class WorldCheckTransformResult:
    """Complete transformation result for WorldCheck record."""

    success: bool
    source_record: Dict[str, Any]
    target_record: Dict[str, Any]
    transformation_log: List[Dict[str, Any]] = field(default_factory=list)
    issues: List[Dict[str, Any]] = field(default_factory=list)
    requires_review: bool = False
    overall_confidence: float = 1.0
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "source_record": self.source_record,
            "target_record": self.target_record,
            "transformation_log": self.transformation_log,
            "issues": self.issues,
            "requires_review": self.requires_review,
            "overall_confidence": self.overall_confidence,
            "error_message": self.error_message,
        }


@dataclass
class OrchestratorConfig:
    """Configuration for transformation orchestrator."""

    # Feature flags
    enable_name_parsing: bool = True
    enable_risk_scoring: bool = True
    enable_gender_transform: bool = True
    enable_record_type_classification: bool = True
    enable_date_validation: bool = True
    enable_confidence_scoring: bool = True
    enable_pep_classification: bool = True

    # Thresholds
    confidence_threshold: float = 0.70
    failure_threshold: float = 0.50

    # Default values
    default_values: Dict[str, Any] = field(
        default_factory=lambda: {
            "ListSubKey": "Private",
            "ListRecordOrigin": "WORLDCHECK",
            "NameType": "Primary Name",
            "InactiveFlag": False,
            "DeceasedFlag": False,
        }
    )

    # Risk scoring config
    risk_config: Optional[Dict[str, Any]] = None


# Output contract for the WorldCheck -> Private Individuals transformer: the
# fields emitted per record (in order) and the PII fields forced to null. Owned
# by the transformer module so the generic pipeline need not inline them.
TARGET_FIELDS: List[str] = [
    "ListSubKey",
    "ListRecordType",
    "ListRecordOrigin",
    "ListRecordId",
    "FullName",
    "GivenNames",
    "FamilyName",
    "NameType",
    "PrimaryName",
    "Title",
    "IsEntity",
    "Gender",
    "AddedDate",
    "LastUpdatedDate",
    "EnteredValid",
    "UpdatedValid",
    "Category",
    "SubCategory",
    "RiskScore",
    "BaseScore",
    "RiskCategory",
    "PEPBoostApplied",
    "PEPclassification",
    "IsPEP",
    "PEPLevel",
    "DataConfidenceScore",
    "ConfidenceCategory",
    "Confidence",
    "RequiresReview",
    "RuleApplied",
    "InactiveFlag",
    "DeceasedFlag",
    "SourceValue",
    "SourceEntityType",
    "SourceCategory",
    "SourceSubCategory",
    "OriginalFirstName",
    "OriginalLastName",
]
PII_NULL_FIELDS: List[str] = [
    "PassportNumber",
    "PassportIssCountry",
    "NationalId",
    "Identifiers",
    "OriginalScriptName",
]


class WorldCheckTransformOrchestrator(BaseTransformer):
    """
    Orchestrates all transformations for WorldCheck to Private Individuals migration.

    This class coordinates the execution of all transformers in the correct order,
    aggregates results, applies defaults, and generates comprehensive logs.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the orchestrator with transformers.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        self.transformation_name = "WorldCheckTransformOrchestrator"

        # Load configuration
        self.orchestrator_config = self._load_config(config)

        # Initialize transformers
        self.name_parser = ConditionalNameParser()
        self.risk_scorer = RiskScoringEngine(self.orchestrator_config.risk_config)
        self.gender_transformer = GenderTransformer()
        self.record_type_classifier = RecordTypeClassifier()
        self.date_validator = DateValidator()
        self.confidence_calculator = ConfidenceCalculator()
        self.pep_classifier = PEPClassifier()

        # Mandatory target fields
        self.mandatory_fields = {
            "ListRecordId",
            "ListRecordType",
            "FullName",
            "FamilyName",
            "AddedDate",
            "LastUpdatedDate",
        }

    def _load_config(self, config: Optional[Dict[str, Any]]) -> OrchestratorConfig:
        """Load orchestrator configuration."""
        if config:
            return OrchestratorConfig(
                enable_name_parsing=config.get("enable_name_parsing", True),
                enable_risk_scoring=config.get("enable_risk_scoring", True),
                enable_gender_transform=config.get("enable_gender_transform", True),
                enable_record_type_classification=config.get("enable_record_type_classification", True),
                enable_date_validation=config.get("enable_date_validation", True),
                enable_confidence_scoring=config.get("enable_confidence_scoring", True),
                enable_pep_classification=config.get("enable_pep_classification", True),
                confidence_threshold=config.get("confidence_threshold", 0.70),
                failure_threshold=config.get("failure_threshold", 0.50),
                default_values=config.get("default_values", {}),
                risk_config=config.get("risk_config"),
            )
        return OrchestratorConfig()

    def transform(self, source_record: Dict[str, Any]) -> WorldCheckTransformResult:
        """
        Transform a WorldCheck record to Private Individuals format.

        Args:
            source_record: Source WorldCheck record

        Returns:
            WorldCheckTransformResult with complete transformation
        """
        result = WorldCheckTransformResult(
            success=True, source_record=source_record, target_record={}, requires_review=False, overall_confidence=1.0
        )

        try:
            # Step 1: Validate Dates (T5)
            if self.orchestrator_config.enable_date_validation:
                self._apply_date_validation(source_record, result)

            # Step 2: Parse Names (T1)
            if self.orchestrator_config.enable_name_parsing:
                self._apply_name_parsing(source_record, result)

            # Step 3: Derive Record Type (T4)
            if self.orchestrator_config.enable_record_type_classification:
                self._apply_record_type_classification(source_record, result)

            # Step 4: Calculate Risk Score (T2)
            if self.orchestrator_config.enable_risk_scoring:
                self._apply_risk_scoring(source_record, result)

            # Step 5: Transform Gender (T3)
            if self.orchestrator_config.enable_gender_transform:
                self._apply_gender_transform(source_record, result)

            # Step 6: Derive PEP Classification (T7)
            if self.orchestrator_config.enable_pep_classification:
                self._apply_pep_classification(source_record, result)

            # Step 7: Calculate Confidence Score (T6)
            if self.orchestrator_config.enable_confidence_scoring:
                self._apply_confidence_scoring(source_record, result)

            # Step 8: Apply Default Values
            self._apply_default_values(result)

            # Step 9: Set ListRecordId from uid (before validation)
            self._apply_record_id(source_record, result)

            # Step 10: Validate Mandatory Fields (after all data is set)
            self._validate_mandatory_fields(result)

            # Calculate overall confidence
            result.overall_confidence = self._calculate_overall_confidence(result)

            # Determine if review required
            result.requires_review = result.overall_confidence < self.orchestrator_config.confidence_threshold or any(
                issue.get("severity") in ["ERROR", "CRITICAL"] for issue in result.issues
            )

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            result.issues.append(
                {"code": "ORCH_001", "message": f"Transformation failed: {str(e)}", "severity": "CRITICAL"}
            )

        return result

    def _apply_date_validation(self, source_record: Dict[str, Any], result: WorldCheckTransformResult) -> None:
        """Apply date validation (T5)."""
        transform_result = self.date_validator.transform(source_record)
        self._merge_transform_result(transform_result, result)

    def _apply_name_parsing(self, source_record: Dict[str, Any], result: WorldCheckTransformResult) -> None:
        """Apply name parsing (T1)."""
        transform_result = self.name_parser.transform(source_record)
        self._merge_transform_result(transform_result, result)

    def _apply_record_type_classification(
        self, source_record: Dict[str, Any], result: WorldCheckTransformResult
    ) -> None:
        """Apply record type classification (T4)."""
        transform_result = self.record_type_classifier.transform(source_record)
        self._merge_transform_result(transform_result, result)

    def _apply_risk_scoring(self, source_record: Dict[str, Any], result: WorldCheckTransformResult) -> None:
        """Apply risk scoring (T2)."""
        transform_result = self.risk_scorer.transform(source_record)
        self._merge_transform_result(transform_result, result)

    def _apply_gender_transform(self, source_record: Dict[str, Any], result: WorldCheckTransformResult) -> None:
        """Apply gender transformation (T3)."""
        transform_result = self.gender_transformer.transform(source_record)
        self._merge_transform_result(transform_result, result)

    def _apply_pep_classification(self, source_record: Dict[str, Any], result: WorldCheckTransformResult) -> None:
        """Apply PEP classification (T7)."""
        transform_result = self.pep_classifier.transform(source_record)
        self._merge_transform_result(transform_result, result)

    def _apply_confidence_scoring(self, source_record: Dict[str, Any], result: WorldCheckTransformResult) -> None:
        """Apply confidence scoring (T6)."""
        transform_result = self.confidence_calculator.transform(source_record)
        self._merge_transform_result(transform_result, result)

    def _apply_default_values(self, result: WorldCheckTransformResult) -> None:
        """Apply default values from config."""
        defaults = self.orchestrator_config.default_values
        for key, value in defaults.items():
            if key not in result.target_record or result.target_record[key] is None:
                result.target_record[key] = value

    def _apply_record_id(self, source_record: Dict[str, Any], result: WorldCheckTransformResult) -> None:
        """Apply ListRecordId from source uid."""
        uid = self._safe_get(source_record, "uid")
        if uid is not None:
            result.target_record["ListRecordId"] = int(uid)

    def _validate_mandatory_fields(self, result: WorldCheckTransformResult) -> None:
        """Validate that all mandatory fields are present."""
        missing_fields = []
        for fld in self.mandatory_fields:
            if fld not in result.target_record or result.target_record[fld] is None:
                missing_fields.append(fld)

        if missing_fields:
            result.issues.append(
                {
                    "code": "MANDATORY_001",
                    "message": f"Missing mandatory fields: {', '.join(missing_fields)}",
                    "severity": "CRITICAL",
                    "fields": missing_fields,
                }
            )
            result.success = False

    def _merge_transform_result(
        self, transform_result: TransformationResult, result: WorldCheckTransformResult
    ) -> None:
        """Merge a transformer result into the orchestrator result."""
        # Add data to target record
        if transform_result.data:
            result.target_record.update(transform_result.data)

        # Add issues
        for issue in transform_result.issues:
            result.issues.append(issue.to_dict())

        # Add to transformation log
        log_entry = self._log_transformation(result.source_record, transform_result)
        result.transformation_log.append(log_entry)

        # Update confidence if lower
        if transform_result.confidence < 1.0:
            result.requires_review = result.requires_review or transform_result.requires_review

    def _calculate_overall_confidence(self, result: WorldCheckTransformResult) -> float:
        """Calculate overall confidence from all transformations."""
        # Start with data confidence score if available
        data_confidence = result.target_record.get("DataConfidenceScore", 85) / 100.0

        # Reduce confidence based on issues
        critical_count = sum(1 for i in result.issues if i.get("severity") == "CRITICAL")
        error_count = sum(1 for i in result.issues if i.get("severity") == "ERROR")
        warning_count = sum(1 for i in result.issues if i.get("severity") == "WARNING")

        confidence = data_confidence
        confidence -= critical_count * 0.30
        confidence -= error_count * 0.20
        confidence -= warning_count * 0.05

        return max(0.0, min(1.0, confidence))

    def transform_batch(self, source_records: List[Dict[str, Any]]) -> List[WorldCheckTransformResult]:
        """
        Transform a batch of WorldCheck records.

        Args:
            source_records: List of source WorldCheck records

        Returns:
            List of WorldCheckTransformResult objects
        """
        return [self.transform(record) for record in source_records]

    def get_batch_summary(self, results: List[WorldCheckTransformResult]) -> Dict[str, Any]:
        """
        Get summary statistics for a batch of transformations.

        Args:
            results: List of transformation results

        Returns:
            Batch summary with statistics
        """
        total = len(results)
        successful = sum(1 for r in results if r.success)
        requires_review = sum(1 for r in results if r.requires_review)

        # Count issues by severity
        issue_counts = {"CRITICAL": 0, "ERROR": 0, "WARNING": 0, "INFO": 0}
        for result in results:
            for issue in result.issues:
                severity = issue.get("severity", "INFO")
                if severity in issue_counts:
                    issue_counts[severity] += 1

        # PEP statistics
        pep_count = sum(1 for r in results if r.target_record.get("IsPEP", False))

        # Average confidence
        avg_confidence = sum(r.overall_confidence for r in results) / total if total > 0 else 0

        return {
            "total_records": total,
            "successful_transformations": successful,
            "failed_transformations": total - successful,
            "requires_review": requires_review,
            "review_percentage": (requires_review / total * 100) if total > 0 else 0,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "average_confidence": avg_confidence,
            "issue_counts": issue_counts,
            "pep_count": pep_count,
            "pep_percentage": (pep_count / total * 100) if total > 0 else 0,
        }


def create_orchestrator(config: Optional[Dict[str, Any]] = None) -> WorldCheckTransformOrchestrator:
    """
    Factory function to create a transformation orchestrator.

    Args:
        config: Optional configuration dictionary

    Returns:
        Configured WorldCheckTransformOrchestrator instance
    """
    return WorldCheckTransformOrchestrator(config)
