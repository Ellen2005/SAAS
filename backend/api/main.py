from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime, timezone
UTC = timezone.utc
import os
import re
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv

# Configure logging - handle missing correlation_id gracefully
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path)
logger.info(f"Environment loaded from: {env_path}")

from .core.env_config import validate_environment, configure_cors_origins
from .core.supabase_client import get_supabase
from .core.auth import require_role, resolve_user_id
from .services.email_service import send_automated_briefing, normalize_recipient_email
from .core.scheduler import start_scheduler, shutdown_scheduler
from .services.cache_service import get_cached, set_cached
from .services.audit_service import log_config_change
from .core.utils import safe_data

from .routers import departments, users, semantic, validation, admin, heartbeat, templates, introspect, analyst, assistant, analysis, executive_reports, export, dashboards, webhooks, filters, executive_analytics, data_quality, scheduled_reports, email_test  # noqa: F401
from .routers import admin_ai  # noqa: F401
from .routers import dashboard as dashboard_router
from .routers import reports as reports_router
from .routers import settings as settings_router
from .routers import etl_routes as etl_router
from .services.nlq_service import run_nlq
from .services.analysis_engine import run_analysis as run_goal_analysis

# ── SQL Injection Prevention ──────────────────────────────────────────────────
_SQL_FORBIDDEN_KEYWORDS = re.compile(
    r'\b(DROP\s|ALTER\s|CREATE\s|DELETE\s|INSERT\s|UPDATE\s|TRUNCATE\s|'
    r'EXEC\s|EXECUTE\s|GRANT\s|REVOKE\s|SHUTDOWN|KILL\s|XP_|MERGE\s|'
    r'REPLACE\s|LOAD\s|INTO\s|INFORMATION_SCHEMA\.|PG_SLEEP|WAITFOR\s|DELAY|BENCHMARK)\b',
    re.IGNORECASE
)

_SQL_SAFE_PREFIXES = frozenset({"SELECT", "WITH", "EXPLAIN", "DESCRIBE", "SHOW", "PRAGMA"})


def validate_sql_read_only(sql: str) -> tuple[bool, str]:
    """Validate that SQL is read-only and safe for execution. Returns (is_safe, error_message)."""
    if not sql or not sql.strip():
        return False, "SQL query is empty."
    stripped = sql.strip()
    upper = stripped.upper()
    if not upper.startswith(tuple(_SQL_SAFE_PREFIXES)):
        return False, "Only SELECT/WITH/DESCRIBE/SHOW/PRAGMA queries allowed."
    if _SQL_FORBIDDEN_KEYWORDS.search(stripped):
        return False, "SQL contains forbidden destructive operations."
    cleaned = re.sub(r"'[^']*'", '', re.sub(r'--.*$', '', stripped, flags=re.MULTILINE))
    semi_pos = cleaned.find(';')
    if semi_pos != -1 and semi_pos < len(cleaned.rstrip(';')) - 1:
        return False, "Multi-statement SQL is not allowed."
    if re.search(r'UNION\s+(ALL\s+)?(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\b', upper):
        return False, "UNION with DDL/DML is forbidden."
    return True, ""


from .core.constants import LEGACY_DEMO_KPI_NAMES, is_legacy_demo_kpi as _is_legacy_demo_kpi, is_legacy_demo_report as _is_legacy_demo_report


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Validating environment...")
        env_validation = validate_environment()
        logger.info(f"Environment validation: {env_validation}")
        
        logger.info("Starting scheduler...")
        start_scheduler()
        logger.info("Application startup complete ✓")
        
        # Run pending migrations if AUTO_MIGRATE is enabled
        if os.getenv("AUTO_MIGRATE", "false").lower() == "true":
            logger.info("AUTO_MIGRATE enabled, running startup migrations...")
            try:
                from .services.migration_runner import auto_run_migrations_on_startup
                await auto_run_migrations_on_startup()
            except Exception as e:
                logger.error(f"Startup migrations failed: {e}")
                # Don't raise - allow app to start even if migrations fail
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}", exc_info=True)
        raise
    
    try:
        yield
    finally:
        logger.info("Shutting down scheduler...")
        shutdown_scheduler()
        
        # Close Groq HTTP client
        logger.info("Closing Groq HTTP client...")
        try:
            from .services.groq_utils import close_groq_client
            await close_groq_client()
        except Exception as e:
            logger.warning(f"Failed to close Groq client: {e}")
        
        logger.info("Application shutdown complete ✓")


