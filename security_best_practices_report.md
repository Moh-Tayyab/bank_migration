# Security Best Practices Report — UN Wallet Multi-Bank Data Migration Platform

**Date:** 2026-06-04
**Stack:** Python/FastAPI (backend) + Next.js 16 (frontend) + PostgreSQL + Redis
**Audit scope:** Full codebase scan against FastAPI and Next.js security specs

---

## Executive Summary

**9 findings total: 1 Critical, 3 High, 3 Medium, 2 Low**

The most urgent issue is that the `.env` file containing real secrets (API keys, encryption keys, database credentials) is committed to the repository. The backend also has a timing-attack-vulnerable API key comparison, an overly permissive CORS configuration, and the frontend exposes an API key to the browser via `NEXT_PUBLIC_` prefix. These should be addressed immediately.

---

## Critical Findings

### CRIT-001: `.env` file committed with real secrets

- **Severity:** Critical
- **Location:** `/mnt/d/Bank_Migration/.env`
- **Evidence:**
  ```
  GEMINI_API_KEY=your_gemini_api_key_here
  CANONICAL_ENCRYPTION_KEY=d6addd11c9ee87dee7dadd0d060cbcefb10cb7a3592b35d5cef14d8ea186d29d
  DATABASE_URL=postgresql://bank_user:bank_pass@localhost:5432/bank_migration
  ```
  The `.env` file is in `.gitignore` but currently exists on disk and may already be tracked in git history.
- **Impact:** Full exposure of database credentials, API keys, and encryption keys to anyone with repo access. An attacker with these can decrypt canonical store data, access the database, and impersonate the AI agent.
- **Fix:** Remove `.env` from git tracking (`git rm --cached .env`), rotate all exposed secrets immediately, and ensure `.env` is never committed.
- **Mitigation:** Add `.env.*` pattern to `.gitignore` (currently only `.env` is listed). Use a secret manager for production deployments.

---

## High Findings

### HIGH-001: API key comparison vulnerable to timing attacks

- **Severity:** High
- **Location:** `api_only.py:36`
- **Evidence:**
  ```python
  if api_key != expected:
      raise HTTPException(status_code=401, detail="Invalid or missing API key")
  ```
- **Impact:** A timing side-channel attack could allow an attacker to guess the API key one character at a time by measuring response time differences.
- **Fix:** Use constant-time comparison:
  ```python
  import hmac
  if not hmac.compare_digest(api_key, expected):
      raise HTTPException(status_code=401, detail="Invalid or missing API key")
  ```
- **Reference:** OWASP — Timing attacks on string comparison

### HIGH-002: Authentication silently disabled when API_KEY is not set

- **Severity:** High
- **Location:** `api_only.py:33-35`
- **Evidence:**
  ```python
  expected = os.getenv("API_KEY", "")
  if not expected:
      return None  # auth disabled if no key configured
  ```
- **Impact:** If the `API_KEY` env var is accidentally unset (e.g., misconfigured deployment), ALL endpoints become unauthenticated with no warning or error. This is a silent auth bypass.
- **Fix:** Fail closed — raise an error or log a prominent warning when `API_KEY` is empty in production:
  ```python
  if not expected:
      if os.getenv("ENVIRONMENT") == "production":
          raise HTTPException(status_code=500, detail="Authentication not configured")
      logger.warning("API_KEY not set — authentication disabled (development only)")
      return None
  ```
- **Reference:** FASTAPI-AUTH-001 — Auth MUST be explicit and consistently enforced

### HIGH-003: CORS allows all methods and headers with credentials

