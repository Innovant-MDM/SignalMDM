r"""
MDM_Backend\signalmdm\routers\source_router.py
------------------------------------
API endpoints for SourceSystem management.

Security:
  All endpoints require a valid encrypted JWT (via require_auth).
  tenant_id is extracted from the verified JWT — NOT a raw header.
  DELETE is restricted to admin role.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from signalmdm.database import get_db
from signalmdm.schemas.source_schema import SourceSystemCreate, SourceSystemRead
from signalmdm.schemas.common import ok
from signalmdm.services.source_service import source_service
from signalmdm.middleware.auth import TokenPayload, require_auth, require_admin
from signalmdm.enums import StatusEnum

router = APIRouter(prefix="/sources", tags=["Source Systems"])


@router.post(
    "/",
    summary="Register a new source system",
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/register",
    summary="Register a new source system (deprecated alias — use POST /sources)",
    status_code=status.HTTP_201_CREATED,
    deprecated=True,
)
def register_source(
    body: SourceSystemCreate,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """
    Register a new data source for the authenticated tenant.

    - `source_code` must be unique (lowercase slug, e.g. `salesforce_crm`).
    - `source_type` and `connection_type` use predefined enums.
    - `config_json` stores non-sensitive connection parameters.
    - `tenant_id`: 
        - For standard users, it comes from the verified JWT.
        - For SuperAdmins (platform tenant), it can be overridden via `X-Tenant-ID` header.
    """
    # Determine the target tenant
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    source = source_service.create_source(
        db,
        tenant_id=target_tenant,
        data=body,
        performed_by=auth.user_id,
    )
    return ok(
        data=SourceSystemRead.model_validate(source).model_dump(),
        message="Source system registered successfully.",
    )


@router.get(
    "/",
    summary="List all source systems for the authenticated tenant",
)
def list_sources(
    skip: int = 0,
    limit: int = 50,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """Return all active source systems scoped to the authenticated tenant."""
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    sources = source_service.list_sources(db, tenant_id=target_tenant, skip=skip, limit=limit)
    return ok(
        data=[SourceSystemRead.model_validate(s).model_dump() for s in sources],
        message=f"{len(sources)} source system(s) found.",
    )


@router.get(
    "/{source_id}",
    summary="Get a source system by ID",
)
def get_source(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """Fetch a single source system scoped to the authenticated tenant."""
    source = source_service.get_source(db, tenant_id=auth.tenant_id, source_system_id=source_id)
    return ok(data=SourceSystemRead.model_validate(source).model_dump())


@router.delete(
    "/{source_id}",
    summary="Deactivate a source system (admin only)",
)
def deactivate_source(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_admin),   # admin only
):
    """Soft-deactivate (is_active=False). Restricted to admin role."""
    source = source_service.deactivate_source(
        db,
        tenant_id=auth.tenant_id,
        source_system_id=source_id,
        performed_by=auth.user_id,
    )
    return ok(
        data=SourceSystemRead.model_validate(source).model_dump(),
        message="Source system deactivated.",
    )


@router.patch(
    "/{source_id}/status",
    summary="Update a source system's status (admin only)",
)
def update_status(
    source_id: uuid.UUID,
    status: StatusEnum,
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_admin),
):
    """Change status to ACTIVE, SUSPENDED, ARCHIVED, or DEACTIVATED."""
    source = source_service.update_source_status(
        db,
        tenant_id=auth.tenant_id,
        source_system_id=source_id,
        new_status=status,
        performed_by=auth.user_id,
    )
    return ok(
        data=SourceSystemRead.model_validate(source).model_dump(),
        message=f"Source system status updated to {status.value}.",
    )
