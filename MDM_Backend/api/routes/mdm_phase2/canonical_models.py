from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from db.sessions.database import get_db
from schemas.mdm_phase2.canonical_model_schema import CanonicalFieldCreate, CanonicalFieldRead
from schemas.common import ok
from services.mdm_phase2.canonical.canonical_service import canonical_service
from middleware.auth import TokenPayload, require_auth

router = APIRouter(prefix="/mdm/canonical-models", tags=["MDM Phase 2 — Canonical Models"])


@router.post(
    "/",
    summary="Create a new canonical field definition",
    status_code=status.HTTP_201_CREATED,
)
def create_canonical_field(
    body: CanonicalFieldCreate,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    field = canonical_service.create_canonical_field(
        db,
        tenant_id=target_tenant,
        data=body,
        performed_by=auth.user_id,
    )
    return ok(
        data=CanonicalFieldRead.model_validate(field).model_dump(),
        message="Canonical field definition created successfully.",
    )


@router.get(
    "/",
    summary="List all canonical field definitions",
)
def list_canonical_fields(
    entity_type: Optional[str] = None,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    fields = canonical_service.list_canonical_fields(
        db,
        tenant_id=target_tenant,
        entity_type=entity_type,
    )
    return ok(
        data=[CanonicalFieldRead.model_validate(f).model_dump() for f in fields],
        message=f"{len(fields)} canonical field(s) found.",
    )


@router.put(
    "/{field_id}",
    summary="Update a canonical field definition",
)
def update_canonical_field(
    field_id: uuid.UUID,
    body: CanonicalFieldCreate,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    field = canonical_service.update_canonical_field(
        db,
        tenant_id=target_tenant,
        field_id=field_id,
        data=body,
        performed_by=auth.user_id,
    )
    return ok(
        data=CanonicalFieldRead.model_validate(field).model_dump(),
        message="Canonical field definition updated successfully.",
    )


@router.patch(
    "/{field_id}/status",
    summary="Patch status of a canonical field definition",
)
def patch_canonical_field_status(
    field_id: uuid.UUID,
    status_val: str,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    field = canonical_service.patch_canonical_field_status(
        db,
        tenant_id=target_tenant,
        field_id=field_id,
        status_val=status_val,
        performed_by=auth.user_id,
    )
    return ok(
        data=CanonicalFieldRead.model_validate(field).model_dump(),
        message="Canonical field status updated successfully.",
    )
