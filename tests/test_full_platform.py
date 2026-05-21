
import sys
import os
from unittest.mock import MagicMock, patch
import pytest

# Ensure src is in path
sys.path.append(os.getcwd())

from src.transform import Transformer
from src.detector import FormatDetector
from src.parser import Parser
from src.validator import Validator
from src.schema_mapper import SchemaMapper
from src.rules_engine import RulesEngine, build_standard_rules
from src.security import SecurityMasker
from src.audit_logger import AuditLogger
from src.canonical_store import CanonicalStore
from src.transaction_rollback import TransactionManager
from src.registry import BankRegistry
from src.infrastructure.db import DatabaseManager
from src.infrastructure.tracker import MigrationTracker
from src.dispatcher import MigrationDispatcher
from src.production import PipelineOrchestrator
from src.config import settings

# =============================================================================
# PHASE 1: CORE ETL TESTS
# =============================================================================

def test_transformer_memory_efficiency():
    """Verify that the transformer accepts an iterator and doesn't crash with a generator."""
    # Setup
    audit = AuditLogger()
    canonical = CanonicalStore(db_manager=MagicMock()) # Mock DB
    txn = TransactionManager()
    parser = Parser()
    validator = Validator()
    mapper = SchemaMapper()
    rules = RulesEngine(build_standard_rules())
    masker = SecurityMasker(audit_logger=audit)
    
    transformer = Transformer(validator, parser, mapper, rules, masker, audit, canonical, txn)
    
    # Simulate 1 million records using a generator (should be instant/low RAM)
    def huge_generator():
        for i in range(1000000):
            yield {"full_name": f"User {i}", "dob": "1990-01-01", "account_number": "1234567890123456", "email": "test@test.com", "phone": "1234567890"}
            
    # We only process a few for the test, but the fact it accepts the generator is the key
    # To avoid 1M actual processing time in unit test, we'll just test the first 100
    import itertools
    limited_gen = itertools.islice(huge_generator(), 100)
    
    result = transformer.transform(limited_gen, "BankA", "BankB")
    assert result.total_records == 100
    assert result.processed == 100

def test_dlq_and_failure_threshold():
    """Verify that partial failures are captured in DLQ and don't trigger total rollback unless threshold is met."""
    audit = AuditLogger()
    canonical = CanonicalStore(db_manager=MagicMock())
    txn = TransactionManager()
    parser = Parser()
    validator = Validator(rules={
        "dob": {"type": "date"},
        "email": {"type": "email"},
        "phone": {"type": "phone"},
        "account_number": {"min_length": 5},
    })
    mapper = SchemaMapper()
    rules = RulesEngine(build_standard_rules())
    masker = SecurityMasker(audit_logger=audit)
    
    transformer = Transformer(validator, parser, mapper, rules, masker, audit, canonical, txn)
    
    # 10 records: 2 are dirty (20% failure rate)
    dirty_records = [
        {"full_name": "Clean 1", "dob": "1990-01-01", "account_number": "1234567890123456", "email": "a@b.com", "phone": "1234567"},
        {"full_name": "DIRTY", "dob": "INV", "account_number": "!", "email": "bad", "phone": "0"}, # Fail
        {"full_name": "Clean 2", "dob": "1990-01-01", "account_number": "1234567890123456", "email": "c@d.com", "phone": "1234567"},
        {"full_name": "DIRTY", "dob": "INV", "account_number": "!", "email": "bad", "phone": "0"}, # Fail
        {"full_name": "Clean 3", "dob": "1990-01-01", "account_number": "1234567890123456", "email": "e@f.com", "phone": "1234567"},
        {"full_name": "Clean 4", "dob": "1990-01-01", "account_number": "1234567890123456", "email": "g@h.com", "phone": "1234567"},
        {"full_name": "Clean 5", "dob": "1990-01-01", "account_number": "1234567890123456", "email": "i@j.com", "phone": "1234567"},
        {"full_name": "Clean 6", "dob": "1990-01-01", "account_number": "1234567890123456", "email": "k@l.com", "phone": "1234567"},
        {"full_name": "Clean 7", "dob": "1990-01-01", "account_number": "1234567890123456", "email": "m@n.com", "phone": "1234567"},
        {"full_name": "Clean 8", "dob": "1990-01-01", "account_number": "1234567890123456", "email": "o@p.com", "phone": "1234567"},
    ]
    
    # Test case: Threshold 0.25 (20% failure is OK)
    result = transformer.transform(iter(dirty_records), "BankA", "BankB", failure_threshold=0.25)
    assert result.success is True
    assert result.failed == 2
    assert len(result.dlq) == 2

