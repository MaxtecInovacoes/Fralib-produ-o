# PERF_004_LATENCY - API Latency Issues Audit

**Date:** 2025-01-15
**Auditor:** Claude Performance Engineer
**Files Audited:**
- `backend/endpoints/pipeline_start_endpoints.py`
- `backend/endpoints/pipeline_edit_endpoints.py`
- `backend/endpoints/sse_endpoints.py`
- `backend/services/vite_react_renderer.py`
- `backend/services/vite_build_executor.py`
- `backend/core/database.py`

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 2     |
| HIGH     | 4     |

---

## FINDING 1 — CRITICAL: `time.sleep()` inside batch generation loop blocks event loop

**File:** `backend/services/vite_react_renderer.py`
**Lines:** 1071, 1124, 1155, 1172–1174

**Endpoint / Operation:** `_generate_vite_project_files_in_batches()` — called by `render_vite_react_site()`

**Problem:**
`_generate_vite_project_files_in_batches()` is a **purely synchronous function** (no `async`), yet it calls LLM APIs and contains multiple blocking `time.sleep()` calls:

```python
# vite_react_renderer.py:1071 — retry delay, blocks entire event loop
time.sleep(_transient_proxy_retry_delay_seconds(attempt))

# vite_react_renderer.py:1124 — spacing between batches
if delay > 0:
    time.sleep(delay)  # namehost: 8s blocking

# vite_react_renderer.py:1155 — retry delay for component batches
time.sleep(_transient_proxy_retry_delay_seconds(attempt))

# vite_react_renderer.py:1172–1174 — spacing between component sub-batches
if delay > 0:
    time.sleep(delay)  # namehost: 8s blocking
```

With namehost mode (`_is_namehost_base() == True`), `_batch_spacing_seconds()` returns `8.0`. For a project with 5 core batches + 3 component sub-batches, the cumulative blocking time is:

- 5 core batches: 5 × 8s = **40 seconds** of blocking
- 3 component sub-batches: 3 × 8s = **24 seconds** of blocking
- Retry delays: up to 10–600s each
- **Total potential blocking per render: 30–600+ seconds**

**Impact:** The entire FastAPI event loop is frozen during all these sleeps. All other concurrent requests to this server are blocked for the full duration.

**Estimated Latency Added:** 8–600 seconds per render call, depending on number of batches, retry attempts, and namehost mode.

**Fix:**
1. Convert `_generate_vite_project_files_in_batches()` and its callers to `async` functions using `asyncio.sleep()` instead of `time.sleep()`.
2. Use `asyncio.to_thread()` or a `ProcessPoolExecutor` to run the synchronous LLM call (`_call_vite_react_llm`) in a thread/process, keeping the event loop free.
3. Example:

```python
import asyncio

async def _generate_vite_project_files_in_batches_async(...):
    for batch_index, (batch_name, paths) in enumerate(batches, 1):
        raw = await asyncio.to_thread(
            _call_vite_react_llm, batch_prompt, model, max_tokens, temperature
        )
        # ... process raw ...
        if delay > 0:
            await asyncio.sleep(delay)  # non-blocking
```

---

## FINDING 2 — CRITICAL: `subprocess.run()` blocks event loop during Vite build

**File:** `backend/services/vite_build_executor.py`
**Lines:** 174–192 (`npm install`), 199–216 (`vite build`)

**Endpoint / Operation:** `build_vite_project()` — called from `render_vite_react_site()` inside the batch loop

**Problem:**
`build_vite_project()` runs `subprocess.run()` synchronously, blocking the entire event loop:

```python
# vite_build_executor.py:174
result = subprocess.run(
    [npm, "install", "--prefer-offline"],
    capture_output=True, text=True,
    timeout=node_timeout,  # default 180s
    cwd=workspace,
)
# ...
# vite_build_executor.py:199
result = subprocess.run(
    [node, "node_modules/vite/bin/vite.js", "build"],
    capture_output=True, text=True,
    timeout=timeout,  # default 300s
    cwd=workspace,
)
```

Typical build times:
- `npm install` (cache hit: ~3s; cache miss: 30–180s)
- `vite build`: 20–120s

**Impact:** Event loop is completely blocked for 23–300 seconds per build, serializing all concurrent FastAPI requests on the same worker.

**Estimated Latency Added:** 20–300 seconds blocking per render call.

**Fix:**
Run builds in a process pool using `asyncio.to_thread()`:

