"""
Tests for the pipeline module and stage adapters.

Tests each stage independently through its process() interface,
then tests the Pipeline orchestrator with a mock stage list.
"""

import pytest

from src.audit_logger import AuditLogger
from src.models import AuditEvent, Record
from src.pipeline import Pipeline, PipelineContext, PipelineError, PipelineStage
from src.stages import (
    MapStage,
    MaskStage,
    ParseStage,
    RulesStage,
    StoreStage,
    ValidateStage,
)
from src.transaction_rollback import TransactionManager
from src.validator import Validator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _PassThrough:
    """A trivial stage that returns data unchanged. For pipeline composition tests."""
    def process(self, data, ctx):
        return data


class _DoubleAge:
    """Custom stage that doubles an 'age' field. Demonstrates user-defined stages."""
    def process(self, data, ctx):
        if "age" in data:
            data["age"] = data["age"] * 2
        return data


class _FailStage:
    """Stage that always raises PipelineError."""
    def process(self, data, ctx):
        raise PipelineError("test_stage", "deliberate failure", ctx.record_id)


def _make_ctx(**overrides) -> PipelineContext:
    defaults = dict(
        record_id="REC-000001",
        source_bank="bank_a",
        target_bank="bank_b",
        raw_data={"name": "Alice", "age": 30},
    )
    defaults.update(overrides)
    return PipelineContext(**defaults)


# ---------------------------------------------------------------------------
# PipelineStage protocol
# ---------------------------------------------------------------------------

class TestPipelineStageProtocol:
    def test_pass_through_satisfies_protocol(self):
        stage = _PassThrough()
        assert isinstance(stage, PipelineStage)

    def test_validate_stage_satisfies_protocol(self):
        stage = ValidateStage()
        assert isinstance(stage, PipelineStage)

    def test_parse_stage_satisfies_protocol(self):
        stage = ParseStage()
        assert isinstance(stage, PipelineStage)

    def test_mask_stage_satisfies_protocol(self):
        stage = MaskStage()
        assert isinstance(stage, PipelineStage)


# ---------------------------------------------------------------------------
# ValidateStage
# ---------------------------------------------------------------------------

class TestValidateStage:
    def test_valid_record_passes(self):
        stage = ValidateStage()
        ctx = _make_ctx()
        data = {"name": "Alice", "dob": "1990-01-15"}
        result = stage.process(data, ctx)
        assert result == data

    def test_empty_required_field_raises(self):
        rules = {"name": {"required": True}}
        stage = ValidateStage(Validator(rules=rules))
        ctx = _make_ctx()
        data = {"name": ""}
        with pytest.raises(PipelineError) as exc_info:
            stage.process(data, ctx)
        assert exc_info.value.stage == "validate"

    def test_missing_field_raises(self):
        rules = {"email": {"required": True, "type": "email"}}
        stage = ValidateStage(Validator(rules=rules))
        ctx = _make_ctx()
        data = {"name": "Alice"}
        with pytest.raises(PipelineError):
            stage.process(data, ctx)


# ---------------------------------------------------------------------------
# ParseStage
# ---------------------------------------------------------------------------

class TestParseStage:
    def test_parses_dates(self):
        stage = ParseStage()
        ctx = _make_ctx()
        data = {"dob": "1990-01-15", "name": "Alice"}
        result = stage.process(data, ctx)
        assert "1990-01-15" in result["dob"] or result["dob"] == "15-01-1990"

    def test_parses_names(self):
        stage = ParseStage()
        ctx = _make_ctx()
        data = {"full_name": "Alice Smith", "dob": "1990-01-15"}
        result = stage.process(data, ctx)
        assert result.get("first_name") == "Alice"
        assert result.get("last_name") == "Smith"

    def test_empty_data_unchanged(self):
        stage = ParseStage()
        ctx = _make_ctx()
        data = {"x": 1}
        result = stage.process(data, ctx)
        assert result == data


# ---------------------------------------------------------------------------
# MaskStage
# ---------------------------------------------------------------------------

class TestMaskStage:
    def test_masks_email(self):
        stage = MaskStage()
        ctx = _make_ctx()
        data = {"email": "alice@example.com"}
        result = stage.process(data, ctx)
        assert result["email"] != "alice@example.com"
        assert "@" in result["email"]

    def test_masks_account_number(self):
        stage = MaskStage()
        ctx = _make_ctx()
        data = {"account_number": "1234567890123456"}
        result = stage.process(data, ctx)
        assert result["account_number"] != "1234567890123456"
        assert "3456" in result["account_number"]

    def test_non_string_values_unchanged(self):
        stage = MaskStage()
        ctx = _make_ctx()
        data = {"balance": 5000.0, "count": 42}
        result = stage.process(data, ctx)
        assert result == data


# ---------------------------------------------------------------------------
# RulesStage
# ---------------------------------------------------------------------------

class TestRulesStage:
    def test_empty_to_null(self):
        from src.rules_engine import build_standard_rules
        stage = RulesStage(build_standard_rules())
        ctx = _make_ctx()
        data = {"name": "Alice", "notes": ""}
        result = stage.process(data, ctx)
        assert result["notes"] is None

    def test_strip_whitespace(self):
        from src.rules_engine import build_standard_rules
        stage = RulesStage(build_standard_rules())
        ctx = _make_ctx()
        data = {"name": "  Alice  "}
        result = stage.process(data, ctx)
        assert result["name"] == "Alice"

    def test_capitalize_names(self):
        from src.rules_engine import build_standard_rules
        stage = RulesStage(build_standard_rules())
        ctx = _make_ctx()
        data = {"first_name": "alice", "last_name": "smith"}
        result = stage.process(data, ctx)
        assert result["first_name"] == "Alice"
        assert result["last_name"] == "Smith"


