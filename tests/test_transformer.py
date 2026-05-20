"""
Tests for Transformer — full ETL pipeline integration tests.
"""
import os
import pytest

from src.transform import Transformer
from src.models import Record, AuditEvent


# ===========================================================================
# Transformer Integration Tests
# ===========================================================================

class TestTransformer:
    """Test the full transform pipeline."""

    def test_transform_all_valid_records(self, mock_components):
        """All valid records should be processed successfully."""
        transformer = Transformer(
            mock_components["validator"],
            mock_components["parser"],
            mock_components["mapper"],
            mock_components["rules"],
            mock_components["masker"],
            mock_components["audit"],
            mock_components["canonical"],
            mock_components["txn"],
        )
        records = [
            {"full_name": "Muhammad Tayyab", "dob": "1995-03-15", "account_number": "1234567890123456", "email": "t@test.com", "phone": "03001234567"},
            {"full_name": "Ali Ahmed", "dob": "1988-07-22", "account_number": "9876543210987654", "email": "a@b.com", "phone": "03219876543"},
        ]
        result = transformer.transform(iter(records), "source_bank", "target_bank")
        assert result.success is True
        assert result.total_records == 2
        assert result.processed == 2
        assert result.failed == 0

    def test_transform_empty_input(self, mock_components):
        """Empty input should return success with 0 records."""
        transformer = Transformer(
            mock_components["validator"],
            mock_components["parser"],
            mock_components["mapper"],
            mock_components["rules"],
            mock_components["masker"],
            mock_components["audit"],
            mock_components["canonical"],
            mock_components["txn"],
        )
        result = transformer.transform(iter([]), "source_bank", "target_bank")
        assert result.total_records == 0
        assert result.processed == 0
        assert result.failed == 0

    def test_transform_with_validation_rules(self, mock_components):
        """Records failing validation should be counted as failed."""
        from src.validator import Validator
        strict_validator = Validator(rules={
            "dob": {"type": "date"},
            "email": {"type": "email"},
            "account_number": {"min_length": 5},
        })
        transformer = Transformer(
            strict_validator,
            mock_components["parser"],
            mock_components["mapper"],
            mock_components["rules"],
            mock_components["masker"],
            mock_components["audit"],
            mock_components["canonical"],
            mock_components["txn"],
        )
        records = [
            {"full_name": "Good", "dob": "1990-01-01", "account_number": "1234567890123456", "email": "good@test.com"},
            {"full_name": "Bad", "dob": "INVALID", "account_number": "!", "email": "not-email"},
        ]
        result = transformer.transform(iter(records), "source_bank", "target_bank")
        assert result.total_records == 2
        assert result.processed == 1
        assert result.failed == 1

    def test_transform_failure_threshold_exceeded(self, mock_components):
        """If failure rate exceeds threshold, migration should fail."""
        from src.validator import Validator
        strict_validator = Validator(rules={
            "dob": {"type": "date"},
            "email": {"type": "email"},
        })
        transformer = Transformer(
            strict_validator,
            mock_components["parser"],
            mock_components["mapper"],
            mock_components["rules"],
            mock_components["masker"],
            mock_components["audit"],
            mock_components["canonical"],
            mock_components["txn"],
        )
        # 4 records, 2 bad = 50% failure rate, threshold = 10%
        records = [
            {"full_name": "Good 1", "dob": "1990-01-01", "account_number": "1234567890123456", "email": "a@b.com"},
            {"full_name": "Bad 1", "dob": "INV", "account_number": "!", "email": "bad"},
            {"full_name": "Good 2", "dob": "1990-01-01", "account_number": "1234567890123456", "email": "c@d.com"},
            {"full_name": "Bad 2", "dob": "INV", "account_number": "!", "email": "bad"},
        ]
        result = transformer.transform(iter(records), "source_bank", "target_bank", failure_threshold=0.10)
        assert result.success is False
        assert result.failed == 2

    def test_transform_failure_threshold_within_limit(self, mock_components):
        """If failure rate is within threshold, migration should succeed."""
        from src.validator import Validator
        strict_validator = Validator(rules={
            "dob": {"type": "date"},
            "email": {"type": "email"},
        })
        transformer = Transformer(
            strict_validator,
            mock_components["parser"],
            mock_components["mapper"],
            mock_components["rules"],
            mock_components["masker"],
            mock_components["audit"],
            mock_components["canonical"],
            mock_components["txn"],
        )
        # 10 records, 2 bad = 20% failure rate, threshold = 25%
        records = []
        for i in range(8):
            records.append({"full_name": f"Good {i}", "dob": "1990-01-01", "account_number": "1234567890123456", "email": f"{i}@b.com"})
        records.append({"full_name": "Bad 1", "dob": "INV", "account_number": "!", "email": "bad"})
        records.append({"full_name": "Bad 2", "dob": "INV", "account_number": "!", "email": "bad"})
        result = transformer.transform(iter(records), "source_bank", "target_bank", failure_threshold=0.25)
        assert result.success is True
        assert result.failed == 2
        assert len(result.dlq) == 2

    def test_transform_dlq_contains_failed_records(self, mock_components):
        """DLQ should contain details of failed records."""
        from src.validator import Validator
        strict_validator = Validator(rules={
            "dob": {"type": "date"},
            "email": {"type": "email"},
        })
        transformer = Transformer(
            strict_validator,
            mock_components["parser"],
            mock_components["mapper"],
            mock_components["rules"],
            mock_components["masker"],
            mock_components["audit"],
            mock_components["canonical"],
            mock_components["txn"],
        )
        records = [
            {"full_name": "Good", "dob": "1990-01-01", "account_number": "1234567890123456", "email": "a@b.com"},
            {"full_name": "Bad", "dob": "INV", "account_number": "!", "email": "bad"},
        ]
        result = transformer.transform(iter(records), "source_bank", "target_bank", failure_threshold=0.50)
        assert result.success is True
        assert result.dlq is not None
        assert len(result.dlq) == 1

    def test_transform_audit_trail_populated(self, mock_components):
        """Audit trail should have entries after transformation."""
        transformer = Transformer(
            mock_components["validator"],
            mock_components["parser"],
            mock_components["mapper"],
            mock_components["rules"],
            mock_components["masker"],
            mock_components["audit"],
            mock_components["canonical"],
            mock_components["txn"],
        )
        records = [
            {"full_name": "Test User", "dob": "1990-01-01", "account_number": "1234567890123456", "email": "t@t.com", "phone": "03001234567"},
        ]
        result = transformer.transform(iter(records), "source_bank", "target_bank")
        assert len(result.audit_trail) > 0

    def test_transform_large_batch(self, mock_components):
        """Transformer should handle large batches efficiently via iterator."""
        transformer = Transformer(
            mock_components["validator"],
            mock_components["parser"],
            mock_components["mapper"],
            mock_components["rules"],
            mock_components["masker"],
            mock_components["audit"],
            mock_components["canonical"],
            mock_components["txn"],
        )
        def record_generator(count):
            for i in range(count):
                yield {"full_name": f"User {i}", "dob": "1990-01-01", "account_number": "1234567890123456", "email": f"u{i}@t.com", "phone": "03001234567"}
        result = transformer.transform(record_generator(1000), "source_bank", "target_bank")
        assert result.total_records == 1000
        assert result.processed == 1000
        assert result.success is True

    def test_transform_generator_not_materialized(self, mock_components):
        """Verify that transformer accepts a generator (lazy evaluation)."""
        transformer = Transformer(
            mock_components["validator"],
            mock_components["parser"],
            mock_components["mapper"],
            mock_components["rules"],
            mock_components["masker"],
            mock_components["audit"],
            mock_components["canonical"],
            mock_components["txn"],
        )
        def gen():
            for i in range(5):
                yield {"full_name": f"User {i}", "dob": "1990-01-01", "account_number": "1234567890123456", "email": f"u{i}@t.com", "phone": "03001234567"}
        # Should work with generator directly
        result = transformer.transform(gen(), "source_bank", "target_bank")
        assert result.total_records == 5
