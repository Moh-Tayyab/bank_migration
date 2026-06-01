import json
import logging
import mimetypes
import os
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Security, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.config import settings
from src.infrastructure.retention import DataRetentionPolicy
from src.production import PipelineOrchestrator

logger = logging.getLogger(__name__)

API_KEY_NAME = "X-API-Key"
_api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

limiter = Limiter(key_func=get_remote_address)


async def verify_api_key(api_key: str = Security(_api_key_header)):
    expected = os.getenv("API_KEY", "")
    if not expected:
        return None  # auth disabled if no key configured
    if api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key


def _get_celery_tasks():
    try:
        from src.infrastructure.tasks import run_data_migration_task, run_full_migration_task, run_multi_migration_task

        return run_full_migration_task, run_data_migration_task, run_multi_migration_task
    except Exception:
        logger.debug("Celery tasks not available, falling back to synchronous processing")
        return None, None, None


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.cleanup_on_startup:
        try:
            policy = DataRetentionPolicy()
            report = policy.run_all()
            if report.total_deleted > 0:
                logger.info(
                    "Startup cleanup: deleted %d uploads, %d output, %d audit, %d canonical",
                    report.uploads_deleted,
                    report.output_deleted,
                    report.audit_deleted,
                    report.canonical_deleted,
                )
        except Exception as e:
            logger.warning("Startup cleanup failed (non-fatal): %s", e)
    yield


app = FastAPI(
    title="UN Wallet Multi-Bank Data Migration API",
    description="Production-Grade Interbank ETL Platform",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = PipelineOrchestrator()
_schema_ai = None
_anomaly_ai = None


def get_schema_ai():
    global _schema_ai
    if _schema_ai is None:
        from src.ai.schema_agent import SchemaIntelligenceAgent

        _schema_ai = SchemaIntelligenceAgent()
    return _schema_ai


def get_anomaly_ai():
    global _anomaly_ai
    if _anomaly_ai is None:
        from src.ai.anomaly_agent import AnomalyDetectionAgent

        _anomaly_ai = AnomalyDetectionAgent()
    return _anomaly_ai


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/migrate/upload")
@limiter.limit("10/minute")
async def migrate_upload(
    request: Request,
    _auth=Depends(verify_api_key),
    file: UploadFile = File(...),
    source_bank: str = Form(...),
    target_banks: str = Form("[]"),
    output_format: Optional[str] = Form("json"),
):
    import json as _json

    banks = _json.loads(target_banks) if isinstance(target_banks, str) else target_banks
    os.makedirs(settings.upload_dir, exist_ok=True)
    safe_filename = os.path.basename(file.filename or "upload")
    file_id = str(uuid.uuid4())
    filepath = os.path.join(settings.upload_dir, f"{file_id}_{safe_filename}")
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    try:
        with open(filepath, "wb") as f:
            total = 0
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_file_size_mb}MB limit")
                f.write(chunk)
    except BaseException:
        if os.path.exists(filepath):
            os.remove(filepath)
        raise

    celery_dispatched = False
    try:
        if len(banks) == 1:
            run_full, _, _ = _get_celery_tasks()
            if run_full:
                try:
                    task = run_full.delay(filepath, source_bank, banks[0], output_format)
                    celery_dispatched = True
                    task_id = task.id
                    return {
                        "task_id": task_id,
                        "status": "queued",
                        "message": (
                            f"Migration to {len(banks)} target bank(s) started in "
                            f"background. Use /status/{task_id} to check progress."
                        ),
                        "file_id": file_id,
                    }
                except Exception:
                    logger.debug("Celery task dispatch failed, running synchronously")
            result = orchestrator.migrate_file(filepath, source_bank, banks[0], output_format)
            return json.loads(result.model_dump_json())
        else:
            _, _, run_multi = _get_celery_tasks()
            if run_multi:
                try:
                    task = run_multi.delay(filepath, source_bank, banks, output_format)
                    celery_dispatched = True
                    task_id = task.id
                    return {
                        "task_id": task_id,
                        "status": "queued",
                        "message": (
                            f"Migration to {len(banks)} target bank(s) started in "
                            f"background. Use /status/{task_id} to check progress."
                        ),
                        "file_id": file_id,
                    }
                except Exception:
                    logger.debug("Celery multi-task dispatch failed, running synchronously")
            result = orchestrator.migrate_file_multi(filepath, source_bank, banks, output_format)
            return json.loads(result.model_dump_json())
    except HTTPException:
        raise
    except Exception:
        logger.exception("Migration failed")
        raise HTTPException(status_code=500, detail="Migration failed. Check server logs for details.")
    finally:
        if not celery_dispatched and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass


