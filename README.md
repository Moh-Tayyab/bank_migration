# UN Wallet Multi-Bank Data Migration Platform

Production-Grade Interbank ETL Platform for migrating billions of customer records between bank schemas with full audit trails, PII masking, and rollback safety.

## Architecture

```
INGEST → CANONICAL STORE → TRANSFORM → SECURE → DELIVER
```

## Quick Start

```bash
uv sync
uv run python api_only.py
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/banks` | List registered banks |
| POST | `/migrate/upload` | Upload file + migrate |
| POST | `/migrate/data` | Submit JSON records |
| GET | `/audit/{id}` | Get audit trail |

## Docker

```bash
cd docker
docker compose up --build
```

## Tech Stack

Python 3.11+, FastAPI, Pydantic v2, cryptography, openpyxl, python-docx

## Phase 1 Components

- Format auto-detection (CSV, JSON, DOCX, XLSX, XML, TXT)
- Validation engine (Pydantic-based)
- Intelligent name/date/address/currency parser
- Schema mapping engine (config-driven, multi-bank)
- Business rules engine
- PII detection & masking (account, email, phone)
- Immutable audit logging
- Transaction manager with rollback
- Multi-format output (JSON, CSV, DOCX, XLSX, HTML)
- AES-256 encrypted canonical data store