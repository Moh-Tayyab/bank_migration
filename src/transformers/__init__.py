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
from .orchestrator import (
    TARGET_FIELDS,
    PII_NULL_FIELDS,
    WorldCheckTransformOrchestrator,
    WorldCheckTransformResult,
    create_orchestrator,
)
from .pep_classifier import PEPClassifier
from .record_type_classifier import RecordTypeClassifier
from .risk_scorer import RiskScoringEngine

# Registry of source banks that own a dedicated transformation engine. Register a
# new bank's transformer factory here when one is added; the generic migration
# pipeline (src/production.py) discovers engines via get_transformer() and never
# hardcodes bank names itself.
_TRANSFORMER_FACTORIES = {
    "worldcheck": create_orchestrator,
}


def get_transformer(source_bank: str):
    """Return a transformation engine instance for the source bank, or None.

    Lets the orchestrator ask 'does this source bank have a transformer?' instead
    of hardcoding bank pair names. Returning None tells the caller to fall back to
    the generic mapping pipeline.
    """
    factory = _TRANSFORMER_FACTORIES.get((source_bank or "").lower())
    return factory() if factory else None


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
    # Transformer registry + output contract
    "get_transformer",
    "TARGET_FIELDS",
    "PII_NULL_FIELDS",
]
