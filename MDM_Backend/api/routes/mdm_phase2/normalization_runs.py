from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from db.sessions.database import get_db
from schemas.mdm_phase2.normalization_run_schema import NormalizationRunCreate, NormalizationRunRead
from schemas.common import ok
from services.mdm_phase2.normalization.normalization_service import normalization_service
from middleware.auth import TokenPayload, require_auth

router = APIRouter(prefix="/mdm/normalization-runs", tags=["MDM Phase 2 — Normalization Runs"])


@router.post(
    "/",
    summary="Trigger a new normalization run",
    status_code=status.HTTP_201_CREATED,
)
def create_normalization_run(
    body: NormalizationRunCreate,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    run = normalization_service.run_normalization(
        db,
        tenant_id=target_tenant,
        data=body,
        performed_by=auth.user_id,
    )
    return ok(
        data=NormalizationRunRead.model_validate(run).model_dump(),
        message="Normalization run triggered successfully.",
    )


@router.get(
    "/",
    summary="List all normalization runs",
)
def list_normalization_runs(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    runs = normalization_service.list_normalization_runs(db, tenant_id=target_tenant)
    return ok(
        data=[NormalizationRunRead.model_validate(r).model_dump() for r in runs],
        message=f"{len(runs)} normalization run(s) found.",
    )


@router.get(
    "/{run_id}/status",
    summary="Get normalization run status",
)
def get_normalization_run_status(
    run_id: uuid.UUID,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    run = normalization_service.get_normalization_run(db, tenant_id=target_tenant, run_id=run_id)
    return ok(
        data=NormalizationRunRead.model_validate(run).model_dump(),
        message=f"Normalization run status: {run.status}.",
    )