```python
async def build_vite_project_async(workspace: Path, timeout: int = 300, node_timeout: int = 180):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,  # uses default ThreadPoolExecutor
        lambda: _build_vite_project_sync(workspace, timeout, node_timeout)
    )
```

Or use a dedicated `ProcessPoolExecutor` to avoid GIL contention during CPU-heavy TypeScript compilation.

---

## FINDING 3 — HIGH: Synchronous file I/O (`open()`) inside async FastAPI endpoints

**File:** `backend/endpoints/pipeline_edit_endpoints.py`
**Lines:** 66–67, 76–77, 111–112

**Endpoint:** `POST /api/pipeline/editar-secao`, `GET /api/pipeline/listar-secoes/{lead_id}`

**Problem:**
Both async endpoints use blocking `open()` for reading and writing HTML files:

```python
# editar_secao_endpoint (line 66–67)
with open(html_path, "r", encoding="utf-8") as f:
    html_atual = f.read()
# ...
# line 76–77
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_editado)

# listar_secoes_endpoint (line 111–112)
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()
```

**Impact:** Each file operation blocks the event loop for the duration of the disk I/O. For HTML files on network storage (NFS, CIFS), latency can reach **50–200ms** per operation. Combined with the `editar_secao()` LLM call (which is also synchronous), the endpoint can block for **5–30+ seconds**.

**Estimated Latency Added:** 5–50ms (local SSD) to 50–200ms (network storage) per read/write, plus LLM latency.

**Fix:**
Replace with `asyncio.to_thread()`:

```python
async def editar_secao_endpoint(...):
    html_atual = await asyncio.to_thread(_read_file, html_path)
    html_editado = editar_secao(html_atual, req.secao, req.instrucao)
    await asyncio.to_thread(_write_file, html_path, html_editado)

def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def _write_file(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
```

---

## FINDING 4 — HIGH: New `httpx.Client` created per LLM call — no connection reuse

**File:** `backend/services/vite_react_renderer.py`
**Line:** 835

**Operation:** `_call_proxy_openai_chat()`

**Problem:**
Each LLM call creates a brand-new `httpx.Client`, performs one request, then discards it. This means **no TCP/TLS connection reuse**, and no connection pooling:

```python
# vite_react_renderer.py:835
with httpx.Client(timeout=httpx.Timeout(connect=10.0, read=420.0, write=60.0, pool=10.0)) as client:
    response = client.post(...)
```

In `_generate_vite_project_files_in_batches()`, there can be **10–20+ LLM calls** per render (5 core batches + 3 component sub-batches, each with 1–3 retry attempts). Each call pays the cost of:
- New TCP handshake: ~10–30ms
- New TLS handshake: ~30–100ms
- Total overhead per call: **40–130ms**

**Impact:** Cumulative overhead of 400ms–2.6 seconds per render, plus increased server load from connection churn.

**Estimated Latency Added:** 40–130ms per LLM call × 10–20 calls = 400ms–2.6 seconds per render.

**Fix:**
Create a **module-level or class-level shared `httpx.AsyncClient`** with connection pooling:

```python
# module level
_http_client: httpx.AsyncClient | None = None

def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=420.0, write=60.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        )
    return _http_client

async def _call_proxy_openai_chat_async(...) -> tuple[str, dict[str, Any]]:
    client = _get_http_client()
    response = await client.post(...)
```

---

## FINDING 5 — HIGH: All SQLAlchemy `db.execute()` calls in `iniciar_pipeline` block the event loop

**File:** `backend/endpoints/pipeline_start_endpoints.py`
**Lines:** 32–38, 72, 75–86, 97, 112–123, 133

**Endpoint:** `POST /api/pipeline/iniciar`

**Problem:**
`iniciar_pipeline` is declared `async def` but performs **6 synchronous database queries** via SQLAlchemy's `db.execute(text(...))`:

```python
# pipeline_start_endpoints.py:32
_plano_row = db.execute(text("SELECT plano, status, trial_expires_at ...")).fetchone()

# pipeline_start_endpoints.py:72
_state = get_pipeline_state(db, tenant_id)  # → db.execute()

# pipeline_start_endpoints.py:75–86
active_jobs = db.execute(text("SELECT COUNT(*) FROM jobs WHERE ...")).scalar()

# pipeline_start_endpoints.py:97
perm = validar_permissao_pipeline(db, tenant_id)  # → db.execute() inside

# pipeline_start_endpoints.py:112–123
_fila = db.execute(text("SELECT COUNT(*) FROM leads WHERE ...")).scalar()

# pipeline_start_endpoints.py:133
update_pipeline_state(db, tenant_id, ...)  # → db.execute() + commit()
```

