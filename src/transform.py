from datetime import datetime
from typing import Any, Dict, Iterator, List

from .audit_logger import AuditLogger
from .canonical_store import CanonicalStore
from .detector import FormatDetector
from .models import AuditEvent, CanonicalRecord, MigrationResult, Record
from .parser import Parser
from .rules_engine import build_standard_rules
from .schema_mapper import SchemaMapper
from .security import SecurityMasker
from .transaction_rollback import TransactionManager
from .validator import Validator


class Transformer:
    def __init__(
        self, validator=None, parser=None, mapper=None, rules=None, masker=None, audit=None, canonical=None, txn=None
    ):
        self._validator = validator or Validator()
        self._parser = parser or Parser()
        self._mapper = mapper or SchemaMapper()
        self._rules = rules or build_standard_rules()
        self._masker = masker or SecurityMasker()
        self._audit = audit or AuditLogger()
        self._canonical = canonical or CanonicalStore()
        self._txn = txn or TransactionManager()
        self._committed_records: List[Dict[str, Any]] = []

    def process_file(
        self, filepath: str, source_bank: str, target_bank: str, failure_threshold: float = 0.05
    ) -> MigrationResult:
        """Process a file from start to finish."""
        started_at = datetime.utcnow()
        try:
            # Detect format and extract records
            file_format = FormatDetector.detect_format(filepath)
            records = FormatDetector.extract(filepath, file_format)

            # Log file processing start
            self._audit.log(
                AuditEvent.TRANSFORM,
                record_id="",
                bank_pair=f"{source_bank}->{target_bank}",
                details=f"Started processing file: {filepath} ({len(records)} records)",
            )

            # Transform records using the existing transform method
            result = self.transform(iter(records), source_bank, target_bank, failure_threshold)

            # Update with timing
            result.started_at = started_at
            result.completed_at = datetime.utcnow()

            if result.success:
                self._audit.log(
                    AuditEvent.COMMITTED,
                    record_id="",
                    bank_pair=f"{source_bank}->{target_bank}",
                    details=f"Successfully processed {result.processed}/{result.total_records} records from {filepath}",
                )
            else:
                result.error = (
                    f"Failure rate {result.failed / result.total_records:.2%} exceeds threshold {failure_threshold:.2%}"
                )
                self._audit.log(
                    AuditEvent.ROLLED_BACK,
                    record_id="",
                    bank_pair=f"{source_bank}->{target_bank}",
                    details=result.error,
                )

            return result
        except Exception as e:
            completed_at = datetime.utcnow()
            self._audit.log(
                AuditEvent.ERROR,
                record_id="",
                bank_pair=f"{source_bank}->{target_bank}",
                details=f"File processing failed: {str(e)}",
            )
            return MigrationResult(
                success=False,
                total_records=0,
                processed=0,
                failed=0,
                audit_trail=self._audit.get_trail(),
                started_at=started_at,
                completed_at=completed_at,
                error=str(e),
            )

    def process_records(
        self, records: List[Dict[str, Any]], source_bank: str, target_bank: str, failure_threshold: float = 0.05
    ) -> MigrationResult:
        """Process a list of records from start to finish."""
        started_at = datetime.utcnow()
        try:
            self._audit.log(
                AuditEvent.TRANSFORM,
                record_id="",
                bank_pair=f"{source_bank}->{target_bank}",
                details=f"Started processing {len(records)} records",
            )

            # Transform records
            result = self.transform(iter(records), source_bank, target_bank, failure_threshold)

            # Update with timing
            result.started_at = started_at
            result.completed_at = datetime.utcnow()

            if result.success:
                self._audit.log(
                    AuditEvent.COMMITTED,
                    record_id="",
                    bank_pair=f"{source_bank}->{target_bank}",
                    details=f"Successfully processed {result.processed}/{result.total_records} records",
                )
            else:
                result.error = (
                    f"Failure rate {result.failed / result.total_records:.2%} exceeds threshold {failure_threshold:.2%}"
                )
                self._audit.log(
                    AuditEvent.ROLLED_BACK,
                    record_id="",
                    bank_pair=f"{source_bank}->{target_bank}",
                    details=result.error,
                )

            return result
        except Exception as e:
            completed_at = datetime.utcnow()
            self._audit.log(
                AuditEvent.ERROR,
                record_id="",
                bank_pair=f"{source_bank}->{target_bank}",
                details=f"Record processing failed: {str(e)}",
            )
            return MigrationResult(
                success=False,
                total_records=0,
                processed=0,
                failed=0,
                audit_trail=self._audit.get_trail(),
                started_at=started_at,
                completed_at=completed_at,
                error=str(e),
            )

    def get_committed_records(self) -> List[Dict[str, Any]]:
        """Get the processed and committed records."""
        return self._txn._committed if hasattr(self._txn, "_committed") else self._committed_records

    def transform(
        self,
        records_iterator: Iterator[Dict[str, Any]],
        source_bank: str,
        target_bank: str,
        failure_threshold: float = 0.05,
    ) -> MigrationResult:
        processed, failed = 0, 0
        self._txn.begin()
        for i, raw in enumerate(records_iterator):
            record_id = f"REC-{i + 1:06d}"
            try:
                record = Record(data=raw, record_id=record_id, source_bank=source_bank)
                validation = self._validator.validate(record)
                if not validation.is_valid:
                    failed += 1
                    self._txn.mark_failed(record_id, "Validation failed")
                    continue
                parsed = self._parser.parse_all(record.data)
                record.data = parsed
                record = self._mapper.map_record(record, target_bank)
                transformed = self._rules.apply(record)
                canonical = CanonicalRecord(
                    record_id=record_id,
                    raw_data=raw,
                    canonical_data=dict(transformed) if isinstance(transformed, dict) else dict(record.data),
                    source_bank=source_bank,
                )
                self._canonical.store(canonical)
                masked = self._masker.mask(transformed, record_id)
                self._txn.savepoint(record_id, masked)
                processed += 1
            except Exception as e:
                failed += 1
                self._txn.mark_failed(record_id, str(e))

        total = processed + failed
        failure_rate = failed / total if total > 0 else 0
        if failure_rate <= failure_threshold:
            self._txn.commit()
        else:
            self._txn.rollback()
        return MigrationResult(
            success=failure_rate <= failure_threshold,
            total_records=total,
            processed=processed,
            failed=failed,
            records=self.get_committed_records() if failure_rate <= failure_threshold else [],
            audit_trail=self._audit.get_trail(),
            dlq=self._txn.get_failed_records(),
        )
