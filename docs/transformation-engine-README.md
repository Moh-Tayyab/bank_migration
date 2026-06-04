# WorldCheck Transformation Engine

A comprehensive Python transformation engine for migrating WorldCheck data to Private Individuals schema in AML/KYC screening systems.

## Overview

This engine handles the complex transformation from WorldCheck's 10-column format to the 93-column Private Individuals schema used in bank screening systems.

## Features

### 7 Transformation Modules

| Module | Description | Confidence |
|--------|-------------|------------|
| **T1: ConditionalNameParser** | Handles entity names stored in last_name field | 85-95% |
| **T2: RiskScoringEngine** | Calculates risk scores from categories (0-100) | 70-100% |
| **T3: GenderTransformer** | Maps e-i values to Gender (M/F/U) | 70-100% |
| **T4: RecordTypeClassifier** | Derives SAN/PEP/SIP classifications | 70-95% |
| **T5: DateValidator** | Validates and formats dates to ISO 8601 | 95-100% |
| **T6: ConfidenceCalculator** | Scores data completeness (0-100) | Derived |
| **T7: PEPClassifier** | Identifies PEP status and levels | 70-95% |

## Installation

```bash
cd /mnt/d/Bank_Migration
uv sync
```

## Quick Start

```python
from src.transformers import create_orchestrator

# Create orchestrator with default config
orchestrator = create_orchestrator()

# Transform a single record
source_record = {
    "category": "POLITICAL INDIVIDUAL",
    "sub-category": "PEP",
    "uid": 7,
    "entered": "2000-10-16",
    "updated": "2023-03-09",
    "e-i": "M",
    "first_name": "Bashar",
    "last_name": "AL-ASSAD",
    "editor": None,
    "entity_type": "person"
}

result = orchestrator.transform(source_record)

print(f"Success: {result.success}")
print(f"FullName: {result.target_record['FullName']}")
print(f"ListRecordType: {result.target_record['ListRecordType']}")
print(f"RiskScore: {result.target_record['RiskScore']}")
```

## Advanced Configuration

```python
config = {
    "confidence_threshold": 0.80,
    "risk_config": {
        "base_scores": {
            "CRIME - TERROR": 100,
            "POLITICAL INDIVIDUAL": 70,
            "INDIVIDUAL": 50
        }
    },
    "default_values": {
        "ListSubKey": "Private",
        "ListRecordOrigin": "WORLDCHECK"
    }
}

orchestrator = create_orchestrator(config)
```

## Batch Processing

```python
# Transform multiple records
results = orchestrator.transform_batch(source_records)

# Get batch summary
summary = orchestrator.get_batch_summary(results)
print(f"Success Rate: {summary['success_rate']}%")
print(f"Average Confidence: {summary['average_confidence']:.2%}")
print(f"PEP Count: {summary['pep_count']}")
```

## Transformation Output

Each transformation produces:

```python
{
    "success": True,
    "target_record": {
        "ListRecordId": 7,
        "ListRecordType": "PEP",
        "FullName": "Bashar AL-ASSAD",
        "GivenNames": "Bashar",
        "FamilyName": "AL-ASSAD",
        "Gender": "M",
        "RiskScore": 80,
        "PEPclassification": "PEP",
        "IsPEP": True,
        "DataConfidenceScore": 100,
        # ... more fields
    },
    "transformation_log": [...],
    "issues": [],
    "requires_review": False,
    "overall_confidence": 0.95
}
```

## Individual Transformers

You can also use individual transformers:

```python
from src.transformers import (
    ConditionalNameParser,
    RiskScoringEngine,
    GenderTransformer
)

# Name parsing
parser = ConditionalNameParser()
name_result = parser.transform({
    "first_name": None,
    "last_name": "REVOLUTIONARY ORGANIZATION 17 NOVEMBER"
})
# Returns: FullName, IsEntity=True

# Risk scoring
scorer = RiskScoringEngine()
risk_result = scorer.transform({
    "category": "CRIME - TERROR",
    "sub-category": None
})
# Returns: RiskScore=100, RiskCategory="CRITICAL"
```

## Running the Demo

```bash
uv run python examples/worldcheck_transformation_demo.py
```

## Running Tests

```bash
uv run pytest tests/transformers/test_transformers.py -v
```

## Documentation

- [Mapping Table](./01-mapping-table.md) - Field mappings with confidence scores
- [Validation Table](./02-validation-table.md) - Per-field validation rules
- [Transformation Table](./03-transformation-table.md) - Exact transformation logic
- [Risk Table](./04-risk-table.md) - Data quality risks
- [Product Roadmap](./05-product-improvement-roadmap.md) - Engine gaps and timeline

## Architecture

```
src/transformers/
├── __init__.py              # Public API exports
├── base.py                  # Base classes and models
├── name_parser.py           # T1: Conditional Name Parser
├── risk_scorer.py           # T2: Risk Scoring Engine
├── gender_transformer.py    # T3: Gender Transformer
├── record_type_classifier.py # T4: Record Type Classifier
├── date_validator.py        # T5: Date Validator
├── confidence_calculator.py # T6: Confidence Calculator
├── pep_classifier.py        # T7: PEP Classifier
└── orchestrator.py          # Main orchestrator
```

## Key Design Decisions

1. **Conditional Name Parsing**: WorldCheck stores entity names in `last_name` when `first_name` is NULL. The parser detects this pattern automatically.

2. **Risk Scoring Matrix**: Configurable category-to-score mapping with PEP boost logic.

3. **Confidence Thresholds**: Records below 70% confidence are flagged for manual review.

4. **Transformation Audit Trail**: Every transformation is logged for compliance requirements.

## AML/KYC Compliance

This engine supports:
- PEP classification and level detection
- Risk-based prioritization
- Data quality scoring
- Mandatory field validation
- Transformation audit logging

## License

Part of the UN Wallet Multi-Bank Data Migration Platform.
