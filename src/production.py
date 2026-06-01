from datetime import datetime
from typing import Any, Dict, List, Optional

from .audit_logger import AuditEntry, AuditLogger
from .config import settings
from .detector import FormatDetector
from .models import AuditEvent, MigrationResult, MultiBankMigrationResult
from .output import get_writer
from .registry import BankRegistry
from .transform import Transformer


class PipelineOrchestrator:
    def __init__(self):
        self._registry = BankRegistry(str(settings.bank_schema_dir))
        self._audit_logger = AuditLogger()
        self._transformer = Transformer(
            audit=self._audit_logger,
        )

    def migrate_file(
        self,
        filepath: str,
        source_bank: str,
        target_bank: str,
        output_format: Optional[str] = None,
    ) -> MigrationResult:
        result = self._transformer.process_file(filepath, source_bank, target_bank)
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
        result = self._transformer.process_records(records, source_bank, target_bank)
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

    def preview_file(self, filepath: str, row_limit: int = 10) -> tuple[str, List[Dict[str, Any]]]:
        detected = FormatDetector.detect_format(filepath)
        records = FormatDetector.extract(filepath, detected)
        return detected.value, records[:row_limit]

    def get_audit_trail(self, migration_id: str) -> List[AuditEntry]:
        log_path = settings.log_dir / f"audit_{migration_id}.jsonl"
        return AuditLogger.read_trail(str(log_path))
