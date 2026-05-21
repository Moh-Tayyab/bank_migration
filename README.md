# UN Wallet Multi-Bank Data Migration Platform

Production-Grade Interbank ETL Platform for migrating billions of customer records between bank schemas with full audit trails, PII masking, and rollback safety.

## Architecture

```
INGEST → CANONICAL STORE → TRANSFORM → SECURE → DELIVER
```

## Quick Start (Local Dev)

### 1. Backend

```bash
cd D:\Bank_Migration
uv sync
uv run python api_only.py
```

API → `http://localhost:8000`

### 2. Frontend

```bash
cd D:\Bank_Migration\frontend
npm install
npm run dev
```

UI → `http://localhost:3000`

## Docker Deployment (One Command)

```bash
cp .env.example .env
# Edit .env with your values
cd docker
docker compose up --build
```

Services:
- **PostgreSQL** → `localhost:5432`
- **Redis** → `localhost:6379`
- **API** → `http://localhost:8000`
- **Frontend** → `http://localhost:3000`
- **Celery Worker** → background task processing

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/banks` | List registered banks |
| POST | `/migrate/upload` | Upload file + migrate |
| POST | `/migrate/data` | Submit JSON records |
| POST | `/preview` | Preview file (first N rows) |
| GET | `/download/{filename}` | Download output file |
| GET | `/schema/{source}/{target}` | Get column mapping |
| GET | `/audit/{id}` | Get audit trail |
| GET | `/audit/{id}/export` | Export audit as CSV |
| POST | `/ai/suggest-mapping` | AI schema mapping suggestion |
| GET | `/ai/analyze-anomaly/{id}` | AI anomaly detection |

## Tech Stack

Python 3.11+, FastAPI, Pydantic v2, Next.js 16, PostgreSQL, Redis, Celery, cryptography

## Phase 1 Components

- Format auto-detection (CSV, JSON, DOCX, XLSX, XML, TXT)
- Column-aware extraction (only available source columns)
- Column mapping to target schema (config-driven, multi-bank)
- Default values for missing columns
- Validation engine (Pydantic-based)
- Intelligent name/date/address/currency parser
- Business rules engine
- PII detection & masking (account, email, phone)
- Immutable audit logging
- Transaction manager with ACID rollback
- Multi-format output (JSON, CSV, DOCX, XLSX, HTML)
- AES-256 encrypted canonical data store
- REST API + Web Dashboard
- Docker deployment with PostgreSQL + Redis
