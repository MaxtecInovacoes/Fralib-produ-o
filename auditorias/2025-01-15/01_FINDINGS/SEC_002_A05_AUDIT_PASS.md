# AUDIT REPORT — OWASP A05:2021 Security Injection

**Audit Date:** 2025-01-15
**Auditor:** Claude Code Security Auditor
**OWASP Category:** A05:2021 - Security Misconfiguration / Injection
**Scope Files:**
  - `backend/endpoints/leads_endpoints.py`
  - `backend/endpoints/pipeline_endpoints.py`
  - `backend/database.py`
  - `backend/endpoints/site_editor_endpoints.py`
  - `backend/endpoints/leads_crud.py`
  - `backend/endpoints/leads_queries.py`
  - `backend/endpoints/leads_crud_sdr.py`
  - `backend/services/hermes_watchdog.py`
  - `backend/services/vite_build_executor.py`
  - `backend/services/vite_react_renderer.py`
  - `backend/services/pipeline_executors.py`
  - `backend/endpoints/pipeline_orchestrator_service.py`
  - `backend/endpoints/pipeline_phase_helpers.py`
  - `backend/endpoints/blog_endpoints.py`

---

## RESULT: AUDIT PASSED — NO CRITICAL OR HIGH VULNERABILITIES FOUND

---

## 1. SQL Injection — PASSED

### Analysis per File

| File | Lines | Pattern Used | Status |
|------|-------|-------------|--------|
| `leads_endpoints.py` | 1-26 | Router aggregator only; no SQL | SAFE |
| `pipeline_endpoints.py` | 17-29 | `text()` with named params `{"uid": tenant_id_c}` — parameterized | SAFE |
| `database.py` | 948-955, 975-1028, 1046-1054 | `text()` with named params throughout; dynamic column list in `update_pipeline_state` built exclusively from hardcoded keys `rodando/pausado/config` | SAFE |
| `site_editor_endpoints.py` | 143-151, 257-260, 478-481 | `text()` with named params `{"id", "uid", "h"}` | SAFE |
| `leads_crud.py` | 63-72, 139-144, 166-170, 211-214, 343-345, 434-452, 498-501, 538-543, 568-573, 593-596, 622-624 | `text()` with named params throughout; dynamic SET clause in `atualizar_lead` (line 136) built from `campos_permitidos` whitelist only | SAFE |
| `leads_queries.py` | All | `text()` with named params throughout | SAFE |
| `leads_crud_sdr.py` | All | `text()` with named params throughout | SAFE |

**Finding:** All SQL queries across all scope files use `sqlalchemy.text()` with named parameterized bindings. No raw string concatenation, f-string interpolation, or `%s`-style formatting used in SQL queries. Tenant isolation enforced via `user_id`/`tenant_id` in every WHERE clause.

**Minor Note (LOW):** In `leads_crud.py` lines 136 and 619, the column names for dynamic UPDATE SET clauses are built programmatically via list comprehension. The column names come from hardcoded whitelists (`campos_permitidos` and `CamposLeadRequest` model fields), not from user input — so this is controlled, not exploitable.

---

## 2. XSS (Cross-Site Scripting) — PASSED

### Analysis: `site_editor_endpoints.py`

| Layer | Mechanism | Status |
|-------|-----------|--------|
| Pre-sanitization filter | `_rejeitar_html_ativo()` — blocks `<script>`, `<iframe>`, `<object>`, `<embed>`, `<base>`, `http-equiv=refresh`, inline event handlers (`on*=`), `javascript:/data:/vbscript:` URLs | SAFE |
| Primary sanitization | `bleach.clean()` with explicit `tags` allowlist (safe formatting/structure tags only) and `attributes` allowlist (href, src, class, id only) with `strip=True` — unknown tags and attributes are fully stripped, not escaped | SAFE |
| Output encoding | HTML returned by FastAPI is JSON-encoded by default; response format is `{"html": "...", ...}` | SAFE |
| `leads_crud.py` | `_reject_unsafe_site_html()` same pattern — regex blocks + allowed_tailwind allowlist | SAFE |

**Finding:** The HTML sanitization in `site_editor_endpoints.py` uses defense in depth with three layers: (1) blocklist regex, (2) `bleach` allowlist with `strip=True`, (3) safe return format. No `innerHTML` assignments found. No `Response` or `HTMLResponse` with raw user content.

**No XSS vectors found.**

---

## 3. Command Injection — PASSED

### Analysis

| File | Lines | Command | Input Source | Status |
|------|-------|---------|-------------|--------|
| `hermes_watchdog.py` | 137 | `pm2 jlist` | Hardcoded | SAFE |
| `hermes_watchdog.py` | 177 | `redis-cli ping` | Hardcoded | SAFE |
| `hermes_watchdog.py` | 602 | `runtime_cmd` via `_coerce_command_for_runtime` | Internal watchdog logic; not user-supplied | SAFE |
| `vite_build_executor.py` | 174, 199, 231 | `npm install`, `vite build` | Hardcoded binary paths, `workspace` from server-side state | SAFE |
| `pipeline_orchestrator_service.py` | 2092-2093 | `chown`, `chmod` | Hardcoded, `web_dir` from controlled tenant/slug | SAFE |
| `pipeline_phase_helpers.py` | 396-397 | `chown`, `chmod` | Hardcoded, `web_dir` from controlled state | SAFE |
| `pipeline_executors.py` | 396-397 | `chown`, `chmod` | Hardcoded, `web_dir` from controlled state | SAFE |
| `vite_react_renderer.py` | 2590 | `_run()` receives `command: list[str]` | Internal builder only; not user-supplied | SAFE |

**Finding:** All `subprocess.run()` calls use hardcoded command arrays with no user-controllable arguments. The `vite_react_renderer.py` `_run()` accepts a `list[str]` parameter, but callers (`vite.build_project`) build commands from internal builder state, not HTTP input. `shell=False` enforced in watchdog. No `os.system`, `os.popen`, `eval`, or `exec` found anywhere in scope.

---

## 4. NoSQL Injection — N/A

The codebase uses **PostgreSQL with SQLAlchemy ORM**. No MongoDB or other NoSQL databases are in scope. All database operations go through `sqlalchemy.text()` or SQLAlchemy ORM models.

---

## 5. Parameter Pollution — PASSED

**Analysis:** SQLAlchemy handles parameter binding at the driver level. Named parameters (`:uid`, `:id`, `:lead_id`, etc.) are bound as proper typed parameters, not concatenated. Duplicate parameter names in a single query are not a vector because each binding uses a unique name per value.

FastAPI path parameters (`lead_id: str`) are validated by Pydantic models where present and by SQLAlchemy's type system on the binding side.

---

## Summary

| OWASP A05 Category | Result |
|--------------------|--------|
| SQL Injection | PASSED — all queries parameterized |
| XSS | PASSED — bleach allowlist + blocklist defense in depth |
| Command Injection | PASSED — no user input in subprocess calls |
| NoSQL Injection | N/A — PostgreSQL only |
| Parameter Pollution | PASSED — proper parameter binding |

**CRITICAL issues:** 0
**HIGH issues:** 0
**MEDIUM issues:** 0
**LOW notes:** 1 (dynamic column building from hardcoded whitelist — acceptable)
