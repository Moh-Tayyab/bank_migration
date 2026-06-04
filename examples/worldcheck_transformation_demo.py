#!/usr/bin/env python3
"""
WorldCheck Transformation Engine Demo

This script demonstrates the WorldCheck to Private Individuals transformation engine.
It loads sample WorldCheck data and transforms it using the orchestrator.

Usage:
    python worldcheck_transformation_demo.py
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.transformers import (
    create_orchestrator,
    ConditionalNameParser,
    RiskScoringEngine,
    GenderTransformer,
    RecordTypeClassifier,
    DateValidator,
    ConfidenceCalculator,
    PEPClassifier
)


def print_section(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_subsection(title: str) -> None:
    """Print a subsection header."""
    print(f"\n{title}")
    print("-" * len(title))


def demo_individual_transformers():
    """Demonstrate each individual transformer."""
    print_section("INDIVIDUAL TRANSFORMER DEMO")

    # Sample data
    person_record = {
        "category": "POLITICAL INDIVIDUAL",
        "editor": None,
        "entered": "2000-10-16",
        "sub-category": "PEP",
        "uid": 7,
        "updated": "2023-03-09",
        "entity_type": "person",
        "e-i": "M",
        "first_name": "Bashar",
        "last_name": "AL-ASSAD"
    }

    entity_record = {
        "category": "CRIME - TERROR",
        "editor": None,
        "entered": "2000-11-10",
        "sub-category": None,
        "uid": 1,
        "updated": "2022-11-15",
        "entity_type": "person",
        "e-i": "E",
        "first_name": None,
        "last_name": "REVOLUTIONARY ORGANIZATION 17 NOVEMBER"
    }

    # T1: Name Parser
    print_subsection("T1: Conditional Name Parser")
    print("\nPerson Record:")
    result = ConditionalNameParser().transform(person_record)
    print(json.dumps(result.data, indent=2))

    print("\nEntity Record:")
    result = ConditionalNameParser().transform(entity_record)
    print(json.dumps(result.data, indent=2))

    # T2: Risk Scorer
    print_subsection("T2: Risk Scoring Engine")
    print("\nRisk Matrix:")
    scorer = RiskScoringEngine()
    for category in ["CRIME - TERROR", "POLITICAL INDIVIDUAL", "INDIVIDUAL"]:
        result = scorer.transform({"category": category, "sub-category": None})
        print(f"  {category}: {result.data['RiskScore']} ({result.data['RiskCategory']})")

    print("\nWith PEP Boost:")
    result = scorer.transform({"category": "POLITICAL INDIVIDUAL", "sub-category": "PEP"})
    print(f"  POLITICAL INDIVIDUAL + PEP: {result.data['RiskScore']}")

    # T3: Gender Transformer
    print_subsection("T3: Gender Transformer")
    for ei_value in ["M", "F", "E", None]:
        result = GenderTransformer().transform({"e-i": ei_value})
        print(f"  e-i={repr(ei_value)} → Gender={result.data['Gender']}")

    # T4: Record Type Classifier
    print_subsection("T4: Record Type Classifier")
    test_cases = [
        {"category": "POLITICAL INDIVIDUAL", "sub-category": "PEP"},
        {"category": "CRIME - TERROR", "sub-category": None},
        {"category": "INDIVIDUAL", "sub-category": None}
    ]
    for tc in test_cases:
        result = RecordTypeClassifier().transform(tc)
        print(f"  {tc['category']}: {result.data['ListRecordType']} ({result.data['RuleApplied']})")

    # T5: Date Validator
    print_subsection("T5: Date Validator")
    result = DateValidator().transform({
        "entered": "16/10/2000",
        "updated": "09/03/2023"
    })
    print(f"  Entered (16/10/2000) → {result.data['AddedDate']}")
    print(f"  Updated (09/03/2023) → {result.data['LastUpdatedDate']}")

    # T6: Confidence Calculator
    print_subsection("T6: Confidence Calculator")
    complete_record = person_record.copy()
    incomplete_record = person_record.copy()
    incomplete_record["first_name"] = None
    incomplete_record["sub-category"] = None

    for label, record in [("Complete", complete_record), ("Incomplete", incomplete_record)]:
        result = ConfidenceCalculator().transform(record)
        print(f"  {label}: {result.data['DataConfidenceScore']} ({result.data['ConfidenceCategory']})")

    # T7: PEP Classifier
    print_subsection("T7: PEP Classifier")
    for category, sub_cat in [
        ("POLITICAL INDIVIDUAL", "PEP"),
        ("POLITICAL INDIVIDUAL", None),
        ("INDIVIDUAL", None)
    ]:
        result = PEPClassifier().transform({"category": category, "sub-category": sub_cat})
        print(f"  {category}: IsPEP={result.data['IsPEP']}, Classification={result.data['PEPclassification']}")


def demo_orchestrator():
    """Demonstrate the full orchestrator."""
    print_section("ORCHESTRATOR DEMO")

    # Create orchestrator with custom config
    config = {
        "confidence_threshold": 0.70,
        "risk_config": {
            "base_scores": {
                "CRIME - TERROR": 100,
                "POLITICAL INDIVIDUAL": 70,
                "INDIVIDUAL": 50
            }
        }
    }

    orchestrator = create_orchestrator(config)

    # Sample records
    records = [
        {
            "category": "POLITICAL INDIVIDUAL",
            "editor": None,
            "entered": "2000-10-16",
            "sub-category": "PEP",
            "uid": 7,
            "updated": "2023-03-09",
            "entity_type": "person",
            "e-i": "M",
            "first_name": "Bashar",
            "last_name": "AL-ASSAD"
        },
        {
            "category": "CRIME - TERROR",
            "editor": None,
            "entered": "2000-11-10",
            "sub-category": None,
            "uid": 1,
            "updated": "2022-11-15",
            "entity_type": "person",
            "e-i": "E",
            "first_name": None,
            "last_name": "REVOLUTIONARY ORGANIZATION 17 NOVEMBER"
        },
        {
            "category": "INDIVIDUAL",
            "editor": None,
            "entered": "2000-01-15",
            "sub-category": None,
            "uid": 100,
            "updated": "2023-01-20",
            "entity_type": "person",
            "e-i": "F",
            "first_name": "Jane",
            "last_name": "SMITH"
        }
    ]

    print_subsection("Transforming Records")
    results = orchestrator.transform_batch(records)

    for i, result in enumerate(results, 1):
        print(f"\nRecord {i}:")
        print(f"  Success: {result.success}")
        print(f"  Confidence: {result.overall_confidence:.2%}")
        print(f"  Requires Review: {result.requires_review}")
        print(f"  ListRecordType: {result.target_record.get('ListRecordType')}")
        print(f"  RiskScore: {result.target_record.get('RiskScore')}")
        print(f"  PEP: {result.target_record.get('IsPEP')}")
        print(f"  FullName: {result.target_record.get('FullName')}")

        if result.issues:
            print(f"  Issues ({len(result.issues)}):")
            for issue in result.issues[:3]:  # Show first 3
                print(f"    - [{issue['severity']}] {issue['message']}")
            if len(result.issues) > 3:
                print(f"    ... and {len(result.issues) - 3} more")

    print_subsection("Batch Summary")
    summary = orchestrator.get_batch_summary(results)
    print(json.dumps(summary, indent=2))


def demo_real_worldcheck_file():
    """Load and transform real WorldCheck file if available."""
    print_section("REAL WORLDCHECK FILE DEMO")

    worldcheck_path = Path("/mnt/c/Users/Muhammad Tayyab/Downloads/worldcheck_first50.xlsx")

    if not worldcheck_path.exists():
        print(f"\nWorldCheck file not found at: {worldcheck_path}")
        print("Skipping real file demo.")
        return

    try:
        import pandas as pd

        print(f"\nLoading WorldCheck file: {worldcheck_path}")
        df = pd.read_excel(worldcheck_path)
        print(f"Loaded {len(df)} records")

        # Convert to list of dicts
        records = df.to_dict("records")

        # Create orchestrator
        orchestrator = create_orchestrator()

        # Transform
        print("\nTransforming records...")
        results = orchestrator.transform_batch(records)

        # Summary
        summary = orchestrator.get_batch_summary(results)

        print_subsection("Transformation Summary")
        print(json.dumps(summary, indent=2))

        # Show some sample results
        print_subsection("Sample Results (First 3)")
        for i, result in enumerate(results[:3], 1):
            print(f"\nRecord {i} (uid={result.source_record.get('uid')}):")
            print(f"  FullName: {result.target_record.get('FullName')}")
            print(f"  ListRecordType: {result.target_record.get('ListRecordType')}")
            print(f"  RiskScore: {result.target_record.get('RiskScore')}")
            print(f"  IsPEP: {result.target_record.get('IsPEP')}")
            print(f"  Requires Review: {result.requires_review}")

    except Exception as e:
        print(f"\nError processing WorldCheck file: {e}")


def main():
    """Run all demos."""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "WORLDCHECK TRANSFORMATION ENGINE DEMO" + " " * 28 + "║")
    print("╚" + "═" * 78 + "╝")

    demo_individual_transformers()
    demo_orchestrator()
    demo_real_worldcheck_file()

    print_section("DEMO COMPLETE")
    print("\nThe transformation engine is ready for production use!")
    print("\nNext steps:")
    print("  1. Review and approve risk scoring matrix")
    print("  2. Configure confidence thresholds")
    print("  3. Set up manual review workflow")
    print("  4. Run full migration with batch processing")
    print()


if __name__ == "__main__":
    main()