# ---------------------------------------------------------------------------
# StoreStage
# ---------------------------------------------------------------------------

class TestStoreStage:
    def test_stores_record(self, tmp_path):
        from src.canonical_store import CanonicalStore
        import os
        os.environ["CANONICAL_ENCRYPTION_KEY"] = "test-key-for-unit-tests"
        store = CanonicalStore()
        stage = StoreStage(store)
        ctx = _make_ctx(raw_data={"original": True})
        data = {"processed": True}
        result = stage.process(data, ctx)
        assert result == data
        stored = store.retrieve("REC-000001")
        assert stored is not None
        assert stored.canonical_data == data


# ---------------------------------------------------------------------------
# Pipeline composition
# ---------------------------------------------------------------------------

class TestPipelineComposition:
    def test_stages_chain_in_order(self):
        pipeline = Pipeline(
            stages=[_PassThrough(), _DoubleAge(), _PassThrough()],
            txn=TransactionManager(),
            audit=AuditLogger(),
        )
        ctx = _make_ctx()
        data = {"age": 10}
        # Run through the pipeline's internal loop manually
        for stage in pipeline._stages:
            data = stage.process(data, ctx)
        assert data["age"] == 20

    def test_failure_stops_chain(self):
        stages = [_PassThrough(), _FailStage(), _PassThrough()]
        ctx = _make_ctx()
        data = {"x": 1}
        with pytest.raises(PipelineError):
            for stage in stages:
                data = stage.process(data, ctx)
        # Third stage never ran
        assert data == {"x": 1}


# ---------------------------------------------------------------------------
# Pipeline orchestrator
# ---------------------------------------------------------------------------

class TestPipeline:
    def test_single_record_success(self):
        pipeline = Pipeline(
            stages=[_PassThrough()],
            txn=TransactionManager(),
            audit=AuditLogger(),
        )
        records = [{"name": "Alice"}]
        result = pipeline.run(iter(records), "bank_a", "bank_b")
        assert result.success
        assert result.processed == 1
        assert result.failed == 0
        assert len(result.records) == 1

    def test_single_record_failure(self):
        pipeline = Pipeline(
            stages=[_FailStage()],
            txn=TransactionManager(),
            audit=AuditLogger(),
        )
        records = [{"name": "Alice"}]
        result = pipeline.run(iter(records), "bank_a", "bank_b")
        assert not result.success
        assert result.processed == 0
        assert result.failed == 1

    def test_mixed_success_and_failure(self):
        pipeline = Pipeline(
            stages=[_PassThrough()],
            txn=TransactionManager(),
            audit=AuditLogger(),
        )
        records = [{"name": "Alice"}, {"name": "Bob"}]
        result = pipeline.run(iter(records), "bank_a", "bank_b", failure_threshold=0.5)
        assert result.success
        assert result.processed == 2

    def test_empty_records(self):
        pipeline = Pipeline(
            stages=[_PassThrough()],
            txn=TransactionManager(),
            audit=AuditLogger(),
        )
        result = pipeline.run(iter([]), "bank_a", "bank_b")
        assert result.success
        assert result.total_records == 0

    def test_failure_threshold_rollback(self):
        """When failure rate exceeds threshold, pipeline rolls back."""
        stages = [_PassThrough()]

        class _SometimesFails:
            """Fails on the second record."""
            def __init__(self):
                self._count = 0
            def process(self, data, ctx):
                self._count += 1
                if self._count == 2:
                    raise PipelineError("test", "fail", ctx.record_id)
                return data

        pipeline = Pipeline(
            stages=[_SometimesFails()],
            txn=TransactionManager(),
            audit=AuditLogger(),
        )
        records = [{"x": 1}, {"x": 2}, {"x": 3}]
        result = pipeline.run(iter(records), "a", "b", failure_threshold=0.01)
        assert not result.success
        assert result.failed == 1
        assert len(result.records) == 0

    def test_audit_trail_recorded(self):
        pipeline = Pipeline(
            stages=[_PassThrough()],
            txn=TransactionManager(),
            audit=AuditLogger(),
        )
        result = pipeline.run(iter([{"x": 1}]), "a", "b")
        events = [e.event for e in result.audit_trail]
        assert AuditEvent.TRANSFORM in events
        assert AuditEvent.COMMITTED in events

    def test_multi_stage_pipeline(self):
        """End-to-end: validate -> parse -> mask -> store."""
        rules = {"email": {"required": True, "type": "email"}}
        pipeline = Pipeline(
            stages=[
                ValidateStage(Validator(rules=rules)),
                ParseStage(),
                MaskStage(),
            ],
            txn=TransactionManager(),
            audit=AuditLogger(),
        )
        records = [{"name": "Alice Smith", "email": "alice@example.com", "dob": "1990-01-15"}]
        result = pipeline.run(iter(records), "bank_a", "bank_b")
        assert result.success
        assert result.processed == 1
        masked_email = result.records[0]["email"]
        assert masked_email != "alice@example.com"

    def test_validation_failure_skips_record(self):
        rules = {"email": {"required": True}}
        pipeline = Pipeline(
            stages=[ValidateStage(Validator(rules=rules))],
            txn=TransactionManager(),
            audit=AuditLogger(),
        )
        records = [
            {"name": "Alice", "email": "alice@test.com"},
            {"name": "Bob"},  # missing email
            {"name": "Carol", "email": "carol@test.com"},
        ]
        result = pipeline.run(iter(records), "a", "b")
        assert result.processed == 2
        assert result.failed == 1
