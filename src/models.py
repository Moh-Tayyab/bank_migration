from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime


class FileFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    DOCX = "docx"
    XLSX = "xlsx"
    XML = "xml"
    TXT = "txt"


class AuditEvent(str, Enum):
    INPUT_RECEIVED = "INPUT_RECEIVED"
    VALIDATION = "VALIDATION"
    MAPPING = "MAPPING"
    TRANSFORM = "TRANSFORM"
    SECURITY_MASK = "SECURITY_MASK"
    OUTPUT_GENERATED = "OUTPUT_GENERATED"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"
    ERROR = "ERROR"


class Record(BaseModel):
    data: Dict[str, Any]
    record_id: str = ""
    source_bank: str = ""
    target_bank: str = ""
    schema_version: str = ""


class CanonicalRecord(BaseModel):
    record_id: str
    raw_data: Dict[str, Any]
    canonical_data: Dict[str, Any]
    source_bank: str
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    encrypted: bool = False


class MappingRule(BaseModel):
    source_field: str
    target_field: str
    transform: Optional[str] = None
    default: Optional[Any] = None
    required: bool = False


class BankSchema(BaseModel):
    bank_name: str
    version: str
    fields: Dict[str, Dict[str, Any]]
    mappings: List[MappingRule]
    masking_rules: Dict[str, str]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditEntry(BaseModel):
    event: AuditEvent
    record_id: str
    bank_pair: str
    details: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MigrationResult(BaseModel):
    success: bool
    total_records: int
    processed: int
    failed: int
    output_path: Optional[str] = None
    audit_trail: List[AuditEntry] = []
    error: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None