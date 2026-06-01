import json
import logging
import os as _os
from typing import List

from celery import shared_task

from src.production import PipelineOrchestrator

from .retention import DataRetentionPolicy

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def run_full_migration_task(self, filepath: str, source_bank: str, target_bank: str, output_format: str = "json"):
    """
    The primary background task that handles the entire ETL pipeline for a file.
    """
    logger.info(f"Starting background migration for file: {filepath}")
    orchestrator = None

    try:
        orchestrator = PipelineOrchestrator()
        result = orchestrator.migrate_file(
            filepath=filepath, source_bank=source_bank, target_bank=target_bank, output_format=output_format
        )
        return {
            "success": result.success,
            "total_records": result.total_records,
            "processed": result.processed,
            "failed": result.failed,
            "output_path": result.output_path,
            "error": result.error,
        }
    except Exception as e:
        logger.error(f"Migration failed for {filepath}: {str(e)}")
        return {"success": False, "error": str(e), "total_records": 0, "processed": 0, "failed": 0, "output_path": None}
    finally:
        if filepath and _os.path.exists(filepath):
            try:
                _os.remove(filepath)
                logger.info(f"Cleaned up uploaded file: {filepath}")
            except OSError as e:
                logger.warning(f"Failed to clean up uploaded file {filepath}: {e}")
        if orchestrator and hasattr(orchestrator, "_transformer"):
            DataRetentionPolicy.clear_in_memory_store(orchestrator._transformer._canonical)


@shared_task(bind=True)
def run_multi_migration_task(
    self, filepath_or_records, source_bank: str, target_banks: List[str], output_format: str = "json"
):
    logger.info(f"Starting multi-target migration to {target_banks}")
    orchestrator = None
    filepath = None

    try:
        orchestrator = PipelineOrchestrator()
        if isinstance(filepath_or_records, str):
            filepath = filepath_or_records
            result = orchestrator.migrate_file_multi(filepath, source_bank, target_banks, output_format)
        else:
            result = orchestrator.migrate_data_multi(filepath_or_records, source_bank, target_banks, output_format)
        return json.loads(result.model_dump_json())
    except Exception as e:
        logger.error(f"Multi-target migration failed: {str(e)}")
        return {"success": False, "error": str(e)}
    finally:
        if filepath and _os.path.exists(filepath):
            try:
                _os.remove(filepath)
                logger.info(f"Cleaned up uploaded file: {filepath}")
            except OSError as e:
                logger.warning(f"Failed to clean up uploaded file {filepath}: {e}")
        if orchestrator and hasattr(orchestrator, "_transformer"):
            DataRetentionPolicy.clear_in_memory_store(orchestrator._transformer._canonical)


@shared_task(bind=True)
def run_data_migration_task(self, records: list, source_bank: str, target_bank: str, output_format: str = "json"):
    """
    Task to process raw record lists asynchronously.
    """
    logger.info(f"Starting background record migration for {len(records)} records")
    orchestrator = None

    try:
        orchestrator = PipelineOrchestrator()
        result = orchestrator.migrate_data(records, source_bank, target_bank, output_format)
        return {
            "success": result.success,
            "total_records": result.total_records,
            "processed": result.processed,
            "failed": result.failed,
            "output_path": result.output_path,
            "error": result.error,
        }
    except Exception as e:
        logger.error(f"Data migration failed: {str(e)}")
        return {"success": False, "error": str(e), "total_records": 0, "processed": 0, "failed": 0, "output_path": None}
    finally:
        if orchestrator and hasattr(orchestrator, "_transformer"):
            DataRetentionPolicy.clear_in_memory_store(orchestrator._transformer._canonical)