Combined with the job enqueue at line 143 (`_jq.enqueue(db, ...)`), this endpoint can block for **50–500ms** on a loaded database.

**Impact:** Event loop blocked during each query. Under load, this serializes request handling and degrades throughput.

**Estimated Latency Added:** 10–100ms per query × 6 queries = 60–600ms blocking per request.

**Fix:**
Use SQLAlchemy's async engine with `AsyncSession`:

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Replace sync engine with async engine
async_engine = create_async_engine(DATABASE_URL, ...)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession)

async def iniciar_pipeline(...):
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("SELECT ..."))
        # ...
```

Alternatively, if async migration is not feasible, wrap the entire endpoint body in `await asyncio.to_thread(functools.partial(_iniciar_pipeline_sync, ...))`.

---

## FINDING 6 — MEDIUM: `psycopg2.connect()` in SSE stream per request without connection pooling

**File:** `backend/endpoints/sse_endpoints.py`
**Lines:** 207–209

**Operation:** SSE `/api/logs/stream` endpoint

**Problem:**
The SSE stream creates a new `psycopg2` connection per SSE client connection:

```python
# sse_endpoints.py:207
pg_conn = psycopg2.connect(dsn)
pg_conn.autocommit = True
with pg_conn.cursor() as cur:
    cur.execute(f"LISTEN {canal}")
```

While the `_notify_conn` is reused for `pg_notify`, each SSE **client** creates its own dedicated `psycopg2` connection. With 100 concurrent SSE clients, that is 100 PostgreSQL connections. PostgreSQL default `max_connections` is 100, which can cause connection exhaustion.

**Impact:** Under high concurrency, new SSE clients will be rejected with "too many connections". Each new connection also adds ~10–50ms latency on connect.

**Estimated Latency Added:** 10–50ms per new SSE client connection.

**Fix:**
Use a connection pool (e.g., `psycopg2.pool.ThreadedConnectionPool`) for SSE connections, or use PgBouncer in front of PostgreSQL to multiplex connections. Example:

```python
from psycopg2 import pool

_sse_conn_pool = pool.ThreadedConnectionPool(
    minconn=2, maxconn=20,
    dsn=os.getenv("DATABASE_URL", "")
)

def _get_sse_pg_conn():
    try:
        return _sse_conn_pool.getconn()
    except psycopg2.pool.PoolError:
        return None
```

---

## Aggregated Impact Summary

| Finding | Blocking Type | Latency Range | Event Loop Impact |
|---------|-------------|---------------|------------------|
| F1: `time.sleep()` in batch gen | CPU sleep | 8–600s per render | CRITICAL — all requests blocked |
| F2: `subprocess.run()` for Vite build | Subprocess | 20–300s per render | CRITICAL — all requests blocked |
| F3: Sync file I/O in edit endpoints | Disk I/O | 5–200ms per operation | HIGH — per-request blocking |
| F4: No HTTP connection reuse | Network handshake | 400ms–2.6s per render | HIGH — per-call overhead |
| F5: Sync DB queries in async endpoint | DB I/O | 60–600ms per request | HIGH — per-request blocking |
| F6: New psycopg2 per SSE client | DB connection | 10–50ms + exhaustion risk | MEDIUM — scalability risk |

---

## Recommendations (Priority Order)

1. **[F1 + F2]** Convert `render_vite_react_site()` and `_generate_vite_project_files_in_batches()` to async, replacing `time.sleep()` with `asyncio.sleep()` and `subprocess.run()` with `asyncio.to_thread()`. This is the highest-impact fix.
2. **[F4]** Replace per-call `httpx.Client` with a module-level `httpx.AsyncClient` with connection pooling.
3. **[F3]** Wrap `open()` calls in `pipeline_edit_endpoints.py` with `asyncio.to_thread()`.
4. **[F5]** Migrate to SQLAlchemy async engine, or wrap the sync DB operations in `asyncio.to_thread()` as a quick fix.
5. **[F6]** Add a `ThreadedConnectionPool` for SSE PostgreSQL connections.

---

## References

- FastAPI async best practices: https://fastapi.tiangolo.com/async/#path-operation-functions
- SQLAlchemy async: https://docs.sqlalchemy.org/en/20/async.html
- httpx connection pooling: https://www.python-httpx.org/advanced/connection-pooling/
- asyncio.to_thread: https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread
