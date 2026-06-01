import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class CleanupReport:
    uploads_deleted: int = 0
    output_deleted: int = 0
    audit_deleted: int = 0
    canonical_deleted: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def total_deleted(self) -> int:
        return self.uploads_deleted + self.output_deleted + self.audit_deleted + self.canonical_deleted


class DataRetentionPolicy:
    def __init__(
        self,
        upload_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        log_dir: Optional[Path] = None,
        upload_ttl_hours: Optional[int] = None,
        output_ttl_hours: Optional[int] = None,
        audit_ttl_hours: Optional[int] = None,
        canonical_ttl_hours: Optional[int] = None,
        dry_run: bool = False,
    ):
        self._upload_dir = upload_dir or settings.upload_dir
        self._output_dir = output_dir or settings.output_dir
        self._log_dir = log_dir or settings.log_dir
        self._upload_ttl = upload_ttl_hours if upload_ttl_hours is not None else settings.upload_ttl_hours
        self._output_ttl = output_ttl_hours if output_ttl_hours is not None else settings.output_ttl_hours
        self._audit_ttl = audit_ttl_hours if audit_ttl_hours is not None else settings.audit_ttl_hours
        self._canonical_ttl = canonical_ttl_hours if canonical_ttl_hours is not None else settings.canonical_ttl_hours
        self._dry_run = dry_run or settings.cleanup_dry_run

    def run_all(self, canonical_store=None) -> CleanupReport:
        report = CleanupReport()
        report.uploads_deleted = self._cleanup_uploads()
        report.output_deleted = self._cleanup_output()
        report.audit_deleted = self._cleanup_audit_logs()
        report.canonical_deleted = self._cleanup_canonical_store(canonical_store)
        return report

    def cleanup_uploads(self) -> int:
        return self._cleanup_uploads()

    def cleanup_output(self) -> int:
        return self._cleanup_output()

    def cleanup_audit_logs(self) -> int:
        return self._cleanup_audit_logs()

    def cleanup_canonical_store(self, canonical_store=None) -> int:
        return self._cleanup_canonical_store(canonical_store)

    def _cleanup_uploads(self) -> int:
        return self._cleanup_dir_by_age(self._upload_dir, self._upload_ttl, "upload")

    def _cleanup_output(self) -> int:
        return self._cleanup_dir_by_age(self._output_dir, self._output_ttl, "output")

    def _cleanup_audit_logs(self) -> int:
        return self._cleanup_dir_by_age(self._log_dir, self._audit_ttl, "audit", pattern="audit_*.jsonl")

    def _cleanup_dir_by_age(self, directory: Path, ttl_hours: int, label: str, pattern: str = None) -> int:
        if ttl_hours <= 0:
            logger.debug("TTL for %s is 0 (disabled), skipping cleanup", label)
            return 0
        if not directory.exists():
            return 0

        cutoff = time.time() - (ttl_hours * 3600)
        deleted = 0
        glob_pattern = pattern or "*"

        for filepath in directory.glob(glob_pattern):
            if not filepath.is_file():
                continue
            if filepath.name.startswith("."):
                continue
            try:
                if filepath.stat().st_mtime < cutoff:
                    if self._dry_run:
                        logger.info("[DRY RUN] Would delete %s file: %s", label, filepath)
                    else:
                        filepath.unlink()
                        logger.info("Deleted expired %s file: %s", label, filepath)
                    deleted += 1
            except OSError as e:
                logger.warning("Failed to delete %s file %s: %s", label, filepath, e)

        return deleted

    def _cleanup_canonical_store(self, canonical_store=None) -> int:
        if self._canonical_ttl <= 0:
            logger.debug("Canonical TTL is 0 (disabled), skipping cleanup")
            return 0

        if canonical_store is None:
            try:
                from ..canonical_store import CanonicalStore

                canonical_store = CanonicalStore()
            except Exception as e:
                logger.warning("Cannot initialize canonical store for cleanup: %s", e)
                return 0

        deleted = 0

        if canonical_store._db_available and canonical_store.db is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=self._canonical_ttl)
            try:
                result = canonical_store.db.execute(
                    "SELECT record_id FROM canonical_records WHERE created_at < %s",
                    (cutoff,),
                )
                if result:
                    for row in result:
                        record_id = row["record_id"]
                        if self._dry_run:
                            logger.info("[DRY RUN] Would delete canonical record: %s", record_id)
                        else:
                            canonical_store.delete(record_id)
                        deleted += 1
            except Exception as e:
                logger.warning("Failed to cleanup canonical store records: %s", e)
        else:
            for record_id in canonical_store.list_records():
                if self._dry_run:
                    logger.info("[DRY RUN] Would delete in-memory canonical record: %s", record_id)
                else:
                    canonical_store.delete(record_id)
                deleted += 1

        return deleted

    @staticmethod
    def clear_in_memory_store(canonical_store) -> int:
        if canonical_store is None:
            return 0
        if hasattr(canonical_store, "_memory_store"):
            count = len(canonical_store._memory_store._records)
            canonical_store._memory_store._records.clear()
            logger.info("Cleared %d records from in-memory canonical store", count)
            return count
        return 0
