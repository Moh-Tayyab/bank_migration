"""
WorldCheck Transformation Engine

Provides specialized transformers for WorldCheck to Private Individuals migration.
Each transformer handles a specific aspect of the data transformation process.

Transformations:
    T1: Name Parsing (ConditionalNameParser)
    T2: Risk Score Calculation (RiskScoringEngine)
    T3: Gender Transformation (GenderTransformer)
    T4: ListRecordType Derivation (RecordTypeClassifier)
    T5: Date Format Validation (DateValidator)
    T6: Data Confidence Scoring (ConfidenceCalculator)
    T7: PEP Classification Enrichment (PEPClassifier)

Usage:
    from src.transformers import WorldCheckTransformOrchestrator

    orchestrator = WorldCheckTransformOrchestrator()
    result = orchestrator.transform(source_record)
"""

from .base import BaseTransformer, TransformationResult
from .confidence_calculator import ConfidenceCalculator
from .date_validator import DateValidator
from .gender_transformer import GenderTransformer
from .name_parser import ConditionalNameParser, NameResult
from .orchestrator import WorldCheckTransformOrchestrator, WorldCheckTransformResult, create_orchestrator
from .pep_classifier import PEPClassifier
from .record_type_classifier import RecordTypeClassifier
from .risk_scorer import RiskScoringEngine

__all__ = [
    # Base classes
    "BaseTransformer",
    "TransformationResult",
    # Individual transformers
    "ConditionalNameParser",
    "NameResult",
    "RiskScoringEngine",
    "GenderTransformer",
    "RecordTypeClassifier",
    "DateValidator",
    "ConfidenceCalculator",
    "PEPClassifier",
    # Orchestrator
    "WorldCheckTransformOrchestrator",
    "WorldCheckTransformResult",
    "create_orchestrator",
]
