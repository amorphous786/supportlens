import json
import logging
import time
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import create_tables, engine
from app.routers import analysis, analytics, tickets, traces
from app.routers.analytics import get_analytics
from app.routers.traces import list_traces
from app.seed import seed_database

# ── Structured JSON logging ────────────────────────────────────────────────────

class _JsonFormatter(logging.Formatter):
    """Emit every log record as a single-line JSON object on stdout."""

    _SKIP = frozenset({
        "args", "asctime", "created", "exc_info", "exc_text", "filename",
        "funcName", "levelname", "levelno", "lineno", "message", "module",
        "msecs", "msg", "name", "pathname", "process", "processName",
        "relativeCreated", "stack_info", "thread", "threadName", "taskName",
    })

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["error"] = self.formatException(record.exc_info)
        for key, val in record.__dict__.items():
            if key not in self._SKIP and not key.startswith("_"):
                entry[key] = val
        return json.dumps(entry, default=str)


_handler = logging.StreamHandler()
_handler.setFormatter(_JsonFormatter())
logging.root.handlers = [_handler]
logging.root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

logger = logging.getLogger(__name__)

# ── Process start time (uptime) ───────────────────────────────────────────────

_process_start: float = time.monotonic()


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables()
    seed_database()
    yield


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    description="AI-powered customer support analysis platform.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ─────────────────────────────────────────────────
# Health probes (GET /health) are logged at DEBUG to avoid log spam.

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next) -> Response:
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    start = time.perf_counter()

    status_code = 500
    error_detail: str | None = None

    try:
        response: Response = await call_next(request)
        status_code = response.status_code
    except Exception as exc:
        error_detail = str(exc)
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.error(
            "http_request",
            extra={
                "event": "http_request",
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "duration_ms": duration_ms,
                "request_id": request_id,
                "error": error_detail,
            },
        )
        raise

    duration_ms = int((time.perf_counter() - start) * 1000)
    is_health_probe = request.url.path == "/health"
    log_level = logging.DEBUG if is_health_probe else logging.INFO

    logger.log(
        log_level,
        "http_request",
        extra={
            "event": "http_request",
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "request_id": request_id,
        },
    )
    response.headers["X-Request-ID"] = request_id
    return response


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(tickets.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(traces.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")

# ── Convenience short-path aliases (no /api/v1 prefix) ───────────────────────
# Allows `curl localhost:8000/traces` and `curl localhost:8000/analytics`
# without duplicating any handler logic.
app.add_api_route("/traces", list_traces, methods=["GET"], include_in_schema=False)
app.add_api_route("/analytics", get_analytics, methods=["GET"], include_in_schema=False)


# ── Health endpoint ───────────────────────────────────────────────────────────
#
# Status semantics:
#   healthy   — all systems operational; LLM model is available
#   degraded  — non-critical dependency unavailable (LLM / model not pulled);
#               read endpoints still work; trace creation returns 503
#   unhealthy — critical dependency unavailable (database); nothing works
#
# Operator guidance:
#   healthy   → informational only; no action needed
#   degraded  → investigate LLM; existing data is safe
#   unhealthy → page on-call immediately; app is non-functional


@app.get("/health", tags=["health"])
async def health():
    """
    Dependency health check. Always returns HTTP 200; inspect ``status`` field.

    Never crashes; each check has a 2 s hard timeout.
    Health probes are logged at DEBUG level to avoid noise.
    """
    uptime_s = int(time.monotonic() - _process_start)
    deps: dict = {}

    # ── Database (critical) ───────────────────────────────────────────────────
    t0 = time.perf_counter()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        deps["database"] = {
            "status": "healthy",
            "latency_ms": int((time.perf_counter() - t0) * 1000),
        }
    except Exception as exc:
        logger.error(
            "health_db_fail",
            extra={"event": "health_db_fail", "error": str(exc)},
        )
        deps["database"] = {"status": "unhealthy", "error": type(exc).__name__}

    # ── Ollama reachability + model availability (non-critical) ───────────────
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
        latency_ms = int((time.perf_counter() - t0) * 1000)

        if r.status_code == 200:
            models = [m.get("name", "") for m in r.json().get("models", [])]
            model_ok = any(settings.ollama_model in m for m in models)
            deps["ollama"] = {
                "status": "healthy" if model_ok else "degraded",
                "latency_ms": latency_ms,
                "model": settings.ollama_model,
                "model_available": model_ok,
            }
        else:
            deps["ollama"] = {
                "status": "unavailable",
                "http_status": r.status_code,
            }
    except Exception as exc:
        # Log at DEBUG — Ollama being down is not immediately operator-actionable
        # and health probes run frequently.
        logger.debug(
            "health_ollama_fail",
            extra={"event": "health_ollama_fail", "error": type(exc).__name__},
        )
        deps["ollama"] = {"status": "unavailable", "error": type(exc).__name__}

    # ── Overall status ────────────────────────────────────────────────────────
    db_ok = deps.get("database", {}).get("status") == "healthy"
    llm_ok = deps.get("ollama", {}).get("status") == "healthy"

    if not db_ok:
        overall = "unhealthy"
    elif not llm_ok:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "status": overall,
        "uptime_seconds": uptime_s,
        "service": settings.app_name,
        "dependencies": deps,
    }
