"""
Tests for AuditLogger — immutable audit trail logging.
"""
import os
import json
import pytest

from src.audit_logger import AuditLogger
from src.models import AuditEvent


# ===========================================================================
# Basic Logging Tests
# ===========================================================================

class TestAuditLogger:
    """Test basic audit logging functionality."""

    def test_log_entry_creation(self, audit_logger):
        entry = audit_logger.log(
            AuditEvent.VALIDATION,
            record_id="REC-001",
            details="Record validated successfully",
        )
        assert entry.event == AuditEvent.VALIDATION
        assert entry.record_id == "REC-001"
        assert entry.details == "Record validated successfully"

    def test_log_multiple_entries(self, audit_logger):
        audit_logger.log(AuditEvent.VALIDATION, record_id="REC-001")
        audit_logger.log(AuditEvent.MAPPING, record_id="REC-001")
        audit_logger.log(AuditEvent.TRANSFORM, record_id="REC-001")
        trail = audit_logger.get_trail()
        assert len(trail) == 3

    def test_trail_returns_entries_in_order(self, audit_logger):
        events = [AuditEvent.VALIDATION, AuditEvent.MAPPING, AuditEvent.SECURITY_MASK]
        for i, event in enumerate(events):
            audit_logger.log(event, record_id=f"REC-{i:03d}")
        trail = audit_logger.get_trail()
        assert [e.event for e in trail] == events

    def test_log_with_bank_pair(self, audit_logger):
        entry = audit_logger.log(
            AuditEvent.COMMITTED,
            bank_pair="source_bank->target_bank",
            details="Migration committed",
        )
        assert entry.bank_pair == "source_bank->target_bank"

    def test_log_with_all_fields(self, audit_logger):
        entry = audit_logger.log(
            AuditEvent.ERROR,
            record_id="REC-001",
            bank_pair="A->B",
            details="Something went wrong",
        )
        assert entry.event == AuditEvent.ERROR
        assert entry.record_id == "REC-001"
        assert entry.bank_pair == "A->B"
        assert entry.details == "Something went wrong"


# ===========================================================================
# File Persistence Tests
# ===========================================================================

class TestAuditFilePersistence:
    """Test that audit entries are written to disk."""

    def test_entries_written_to_file(self, audit_logger):
        audit_logger.log(AuditEvent.VALIDATION, record_id="REC-001", details="Test")
        assert os.path.exists(audit_logger._log_path)

    def test_file_contains_valid_jsonl(self, audit_logger):
        audit_logger.log(AuditEvent.VALIDATION, record_id="REC-001", details="Test")
        audit_logger.log(AuditEvent.MAPPING, record_id="REC-002", details="Mapped")
        with open(audit_logger._log_path) as f:
            lines = f.readlines()
        assert len(lines) == 2
        # Each line should be valid JSON
        for line in lines:
            data = json.loads(line)
            assert "event" in data

    def test_read_trail_from_file(self, audit_logger):
        audit_logger.log(AuditEvent.VALIDATION, record_id="REC-001", details="Test")
        audit_logger.log(AuditEvent.ERROR, record_id="REC-002", details="Failed")
        trail = AuditLogger.read_trail(str(audit_logger._log_path))
        assert len(trail) == 2
        assert trail[0].event == AuditEvent.VALIDATION
        assert trail[1].event == AuditEvent.ERROR

    def test_read_trail_nonexistent_file(self, tmp_dir):
        """Reading from a nonexistent file should return empty list."""
        trail = AuditLogger.read_trail(os.path.join(tmp_dir, "nonexistent.jsonl"))
        assert trail == []

    def test_get_log_path(self, audit_logger):
        path = audit_logger.get_log_path()
        assert path == str(audit_logger._log_path)


# ===========================================================================
# Migration ID Tests
# ===========================================================================

class TestMigrationId:
    """Test migration ID generation and usage."""

    def test_custom_migration_id(self, tmp_dir):
        logger = AuditLogger(migration_id="custom_123")
        logger._log_path = os.path.join(tmp_dir, "audit_custom_123.jsonl")
        assert logger.migration_id == "custom_123"

    def test_auto_generated_migration_id(self):
        """Without a migration_id, one should be auto-generated."""
        logger = AuditLogger()
        assert logger.migration_id != ""
        # Should be a timestamp-like string
        assert "_" in logger.migration_id or len(logger.migration_id) > 0


# ===========================================================================
# All Audit Event Types
# ===========================================================================

class TestAllEventTypes:
    """Test that all AuditEvent enum values can be logged."""

    @pytest.mark.parametrize("event", [
        AuditEvent.VALIDATION,
        AuditEvent.MAPPING,
        AuditEvent.TRANSFORM,
        AuditEvent.SECURITY_MASK,
        AuditEvent.ERROR,
        AuditEvent.COMMITTED,
        AuditEvent.ROLLED_BACK,
    ])
    def test_log_all_event_types(self, audit_logger, event):
        entry = audit_logger.log(event, record_id="REC-001")
        assert entry.event == event

    def test_all_events_in_trail(self, audit_logger):
        for event in AuditEvent:
            audit_logger.log(event, record_id="REC-001")
        trail = audit_logger.get_trail()
        assert len(trail) == len(AuditEvent)
