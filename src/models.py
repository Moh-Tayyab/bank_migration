from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class FileFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    DOCX = "docx"
    XLSX = "xlsx"
    XML = "xml"
    TXT = "txt"

class Record(BaseModel):
    data: Dict[str, Any]
    record_id: str
    source_bank: str
    target_bank: Optional[str] = None

class AuditEvent(str, Enum):
    VALIDATION = "VALIDATION"
    MAPPING = "MAPPING"
    TRANSFORM = "TRANSFORM"
    SECURITY_MASK = "SECURITY_MASK"
    ERROR = "ERROR"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"
    OUTPUT_GENERATED = "OUTPUT_GENERATED"

class AuditEntry(BaseModel):
    event: AuditEvent
    record_id: str = ""
    bank_pair: str = ""
    details: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class CanonicalRecord(BaseModel):
    record_id: str
    raw_data: Dict[str, Any]
    canonical_data: Dict[str, Any]
    source_bank: str
    encrypted: bool = False

class MigrationResult(BaseModel):
    success: bool
    total_records: int
    processed: int
    failed: int
    audit_trail: List[AuditEntry]
    records: List[Dict[str, Any]] = []
    dlq: Optional[Dict] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_path: Optional[str] = None
    error: Optional[str] = None

class MultiBankMigrationResult(BaseModel):
    success: bool
    source_bank: str
    target_banks: List[str]
    results: List[MigrationResult]

class MappingRule(BaseModel):
    source_field: str
    target_field: str
    default: Optional[Any] = None
    transform: Optional[str] = None

class BankSchema(BaseModel):
    bank_name: str
    version: str
    fields: Dict[str, Any]
    mappings: List[MappingRule]
    masking_rules: Dict[str, str]
