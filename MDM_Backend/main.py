"""
main.py
--------
SignalMDM Phase 1 — FastAPI Application Entrypoint

Security layers:
  1. SecurityHeadersMiddleware — sets strict HTTP security headers on every response
  2. require_auth (FastAPI dependency) — AES decrypt → Redis check → JWT verify → fingerprint

Run:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
from starlette.middleware.base import BaseHTTPMiddleware

from dotenv import load_dotenv
load_dotenv()

# ---------------------------------------------------------------------------
# Import all models so SQLAlchemy sees them before create_all()
# ---------------------------------------------------------------------------
import signalmdm.models  # noqa: F401 — registers all mappers with Base

from signalmdm.database import engine, Base
from core.config import settings

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
from signalmdm.routers.tenant_router        import router as tenant_router
from signalmdm.routers.source_router        import router as source_router
from signalmdm.routers.ingestion_router     import router as ingestion_router
from signalmdm.routers.raw_router           import router as raw_router
from signalmdm.routers.platform_rbac_router import router as platform_rbac_router
from signalmdm.routers.staging_router       import router as staging_router
from signalmdm.routers.api_logs_router      import router as api_logs_router
from signalmdm.routers.auth_router          import router as auth_router
from signalmdm.routers.admin_router         import router as admin_router
from signalmdm.routers.tenant_config_router import router as tenant_config_router
from signalmdm.routers.upload_router        import router as upload_router
from signalmdm.routers.domain_router        import router as domain_router

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Security Headers Middleware
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware:
    """
    Adds strict HTTP security headers to every response.

    These headers are the first line of defence at the HTTP layer and
    are independent of the JWT / AES auth flow.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.monotonic()

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))

                # Security headers to set/override (single-value headers only)
                security_headers = {
                    b"x-content-type-options": b"nosniff",
                    b"x-frame-options": b"DENY",
                    b"strict-transport-security": b"max-age=31536000; includeSubDomains",
                    b"referrer-policy": b"strict-origin-when-cross-origin",
                    b"permissions-policy": b"geolocation=(), microphone=(), camera=()",
                    b"x-xss-protection": b"1; mode=block",
                    b"content-security-policy": b"default-src 'self'",
                }

                # Headers to remove
                remove_headers = {b"server"}

                # Build new header list: keep existing headers that we don't
                # need to override, preserving duplicates (e.g. Set-Cookie)
                override_keys = set(security_headers.keys()) | remove_headers
                new_headers = [
                    (k, v) for k, v in headers
                    if k.lower() not in override_keys
                ]

                # Append security headers
                for k, v in security_headers.items():
                    new_headers.append((k, v))

                # Append response time
                elapsed = round((time.monotonic() - start) * 1000, 2)
                new_headers.append((b"x-response-time", f"{elapsed}ms".encode("utf-8")))

                message["headers"] = new_headers

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            logger.exception("SecurityHeadersMiddleware unhandled error")
            response = JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Internal server error",
                    "data": None,
                    "errors": [str(exc)],
                },
            )
            await response(scope, receive, send_wrapper)
    
