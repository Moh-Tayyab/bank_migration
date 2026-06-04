#!/usr/bin/env python3
"""
WorldCheck → Private Individuals Production Migration Script

Loads raw WorldCheck records, runs all T1-T7 transformers via the orchestrator,
and writes target-format output (JSON, CSV) plus a transformation audit log.

Usage:
    uv run python scripts/migrate_worldcheck.py
    uv run python scripts/migrate_worldcheck.py --input data/worldcheck_raw.json --output-dir output
"""

import argparse
import json
import sys
import csv
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.transformers import create_orchestrator


# ----------------------------------------------------------------------
# Field projection: orchestrator target record -> Private Individuals schema
# ----------------------------------------------------------------------
TARGET_FIELDS = [
    "ListSubKey", "ListRecordType", "ListRecordOrigin", "ListRecordId",
    "FullName", "GivenNames", "FamilyName", "NameType", "PrimaryName",
    "Title", "IsEntity", "Gender",
    "AddedDate", "LastUpdatedDate",
    "EnteredValid", "UpdatedValid",
    "Category", "SubCategory", "RiskScore", "BaseScore", "RiskCategory",
    "PEPBoostApplied", "PEPclassification", "IsPEP", "PEPLevel",
    "DataConfidenceScore", "ConfidenceCategory", "Confidence", "RequiresReview",
    "RuleApplied", "InactiveFlag", "DeceasedFlag",
    "SourceValue", "SourceEntityType", "SourceCategory", "SourceSubCategory",
    "OriginalFirstName", "OriginalLastName",
]

# Fields that should be nulled because WorldCheck does not provide them
PII_FIELDS_TO_NULL = [
    "PassportNumber", "PassportIssCountry", "NationalId", "Identifiers",
    "OriginalScriptName", "Title",
]


def load_source(input_path: Path) -> List[Dict[str, Any]]:
    """Load source records from JSON or CSV."""
    if input_path.suffix.lower() == ".json":
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "records" in data:
                return data["records"]
            return data
    elif input_path.suffix.lower() == ".csv":
        with open(input_path, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    else:
        raise ValueError(f"Unsupported source format: {input_path.suffix}")


def project_to_target(orch_result) -> Dict[str, Any]:
    """Project orchestrator result to Private Individuals schema fields."""
    target = orch_result.target_record.copy()

    # Ensure all TARGET_FIELDS present
    projected = {field: target.get(field) for field in TARGET_FIELDS}

    # Set null for PII fields not available in WorldCheck
    for field in PII_FIELDS_TO_NULL:
        projected[field] = None

    # Add migration metadata
    projected["MigrationTimestamp"] = datetime.utcnow().isoformat() + "Z"
    projected["MigrationSource"] = "WORLDCHECK"
    projected["MigrationTarget"] = "PRIVATE_INDIVIDUALS"
    projected["RecordHash"] = hashlib.sha256(
        json.dumps(orch_result.source_record, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]

    return projected


def write_outputs(
    projected_records: List[Dict[str, Any]],
    source_records: List[Dict[str, Any]],
    results: List[Any],
    summary: Dict[str, Any],
    output_dir: Path,
    timestamp: str,
):
    """Write JSON, CSV, and audit log outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Target JSON (Private Individuals format)
    target_json = output_dir / f"migration_private_individuals_{timestamp}.json"
    with open(target_json, "w", encoding="utf-8") as f:
        json.dump({
            "metadata": {
                "migration_name": "WorldCheck → Private Individuals",
                "schema_version": "1.0",
                "source": "WorldCheck",
                "target": "Private Individuals",
                "executed_at": datetime.utcnow().isoformat() + "Z",
                "record_count": len(projected_records),
                "summary": summary,
            },
            "records": projected_records,
        }, f, indent=2, default=str, ensure_ascii=False)

    # 2. Target CSV
    target_csv = output_dir / f"migration_private_individuals_{timestamp}.csv"
    if projected_records:
        fieldnames = list(projected_records[0].keys())
        with open(target_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for rec in projected_records:
                # Stringify dict fields for CSV
                row = {}
                for k, v in rec.items():
                    if isinstance(v, (dict, list)):
                        row[k] = json.dumps(v, default=str)
                    else:
                        row[k] = v
                writer.writerow(row)

    # 3. Audit log (JSONL)
    audit_log = output_dir / f"migration_audit_{timestamp}.jsonl"
    with open(audit_log, "w", encoding="utf-8") as f:
        for source, result in zip(source_records, results):
            entry = {
                "source_uid": source.get("uid"),
                "source_category": source.get("category"),
                "source_name": f"{source.get('first_name') or ''} {source.get('last_name')}".strip(),
                "target_listrecordid": result.target_record.get("ListRecordId"),
                "target_listrecordtype": result.target_record.get("ListRecordType"),
                "success": result.success,
                "requires_review": result.requires_review,
                "overall_confidence": result.overall_confidence,
                "issues": result.issues,
                "transformation_log": result.transformation_log,
            }
            f.write(json.dumps(entry, default=str) + "\n")

    # 4. Summary report
    report = output_dir / f"migration_summary_{timestamp}.json"
    with open(report, "w", encoding="utf-8") as f:
        json.dump({
            "summary": summary,
            "output_files": {
                "target_json": str(target_json),
                "target_csv": str(target_csv),
                "audit_log": str(audit_log),
                "summary_report": str(report),
            },
            "sample_records": projected_records[:3],
        }, f, indent=2, default=str, ensure_ascii=False)

    return {
        "target_json": target_json,
        "target_csv": target_csv,
        "audit_log": audit_log,
        "summary_report": report,
    }


def run_migration(input_path: Path, output_dir: Path) -> Dict[str, Any]:
    """Run full migration: load → transform → write."""
    print(f"[1/4] Loading source records from {input_path}")
    source_records = load_source(input_path)
    print(f"      Loaded {len(source_records)} records")

    print(f"[2/4] Initializing transformation orchestrator")
    orchestrator = create_orchestrator()

    print(f"[3/4] Transforming records (T1-T7 + defaults + validation)")
    results = orchestrator.transform_batch(source_records)
    summary = orchestrator.get_batch_summary(results)

    # Project to target schema
    projected = [project_to_target(r) for r in results]

    print(f"      Successful: {summary['successful_transformations']}/{summary['total_records']}")
    print(f"      Requires review: {summary['requires_review']} ({summary['review_percentage']:.1f}%)")
    print(f"      PEP records: {summary['pep_count']} ({summary['pep_percentage']:.1f}%)")
    print(f"      Avg confidence: {summary['average_confidence']:.3f}")

    # Issue breakdown
    print(f"      Issues: {summary['issue_counts']}")

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    print(f"[4/4] Writing outputs to {output_dir}")
    files = write_outputs(projected, source_records, results, summary, output_dir, timestamp)
    for label, path in files.items():
        print(f"      {label}: {path}")

    return {"summary": summary, "files": {k: str(v) for k, v in files.items()}}


def main():
    parser = argparse.ArgumentParser(description="Run WorldCheck → Private Individuals migration")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "worldcheck_raw.json",
        help="Input file (JSON or CSV)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "output",
        help="Output directory",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    print("=" * 80)
    print(" WorldCheck → Private Individuals Migration")
    print("=" * 80)
    result = run_migration(args.input, args.output_dir)
    print("\n" + "=" * 80)
    print(" MIGRATION COMPLETE")
    print("=" * 80)
    print(json.dumps(result["summary"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
