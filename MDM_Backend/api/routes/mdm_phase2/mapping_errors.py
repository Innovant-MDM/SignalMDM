from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from db.sessions.database import get_db
from schemas.mdm_phase2.mapping_error_schema import MappingErrorRead
from schemas.common import ok
from services.mdm_phase2.retry.retry_service import retry_service
from middleware.auth import TokenPayload, require_auth

router = APIRouter(prefix="/mdm/mapping-errors", tags=["MDM Phase 2 — Mapping Errors"])


@router.get(
    "/",
    summary="List mapping errors",
)
def list_mapping_errors(
    status_val: str = "OPEN",
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    errors = retry_service.list_mapping_errors(db, tenant_id=target_tenant, status_val=status_val)
    return ok(
        data=[MappingErrorRead.model_validate(e).model_dump() for e in errors],
        message=f"{len(errors)} mapping error(s) found.",
    )


@router.post(
    "/{error_id}/retry",
    summary="Retry a failed mapping error",
)
def retry_mapping_error(
    error_id: uuid.UUID,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    result = retry_service.retry_mapping_error(
        db,
        tenant_id=target_tenant,
        error_id=error_id,
        performed_by=auth.user_id,
    )
    return ok(data=result, message=result["message"])
