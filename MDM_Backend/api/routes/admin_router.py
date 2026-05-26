"""
signalmdm/routers/admin_router.py
---------------------------------
Administrative endpoints for system health and monitoring.
"""

from __future__ import annotations

import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from db.sessions.database import get_db
from middleware.auth import TokenPayload, require_admin
from schemas.common import ok
from core.redis_client import is_redis_available

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/health", summary="Detailed system health check")
def system_health(
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_admin)
):
    """
    Returns detailed health status of all system components.
    Restricted to ADMIN role.
    """
    start_time = time.monotonic()
    
    # 1. Check Database
    db_ok = False
    db_latency = 0
    try:
        db_start = time.monotonic()
        db.execute(text("SELECT 1"))
        db_latency = round((time.monotonic() - db_start) * 1000, 2)
        db_ok = True
    except Exception:
        db_ok = False

    # 2. Check Redis
    redis_ok = is_redis_available()

    # 3. Component Statuses
    components = [
        {"name": "API Server", "status": "UP", "latency": f"{round((time.monotonic() - start_time) * 1000, 2)}ms"},
        {"name": "PostgreSQL", "status": "UP" if db_ok else "DOWN", "latency": f"{db_latency}ms"},
        {"name": "Redis Cache", "status": "UP" if redis_ok else "DOWN", "latency": "N/A"},
        {"name": "Background Worker", "status": "UP", "latency": "N/A"}, # Placeholder
    ]

    # 4. Basic Metrics
    try:
        from db.models.tenant import Tenant
        from db.models.source_system import SourceSystem
        from db.models.ingestion_run import IngestionRun
        
        metrics = {
            "total_tenants": db.query(Tenant).count(),
            "total_sources": db.query(SourceSystem).count(),
            "total_ingestion_runs": db.query(IngestionRun).count(),
        }
    except Exception:
        metrics = {}

    return ok(
        data={
            "components": components,
            "metrics": metrics,
            "timestamp": time.time(),
            "environment": "development" # Should come from settings
        },
        message="System health check complete."
    )
