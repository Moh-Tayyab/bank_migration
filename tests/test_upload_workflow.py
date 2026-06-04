"""
Tests for the upload -> column detection -> target bank selection -> auto mapping workflow.

Covers:
- FormatDetector: file format detection and record extraction
- BankRegistry.detect_target_bank: column overlap-based bank detection
- SchemaMapper.map_record: field mapping with transforms
- PipelineOrchestrator.preview_file: end-to-end preview workflow
- Pipeline: full ETL integration with stage adapters
"""

import csv
import json
import os

import pytest

from src.detector import FormatDetector
from src.models import FileFormat, MappingRule, Record
from src.pipeline import Pipeline, PipelineContext, PipelineError
from src.registry import BankRegistry
from src.schema_mapper import SchemaMapper
from src.stages import MapStage, MaskStage, ParseStage, RulesStage, StoreStage, ValidateStage
from src.transaction_rollback import TransactionManager
from src.audit_logger import AuditLogger
from src.validator import Validator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def registry():
    """BankRegistry using the real config directory."""
    return BankRegistry("config/bank_schemas")


@pytest.fixture
def mapper(registry):
    """SchemaMapper backed by the real registry."""
    return SchemaMapper(registry)


@pytest.fixture
def source_record():
    """A Record object with source_bank data ready for mapping."""
    return Record(
        data={
            "name": "Alice Smith",
            "dob": "1990-01-15",
            "account": "ACC-001",
            "email": "alice@example.com",
            "phone": "555-0100",
            "address": "123 Main St",
            "balance": "5000.00",
        },
        record_id="rec-001",
        source_bank="source_bank",
    )


@pytest.fixture
def sample_csv(tmp_path):
    """Create a sample CSV file with source_bank-style columns."""
    filepath = tmp_path / "customers.csv"
    rows = [
        {"name": "Alice Smith", "dob": "1990-01-15", "account": "ACC-001", "email": "alice@example.com", "phone": "555-0100", "address": "123 Main St", "balance": "5000.00"},
        {"name": "Bob Jones", "dob": "1985-06-20", "account": "ACC-002", "email": "bob@example.com", "phone": "555-0200", "address": "456 Oak Ave", "balance": "12000.50"},
        {"name": "Carol White", "dob": "1992-11-30", "account": "ACC-003", "email": "carol@example.com", "phone": "", "address": "789 Pine Rd", "balance": "750.25"},
    ]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return filepath


@pytest.fixture
def sample_csv_target_style(tmp_path):
    """Create a CSV with target_bank-style columns."""
    filepath = tmp_path / "target_data.csv"
    rows = [
        {"first_name": "Alice", "last_name": "Smith", "date_of_birth": "15-01-1990", "account_number": "ACC-001", "email": "alice@example.com", "contact_number": "555-0100", "current_balance": "5000.00"},
        {"first_name": "Bob", "last_name": "Jones", "date_of_birth": "20-06-1985", "account_number": "ACC-002", "email": "bob@example.com", "contact_number": "555-0200", "current_balance": "12000.50"},
    ]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return filepath


@pytest.fixture
def sample_json(tmp_path):
    """Create a sample JSON file."""
    filepath = tmp_path / "customers.json"
    data = [
        {"name": "Alice Smith", "dob": "1990-01-15", "account": "ACC-001", "email": "alice@example.com"},
        {"name": "Bob Jones", "dob": "1985-06-20", "account": "ACC-002", "email": "bob@example.com"},
    ]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return filepath