INSTITUTION_NAME = os.getenv("INSTITUTION_NAME", "Smart Analytics")

app = FastAPI(
    title=f"{INSTITUTION_NAME} System API",
    version="1.0.0",
    description="Data Pipeline & Analytics Engine",
    lifespan=lifespan
)

# Rate Limiting
try:
    from .middleware.rate_limit import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)
    logger.info("Rate limit middleware loaded")
except Exception:
    logger.warning("Rate limiter not available", exc_info=True)

# Security Hardening
try:
    from .middleware.security import CSPMiddleware, RefreshTokenMiddleware
    app.add_middleware(CSPMiddleware)
    app.add_middleware(RefreshTokenMiddleware)
    logger.info("Security middleware loaded")
except Exception:
    logger.warning("Security middleware not available", exc_info=True)

# Configure CORS dynamically based on environment
cors_origins = configure_cors_origins()
logger.info(f"Configuring CORS for origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ── Correlation ID Middleware (Structured Logging) ─────────────────────────────
import uuid
import contextvars

_correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('correlation_id', default='none')

@app.middleware("http")
async def add_correlation_id(request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4())[:8])
    request.state.correlation_id = correlation_id
    _correlation_id_var.set(correlation_id)
    
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


# ── Global Exception Handlers ────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.warning(f"Validation error on {request.url}: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Invalid request parameters",
            "errors": [
                {
                    "field": ".".join(str(x) for x in err["loc"][1:]),
                    "message": err["msg"],
                    "type": err["type"]
                }
                for err in exc.errors()
            ]
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.warning(f"HTTP error on {request.url}: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    # Log full details internally
    logger.error(f"Unhandled exception on {request.url}: {str(exc)}", exc_info=True)
    # Don't leak internal details to client
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": "An unexpected error occurred. Please contact support."
        }
    )

app.include_router(departments.router)
app.include_router(users.router)
app.include_router(semantic.router)
app.include_router(validation.router)
app.include_router(admin.router)
app.include_router(heartbeat.router)
app.include_router(templates.router)
app.include_router(introspect.router)
app.include_router(analyst.router)
app.include_router(assistant.router)
app.include_router(analysis.router)
app.include_router(executive_reports.router)
app.include_router(export.router)
app.include_router(dashboards.router)
app.include_router(webhooks.router)
app.include_router(filters.router)
app.include_router(executive_analytics.router)
app.include_router(data_quality.router)
app.include_router(scheduled_reports.router)
app.include_router(email_test.router)
app.include_router(admin_ai.router)
app.include_router(dashboard_router.router)
app.include_router(reports_router.router)
app.include_router(settings_router.router)
app.include_router(etl_router.router)


# ── Models ────────────────────────────────────────────────────────────────────

class KPIResult(BaseModel):
    id: str
    kpi_name: str
    value: float
    dod_pct: Optional[float] = None
    wow_pct: Optional[float] = None
    avg_7d: Optional[float] = None
    status: str
    recorded_at: str


class AnomalyRecord(BaseModel):
    id: str
    kpi_name: str
    severity: str
    deviation: float
    context: dict
    detected_at: str


class DashboardSummary(BaseModel):
    kpis: List[KPIResult]
    anomalies: List[AnomalyRecord]
    narrative: str
    last_refreshed: str
    validation: List[dict] = []


