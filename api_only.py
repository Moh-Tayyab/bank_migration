import uvicorn
import logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Security, Request
from fastapi.security import APIKeyHeader
from fastapi.responses import FileResponse
from typing import Optional, List
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import json
import mimetypes
from pathlib import Path
from datetime import datetime
from src.models import FileFormat
from src.production import PipelineOrchestrator
from src.config import settings

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
        from src.infrastructure.tasks import run_full_migration_task, run_data_migration_task, run_multi_migration_task
        return run_full_migration_task, run_data_migration_task, run_multi_migration_task
    except Exception:
        logger.debug("Celery tasks not available, falling back to synchronous processing")
        return None, None, None

app = FastAPI(
    title="UN Wallet Multi-Bank Data Migration API",
    description="Production-Grade Interbank ETL Platform",
    version="1.0.0",
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
    with open(filepath, "wb") as f:
        total = 0
        while chunk := await file.read(1024 * 1024):
            total += len(chunk)
            if total > max_bytes:
                f.close()
                os.remove(filepath)
                raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_file_size_mb}MB limit")
            f.write(chunk)

    try:
        if len(banks) == 1:
            run_full, _, _ = _get_celery_tasks()
            if run_full:
                try:
                    task = run_full.delay(filepath, source_bank, banks[0], output_format)
                    return {
                        "task_id": task.id,
                        "status": "queued",
                        "message": f"Migration to {len(banks)} target bank(s) started in background. Use /status/{task_id} to check progress.",
                        "file_id": file_id
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
                    return {
                        "task_id": task.id,
                        "status": "queued",
                        "message": f"Migration to {len(banks)} target bank(s) started in background. Use /status/{task_id} to check progress.",
                        "file_id": file_id
                    }
                except Exception:
                    logger.debug("Celery multi-task dispatch failed, running synchronously")
            result = orchestrator.migrate_file_multi(filepath, source_bank, banks, output_format)
            return json.loads(result.model_dump_json())
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        logger.exception("Migration failed")
        raise HTTPException(status_code=500, detail="Migration failed. Check server logs for details.")


@app.post("/migrate/data")
@limiter.limit("10/minute")
async def migrate_data(
    request: Request,
    records: list[dict],
    source_bank: str = Form(...),
    target_banks: str = Form("[]"),
    output_format: Optional[str] = Form("json"),
    _auth=Depends(verify_api_key),
):
    import json as _json
    banks = _json.loads(target_banks) if isinstance(target_banks, str) else target_banks

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
            "result": task_result.result if task_result.ready() else None
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
    except HTTPException:
        if os.path.exists(filepath):
            os.remove(filepath)
        raise
    try:
        detected, records = orchestrator.preview_file(filepath, row_limit)
        return {
            "filename": file.filename,
            "format": detected,
            "total_columns": len(records[0].keys()) if records else 0,
            "columns": list(records[0].keys()) if records else [],
            "rows": records,
            "row_count": len(records),
        }
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


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


# --- AI Orchestration Endpoints ---

@app.post("/ai/suggest-mapping")
@limiter.limit("5/minute")
async def ai_suggest_mapping(
    request: Request,
    _auth=Depends(verify_api_key),
    source_bank: str = Form(...),
    target_bank: str = Form(...),
    target_docs: str = Form(...)
):
    """
    AI analyzes target bank docs and suggests a schema mapping.
    """
    try:
        suggestion = get_schema_ai().suggest_mapping(source_bank, target_bank, target_docs)
        return {"suggestion": suggestion}
    except Exception as e:
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
    except Exception as e:
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
    except Exception as e:
        logger.exception("AI anomaly analysis failed")
        raise HTTPException(status_code=500, detail="Failed to analyze audit trail.")


def main():
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    uvicorn.run("api_only:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
