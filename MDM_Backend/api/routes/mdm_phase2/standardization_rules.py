from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from db.sessions.database import get_db
from schemas.mdm_phase2.standardization_rule_schema import StandardizationRuleCreate, StandardizationRuleRead
from schemas.common import ok
from services.mdm_phase2.transformation.rule_service import rule_service
from middleware.auth import TokenPayload, require_auth

router = APIRouter(prefix="/mdm/standardization-rules", tags=["MDM Phase 2 — Standardization Rules"])


@router.post(
    "/",
    summary="Create a new standardization rule definition",
    status_code=status.HTTP_201_CREATED,
)
def create_standardization_rule(
    body: StandardizationRuleCreate,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    rule = rule_service.create_standardization_rule(
        db,
        tenant_id=target_tenant,
        data=body,
        performed_by=auth.user_id,
    )
    return ok(
        data=StandardizationRuleRead.model_validate(rule).model_dump(),
        message="Standardization rule created successfully.",
    )


@router.get(
    "/",
    summary="List all standardization rules",
)
def list_standardization_rules(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    rules = rule_service.list_standardization_rules(db, tenant_id=target_tenant)
    return ok(
        data=[StandardizationRuleRead.model_validate(r).model_dump() for r in rules],
        message=f"{len(rules)} standardization rule(s) found.",
    )