@app.post("/migrate/data")
@limiter.limit("10/minute")
async def migrate_data(
    request: Request,
    _auth=Depends(verify_api_key),
):
    import json as _json

    body = await request.json()
    records = body.get("records", [])
    source_bank = body.get("source_bank", "")
    target_banks_raw = body.get("target_banks", [])
    output_format = body.get("output_format", "json")
    banks = target_banks_raw if isinstance(target_banks_raw, list) else _json.loads(target_banks_raw)

    if len(banks) == 1:
        _, run_data, _ = _get_celery_tasks()
        if run_data:
            try:
                task = run_data.delay(records, source_bank, banks[0], output_format)
                return {
                    "task_id": task.id,
                    "status": "queued",
                    "message": f"Migration to {len(banks)} target bank(s) started in background.",
                }
            except Exception:
                logger.debug("Celery data task dispatch failed, running synchronously")
        result = orchestrator.migrate_data(records, source_bank, banks[0], output_format)
        return json.loads(result.model_dump_json())
    else:
        _, _, run_multi = _get_celery_tasks()
        if run_multi:
            try:
                task = run_multi.delay(records, source_bank, banks, output_format)
                return {
                    "task_id": task.id,
                    "status": "queued",
                    "message": f"Migration to {len(banks)} target bank(s) started in background.",
                }
            except Exception:
                logger.debug("Celery multi-data task dispatch failed, running synchronously")
        result = orchestrator.migrate_data_multi(records, source_bank, banks, output_format)
        return json.loads(result.model_dump_json())


@app.get("/status/{task_id}")
@limiter.limit("30/minute")
async def get_task_status(request: Request, task_id: str, _auth=Depends(verify_api_key)):
    try:
        from src.infrastructure.celery_app import app as celery_app

        task_result = celery_app.AsyncResult(task_id)
        response = {
            "task_id": task_id,
            "status": task_result.status,
            "result": task_result.result if task_result.ready() else None,
        }
        return response
    except Exception:
        logger.debug("Celery status check failed")
        return {"task_id": task_id, "status": "unavailable", "result": None}


@app.get("/banks")
@limiter.limit("30/minute")
async def list_banks(request: Request, _auth=Depends(verify_api_key)):
    return {"banks": orchestrator.get_banks()}


@app.get("/schema/{source_bank}/{target_bank}")
@limiter.limit("30/minute")
async def get_schema_mapping(request: Request, source_bank: str, target_bank: str, _auth=Depends(verify_api_key)):
    mappings = orchestrator.get_schema_mapping(source_bank, target_bank)
    return {"source_bank": source_bank, "target_bank": target_bank, "mappings": mappings}


@app.get("/download/{filename}")
@limiter.limit("20/minute")
async def download_file(request: Request, filename: str, _auth=Depends(verify_api_key)):
    safe_name = os.path.basename(filename)
    filepath = settings.output_dir / safe_name
    if not filepath.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    media_type, _ = mimetypes.guess_type(str(filepath))
    return FileResponse(
        path=str(filepath),
        media_type=media_type or "application/octet-stream",
        filename=safe_name,
    )


