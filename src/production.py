from typing import Dict, Any, List, Optional
from pathlib import Path
import json
from datetime import datetime
from .models import MigrationResult, FileFormat, AuditEvent
from .transform import Transformer
from .detector import FormatDetector
from .validator import Validator
from .parser import Parser
from .schema_mapper import SchemaMapper
from .rules_engine import RulesEngine, build_standard_rules
from .security import SecurityMasker
from .audit_logger import AuditLogger, AuditEntry
from .canonical_store import CanonicalStore
from .transaction_rollback import TransactionManager
from .registry import BankRegistry
from .config import settings
from .output import get_writer


class PipelineOrchestrator:
    def __init__(self):
        self._registry = BankRegistry(str(settings.bank_schema_dir))
        self._audit_logger = AuditLogger()
        self._transformer = Transformer(
            audit_logger=self._audit_logger,
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

    def get_banks(self) -> List[str]:
        return self._registry.list_banks()

    def get_audit_trail(self, migration_id: str) -> List[AuditEntry]:
        log_path = settings.log_dir / f"audit_{migration_id}.jsonl"
        return AuditLogger.read_trail(str(log_path))