# ── Request Size Limit Middleware ──────────────────────────────────────────────
@app.middleware("http")
async def request_size_limit(request, call_next):
    if request.method in ("POST", "PUT", "PATCH"):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large (max 10MB)"},
            )
    return await call_next(request)


# ── Health Check Endpoint ──────────────────────────────────────────────────────
from pydantic import BaseModel, Field
from typing import List
import time

class HealthComponent(BaseModel):
    name: str
    status: str  # healthy, degraded, unhealthy
    details: str = ""
    latency_ms: float = 0.0

class HealthResponse(BaseModel):
    status: str  # healthy, degraded, unhealthy
    timestamp: str
    version: str
    components: List[HealthComponent]


class PingResponse(BaseModel):
    ok: bool = True
    timestamp: str


@app.get("/api/ping", response_model=PingResponse, include_in_schema=False)
async def ping():
    """Lightweight liveness probe for Render keep-alive, Docker health checks, and frontend wake-up."""
    return PingResponse(timestamp=datetime.now(timezone.utc).isoformat())


@app.get("/api/health", response_model=HealthResponse, include_in_schema=False)
async def health_check():
    """Comprehensive health check for all system dependencies."""
    start_time = time.perf_counter()
    components = []
    overall_status = "healthy"
    
    # 1. Supabase / Database connectivity
    supabase_start = time.perf_counter()
    try:
        supabase = get_supabase()
        # Simple query to verify connection
        result = supabase.table("departments").select("id").limit(1).execute()
        latency = round((time.perf_counter() - supabase_start) * 1000, 2)
        components.append(HealthComponent(
            name="supabase",
            status="healthy",
            details=f"Connected, {len(result.data) if result.data else 0} dept(s)",
            latency_ms=latency
        ))
    except Exception as e:
        latency = round((time.perf_counter() - supabase_start) * 1000, 2)
        components.append(HealthComponent(
            name="supabase",
            status="unhealthy",
            details=f"Connection failed: {str(e)[:100]}",
            latency_ms=latency
        ))
        overall_status = "unhealthy"
    
    # 2. Redis connectivity
    redis_start = time.perf_counter()
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        try:
            import redis.asyncio as aioredis
            client = aioredis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            await client.ping()
            await client.close()
            latency = round((time.perf_counter() - redis_start) * 1000, 2)
            components.append(HealthComponent(
                name="redis",
                status="healthy",
                details="Connected",
                latency_ms=latency
            ))
        except Exception as e:
            latency = round((time.perf_counter() - redis_start) * 1000, 2)
            components.append(HealthComponent(
                name="redis",
                status="degraded",
                details=f"Connection failed: {str(e)[:100]}",
                latency_ms=latency
            ))
            if overall_status == "healthy":
                overall_status = "degraded"
    else:
        components.append(HealthComponent(
            name="redis",
            status="degraded",
            details="Not configured"
        ))
    
    # 3. Groq API key availability
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        components.append(HealthComponent(
            name="groq_api",
            status="healthy",
            details="API key configured"
        ))
    else:
        components.append(HealthComponent(
            name="groq_api",
            status="degraded",
            details="API key not configured"
        ))
        if overall_status == "healthy":
            overall_status = "degraded"
    
    # 4. Scheduler status
    try:
        from .core.scheduler import scheduler
        if scheduler.running:
            job_count = len(scheduler.get_jobs())
            components.append(HealthComponent(
                name="scheduler",
                status="healthy",
                details=f"{job_count} jobs scheduled"
            ))
        else:
            components.append(HealthComponent(
                name="scheduler",
                status="unhealthy",
                details="Scheduler not running"
            ))
            overall_status = "unhealthy"
    except Exception as e:
        components.append(HealthComponent(
            name="scheduler",
            status="unhealthy",
            details=f"Error: {str(e)[:100]}"
        ))
        overall_status = "unhealthy"
    
    # 5. Database migrations table check
    try:
        supabase = get_supabase()
        result = supabase.table("schema_migrations").select("version, applied_at").order("applied_at", desc=True).limit(1).execute()
        if result.data:
            latest = result.data[0]
            components.append(HealthComponent(
                name="migrations",
                status="healthy",
                details=f"Latest: {latest.get('version', 'unknown')}"
            ))
        else:
            components.append(HealthComponent(
                name="migrations",
                status="degraded",
                details="No migrations recorded"
            ))
    except Exception:
        components.append(HealthComponent(
            name="migrations",
            status="healthy",
            details="Migration tracking not configured"
        ))
    
    total_latency = round((time.perf_counter() - start_time) * 1000, 2)
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        components=components
    )