@pytest.fixture
def sample_xml(tmp_path):
    """Create a sample flat XML file."""
    filepath = tmp_path / "customers.xml"
    content = """<?xml version="1.0" encoding="UTF-8"?>
<records>
  <record>
    <name>Alice Smith</name>
    <dob>1990-01-15</dob>
    <account>ACC-001</account>
    <email>alice@example.com</email>
  </record>
  <record>
    <name>Bob Jones</name>
    <dob>1985-06-20</dob>
    <account>ACC-002</account>
    <email>bob@example.com</email>
  </record>
</records>"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


@pytest.fixture
def sample_txt(tmp_path):
    """Create a sample TXT file."""
    filepath = tmp_path / "notes.txt"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("Line one\nLine two\nLine three\n")
    return filepath


# ---------------------------------------------------------------------------
# 1. FormatDetector — Parameterized Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename,expected", [
    ("data.csv", FileFormat.CSV),
    ("data.json", FileFormat.JSON),
    ("data.xlsx", FileFormat.XLSX),
    ("data.xml", FileFormat.XML),
    ("data.txt", FileFormat.TXT),
    ("data.xyz", FileFormat.TXT),
    ("Data.CSV", FileFormat.CSV),
    ("DATA.Json", FileFormat.JSON),
])
def test_detect_format_by_extension(filename, expected):
    """FormatDetector should detect format from file extension."""
    assert FormatDetector.detect_format(filename) == expected


@pytest.mark.parametrize("path,expected", [
    ("/some/path/to/file.json", FileFormat.JSON),
    ("/home/user/data.csv", FileFormat.CSV),
    ("C:\\Users\\data.xlsx", FileFormat.XLSX),
    ("relative/path/data.xml", FileFormat.XML),
])
def test_detect_format_with_path(path, expected):
    """FormatDetector should handle full paths correctly."""
    assert FormatDetector.detect_format(path) == expected


# ---------------------------------------------------------------------------
# 2. CSV Extraction
# ---------------------------------------------------------------------------

class TestCSVExtraction:
    """Test CSV record extraction and column detection."""

    def test_extract_returns_list_of_dicts(self, sample_csv):
        records = FormatDetector.extract(str(sample_csv), FileFormat.CSV)
        assert isinstance(records, list)
        assert all(isinstance(r, dict) for r in records)

    def test_extract_correct_row_count(self, sample_csv):
        records = FormatDetector.extract(str(sample_csv), FileFormat.CSV)
        assert len(records) == 3

    def test_extract_columns_match_headers(self, sample_csv):
        records = FormatDetector.extract(str(sample_csv), FileFormat.CSV)
        expected_cols = {"name", "dob", "account", "email", "phone", "address", "balance"}
        assert set(records[0].keys()) == expected_cols

    def test_extract_strips_whitespace(self, tmp_path):
        filepath = tmp_path / "spaces.csv"
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["  name  ", "  dob  "])
            writer.writerow(["  Alice  ", "  1990-01-15  "])
        records = FormatDetector.extract(str(filepath), FileFormat.CSV)
        assert "name" in records[0]
        assert records[0]["name"] == "Alice"

    def test_extract_auto_detects_format(self, sample_csv):
        records = FormatDetector.extract(str(sample_csv))
        assert len(records) == 3

    def test_extract_values_are_strings(self, sample_csv):
        records = FormatDetector.extract(str(sample_csv), FileFormat.CSV)
        for key, val in records[0].items():
            assert isinstance(val, str), f"Column '{key}' should be a string"

    def test_extract_single_row_csv(self, tmp_path):
        filepath = tmp_path / "single.csv"
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "email"])
            writer.writeheader()
            writer.writerow({"name": "Solo", "email": "solo@test.com"})
        records = FormatDetector.extract(str(filepath), FileFormat.CSV)
        assert len(records) == 1
        assert records[0]["name"] == "Solo"

    def test_extract_csv_with_special_characters(self, tmp_path):
        filepath = tmp_path / "special.csv"
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "notes"])
            writer.writeheader()
            writer.writerow({"name": "O'Brien", "notes": "has \"quotes\""})
        records = FormatDetector.extract(str(filepath), FileFormat.CSV)
        assert records[0]["name"] == "O'Brien"


# ---------------------------------------------------------------------------
# 3. JSON Extraction
# ---------------------------------------------------------------------------

class TestJSONExtraction:
    """Test JSON record extraction."""

    def test_extract_json_array(self, sample_json):
        records = FormatDetector.extract(str(sample_json), FileFormat.JSON)
        assert len(records) == 2
        assert records[0]["name"] == "Alice Smith"

    def test_extract_json_single_object(self, tmp_path):
        filepath = tmp_path / "single.json"
        with open(filepath, "w") as f:
            json.dump({"name": "Solo", "account": "A-1"}, f)
        records = FormatDetector.extract(str(filepath), FileFormat.JSON)
        assert len(records) == 1
        assert records[0]["name"] == "Solo"

    def test_extract_json_nested_objects(self, tmp_path):
        filepath = tmp_path / "nested.json"
        data = [{"user": {"name": "Alice"}, "id": 1}]
        with open(filepath, "w") as f:
            json.dump(data, f)
        records = FormatDetector.extract(str(filepath), FileFormat.JSON)
        assert records[0]["user"]["name"] == "Alice"


# ---------------------------------------------------------------------------
# 4. XML Extraction
# ---------------------------------------------------------------------------

class TestXMLExtraction:
    """Test XML record extraction."""

    def test_extract_flat_xml(self, sample_xml):
        records = FormatDetector.extract(str(sample_xml), FileFormat.XML)
        assert len(records) == 2
        assert records[0]["name"] == "Alice Smith"
        assert records[0]["account"] == "ACC-001"


# ---------------------------------------------------------------------------
# 5. TXT Extraction
# ---------------------------------------------------------------------------

class TestTXTExtraction:
    """Test TXT record extraction."""

    def test_extract_txt(self, sample_txt):
        records = FormatDetector.extract(str(sample_txt), FileFormat.TXT)
        assert len(records) == 1
        assert "content" in records[0]
        assert "Line one" in records[0]["content"]


# ---------------------------------------------------------------------------
# 6. BankRegistry.detect_target_bank
# ---------------------------------------------------------------------------

class TestDetectTargetBank:
    """Test column overlap-based target bank auto-detection."""

    def test_detects_target_bank_from_source_columns(self, registry):
        columns = ["name", "dob", "account", "email", "phone", "address", "balance"]
        result = registry.detect_target_bank(columns, exclude_banks=["source_bank"])
        assert result is not None

    def test_detects_target_bank_direct_match(self, registry):
        columns = ["first_name", "last_name", "date_of_birth", "account_number", "email"]
        result = registry.detect_target_bank(columns, exclude_banks=["source_bank"])
        assert result == "target_bank"

    def test_no_match_returns_none(self, registry):
        columns = ["col_a", "col_b", "col_c"]
        result = registry.detect_target_bank(columns)
        assert result is None

    def test_exclude_source_bank(self, registry):
        columns = ["name", "dob", "account", "email"]
        result_with_exclude = registry.detect_target_bank(columns, exclude_banks=["source_bank"])
        assert result_with_exclude != "source_bank"

    @pytest.mark.parametrize("columns", [
        ["EMAIL", "Name", "DOB"],
        ["email", "NAME", "dob"],
        ["Email", "Name", "Dob"],
    ])
    def test_case_insensitive_matching(self, registry, columns):
        result = registry.detect_target_bank(columns, exclude_banks=["source_bank"])
        assert result is not None

    def test_best_overlap_wins(self, registry):
        columns = ["first_name", "last_name", "email", "date_of_birth"]
        result = registry.detect_target_bank(columns, exclude_banks=["source_bank"])
        assert result == "target_bank"

    def test_detect_with_empty_columns(self, registry):
        result = registry.detect_target_bank([])
        assert result is None

    def test_detect_single_matching_column(self, registry):
        result = registry.detect_target_bank(["email"], exclude_banks=["source_bank"])
        assert result is not None

    def test_exclude_all_banks_returns_none(self, registry):
        banks = registry.list_banks()
        result = registry.detect_target_bank(["email"], exclude_banks=banks)
        assert result is None


# ---------------------------------------------------------------------------
# 7. SchemaMapper — Parameterized Transforms
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value,transform,expected", [
    ("hello", "upper", "HELLO"),
    ("HELLO", "lower", "hello"),
    ("  hello  ", "strip", "hello"),
    ("hello world", "title", "Hello World"),
    ("abc", "reverse", "cba"),
    ("123", "prefix:ACC-", "ACC-123"),
    ("ACC", "suffix:-001", "ACC-001"),
    ("Hello World", "substring:0,5", "Hello"),
    ("test", "unknown", "test"),
])
def test_apply_transform_parameterized(mapper, value, transform, expected):
    """SchemaMapper transforms should work correctly for all known types."""
    assert mapper._apply_transform(value, transform) == expected


def test_apply_transform_none_passthrough(mapper):
    """None value should pass through transforms unchanged."""
    assert mapper._apply_transform(None, "upper") is None
    assert mapper._apply_transform(None, "lower") is None
    assert mapper._apply_transform(None, "strip") is None


# ---------------------------------------------------------------------------
# 8. SchemaMapper — Record Mapping
# ---------------------------------------------------------------------------

class TestSchemaMapping:
    """Test field mapping via SchemaMapper."""

    def test_map_record_to_target_bank(self, mapper, source_record):
        result = mapper.map_record(source_record, "target_bank")
        assert result.target_bank == "target_bank"
        assert "first_name" in result.data
        assert "last_name" in result.data
        assert "date_of_birth" in result.data
        assert "account_number" in result.data
        assert "email" in result.data

    def test_map_record_email_lowercase_transform(self, mapper, source_record):
        result = mapper.map_record(source_record, "target_bank")
        assert result.data["email"] == "alice@example.com"

    def test_map_record_preserves_source_when_no_mappings(self, mapper):
        record = Record(data={"col_a": "val_a"}, record_id="rec-002", source_bank="source_bank")
        result = mapper.map_record(record, "test_bank")
        assert result.data.get("col_a") == "val_a" or result.data.get("full_name") is None

    def test_map_record_with_default_value(self, mapper):
        record = Record(data={"name": "Test User"}, record_id="rec-003", source_bank="source_bank")
        result = mapper.map_record(record, "test_bank")
        assert result.data.get("full_name") == "Test User"

    def test_map_record_all_source_fields_present(self, mapper, source_record):
        result = mapper.map_record(source_record, "target_bank")
        mapped_keys = set(result.data.keys())
        target_fields = {"first_name", "middle_name", "last_name", "date_of_birth",
                         "account_number", "email", "contact_number", "current_balance"}
        assert target_fields.issubset(mapped_keys)


# ---------------------------------------------------------------------------
# 9. End-to-End Preview Workflow
# ---------------------------------------------------------------------------

class TestPreviewWorkflow:
    """Integration tests simulating the upload -> detect -> map workflow."""

    def test_csv_preview_extracts_columns(self, sample_csv):
        from src.production import PipelineOrchestrator
        orch = PipelineOrchestrator()
        fmt, records = orch.preview_file(str(sample_csv))
        assert fmt == "csv"
        assert len(records) == 3
        columns = list(records[0].keys())
        assert "name" in columns
        assert "email" in columns

    def test_csv_preview_with_row_limit(self, sample_csv):
        from src.production import PipelineOrchestrator
        orch = PipelineOrchestrator()
        fmt, records = orch.preview_file(str(sample_csv), row_limit=2)
        assert len(records) <= 2

    def test_json_preview_extracts_records(self, sample_json):
        from src.production import PipelineOrchestrator
        orch = PipelineOrchestrator()
        fmt, records = orch.preview_file(str(sample_json))
        assert fmt == "json"
        assert len(records) == 2

    def test_full_workflow_csv_to_target_bank(self, sample_csv, registry):
        """Full workflow: detect -> extract -> detect target -> map."""
        from src.production import PipelineOrchestrator
        orch = PipelineOrchestrator()

        fmt, records = orch.preview_file(str(sample_csv))
        assert fmt == "csv"
        assert len(records) == 3

        columns = list(records[0].keys())
        assert set(columns) == {"name", "dob", "account", "email", "phone", "address", "balance"}

        detected_target = registry.detect_target_bank(columns, exclude_banks=["source_bank"])
        assert detected_target is not None

        mapper = SchemaMapper(registry)
        record = Record(data=records[0], record_id="rec-001", source_bank="source_bank")
        mapped = mapper.map_record(record, "target_bank")
        assert mapped.target_bank == "target_bank"
        assert "first_name" in mapped.data
        assert "account_number" in mapped.data
        assert mapped.data["email"] == "alice@example.com"

    def test_full_workflow_target_style_csv(self, sample_csv_target_style, registry):
        """Full workflow with target-bank-style columns."""
        from src.production import PipelineOrchestrator
        orch = PipelineOrchestrator()

        fmt, records = orch.preview_file(str(sample_csv_target_style))
        assert len(records) == 2

        columns = list(records[0].keys())
        detected_target = registry.detect_target_bank(columns, exclude_banks=["source_bank"])
        assert detected_target == "target_bank"

        mapper = SchemaMapper(registry)
        record = Record(data=records[0], record_id="rec-002", source_bank="source_bank")
        mapped = mapper.map_record(record, "target_bank")
        assert mapped.target_bank == "target_bank"
        assert mapped.data["first_name"] is None

    def test_schema_mapping_endpoint_data(self, registry):
        mappings = registry.get_mappings("source_bank", "target_bank")
        assert len(mappings) > 0
        for m in mappings:
            assert isinstance(m, MappingRule)
            assert m.source_field
            assert m.target_field

    def test_list_banks_returns_all(self, registry):
        banks = registry.list_banks()
        assert "source_bank" in banks
        assert "target_bank" in banks
        assert "test_bank" in banks


# ---------------------------------------------------------------------------
# 10. Pipeline Integration — Full ETL Through Stages
# ---------------------------------------------------------------------------

class TestPipelineIntegration:
    """Integration tests: upload -> detect -> validate -> parse -> map -> rules -> mask -> store."""

    def test_full_pipeline_csv_to_target(self, sample_csv, registry):
        """Run the full pipeline on a CSV file through all stages."""
        from src.rules_engine import build_standard_rules
        pipeline = Pipeline(
            stages=[
                ValidateStage(),
                ParseStage(),
                MapStage(SchemaMapper(registry)),
                RulesStage(build_standard_rules()),
                MaskStage(),
            ],
            txn=TransactionManager(),
            audit=AuditLogger(),
        )
        from src.detector import FormatDetector
        records = FormatDetector.extract(str(sample_csv))
        result = pipeline.run(iter(records), "source_bank", "target_bank")

        assert result.success
        assert result.processed == 3
        assert result.failed == 0
        assert len(result.records) == 3

        first = result.records[0]
        assert "first_name" in first
        assert "account_number" in first
        assert first["email"] != "alice@example.com"

    def test_pipeline_validates_rejects_invalid_record(self, tmp_path, registry):
        """Pipeline should skip records that fail validation."""
        filepath = tmp_path / "bad.csv"
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "email"])
            writer.writeheader()
            writer.writerow({"name": "Alice", "email": "alice@test.com"})
            writer.writerow({"name": "", "email": ""})  # empty name

        pipeline = Pipeline(
            stages=[ValidateStage(Validator(rules={"name": {"required": True}})), ParseStage()],
            txn=TransactionManager(),
            audit=AuditLogger(),
        )
        records = FormatDetector.extract(str(filepath))
        result = pipeline.run(iter(records), "source_bank", "target_bank")

        assert result.processed == 1
        assert result.failed == 1

    def test_pipeline_masks_pii_fields(self, registry):
        """Pipeline should mask email and account fields."""
        pipeline = Pipeline(
            stages=[MaskStage()],
            txn=TransactionManager(),
            audit=AuditLogger(),
        )
        records = [
            {"email": "alice@example.com", "account_number": "1234567890123456", "name": "Alice"},
        ]
        result = pipeline.run(iter(records), "source_bank", "target_bank")
        assert result.success

        first = result.records[0]
        assert first["email"] != "alice@example.com"
        assert first["account_number"] != "1234567890123456"
        assert first["name"] == "Alice"

    def test_pipeline_applies_business_rules(self, registry):
        """Pipeline should apply empty_to_null, strip_whitespace, capitalize_names."""
        from src.rules_engine import build_standard_rules
        pipeline = Pipeline(
            stages=[RulesStage(build_standard_rules())],
            txn=TransactionManager(),
            audit=AuditLogger(),
        )
        records = [
            {"first_name": "alice", "last_name": "smith", "notes": ""},
        ]
        result = pipeline.run(iter(records), "source_bank", "target_bank")
        assert result.success

        first = result.records[0]
        assert first["first_name"] == "Alice"
        assert first["last_name"] == "Smith"
        assert first["notes"] is None

    def test_pipeline_failure_threshold_rollback(self, registry):
        """Pipeline should rollback when failure rate exceeds threshold."""
        pipeline = Pipeline(
            stages=[ValidateStage(Validator(rules={"email": {"required": True}}))],
            txn=TransactionManager(),
            audit=AuditLogger(),
        )
        records = [
            {"email": "a@test.com"},
            {"email": ""},  # fails
            {"email": "c@test.com"},
        ]
        result = pipeline.run(iter(records), "a", "b", failure_threshold=0.01)
        assert not result.success
        assert result.failed == 1

    def test_pipeline_audit_trail_recorded(self, sample_csv, registry):
        """Pipeline should record audit events."""
        pipeline = Pipeline(
            stages=[ParseStage()],
            txn=TransactionManager(),
            audit=AuditLogger(),
        )
        records = FormatDetector.extract(str(sample_csv))
        result = pipeline.run(iter(records), "source_bank", "target_bank")

        events = [e.event for e in result.audit_trail]
        from src.models import AuditEvent
        assert AuditEvent.TRANSFORM in events
        assert AuditEvent.COMMITTED in events

    def test_pipeline_detect_target_bank_then_map(self, sample_csv, registry):
        """Full integration: preview -> detect target -> run pipeline with mapping."""
        from src.rules_engine import build_standard_rules
        from src.production import PipelineOrchestrator
        orch = PipelineOrchestrator()

        _, records = orch.preview_file(str(sample_csv))
        columns = list(records[0].keys())
        detected_target = registry.detect_target_bank(columns, exclude_banks=["source_bank"])
        assert detected_target is not None

        pipeline = Pipeline(
            stages=[ParseStage(), MapStage(SchemaMapper(registry)), RulesStage(build_standard_rules()), MaskStage()],
            txn=TransactionManager(),
            audit=AuditLogger(),
        )
        result = pipeline.run(iter(records), "source_bank", detected_target)
        assert result.success
        assert result.processed == 3

        first = result.records[0]
        target_schema = registry.get_schema(detected_target)
        assert target_schema is not None
        for field in target_schema.fields:
            assert field in first
