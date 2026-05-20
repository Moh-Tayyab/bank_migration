from pydantic import BaseModel
from pathlib import Path


class Settings(BaseModel):
    canonical_store_dir: Path = Path("canonical_store")
    canonical_encryption_key: str = ""
    upload_dir: Path = Path("uploads")
    output_dir: Path = Path("output")
    log_dir: Path = Path("logs")
    bank_schema_dir: Path = Path("config/bank_schemas")
    max_file_size_mb: int = 500
    throughput_target: int = 400
    openai_api_key: str = ""


settings = Settings()