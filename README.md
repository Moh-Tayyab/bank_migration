# UN Wallet Multi-Bank Data Migration Platform

Production-grade ETL platform for migrating customer records between different bank schemas. Handles file ingestion, canonical normalization, schema mapping, PII masking, validation, and multi-format output — with full audit trails and rollback safety.

## Architecture

```
INGEST → CANONICAL STORE → TRANSFORM → SECURE → DELIVER
```

**Pipeline flow (per record):**

1. **FormatDetector** — auto-detects file format (CSV, JSON, DOCX, XLSX, XML, TXT) and extracts raw records
2. **Validator** — Pydantic-based field validation
3. **Parser** — intelligent parsing of names, dates, addresses, currencies
4. **SchemaMapper** — maps source fields to target bank schema using config-driven registry
5. **RulesEngine** — applies business rules (completeness, balance range, date validity)
6. **SecurityMasker** — PII masking (account numbers, emails, phones)
7. **TransactionManager** — ACID-style commit/rollback with configurable failure threshold
8. **CanonicalStore** — AES-256 encrypted intermediate storage
9. **AuditLogger** — immutable JSONL audit trail per migration
10. **Output writers** — JSON, CSV, DOCX, XLSX, HTML format writers

## Quick Start

### Backend

```bash
uv sync                          # Install dependencies
uv run python api_only.py        # Start FastAPI server on localhost:8000
```

### Frontend

```bash
cd frontend
npm install                      # Install dependencies
npm run dev                      # Start Next.js dev server on localhost:3000
```

### Docker (full stack)

```bash
cp .env.example .env             # Configure env vars first
cd docker && docker compose up --build
```

Services: PostgreSQL (`:5432`), Redis (`:6379`), API (`:8000`), Frontend (`:3000`), Celery Worker.

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

## Project Structure

```
Bank_Migration/
├── api_only.py                  # FastAPI application (all REST endpoints)
├── src/
│   ├── production.py            # PipelineOrchestrator — full pipeline coordinator
│   ├── transform.py             # Core pipeline engine (chains all components)
│   ├── detector.py              # File format auto-detection & record extraction
│   ├── validator.py             # Pydantic field validation
│   ├── parser.py                # Name/date/address/currency parser
│   ├── schema_mapper.py         # Source-to-target field mapping
│   ├── registry.py              # BankRegistry — loads bank schema configs
│   ├── rules_engine.py          # Business rules engine
│   ├── security.py              # PII masking (accounts, emails, phones)
│   ├── transaction_rollback.py  # ACID commit/rollback manager
│   ├── canonical_store.py       # AES-256 encrypted data store
│   ├── audit_logger.py          # Immutable JSONL audit trail
│   ├── models.py                # Shared data models
│   ├── config.py                # Pydantic Settings (env-based config)
│   ├── dispatcher.py            # Multi-bank fan-out dispatcher
│   ├── schema_version.py        # Schema versioning support
│   ├── ai/
│   │   ├── schema_agent.py      # AI schema mapping suggestions (Gemini 2.0 Flash)
│   │   └── anomaly_agent.py     # AI anomaly detection on audit trails
│   ├── infrastructure/
│   │   ├── celery_app.py        # Celery configuration
│   │   ├── db.py                # PostgreSQL database layer
│   │   ├── tasks.py             # Celery background tasks
│   │   └── tracker.py           # Migration progress tracking
│   └── output/
│       ├── json_writer.py       # JSON output
│       ├── csv_writer.py        # CSV output
│       ├── docx_writer.py       # DOCX output
│       ├── xlsx_writer.py       # XLSX output
│       └── html_writer.py       # HTML output
├── config/
│   └── bank_schemas/            # Bank schema configs (source_bank, target_bank, bank_b, bank_c, etc.)
├── frontend/                    # Next.js 16 + React 19 + Tailwind CSS
│   └── src/
│       ├── app/
│       │   ├── page.tsx         # Main dashboard page
│       │   ├── layout.tsx       # Root layout
│       │   └── components/      # UI components
│       │       ├── FilePreview.tsx
│       │       ├── SchemaPreview.tsx
│       │       ├── MigrationHistory.tsx
│       │       ├── ConfirmationDialog.tsx
│       │       ├── Toast.tsx
│       │       └── Icon.tsx
│       └── ...
├── tests/                       # Pytest test suite
│   ├── conftest.py              # Shared fixtures
│   ├── test_transformer.py
│   ├── test_parser.py
│   ├── test_validator.py
│   ├── test_detector.py
│   ├── test_schema_mapper.py
│   ├── test_registry.py
│   ├── test_rules_engine.py
│   ├── test_security.py
│   ├── test_audit_logger.py
│   ├── test_transaction_rollback.py
│   ├── test_output_writers.py
│   └── test_full_platform.py
├── docker/
│   └── docker-compose.yml       # Full-stack Docker deployment
├── pyproject.toml               # Python project config
└── CLAUDE.md                    # AI assistant instructions
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Pydantic v2 |
| Frontend | Next.js 16, React 19, Tailwind CSS |
| Database | PostgreSQL |
| Task Queue | Celery + Redis |
| Security | cryptography (AES-256), defusedxml |
| AI | OpenAI Agents SDK (Gemini 2.0 Flash) |
| File Formats | openpyxl, python-docx, python-multipart |
| Testing | pytest |

## Testing

```bash
uv run pytest                                    # Run all tests
uv run pytest tests/test_parser.py::test_parse_date  # Run single test
```

Tests use isolated fixtures in `tests/conftest.py` — no external services required.

## Key Concepts

- **Bank schemas** are JSON configs in `config/bank_schemas/<bank_name>/<version>.json`. Each defines fields, source-to-target mappings, and masking rules. `BankRegistry` loads and manages these.
- **Schema mapping** is config-driven — add a new bank by dropping a JSON config, no code changes needed.
- **Failure threshold** is configurable (default 5%) — the pipeline rolls back if too many records fail validation.
- **AI agents** require `OPENAI_API_KEY` env var and use the OpenAI Agents SDK targeting Gemini 2.0 Flash.
- **Celery tasks** fall back to synchronous execution if Celery/Redis is unavailable.

## Environment Variables

Copy `.env.example` to `.env` and configure:

- `OPENAI_API_KEY` — required for AI mapping/anomaly features
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- See `.env.example` for the full list