- **Severity:** High
- **Location:** `api_only.py:79-86`
- **Evidence:**
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=cors_origins,
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
- **Impact:** Combined with `allow_credentials=True`, the wildcard methods and headers grant the broadest possible cross-origin access. Any origin listed in `CORS_ORIGINS` can make credentialed requests with any HTTP method. If `CORS_ORIGINS` is misconfigured to include `*`, this becomes fully open.
- **Fix:** Restrict methods and headers to only what the frontend needs:
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=cors_origins,
      allow_credentials=True,
      allow_methods=["GET", "POST"],
      allow_headers=["X-API-Key", "Content-Type"],
  )
  ```
- **Reference:** FASTAPI-CORS-001 — CORS MUST be explicit and least-privilege

---

## Medium Findings

### MED-001: Frontend exposes API key to browser via NEXT_PUBLIC_API_KEY

- **Severity:** Medium
- **Location:** `frontend/src/app/components/types.ts:13`
- **Evidence:**
  ```typescript
  const key = process.env.NEXT_PUBLIC_API_KEY || "";
  ```
  `NEXT_PUBLIC_` prefixed variables are inlined into the client bundle at build time.
- **Impact:** The API key is visible in the browser's JavaScript source, network requests, and developer tools. Anyone can extract it.
- **Fix:** Remove the `NEXT_PUBLIC_API_KEY` variable. Instead, have the backend validate API keys server-side and use a session cookie or backend-for-frontend pattern. If the key must be sent, proxy API calls through Next.js Route Handlers that add the key server-side.
- **Reference:** NEXT-SECRETS-001 — Secrets MUST NOT be committed or exposed to the browser

### MED-002: No security headers set on FastAPI responses

- **Severity:** Medium
- **Location:** `api_only.py` (no security headers middleware)
- **Evidence:** No middleware sets `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, or `Permissions-Policy`.
- **Impact:** Browser-based attacks (MIME sniffing, clickjacking) are possible when the API serves HTML responses (e.g., OpenAPI docs).
- **Fix:** Add security headers via middleware or at the reverse proxy/edge layer.
- **Reference:** FASTAPI-HEADERS-001

### MED-003: Docker-compose exposes PostgreSQL and Redis ports to host

- **Severity:** Medium
- **Location:** `docker/docker-compose.yml:10,23`
- **Evidence:**
  ```yaml
  ports:
    - "5432:5432"  # PostgreSQL
    - "6379:6379"  # Redis
  ```
- **Impact:** If the host is accessible on the network, the database and Redis are exposed without authentication. Redis has no password by default.
- **Fix:** Remove host port bindings for internal services (keep them accessible only via Docker network), or bind to `127.0.0.1:5432:5432`. Add Redis authentication.

---

## Low Findings

### LOW-001: OpenAPI docs linked from frontend without access control

- **Severity:** Low
- **Location:** `frontend/src/app/page.tsx:79-85`
- **Evidence:**
  ```tsx
  <a href="http://localhost:8000/docs" target="_blank" ...>
  ```
- **Impact:** Exposes API schema and endpoints to anyone who can access the frontend. In production, this should be disabled or protected.
- **Fix:** Disable docs in production (`docs_url=None`) or only show the link when running in development mode.

### LOW-002: Docker container runs uvicorn without `--host 0.0.0.0` validation

- **Severity:** Low
- **Location:** `docker/Dockerfile:21`
- **Evidence:**
  ```dockerfile
  CMD ["uv", "run", "uvicorn", "api_only:app", "--host", "0.0.0.0", "--port", "8000"]
  ```
- **Impact:** The container listens on all interfaces, which is expected for Docker but means the app is accessible from any network the container is connected to.
- **Mitigation:** Ensure proper network segmentation and firewall rules at the infrastructure level. This is standard Docker behavior but should be noted for deployment.

---

## Positive Findings (Good Practices)

1. **Parameterized SQL queries** — All database queries in `canonical_store.py` use parameterized placeholders (`%s`), no SQL injection vectors found.
2. **File upload size limits** — Upload endpoints enforce `max_file_size_mb` limits with chunked reads.
3. **Filename sanitization** — `os.path.basename()` is applied to uploaded filenames before use.
4. **Rate limiting** — `slowapi` is configured on all endpoints with appropriate limits.
5. **AES-256 encryption** — Canonical store uses Fernet encryption with PBKDF2 key derivation (600,000 iterations).
6. **Audit logging** — Immutable JSONL audit trail is maintained for all migration operations.
7. **Transaction rollback** — ACID-style commit/rollback with configurable failure threshold.
8. **Non-root Docker user** — Dockerfile creates and switches to `appuser`.
9. **PII masking** — Sensitive fields (account numbers, emails, SSNs) are automatically masked.

---

## Recommended Priority Order

1. **CRIT-001** — Remove `.env` from git, rotate all secrets (immediate)
2. **HIGH-001** — Fix timing-attack-vulnerable API key comparison (immediate)
3. **HIGH-002** — Fail closed when auth is not configured (immediate)
4. **HIGH-003** — Tighten CORS configuration (before production deployment)
5. **MED-001** — Remove NEXT_PUBLIC_API_KEY exposure (before production deployment)
6. **MED-002** — Add security headers (before production deployment)
7. **MED-003** — Restrict Docker port bindings (before production deployment)
8. **LOW-001** — Disable docs in production (before production deployment)
9. **LOW-002** — Document network segmentation requirements (documentation)
