import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from typing import Optional, List
import os
import uuid
from datetime import datetime
from src.models import FileFormat
from src.production import PipelineOrchestrator
from src.config import settings
from src.infrastructure.tasks import run_full_migration_task, run_data_migration_task, run_multi_migration_task

app = FastAPI(
    title="UN Wallet Multi-Bank Data Migration API",
    description="Production-Grade Interbank ETL Platform",
    version="1.0.0",
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
async def migrate_upload(
    file: UploadFile = File(...),
    source_bank: str = Form(...),
    target_banks: str = Form("[]"),
    output_format: Optional[str] = Form("json"),
):
    import json as _json
    banks = _json.loads(target_banks) if isinstance(target_banks, str) else target_banks
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_id = str(uuid.uuid4())
    filepath = os.path.join(settings.upload_dir, f"{file_id}_{file.filename}")
    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)

    if len(banks) == 1:
        try:
            task = run_full_migration_task.delay(filepath, source_bank, banks[0], output_format)
            return {
                "task_id": task.id,
                "status": "queued",
                "message": f"Migration to {len(banks)} target bank(s) started in background. Use /status/{task_id} to check progress.",
                "file_id": file_id
            }
        except Exception:
            result = orchestrator.migrate_file(filepath, source_bank, banks[0], output_format)
            return result.model_dump()
    else:
        try:
            task = run_multi_migration_task.delay(filepath, source_bank, banks, output_format)
            return {
                "task_id": task.id,
                "status": "queued",
                "message": f"Migration to {len(banks)} target bank(s) started in background. Use /status/{task_id} to check progress.",
                "file_id": file_id
            }
        except Exception:
            result = orchestrator.migrate_file_multi(filepath, source_bank, banks, output_format)
            return result.model_dump()


@app.post("/migrate/data")
async def migrate_data(
    records: list[dict],
    source_bank: str = Form(...),
    target_banks: str = Form("[]"),
    output_format: Optional[str] = Form("json"),
):
    import json as _json
    banks = _json.loads(target_banks) if isinstance(target_banks, str) else target_banks

    if len(banks) == 1:
        try:
            task = run_data_migration_task.delay(records, source_bank, banks[0], output_format)
            return {
                "task_id": task.id,
                "status": "queued",
                "message": f"Migration to {len(banks)} target bank(s) started in background.",
            }
        except Exception:
            result = orchestrator.migrate_data(records, source_bank, banks[0], output_format)
            return result.model_dump()
    else:
        try:
            task = run_multi_migration_task.delay(records, source_bank, banks, output_format)
            return {
                "task_id": task.id,
                "status": "queued",
                "message": f"Migration to {len(banks)} target bank(s) started in background.",
            }
        except Exception:
            result = orchestrator.migrate_data_multi(records, source_bank, banks, output_format)
            return result.model_dump()


@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    from src.infrastructure.celery_app import app as celery_app
    task_result = celery_app.AsyncResult(task_id)
    
    response = {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result if task_result.ready() else None
    }
    return response


@app.get("/banks")
async def list_banks():
    return {"banks": orchestrator.get_banks()}


@app.get("/audit/{migration_id}")
async def get_audit(migration_id: str):
    trail = orchestrator.get_audit_trail(migration_id)
    return {"entries": [e.model_dump() for e in trail]}


# --- AI Orchestration Endpoints ---

@app.post("/ai/suggest-mapping")
async def ai_suggest_mapping(
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
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/apply-mapping")
async def ai_apply_mapping(suggestion: dict):
    """
    Validates and saves an AI suggested mapping to the registry.
    """
    try:
        path = get_schema_ai().apply_suggestion(suggestion)
        return {"status": "success", "saved_at": path}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/ai/analyze-anomaly/{migration_id}")
async def ai_analyze_anomaly(migration_id: str):
    """
    AI analyzes the audit trail for a specific migration to detect quality issues.
    """
    try:
        analysis = get_anomaly_ai().analyze_audit_trail(migration_id)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def main():
    uvicorn.run("api_only:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
