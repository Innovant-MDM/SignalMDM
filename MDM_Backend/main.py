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

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Security Headers Middleware
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds strict HTTP security headers to every response.

    These headers are the first line of defence at the HTTP layer and
    are independent of the JWT / AES auth flow.
    """

    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        elapsed = round((time.monotonic() - start) * 1000, 2)

        # Prevent browsers from MIME-sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Stop clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        # Force HTTPS for 1 year (enable in production behind TLS terminator)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Minimal referrer leakage
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Restrict browser features
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        # Basic XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Remove server fingerprint
        response.headers["Server"] = "SignalMDM"
        # Timing info (useful for monitoring)
        response.headers["X-Response-Time"] = f"{elapsed}ms"

        return response
    
class ResponseEnvelopeMiddleware(BaseHTTPMiddleware):
    """
    Standardises all successful API responses into a uniform envelope:
    { "success": true, "message": "...", "data": T, "errors": [] }

    This ensures the frontend client (api.ts) always receives a predictable structure.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Skip non-JSON or already wrapped responses (like from exception handlers)
        # and skip standard health/root endpoints if desired
        path = request.url.path
        if not path.startswith("/api/v1") or response.status_code >= 400:
            return response

        # Only wrap application/json responses
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            return response

        # Read the body and wrap it
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        try:
            if not body:
                return Response(content=body, status_code=response.status_code, headers=dict(response.headers))

            data = json.loads(body)
            # If it's already wrapped (has 'success' and 'data' keys), don't wrap again
            if isinstance(data, dict) and "success" in data and "data" in data:
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )

            wrapped = {
                "success": True,
                "message": "Request fulfilled successfully.",
                "data": data,
                "errors": []
            }
            
            # Prepare new headers: remove Content-Length as it will be recalculated
            new_headers = dict(response.headers)
            new_headers.pop("content-length", None)
            new_headers.pop("Content-Length", None)
            
            return Response(
                content=json.dumps(wrapped),
                status_code=response.status_code,
                headers=new_headers,
                media_type="application/json"
            )
        except Exception as e:
            logger.error("[middleware] Failed to wrap response: %s", e)
            # Return original body if wrapping fails
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers)
            )


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    print("[SignalMDM] Database tables verified / created.")

    # Warm Redis connection pool (non-blocking — errors are logged, not raised)
    from core.redis_client import is_redis_available
    redis_ok = is_redis_available()
    print(f"[SignalMDM] Redis available: {redis_ok}")

    yield
    print("[SignalMDM] Shutting down.")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

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
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# Middleware — order matters: outermost first
# ---------------------------------------------------------------------------

# 1. Security headers (applied to ALL responses)
app.add_middleware(SecurityHeadersMiddleware)

# 2. Response envelope (wraps successful JSON responses)
app.add_middleware(ResponseEnvelopeMiddleware)

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
