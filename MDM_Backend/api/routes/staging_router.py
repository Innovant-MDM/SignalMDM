"""
signalmdm/routers/staging_router.py
------------------------------------
Read-only Staging API — lists staging_entities with source + run + raw context.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from db.sessions.database import get_db
from middleware.auth import TokenPayload, require_auth
from schemas.common import ok
from schemas.staging_schema import StagingRecordListItem
from services.staging.staging_service import staging_service

router = APIRouter(prefix="/staging-records", tags=["Staging"])


@router.get(
    "/",
    summary="List staging records for Staging screen",
)
def list_staging_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    run_id: uuid.UUID | None = Query(None, description="Filter by ingestion run"),
    source_system_id: uuid.UUID | None = Query(None, description="Filter by source system"),
    entity_type: str | None = Query(None, max_length=50, description="Filter by ingestion entity"),
    search: str | None = Query(None, max_length=200, description="Search ids or JSON text"),
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """
    Paginated staging entities (newest first), scoped like raw-records.

    Platform admins must pass ``X-Tenant-ID`` to scope to one tenant.
    """
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    rows, total = staging_service.list_landing_page(
        db,
        tenant_id=target_tenant,
        skip=skip,
        limit=limit,
        run_id=run_id,
        source_system_id=source_system_id,
        entity_type=entity_type,
        search=search,
    )
    data = [StagingRecordListItem.model_validate(r).model_dump(mode="json") for r in rows]
    return ok(
        data={"items": data, "total": total, "skip": skip, "limit": limit},
        message=f"{len(data)} staging record(s).",
    )
