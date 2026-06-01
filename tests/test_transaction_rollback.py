"""
Tests for TransactionManager — transaction lifecycle, savepoints, rollback, DLQ.
"""

import pytest

from src.transaction_rollback import TransactionManager

# ===========================================================================
# Transaction Lifecycle Tests
# ===========================================================================


class TestTransactionLifecycle:
    """Test begin, commit, rollback lifecycle."""

    def test_begin_starts_transaction(self):
        txn = TransactionManager()
        assert txn.is_active is False
        txn.begin()
        assert txn.is_active is True

    def test_commit_ends_transaction(self):
        txn = TransactionManager()
        txn.begin()
        txn.commit()
        assert txn.is_active is False

    def test_rollback_ends_transaction(self):
        txn = TransactionManager()
        txn.begin()
        txn.rollback()
        assert txn.is_active is False
        assert txn.is_rolled_back is True

    def test_commit_returns_committed_data(self):
        txn = TransactionManager()
        txn.begin()
        txn.savepoint("REC-001", {"name": "Test"})
        txn.savepoint("REC-002", {"name": "Test2"})
        committed = txn.commit()
        assert len(committed) == 2

    def test_rollback_clears_savepoints(self):
        txn = TransactionManager()
        txn.begin()
        txn.savepoint("REC-001", {"name": "Test"})
        txn.rollback()
        assert txn.get_savepoint("REC-001") is None

    def test_begin_resets_state(self):
        """Calling begin() should reset all state from previous transaction."""
        txn = TransactionManager()
        txn.begin()
        txn.savepoint("REC-001", {"name": "Test"})
        txn.mark_failed("REC-002", "error")
        txn.begin()  # reset
        assert txn.get_savepoint("REC-001") is None
        assert txn.get_failed_records() == {}


# ===========================================================================
# Savepoint Tests
# ===========================================================================


class TestSavepoints:
    """Test savepoint management."""

    def test_savepoint_stores_data(self):
        txn = TransactionManager()
        txn.begin()
        txn.savepoint("REC-001", {"name": "Test"})
        assert txn.get_savepoint("REC-001") == {"name": "Test"}

    def test_savepoint_isolation(self):
        """Savepoints should be deep copies — modifying original shouldn't affect stored."""
        txn = TransactionManager()
        txn.begin()
        data = {"name": "Test", "items": [1, 2, 3]}
        txn.savepoint("REC-001", data)
        data["name"] = "Modified"
        data["items"].append(4)
        stored = txn.get_savepoint("REC-001")
        assert stored["name"] == "Test"
        assert stored["items"] == [1, 2, 3]

    def test_savepoint_without_transaction_raises(self):
        txn = TransactionManager()
        with pytest.raises(RuntimeError, match="No active transaction"):
            txn.savepoint("REC-001", {"name": "Test"})

    def test_savepoint_none_data(self):
        txn = TransactionManager()
        txn.begin()
        txn.savepoint("REC-001", None)
        assert txn.get_savepoint("REC-001") is None

    def test_multiple_savepoints(self):
        txn = TransactionManager()
        txn.begin()
        txn.savepoint("REC-001", {"name": "A"})
        txn.savepoint("REC-002", {"name": "B"})
        txn.savepoint("REC-003", {"name": "C"})
        assert txn.get_savepoint("REC-001") == {"name": "A"}
        assert txn.get_savepoint("REC-002") == {"name": "B"}
        assert txn.get_savepoint("REC-003") == {"name": "C"}

    def test_overwrite_savepoint(self):
        txn = TransactionManager()
        txn.begin()
        txn.savepoint("REC-001", {"name": "A"})
        txn.savepoint("REC-001", {"name": "B"})
        assert txn.get_savepoint("REC-001") == {"name": "B"}


# ===========================================================================
# Rollback to Savepoint Tests
# ===========================================================================


class TestRollbackToSavepoint:
    """Test partial rollback to a specific savepoint."""

    def test_rollback_to_savepoint(self):
        txn = TransactionManager()
        txn.begin()
        txn.savepoint("REC-001", {"name": "A"})
        txn.savepoint("REC-002", {"name": "B"})
        txn.savepoint("REC-003", {"name": "C"})
        txn.rollback(to_savepoint="REC-002")
        assert txn.get_savepoint("REC-001") is None
        assert txn.get_savepoint("REC-002") == {"name": "B"}
        assert txn.get_savepoint("REC-003") == {"name": "C"}

    def test_rollback_to_first_savepoint(self):
        txn = TransactionManager()
        txn.begin()
        txn.savepoint("REC-001", {"name": "A"})
        txn.savepoint("REC-002", {"name": "B"})
        txn.rollback(to_savepoint="REC-001")
        assert txn.get_savepoint("REC-001") == {"name": "A"}
        assert txn.get_savepoint("REC-002") == {"name": "B"}


# ===========================================================================
# Dead Letter Queue (DLQ) Tests
# ===========================================================================


class TestDeadLetterQueue:
    """Test failure tracking via DLQ."""

    def test_mark_failed(self):
        txn = TransactionManager()
        txn.begin()
        txn.mark_failed("REC-001", "Validation error")
        failed = txn.get_failed_records()
        assert "REC-001" in failed
        assert failed["REC-001"]["error"] == "Validation error"

    def test_multiple_failures(self):
        txn = TransactionManager()
        txn.begin()
        txn.mark_failed("REC-001", "Error 1")
        txn.mark_failed("REC-002", "Error 2")
        txn.mark_failed("REC-003", "Error 3")
        failed = txn.get_failed_records()
        assert len(failed) == 3

    def test_dlq_survives_commit(self):
        """Failed records should be available after commit."""
        txn = TransactionManager()
        txn.begin()
        txn.savepoint("REC-001", {"name": "Good"})
        txn.mark_failed("REC-002", "Bad record")
        txn.commit()
        failed = txn.get_failed_records()
        assert "REC-002" in failed

    def test_dlq_cleared_on_new_begin(self):
        txn = TransactionManager()
        txn.begin()
        txn.mark_failed("REC-001", "Error")
        txn.begin()  # reset
        assert txn.get_failed_records() == {}


# ===========================================================================
# Edge Cases
# ===========================================================================


class TestEdgeCases:
    """Test edge cases."""

    def test_commit_without_transaction_raises(self):
        txn = TransactionManager()
        with pytest.raises(RuntimeError, match="No active transaction"):
            txn.commit()

    def test_rollback_without_transaction_is_noop(self):
        txn = TransactionManager()
        txn.rollback()  # should not raise
        assert txn.is_active is False

    def test_get_savepoint_nonexistent(self):
        txn = TransactionManager()
        txn.begin()
        assert txn.get_savepoint("nonexistent") is None

    def test_commit_excludes_none_savepoints(self):
        """None savepoints should not appear in committed list."""
        txn = TransactionManager()
        txn.begin()
        txn.savepoint("REC-001", {"name": "Good"})
        txn.savepoint("REC-002", None)
        committed = txn.commit()
        assert len(committed) == 1
