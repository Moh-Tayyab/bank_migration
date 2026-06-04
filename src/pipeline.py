"""
Pipeline — a configurable chain of stages for record transformation.

Each stage is an adapter that implements the PipelineStage protocol:
    process(data, ctx) -> data

The Pipeline orchestrator chains stages, manages transactions, and
handles failure counting. Stages don't know about each other.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, Protocol, runtime_checkable

from .audit_logger import AuditLogger
from .models import AuditEvent, MigrationResult
from .transaction_rollback import TransactionManager


class PipelineError(Exception):
    """Raised by a stage to signal a record should be skipped."""

    def __init__(self, stage: str, message: str, record_id: str = ""):
        self.stage = stage
        self.record_id = record_id
        super().__init__(f"[{stage}] {message}")


@runtime_checkable
class PipelineStage(Protocol):
    """A single step in the transformation pipeline."""

    def process(self, data: Dict[str, Any], ctx: "PipelineContext") -> Dict[str, Any]:
        """Transform data and return the result.

        Raise PipelineError to signal that the record should be skipped.
        Any other exception is also caught and treated as a skip.
        """
        ...


@dataclass
class PipelineContext:
    """Metadata carried alongside the record through the pipeline."""

    record_id: str
    source_bank: str
    target_bank: str
    raw_data: Dict[str, Any]
    audit: Optional[AuditLogger] = None


class Pipeline:
    """A configurable chain of stages with transaction support.

    Usage::

        pipeline = Pipeline(
            stages=[ValidateStage(...), ParseStage(...), ...],
            txn=TransactionManager(),
            audit=AuditLogger(),
        )
        result = pipeline.run(records_iter, "bank_a", "bank_b")
    """

    def __init__(
        self,
        stages: List[PipelineStage],
        txn: Optional[TransactionManager] = None,
        audit: Optional[AuditLogger] = None,
    ):
        self._stages = stages
        self._txn = txn or TransactionManager()
        self._audit = audit or AuditLogger()

    def run(
        self,
        records: Iterator[Dict[str, Any]],
        source_bank: str,
        target_bank: str,
        failure_threshold: float = 0.05,
    ) -> MigrationResult:
        """Run the full pipeline over an iterator of raw records."""
        started_at = datetime.utcnow()
        bank_pair = f"{source_bank}->{target_bank}"

        self._audit.log(
            AuditEvent.TRANSFORM,
            record_id="",
            bank_pair=bank_pair,
            details=f"Pipeline started with {len(self._stages)} stages",
        )

        processed, failed = 0, 0
        self._txn.begin()

        for i, raw in enumerate(records):
            record_id = f"REC-{i + 1:06d}"
            ctx = PipelineContext(
                record_id=record_id,
                source_bank=source_bank,
                target_bank=target_bank,
                raw_data=raw,
                audit=self._audit,
            )
            try:
                data = dict(raw)
                for stage in self._stages:
                    data = stage.process(data, ctx)
                self._txn.savepoint(record_id, data)
                processed += 1
            except Exception as e:
                failed += 1
                self._txn.mark_failed(record_id, str(e))

        total = processed + failed
        failure_rate = failed / total if total > 0 else 0

        committed_records = []
        if failure_rate <= failure_threshold:
            committed_records = self._txn.commit()
            self._audit.log(
                AuditEvent.COMMITTED,
                record_id="",
                bank_pair=bank_pair,
                details=f"Committed {processed}/{total} records",
            )
        else:
            self._txn.rollback()
            self._audit.log(
                AuditEvent.ROLLED_BACK,
                record_id="",
                bank_pair=bank_pair,
                details=f"Rolled back: failure rate {failure_rate:.2%} exceeds threshold {failure_threshold:.2%}",
            )

        completed_at = datetime.utcnow()

        return MigrationResult(
            success=failure_rate <= failure_threshold,
            total_records=total,
            processed=processed,
            failed=failed,
            records=committed_records,
            audit_trail=self._audit.get_trail(),
            dlq=self._txn.get_failed_records(),
            started_at=started_at,
            completed_at=completed_at,
        )

    def run_file(
        self,
        filepath: str,
        source_bank: str,
        target_bank: str,
        failure_threshold: float = 0.05,
    ) -> MigrationResult:
        """Detect format, extract records, and run the pipeline."""
        from .detector import FormatDetector

        started_at = datetime.utcnow()

        file_format = FormatDetector.detect_format(filepath)
        records = FormatDetector.extract(filepath, file_format)

        result = self.run(iter(records), source_bank, target_bank, failure_threshold)
        result.started_at = started_at
        return result
