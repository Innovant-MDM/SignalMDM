from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from db.sessions.database import get_db
from schemas.mdm_phase2.transformation_rule_schema import TransformationRuleCreate, TransformationRuleRead
from schemas.common import ok
from services.mdm_phase2.transformation.rule_service import rule_service
from middleware.auth import TokenPayload, require_auth

router = APIRouter(prefix="/mdm/transformation-rules", tags=["MDM Phase 2 — Transformation Rules"])


@router.post(
    "/",
    summary="Create a new transformation rule definition",
    status_code=status.HTTP_201_CREATED,
)
def create_transformation_rule(
    body: TransformationRuleCreate,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    rule = rule_service.create_transformation_rule(
        db,
        tenant_id=target_tenant,
        data=body,
        performed_by=auth.user_id,
    )
    return ok(
        data=TransformationRuleRead.model_validate(rule).model_dump(),
        message="Transformation rule created successfully.",
    )


@router.get(
    "/",
    summary="List all transformation rules",
)
def list_transformation_rules(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    rules = rule_service.list_transformation_rules(db, tenant_id=target_tenant)
    return ok(
        data=[TransformationRuleRead.model_validate(r).model_dump() for r in rules],
        message=f"{len(rules)} transformation rule(s) found.",
    )
