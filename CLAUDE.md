# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

UN Wallet Multi-Bank Data Migration Platform — an ETL pipeline for migrating customer records between different bank schemas. Handles ingestion, canonical normalization, schema mapping, PII masking, validation, and multi-format output.

## First-time Setup

```bash
# Backend
uv sync

# Frontend
cd frontend && npm install

# Environment (optional, for Docker/full-stack)
cp .env.example .env
# Edit .env with your API keys and configuration
```

Required environment variables (see `.env.example`):
- `OPENAI_API_KEY` — For AI agents (schema intelligence, anomaly detection)
- `REDIS_URL` — For Celery background tasks (optional, falls back to sync)

## Commands

### Backend

```bash
uv sync                          # Install dependencies
uv run python api_only.py        # Run FastAPI server (localhost:8000)
uv run pytest                    # Run all tests
uv run pytest tests/test_parser.py::test_parse_date  # Run single test
```

### Frontend

```bash
cd frontend
npm install                      # Install dependencies
npm run dev                      # Run Next.js dev server (localhost:3000)
npm run build                    # Production build
```

### Docker (full stack)

```bash
cp .env.example .env             # Configure env vars first
cd docker && docker compose up --build
```

## Architecture

```
INGEST → CANONICAL STORE → TRANSFORM → SECURE → DELIVER
```

### Pipeline flow (per record)

1. **FormatDetector** (`src/detector.py`) — auto-detects file format (CSV, JSON, DOCX, XLSX, XML, TXT) and extracts raw records
2. **Validator** (`src/validator.py`) — Pydantic-based field validation
3. **Parser** (`src/parser.py`) — intelligent parsing of names, dates, addresses, currencies
4. **SchemaMapper** (`src/schema_mapper.py`) — maps source fields to target bank schema using registry mappings
5. **RulesEngine** (`src/rules_engine.py`) — applies business rules (completeness, balance range, date validity)
6. **SecurityMasker** (`src/security.py`) — PII masking (account numbers, emails, phones)
7. **TransactionManager** (`src/transaction_rollback.py`) — ACID-style commit/rollback with failure threshold
8. **CanonicalStore** (`src/canonical_store.py`) — AES-256 encrypted intermediate storage
9. **AuditLogger** (`src/audit_logger.py`) — immutable JSONL audit trail per migration
10. **Output writers** (`src/output/`) — JSON, CSV, DOCX, XLSX, HTML format writers

### Entry points

- `api_only.py` — FastAPI application with all REST endpoints. Uses `PipelineOrchestrator` for synchronous processing and Celery tasks for async background processing.
- `src/production.py` — `PipelineOrchestrator` orchestrates the full pipeline. Supports single-bank and multi-bank migration (fan-out to multiple targets).

### Key patterns

- **Bank schemas** are JSON config files in `config/bank_schemas/<bank_name>/<version>.json`. Each defines fields, source-to-target mappings, and masking rules. `BankRegistry` (`src/registry.py`) loads and manages these.
- **Transformer** (`src/transform.py`) is the core pipeline engine. It chains all components in sequence and handles commit/rollback based on a configurable failure threshold (default 5%).
- **AI agents** (`src/ai/`) use the OpenAI Agents SDK targeting Gemini 2.0 Flash. `SchemaIntelligenceAgent` suggests schema mappings; `AnomalyDetectionAgent` analyzes audit trails for quality issues. Requires `OPENAI_API_KEY` (uses Gemini as the underlying model).
- **Celery tasks** (`src/infrastructure/tasks.py`) wrap pipeline operations for background processing. Falls back to synchronous execution if Celery/Redis is unavailable.
- **Settings** come from `src/config.py` (Pydantic `Settings` model), with env vars for secrets (see `.env.example`).

### Frontend

Next.js 16 app with Tailwind CSS. Single-page dashboard at `frontend/src/app/page.tsx` with components for file upload, schema preview, migration history, and toast notifications.

## Skills

This project supports Claude Code skills for automated workflows and specialized tasks.

### Built-in skills (always available)
- **frontend-design** — Build or refactor UI components and pages
- **python-testing-patterns** — Implement pytest test suites and TDD workflows
- **code-review** — Review changes for correctness and improvements
- **verify** — Run the app to confirm a fix or feature works
- **run** — Launch and drive the project locally
- **deep-research** — Multi-source research with verification
- **simplify** — Refactor code for clarity and efficiency
- **security-review** — Complete security audit of changes

### Project-specific skills
Add custom skills to `.claude/skills/<skill-name>/skill.md` following the skill specification format. These are automatically loaded when invoked via `/skill-name` or the Skill tool.

Example: `.claude/skills/migration-validate/skill.md` could define a skill for validating migration configs against target bank schemas.

### Invocation
```bash
/skill-name              # Invoke a skill directly
/codeskill skill-name    # Alternative invocation
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8000 already in use | `lsof -ti:8000 \| xargs kill` or change `PORT` in `.env` |
| Port 3000 already in use | `lsof -ti:3000 \| xargs kill` or change `frontend/package.json` dev script |
| Celery connection errors | Pipeline falls back to sync mode; check `REDIS_URL` in `.env` |
| AI agents not working | Verify `OPENAI_API_KEY` is set in `.env` |
| Tests failing with import errors | Run `uv sync` to ensure dependencies are installed |
| Frontend build errors | Delete `frontend/node_modules` and run `npm install` |

## Test conventions

Tests use `pytest` with fixtures defined in `tests/conftest.py`. Fixtures provide pre-built component instances (`parser`, `validator`, `masker`, etc.) and sample data files (CSV, JSON, XML, XLSX, DOCX). Tests are isolated — no external services required.