@app.post("/preview")
@limiter.limit("10/minute")
async def preview_file(
    request: Request,
    _auth=Depends(verify_api_key),
    file: UploadFile = File(...),
    row_limit: int = Form(10),
    source_bank: Optional[str] = Form(None),
):
    row_limit = min(row_limit, 100)
    os.makedirs(settings.upload_dir, exist_ok=True)
    safe_filename = os.path.basename(file.filename or "upload")
    file_id = str(uuid.uuid4())
    filepath = os.path.join(settings.upload_dir, f"{file_id}_{safe_filename}")
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    try:
        with open(filepath, "wb") as f:
            total = 0
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_file_size_mb}MB limit")
                f.write(chunk)
    except BaseException:
        if os.path.exists(filepath):
            os.remove(filepath)
        raise
    try:
        detected, records = orchestrator.preview_file(filepath, row_limit)
        columns = list(records[0].keys()) if records else []

        # Auto-detect target bank based on column matching
        detected_target = None
        if columns:
            exclude = [source_bank] if source_bank else []
            detected_target = orchestrator._registry.detect_target_bank(columns, exclude_banks=exclude)

        return {
            "filename": file.filename,
            "format": detected,
            "total_columns": len(columns),
            "columns": columns,
            "rows": records,
            "row_count": len(records),
            "detected_target_bank": detected_target,
        }
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@app.post("/sqlldr/generate")
@limiter.limit("10/minute")
async def generate_sqlldr_script(
    request: Request,
    _auth=Depends(verify_api_key),
    file: UploadFile = File(...),
    table_name: Optional[str] = Form(None),
):
    """
    Generate SQL*Loader shell script with embedded control file and data.
    The script can be run on target Oracle database to load the uploaded data.
    """
    import csv

    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.output_dir, exist_ok=True)

    safe_filename = os.path.basename(file.filename or "data.csv")
    file_id = str(uuid.uuid4())
    filepath = os.path.join(settings.upload_dir, f"{file_id}_{safe_filename}")

    max_bytes = settings.max_file_size_mb * 1024 * 1024
    try:
        with open(filepath, "wb") as f:
            total = 0
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_file_size_mb}MB limit")
                f.write(chunk)
    except BaseException:
        if os.path.exists(filepath):
            os.remove(filepath)
        raise

    try:
        # Read CSV directly for SQL*Loader (include all rows)
        records = []
        columns = []

        with open(filepath, "r", newline="", encoding="utf-8") as f:
            # Try to detect delimiter
            sample = f.read(1024)
            f.seek(0)

            sniffer = csv.Sniffer()
            delimiter = ","
            try:
                delimiter = sniffer.sniff(sample).delimiter
            except Exception:
                delimiter = ","

            reader = csv.DictReader(f, delimiter=delimiter)
            if reader.fieldnames:
                columns = list(reader.fieldnames)

            for row in reader:
                # Convert to dict with string values
                records.append({k: (v if v != "" else None) for k, v in row.items()})

        if not records:
            raise HTTPException(status_code=400, detail="No records found in uploaded file")

        # Generate table name if not provided
        if not table_name:
            # Use filename for table name
            base_name = os.path.splitext(safe_filename)[0]
            table_name = re.sub(r"[^a-zA-Z0-9_]", "_", base_name).upper()[:30]
            if not table_name or table_name[0].isdigit():
                table_name = "T_" + table_name
            if not table_name:
                table_name = "BANK_MIGRATION_DATA"

        # Detect column types
        def detect_type(value):
            if value is None or value == "":
                return "CHAR(100)"

            # Try to parse as number (CSV returns strings)
            str_val = str(value).strip()

            # Check for boolean
            if str_val.lower() in ("true", "false", "yes", "no", "1", "0"):
                return "CHAR(1)"

            # Check for integer
            try:
                int(str_val)
                return "INTEGER EXTERNAL"
            except ValueError:
                pass

            # Check for float
            try:
                float(str_val)
                return "DECIMAL EXTERNAL"
            except ValueError:
                pass

            # Check for date patterns
            if re.match(r"^\d{4}-\d{2}-\d{2}$", str_val):
                return "DATE 'YYYY-MM-DD'"
            if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", str_val):
                return "DATE 'YYYY-MM-DD HH24:MI:SS'"

            # Default to CHAR
            str_len = len(str_val)
            if str_len < 50:
                return f"CHAR({max(str_len, 50)})"
            elif str_len < 255:
                return "CHAR(255)"
            else:
                return "CHAR(1000)"

        column_defs = []
        for col in columns:
            col_clean = re.sub(r"[^a-zA-Z0-9_]", "_", str(col)).upper()
            if not col_clean or col_clean[0].isdigit():
                col_clean = "COL_" + col_clean
            col_clean = col_clean[:30]
            # Sample first non-null value for type detection
            sample_val = None
            for record in records:
                if col in record and record[col] is not None:
                    sample_val = record[col]
                    break
            col_type = detect_type(sample_val)
            column_defs.append(f"  {col_clean} {col_type}")

        # Generate script filename
        script_filename = f"sqlldr_{file_id}_{table_name}.sh"
        script_path = os.path.join(settings.output_dir, script_filename)

        # Escape CSV field
        def escape_csv(field):
            if field is None:
                return ""
            value = str(field)
            if any(char in value for char in [",", '"', "\n"]):
                value = value.replace('"', '""')
                return f'"{value}"'
            return value

        # Write SQL*Loader script
        script_lines = [
            "#!/bin/bash",
            "#",
            "# SQL*Loader Script for Bank Data Migration",
            "# Generated by UN Wallet Multi-Bank Data Migration Platform",
            "#",
            f"# Source File: {safe_filename}",
            f"# Target Table: {table_name}",
            f"# Records: {len(records)}",
            "#",
            "# Usage:",
            "#   1. Update database connection below (replace username/password@database)",
            "#   2. Run: bash " + script_filename,
            "#   3. Check log files: migration.log and migration.bad",
            "#",
            "",
            "# ==================== DATABASE CONNECTION ====================",
            "# Update this with your Oracle database connection details",
            'DB_USER="your_username"',
            'DB_PASS="your_password"',
            'DB_CONNECT="your_database"',
            "",
            "# ==================== RUN SQL*LOADER ====================",
            "",
            "sqlldr userid=${DB_USER}/${DB_PASS}@${DB_CONNECT} \\",
            "       control=stdin \\",
            "       log=migration.log \\",
            "       bad=migration.bad \\",
            "       discard=migration.discard <<EOF",
            "",
            "OPTIONS (",
            "    DIRECT=TRUE,",
            "    BINDSIZE=5000000,",
            "    ROWS=1000,",
            "    ERRORS=1000",
            ")",
            "",
            "LOAD DATA",
            "INFILE *",
            f"INTO TABLE {table_name}",
            "TRUNCATE",
            "FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '\"' TRAILING NULLCOLS",
            "(",
            ",\n".join(column_defs),
            ")",
            "",
            "BEGINDATA",
        ]

        # Add data rows
        for record in records:
            row_values = [escape_csv(record.get(col)) for col in columns]
            script_lines.append(",".join(row_values))

        script_lines.extend(
            [
                "EOF",
                "",
                "# ==================== STATUS ====================",
                "echo 'SQL*Loader completed. Check migration.log for details.'",
                "if [ -f migration.bad ]; then",
                "    echo 'Rejected records: ' $(wc -l < migration.bad)",
                "fi",
            ]
        )

        with open(script_path, "w") as f:
            f.write("\n".join(script_lines))

        # Make executable
        try:
            os.chmod(script_path, 0o755)
        except Exception:
            pass

        return {
            "success": True,
            "script_filename": script_filename,
            "download_url": f"/download/{script_filename}",
            "table_name": table_name,
            "records_count": len(records),
            "columns": columns,
            "source_file": safe_filename,
        }

    finally:
        # Clean up uploaded file
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass


