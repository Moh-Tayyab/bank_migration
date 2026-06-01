from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    canonical_store_dir: Path = Path("canonical_store")
    canonical_encryption_key: str = ""
    upload_dir: Path = Path("uploads")
    output_dir: Path = Path("output")
    log_dir: Path = Path("logs")
    bank_schema_dir: Path = Path("config/bank_schemas")
    max_file_size_mb: int = 500
    throughput_target: int = 400
    openai_api_key: str = ""

    upload_ttl_hours: int = 0
    output_ttl_hours: int = 168
    audit_ttl_hours: int = 720
    canonical_ttl_hours: int = 72
    cleanup_on_startup: bool = True
    cleanup_dry_run: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()