# ── Token Verification Helper ─────────────────────────────────────────────────
def _verify_supabase_token(token: str) -> dict:
    """Verify a Supabase JWT token and return the user dict."""
    try:
        supabase = get_supabase()
        user_resp = supabase.auth.get_user(token)
        if not user_resp or not hasattr(user_resp, "user") or not user_resp.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        user = user_resp.user
        if isinstance(user, dict):
            return user
        return {"id": getattr(user, "id", None)}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Token verification failed: {type(e).__name__}")
        raise HTTPException(status_code=401, detail="Token verification failed")


# ── Real-time SSE Stream ──────────────────────────────────────────────────────

@app.get("/api/realtime/stream")
async def realtime_stream(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
):
    """Server-Sent Events stream (heartbeat only).

    Auth via Authorization header (preferred) or ?token= query parameter.
    The query-param fallback is required because the browser EventSource API
    does not support setting custom HTTP headers.
    """
    from fastapi.responses import StreamingResponse
    import asyncio
    import json

    auth_token = (authorization or "").replace("Bearer ", "").strip()
    if not auth_token:
        auth_token = (token or "").strip()
    if not auth_token:
        raise HTTPException(status_code=401, detail="Missing authentication")
    
    try:
        user = _verify_supabase_token(auth_token)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    async def event_generator():
        try:
            while True:
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now(UTC).isoformat()})}\n\n"
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)


@app.get("/")
def read_root():
    return {"message": "Welcome to Enterprise Analytics Platform"}


# ── Models ────────────────────────────────────────────────────────────────────

class NLQRequest(BaseModel):
    question: str

    @field_validator('question')
    @classmethod
    def validate_question_length(cls, v):
        if len(v) > 5000:
            raise ValueError('Question must be 5000 characters or fewer.')
        return v


class CustomChartRequest(BaseModel):
    instruction: str
    chart_type: str = "bar"
    sql: Optional[str] = None
    x_column: Optional[str] = None
    y_column: Optional[str] = None