@app.get("/audit/{migration_id}")
@limiter.limit("30/minute")
async def get_audit(request: Request, migration_id: str, _auth=Depends(verify_api_key)):
    trail = orchestrator.get_audit_trail(migration_id)
    return {"entries": [json.loads(e.model_dump_json()) for e in trail]}


@app.get("/audit/{migration_id}/export")
@limiter.limit("20/minute")
async def export_audit_csv(request: Request, migration_id: str, _auth=Depends(verify_api_key)):
    import csv
    import io

    from fastapi.responses import StreamingResponse

    trail = orchestrator.get_audit_trail(migration_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "event", "record_id", "bank_pair", "details"])
    for entry in trail:
        writer.writerow([entry.timestamp, entry.event.value, entry.record_id, entry.bank_pair, entry.details])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=audit_{migration_id}.csv"},
    )


@app.post("/admin/cleanup")
@limiter.limit("2/minute")
async def admin_cleanup(
    request: Request,
    _auth=Depends(verify_api_key),
    target: Optional[str] = None,
    dry_run: bool = False,
):
    policy = DataRetentionPolicy(dry_run=dry_run)
    if target == "uploads":
        return {"target": "uploads", "deleted": policy.cleanup_uploads(), "dry_run": dry_run}
    elif target == "output":
        return {"target": "output", "deleted": policy.cleanup_output(), "dry_run": dry_run}
    elif target == "audit":
        return {"target": "audit", "deleted": policy.cleanup_audit_logs(), "dry_run": dry_run}
    elif target == "canonical":
        return {"target": "canonical", "deleted": policy.cleanup_canonical_store(), "dry_run": dry_run}
    else:
        report = policy.run_all()
        return {
            "target": "all",
            "dry_run": dry_run,
            "uploads_deleted": report.uploads_deleted,
            "output_deleted": report.output_deleted,
            "audit_deleted": report.audit_deleted,
            "canonical_deleted": report.canonical_deleted,
            "total_deleted": report.total_deleted,
            "errors": report.errors,
        }


