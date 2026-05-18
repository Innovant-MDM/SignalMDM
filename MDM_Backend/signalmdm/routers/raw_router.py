"""
signalmdm/routers/raw_router.py
--------------------------------
Read-only Raw Landing API — lists raw_records with source + run context.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from signalmdm.database import get_db
from signalmdm.middleware.auth import TokenPayload, require_auth
from signalmdm.schemas.common import ok
from signalmdm.schemas.raw_schema import RawRecordListItem
from signalmdm.services.raw_service import raw_service

router = APIRouter(prefix="/raw-records", tags=["Raw landing"])


@router.get(
    "/",
    summary="List raw records for Raw Landing",
)
def list_raw_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    run_id: uuid.UUID | None = Query(None, description="Filter by ingestion run"),
    source_system_id: uuid.UUID | None = Query(None, description="Filter by source system"),
    entity_type: str | None = Query(None, max_length=50, description="Filter by ingestion entity (e.g. CUSTOMER)"),
    exclude_duplicates: bool = Query(False, description="Omit duplicate rows within a run"),
    search: str | None = Query(None, max_length=200, description="Search id, checksum, or JSON text"),
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """
    Paginated raw records (newest first), scoped like ingestion list.

    Platform admins must pass ``X-Tenant-ID`` to scope to one tenant (same rule as ingestion).
    """
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    rows, total = raw_service.list_landing_page(
        db,
        tenant_id=target_tenant,
        skip=skip,
        limit=limit,
        run_id=run_id,
        source_system_id=source_system_id,
        entity_type=entity_type,
        search=search,
        exclude_duplicates=exclude_duplicates,
    )
    data = [RawRecordListItem.model_validate(r).model_dump(mode="json") for r in rows]
    return ok(
        data={"items": data, "total": total, "skip": skip, "limit": limit},
        message=f"{len(data)} raw record(s).",
    )