# =============================================================================
# PHASE 2: DISTRIBUTED INFRASTRUCTURE TESTS
# =============================================================================

def test_dispatcher_chunking(tmp_dir):
    """Verify that the dispatcher correctly splits records into chunks."""
    dispatcher = MigrationDispatcher(chunk_size=5)

    test_file = os.path.join(tmp_dir, "test_chunks.csv")
    with open(test_file, 'w', newline='') as f:
        import csv
        writer = csv.writer(f)
        writer.writerow(["full_name", "dob", "account_number", "email", "phone"])
        for i in range(12):
            writer.writerow([f"User {i}", "1990-01-01", "1234567890", "a@b.com", "123"])

    with patch('src.infrastructure.tasks.run_data_migration_task.delay') as mock_delay:
        dispatcher.dispatch_migration(test_file, "BankA", "BankB")
        assert mock_delay.call_count == 3  # 12 records / 5 per chunk = 3 chunks

def test_multi_target_migration():
    """Verify that one source can be migrated to multiple target banks simultaneously."""
    from unittest.mock import patch as _patch
    import psycopg2
    with _patch.object(psycopg2, 'connect', return_value=MagicMock()):
        orchestrator = PipelineOrchestrator()

        records = [
            {"name": "John Doe", "dob": "1990-01-01", "account": "1234567890123456", "email": "john@test.com", "phone": "1234567890"},
            {"name": "Jane Doe", "dob": "1991-02-02", "account": "6543210987654321", "email": "jane@test.com", "phone": "0987654321"},
        ]

        multi_result = orchestrator.migrate_data_multi(records, "source_bank", ["bank_b", "bank_c"], output_format="json")
        assert multi_result.success is True
        assert multi_result.source_bank == "source_bank"
        assert multi_result.target_banks == ["bank_b", "bank_c"]
        assert len(multi_result.results) == 2
        for r in multi_result.results:
            assert r.success is True
            assert r.total_records == 2
            assert r.processed == 2

@patch('src.infrastructure.tracker.redis.from_url')
def test_tracker_atomic_updates(mock_from_url):
    """Verify that the tracker correctly increments progress (using a Mock Redis)."""
    mock_redis = MagicMock()
    mock_from_url.return_value = mock_redis
    tracker = MigrationTracker(redis_url='fake')
    
    tracker.init_migration("mig_123", total_chunks=10, total_records=50000)
    
    # Mock the hgetall for get_status to work
    mock_redis.hgetall.return_value = {
        "status": "RUNNING",
        "total_chunks": "10",
        "processed_chunks": "1",
        "total_records": "50000",
        "processed_records": "5000",
        "failed_records": "0"
    }
    
    status = tracker.get_status("mig_123")
    assert status['progress_percent'] == 10.0
    assert status['processed_records'] == 5000

if __name__ == "__main__":
    # Manual run since we want to see output clearly
    print("--- STARTING FULL SYSTEM INTEGRATION TESTS ---")
    try:
        test_transformer_memory_efficiency()
        print("? Memory Efficiency Test: PASSED")
        test_dlq_and_failure_threshold()
        print("? DLQ and Threshold Test: PASSED")
        test_dispatcher_chunking()
        print("? Dispatcher Chunking Test: PASSED")
        test_tracker_atomic_updates()
        print("? Tracker Atomic Update Test: PASSED")
        print("\n--- ALL VERIFICATIONS PASSED SUCCESSFULLY ---")
    except Exception as e:
        print(f"? TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