# --- AI Orchestration Endpoints ---


@app.post("/ai/suggest-mapping")
@limiter.limit("5/minute")
async def ai_suggest_mapping(
    request: Request,
    _auth=Depends(verify_api_key),
    source_bank: str = Form(...),
    target_bank: str = Form(...),
    target_docs: str = Form(...),
):
    """
    AI analyzes target bank docs and suggests a schema mapping.
    """
    try:
        suggestion = get_schema_ai().suggest_mapping(source_bank, target_bank, target_docs)
        return {"suggestion": suggestion}
    except Exception:
        logger.exception("AI schema suggestion failed")
        raise HTTPException(status_code=500, detail="Failed to generate schema suggestion.")


@app.post("/ai/apply-mapping")
@limiter.limit("5/minute")
async def ai_apply_mapping(request: Request, suggestion: dict, _auth=Depends(verify_api_key)):
    """
    Validates and saves an AI suggested mapping to the registry.
    """
    try:
        path = get_schema_ai().apply_suggestion(suggestion)
        return {"status": "success", "saved_at": path}
    except Exception:
        logger.exception("AI mapping application failed")
        raise HTTPException(status_code=400, detail="Failed to apply schema mapping.")


@app.get("/ai/analyze-anomaly/{migration_id}")
@limiter.limit("5/minute")
async def ai_analyze_anomaly(request: Request, migration_id: str, _auth=Depends(verify_api_key)):
    """
    AI analyzes the audit trail for a specific migration to detect quality issues.
    """
    try:
        analysis = get_anomaly_ai().analyze_audit_trail(migration_id)
        return analysis
    except Exception:
        logger.exception("AI anomaly analysis failed")
        raise HTTPException(status_code=500, detail="Failed to analyze audit trail.")


def main():
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    uvicorn.run("api_only:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
