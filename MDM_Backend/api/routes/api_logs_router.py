"""
signalmdm/routers/api_logs_router.py
-------------------------------------
Read-only API Logs — lists immutable audit_log entries.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from db.sessions.database import get_db
from middleware.auth import TokenPayload, require_auth
from schemas.audit_schema import ApiLogListItem
from schemas.common import ok
from services.audit import audit_service as audit_svc

router = APIRouter(prefix="/api-logs", tags=["API Logs"])


@router.get(
    "/",
    summary="List audit / API activity logs",
)
def list_api_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    operation_type: str | None = Query(None, description="INSERT, UPDATE, DELETE, or MERGE"),
    entity_name: str | None = Query(None, description="Filter by entity / table name"),
    search: str | None = Query(None, max_length=200, description="Search actor, entity, trace, or JSON"),
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """
    Paginated audit trail (newest first), scoped like raw-records / staging-records.

    Platform admins may pass ``X-Tenant-ID`` to scope to one tenant, or omit it to list all.
    """
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    rows, total = audit_svc.list_api_logs_page(
        db,
        tenant_id=target_tenant,
        skip=skip,
        limit=limit,
        operation_type=operation_type,
        entity_name=entity_name,
        search=search,
    )
    data = [ApiLogListItem.model_validate(r).model_dump(mode="json") for r in rows]
    return ok(
        data={"items": data, "total": total, "skip": skip, "limit": limit},
        message=f"{len(data)} log entr{'y' if len(data) == 1 else 'ies'}.",
    )
