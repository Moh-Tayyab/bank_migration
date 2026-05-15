
from celery import shared_task
from .celery_app import app
import sys
import os

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
from .tracker import MigrationTracker

@shared_task(bind=True)
def process_migration_chunk(self, chunk_id: str, records: list, source_bank: str, target_bank: str, migration_id: str = "default"):
    """
    Task to process a chunk of records asynchronously and update the tracker.
    """
    print(f"Worker processing chunk {chunk_id} for migration {migration_id}...")
    
    # 1. Setup Pipeline
    audit = AuditLogger()
    canonical = CanonicalStore()
    txn = TransactionManager()
    parser = Parser()
    validator = Validator()
    mapper = SchemaMapper()
    rules = RulesEngine(build_standard_rules())
    masker = SecurityMasker(audit_logger=audit)
    registry = BankRegistry()
    
    registry.register_bank(target_bank, {
        "first_name": "full_name",
        "date_of_birth": "dob",
        "account_number": "account_number",
        "email": "email",
        "phone": "phone"
    })
    
    transformer = Transformer(validator, parser, mapper, rules, masker, audit, canonical, txn)
    tracker = MigrationTracker()
    
    # 2. Process
    result = transformer.transform(
        records_iterator=iter(records),
        source_bank=source_bank,
        target_bank=target_bank,
        failure_threshold=0.1
    )
    
    # 3. Update Redis Progress
    tracker.update_chunk_status(
        migration_id=migration_id,
        chunk_id=chunk_id,
        processed=result.processed,
        failed=result.failed
    )
    
    return {
        "chunk_id": chunk_id,
        "processed": result.processed,
        "failed": result.failed,
        "success": result.success
    }
