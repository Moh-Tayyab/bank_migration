import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
import os
import uuid
from datetime import datetime
from src.models import FileFormat
from src.production import PipelineOrchestrator
from src.config import settings

app = FastAPI(
    title="UN Wallet Multi-Bank Data Migration API",
    description="Production-Grade Interbank ETL Platform",
    version="1.0.0",
)

orchestrator = PipelineOrchestrator()


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/migrate/upload")
async def migrate_upload(
    file: UploadFile = File(...),
    source_bank: str = Form(...),
    target_bank: str = Form(...),
    output_format: Optional[str] = Form("json"),
):
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_id = str(uuid.uuid4())
    filepath = os.path.join(settings.upload_dir, f"{file_id}_{file.filename}")
    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)
    try:
        result = orchestrator.migrate_file(filepath, source_bank, target_bank, output_format)
        response_data = {
            "success": result.success,
            "total_records": result.total_records,
            "processed": result.processed,
            "failed": result.failed,
            "output_path": result.output_path,
            "error": result.error,
        }
        if result.output_path and os.path.exists(result.output_path):
            return FileResponse(
                result.output_path,
                filename=os.path.basename(result.output_path),
                media_type="application/octet-stream",
                headers={"X-Migration-Result": str(response_data)},
            )
        return response_data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/migrate/data")
async def migrate_data(
    records: list[dict],
    source_bank: str = Form(...),
    target_bank: str = Form(...),
    output_format: Optional[str] = Form("json"),
):
    try:
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
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/banks")
async def list_banks():
    return {"banks": orchestrator.get_banks()}


@app.get("/audit/{migration_id}")
async def get_audit(migration_id: str):
    trail = orchestrator.get_audit_trail(migration_id)
    return {"entries": [e.model_dump() for e in trail]}


def main():
    uvicorn.run("api_only:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()