@app.post("/api/charts/custom")
def build_custom_chart(
    body: CustomChartRequest,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    from .services.chart_service import build_custom_chart_spec
    from sqlalchemy import create_engine
    from sqlalchemy import text as sql_text

    supabase = get_supabase()
    rows: list = []
    columns: list = []
    sql_used = body.sql

    if body.sql and body.sql.strip():
        # Validate SQL for injection
        is_safe, error_msg = validate_sql_read_only(body.sql)
        if not is_safe:
            raise HTTPException(status_code=400, detail=error_msg)
        
        conn_resp = supabase.table("database_connections").select("*").eq("user_id", context["user_id"]).limit(1).execute()
        if not conn_resp.data:
            raise HTTPException(status_code=400, detail="No database connection configured.")
        from .services.connection_crypto import maybe_decrypt_connection_row
        conn_info = maybe_decrypt_connection_row(conn_resp.data[0])
        db_type = (conn_info.get("db_type") or "postgresql").lower()
        credentials = conn_info.get("credentials") or ""
        
        from .services.connection_utils import normalize_credentials, sqlalchemy_engine_kwargs
        engine = create_engine(
            normalize_credentials(credentials, db_type),
            **sqlalchemy_engine_kwargs(credentials, db_type),
        )
        try:
            from decimal import Decimal as _Decimal
            with engine.connect() as conn:
                result = conn.execute(sql_text(body.sql))
                columns = [c.lower() for c in list(result.keys())]
                rows = []
                for r in result.fetchmany(200):
                    record = {}
                    for col, val in zip(columns, r):
                        if hasattr(val, "isoformat"):
                            record[col] = val.isoformat()
                        elif isinstance(val, _Decimal):
                            record[col] = float(val)
                        elif hasattr(val, "__float__") and not isinstance(val, bool):
                            try:
                                record[col] = float(val)
                            except (TypeError, ValueError):
                                record[col] = str(val)
                        else:
                            record[col] = val
                    rows.append(record)
        finally:
            engine.dispose()
    else:
        nlq_result = run_nlq(context["user_id"], body.instruction.strip(), supabase)
        if nlq_result.get("error"):
            raise HTTPException(status_code=400, detail=nlq_result["error"])
        rows = nlq_result.get("rows") or []
        columns = nlq_result.get("columns") or []
        sql_used = nlq_result.get("sql")

    spec = build_custom_chart_spec(
        rows,
        chart_type=body.chart_type,
        x_column=body.x_column,
        y_column=body.y_column,
        title=body.instruction[:80],
    )
    if not spec:
        raise HTTPException(status_code=400, detail="Could not build chart from query results.")
    return {"chart": spec, "sql": sql_used, "row_count": len(rows), "columns": columns}


@app.post("/api/nlq")
def natural_language_query(
    body: NLQRequest,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    supabase = get_supabase()
    result = run_nlq(context["user_id"], body.question.strip(), supabase)
    return result


@app.post("/api/admin/test-email")
def send_test_email(
    body: dict,
    context: dict = Depends(require_role(["admin", "manager"])),
):
    to_email = normalize_recipient_email((body or {}).get("email", ""))
    if not to_email:
        raise HTTPException(status_code=400, detail="A valid email address is required.")
    api_key = os.getenv("BREVO_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="BREVO_API_KEY not configured.")
    try:
        import sib_api_v3_sdk
        from sib_api_v3_sdk.rest import ApiException
        cfg = sib_api_v3_sdk.Configuration()
        cfg.api_key["api-key"] = api_key
        client = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(cfg))
        sender_email = os.getenv("EMAIL_SENDER_ADDRESS", "noreply@saas-analytics.com")
        sender_name = os.getenv("EMAIL_SENDER_NAME", "SAAS Analytics")
        html = (
            "<h2>Enterprise Analytics — Test Email</h2>"
            "<p>Hello! This is a test email confirming Brevo is configured correctly.</p>"
            "<p>If you received this, your nightly briefings will deliver successfully.</p>"
        )
        resp = client.send_transac_email(sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email}],
            sender={"name": sender_name, "email": sender_email},
            subject="Enterprise Analytics — test email",
            html_content=html,
        ))
        return {"status": "sent", "message_id": resp.message_id, "to": to_email}
    except ApiException as e:
        logger.error(f"Brevo API error: {getattr(e, 'status', 'unknown')}", exc_info=True)
        raise HTTPException(status_code=502, detail="Email service error. Please try again later.")
    except Exception as e:
        logger.error(f"Email send error: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to send email.")


@app.get("/api/audit-log")
def get_audit_log(
    limit: int = 50,
    context: dict = Depends(require_role(["manager", "admin"])),
):
    if limit < 1 or limit > 500:
        limit = 50
    supabase = get_supabase()
    try:
        rows = (
            supabase.table("audit_logs")
            .select("*")
            .eq("user_id", context["user_id"])
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return {"logs": rows.data if hasattr(rows, "data") and rows.data else []}
    except Exception:
        logger.error("Audit log error", exc_info=True)
        return {"logs": [], "error": "Failed to fetch audit logs."}
