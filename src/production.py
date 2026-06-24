from datetime import datetime
from typing import Any, Dict, List, Optional

from .audit_logger import AuditEntry, AuditLogger
from .config import settings
from .detector import FormatDetector
from .models import AuditEvent, MigrationResult, MultiBankMigrationResult
from .output import get_writer
from .pipeline import Pipeline
from .registry import BankRegistry
from .rules_engine import build_standard_rules
from .stages import (
    MapStage,
    MaskStage,
    ParseStage,
    RulesStage,
    StoreStage,
    ValidateStage,
)
from .transaction_rollback import TransactionManager


def _build_generic_pipeline(audit: Optional[AuditLogger] = None) -> Pipeline:
    """Build the default generic migration pipeline."""
    audit = audit or AuditLogger()
    return Pipeline(
        stages=[
            ValidateStage(),
            ParseStage(),
            MapStage(),
            RulesStage(engine=build_standard_rules()),
            StoreStage(),
            MaskStage(),
        ],
        txn=TransactionManager(),
        audit=audit,
    )


class PipelineOrchestrator:
    def __init__(self):
        self._registry = BankRegistry(str(settings.bank_schema_dir))
        self._audit_logger = AuditLogger()
        self._pipeline = _build_generic_pipeline(self._audit_logger)

    def _run_transformer_pipeline(
        self,
        filepath: str,
        source_bank: str,
        target_bank: str,
        transformer,
    ) -> MigrationResult:
        from .transformers import PII_NULL_FIELDS, TARGET_FIELDS

        records = FormatDetector.extract(filepath)
        results = transformer.transform_batch(records)
        summary = transformer.get_batch_summary(results)

        self._audit_logger.log(
            AuditEvent.TRANSFORM,
            bank_pair=f"{source_bank}->{target_bank}",
            details=(
                f"Transformer pipeline ({source_bank}): "
                f"{summary['successful_transformations']}/{summary['total_records']} "
                f"success, {summary['requires_review']} review, "
                f"{summary['pep_count']} PEP, avg confidence {summary['average_confidence']:.2f}"
            ),
        )

        target_records = []
        failed = 0
        for r in results:
            tgt = {f: r.target_record.get(f) for f in TARGET_FIELDS}
            for f in PII_NULL_FIELDS:
                tgt[f] = None
            tgt["MigrationTimestamp"] = datetime.utcnow().isoformat() + "Z"
            tgt["MigrationSource"] = source_bank.upper()
            tgt["MigrationTarget"] = target_bank.upper()
            target_records.append(tgt)
            if not r.success:
                failed += 1

        return MigrationResult(
            success=(failed == 0),
            total_records=len(records),
            processed=len(records) - failed,
            failed=failed,
            records=target_records,
            audit_trail=self._audit_logger.get_trail(),
            source_bank=source_bank,
            target_bank=target_bank,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

    def migrate_file(
        self,
        filepath: str,
        source_bank: str,
        target_bank: str,
        output_format: Optional[str] = None,
    ) -> MigrationResult:
        if source_bank == "auto":
            result = self._pipeline.run_file(filepath, "__auto__", target_bank)
        else:
            from .transformers import get_transformer

            transformer = get_transformer(source_bank)
            if transformer is not None:
                result = self._run_transformer_pipeline(filepath, source_bank, target_bank, transformer)
            else:
                result = self._pipeline.run_file(filepath, source_bank, target_bank)
        if result.success and result.processed > 0:
            result = self._generate_output(result, target_bank, output_format)
        return result

    def migrate_data(
        self,
        records: List[Dict[str, Any]],
        source_bank: str,
        target_bank: str,
        output_format: Optional[str] = None,
    ) -> MigrationResult:
        result = self._pipeline.run(iter(records), source_bank, target_bank)
        if result.success and result.processed > 0:
            result = self._generate_output(result, target_bank, output_format)
        return result

    def _generate_output(
        self,
        result: MigrationResult,
        target_bank: str,
        output_format: Optional[str] = None,
    ) -> MigrationResult:
        fmt = output_format or "json"
        writer = get_writer(fmt)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_path = settings.output_dir / f"migration_{target_bank}_{timestamp}.{fmt}"
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        writer.write(result, str(output_path))
        result.output_path = str(output_path)
        self._audit_logger.log(
            AuditEvent.OUTPUT_GENERATED,
            bank_pair=f"->{target_bank}",
            details=f"Output written to {output_path}",
        )
        return result

    def migrate_file_multi(
        self,
        filepath: str,
        source_bank: str,
        target_banks: List[str],
        output_format: Optional[str] = None,
    ) -> MultiBankMigrationResult:
        results: List[MigrationResult] = []
        all_success = True
        for target_bank in target_banks:
            result = self.migrate_file(filepath, source_bank, target_bank, output_format)
            results.append(result)
            if not result.success:
                all_success = False
        return MultiBankMigrationResult(
            success=all_success,
            source_bank=source_bank,
            target_banks=target_banks,
            results=results,
        )

    def migrate_data_multi(
        self,
        records: List[Dict[str, Any]],
        source_bank: str,
        target_banks: List[str],
        output_format: Optional[str] = None,
    ) -> MultiBankMigrationResult:
        results: List[MigrationResult] = []
        all_success = True
        for target_bank in target_banks:
            result = self.migrate_data(records, source_bank, target_bank, output_format)
            results.append(result)
            if not result.success:
                all_success = False
        return MultiBankMigrationResult(
            success=all_success,
            source_bank=source_bank,
            target_banks=target_banks,
            results=results,
        )

    def get_banks(self) -> List[str]:
        return self._registry.list_banks()

    def get_schema_mapping(self, source_bank: str, target_bank: str) -> List[Dict[str, Any]]:
        try:
            mappings = self._registry.get_mappings(source_bank, target_bank)
            return [m.model_dump() for m in mappings]
        except Exception:
            return []

    def detect_target_bank(self, columns: List[str], exclude_banks: Optional[List[str]] = None) -> Optional[str]:
        return self._registry.detect_target_bank(columns, exclude_banks=exclude_banks)

    def preview_file(self, filepath: str, row_limit: int = 10) -> tuple[str, List[Dict[str, Any]]]:
        detected = FormatDetector.detect_format(filepath)
        records = FormatDetector.extract(filepath, detected)
        return detected.value, records[:row_limit]

    def get_audit_trail(self, migration_id: str) -> List[AuditEntry]:
        log_path = settings.log_dir / f"audit_{migration_id}.jsonl"
        return AuditLogger.read_trail(str(log_path))

    def get_canonical_store(self):
        """Return the canonical store for cleanup operations."""
        for stage in self._pipeline._stages:
            if hasattr(stage, "_canonical"):
                return stage._canonical
        return None