class ResponseEnvelopeMiddleware:
    """
    Standardises all successful API responses into a uniform envelope:
    { "success": true, "message": "...", "data": T, "errors": [] }

    This ensures the frontend client (api.ts) always receives a predictable structure.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not path.startswith("/api/v1"):
            await self.app(scope, receive, send)
            return

        response_start = None
        body_chunks = []

        async def send_wrapper(message):
            nonlocal response_start

            if message["type"] == "http.response.start":
                response_start = message
                return

            if message["type"] == "http.response.body":
                body_chunks.append(message.get("body", b""))
                if message.get("more_body", False):
                    return

                full_body = b"".join(body_chunks)
                status_code = response_start.get("status", 200)
                headers = list(response_start.get("headers", []))

                is_json = False
                for k, v in headers:
                    if k.lower() == b"content-type" and b"application/json" in v.lower():
                        is_json = True
                        break

                if status_code >= 400 or not is_json:
                    await send(response_start)
                    await send({
                        "type": "http.response.body",
                        "body": full_body,
                        "more_body": False
                    })
                    return

                try:
                    if not full_body:
                        await send(response_start)
                        await send(message)
                        return

                    data = json.loads(full_body.decode("utf-8"))
                    
                    # If it's already wrapped (has 'success' and 'data' keys), don't wrap again
                    if isinstance(data, dict) and "success" in data and "data" in data:
                        await send(response_start)
                        await send(message)
                        return

                    wrapped = {
                        "success": True,
                        "message": "Request fulfilled successfully.",
                        "data": data,
                        "errors": []
                    }
                    
                    wrapped_body = json.dumps(wrapped).encode("utf-8")
                    
                    # Prepare new headers: remove Content-Length as it will be recalculated
                    new_headers = []
                    for k, v in headers:
                        if k.lower() != b"content-length":
                            new_headers.append((k, v))
                    new_headers.append((b"content-length", str(len(wrapped_body)).encode("utf-8")))
                    
                    response_start["headers"] = new_headers
                    
                    await send(response_start)
                    await send({
                        "type": "http.response.body",
                        "body": wrapped_body,
                        "more_body": False
                    })
                except Exception as e:
                    logger.error("[middleware] Failed to wrap response: %s", e)
                    await send(response_start)
                    await send({
                        "type": "http.response.body",
                        "body": full_body,
                        "more_body": False
                    })

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            logger.exception("ResponseEnvelopeMiddleware error: %s", exc)
            response = JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Internal server error",
                    "data": None,
                    "errors": [str(exc)]
                }
            )
            await response(scope, receive, send)


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    print("[SignalMDM] Database tables verified / created.")

    # Ensure missing columns in audit_log exist (incremental update)
    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS approved_by VARCHAR(150) NULL;"))
            conn.execute(text("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS approval_reason VARCHAR(500) NULL;"))
            
            # Seed domains permissions in the platform_permission catalog
            conn.execute(text("""
                INSERT INTO platform_permission (screen_key, feature_key, label, description)
                VALUES 
                    ('domains', 'view', 'View Domains', 'Access the domains management screen'),
                    ('domains', 'manage', 'Manage Domains', 'Create, update and deactivate domains')
                ON CONFLICT (screen_key, feature_key) DO NOTHING;
            """))
            
            # Grant domains permissions to super_admin, admin, and data_architect platform roles
            conn.execute(text("""
                INSERT INTO platform_role_permission (role_id, permission_id)
                SELECT r.role_id, p.permission_id
                FROM platform_role r, platform_permission p
                WHERE r.role_key IN ('super_admin', 'admin', 'data_architect')
                  AND p.screen_key = 'domains'
                ON CONFLICT DO NOTHING;
            """))
        print("[SignalMDM] Database migration check completed (audit_log columns and domains permissions verified).")
    except Exception as e:
        print(f"[SignalMDM] Database migration warning: {e}")

    # Warm Redis connection pool (non-blocking — errors are logged, not raised)
    from core.redis_client import is_redis_available
    redis_ok = is_redis_available()
    print(f"[SignalMDM] Redis available: {redis_ok}")

    yield
    print("[SignalMDM] Shutting down.")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

is_prod = settings.app_env == "production"

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=(
        "SignalMDM Phase 1 API — Source registration, ingestion pipeline, "
        "raw data storage, and staging entity creation.\n\n"
        "**Authentication:** All protected endpoints require:\n"
        "- `Authorization: Bearer <AES-256-CBC encrypted JWT>`\n"
        "- `X-Device-ID: <stable device fingerprint>`"
    ),
    lifespan=lifespan,
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json",
)

# ---------------------------------------------------------------------------
# Middleware — order matters: outermost first
# ---------------------------------------------------------------------------

# 1. Rate limiting (applied first/innermost after routing)
from signalmdm.middleware.rate_limit import RateLimitingMiddleware
app.add_middleware(RateLimitingMiddleware)

# 2. Response envelope (wraps successful JSON responses)
app.add_middleware(ResponseEnvelopeMiddleware)

# 3. Security headers (applied to ALL responses, wrapping the envelope and rate limiter)
app.add_middleware(SecurityHeadersMiddleware)

# 3. CORS (before security headers so preflight OPTIONS also gets headers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # Next.js dev server
        "http://localhost:3030",   # New Production Express server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Response-Time"],
)

# ---------------------------------------------------------------------------
# Global exception handler — uniform StandardResponse on unhandled errors
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data": None,
            "errors": [exc.detail],
        },
    )
    # Add CORS headers manually to error responses so they aren't masked by CORS errors
    origin = request.headers.get("origin")
    if origin in ["http://localhost:3030", "http://localhost:5173", "http://localhost:3000"]:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    print(f"[ERROR] Unhandled exception: {exc}")
    traceback.print_exc()

    response = JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "An unexpected server error occurred.",
            "data": None,
            "errors": [str(exc)],
        },
    )
    origin = request.headers.get("origin")
    if origin in ["http://localhost:3030", "http://localhost:5173", "http://localhost:3000"]:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

PREFIX = "/api/v1"

app.include_router(tenant_router,        prefix=PREFIX)
app.include_router(source_router,        prefix=PREFIX)
app.include_router(ingestion_router,     prefix=PREFIX)
app.include_router(raw_router,           prefix=PREFIX)
app.include_router(platform_rbac_router, prefix=PREFIX)
app.include_router(staging_router,       prefix=PREFIX)
app.include_router(api_logs_router,      prefix=PREFIX)
app.include_router(auth_router,          prefix=PREFIX)
app.include_router(admin_router,         prefix=PREFIX)
app.include_router(tenant_config_router, prefix=PREFIX)
app.include_router(upload_router,        prefix=PREFIX)
app.include_router(domain_router,        prefix=PREFIX)


# ---------------------------------------------------------------------------
# Health / root endpoints  (no auth required)
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
def root():
    return {
        "status": "SignalMDM Backend Running",
        "version": settings.app_version,
        "environment": settings.app_env,
        "phase": "Phase 1 — Ingestion Foundation",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    """Kubernetes / load-balancer liveness probe."""
    from core.redis_client import is_redis_available
    return {
        "status": "ok",
        "redis": "connected" if is_redis_available() else "unavailable",
    }
