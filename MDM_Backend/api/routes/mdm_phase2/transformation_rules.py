from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from db.sessions.database import get_db
from schemas.mdm_phase2.transformation_rule_schema import (
    TransformationRuleCreate,
    TransformationRuleRead,
    TransformationRuleUpdate,
)
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


@router.put(
    "/{rule_id}",
    summary="Update an existing transformation rule definition",
)
def update_transformation_rule(
    rule_id: uuid.UUID,
    body: TransformationRuleUpdate,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    rule = rule_service.update_transformation_rule(
        db,
        tenant_id=target_tenant,
        rule_id=rule_id,
        data=body,
        performed_by=auth.user_id,
    )
    return ok(
        data=TransformationRuleRead.model_validate(rule).model_dump(),
        message="Transformation rule updated successfully.",
    )


@router.patch(
    "/{rule_id}/status",
    summary="Patch transformation rule status",
)
def patch_transformation_rule_status(
    rule_id: uuid.UUID,
    status_val: str,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id
    rule = rule_service.patch_transformation_rule_status(
        db,
        tenant_id=target_tenant,
        rule_id=rule_id,
        status_val=status_val,
        performed_by=auth.user_id,
    )
    return ok(
        data=TransformationRuleRead.model_validate(rule).model_dump(),
        message="Transformation rule status updated successfully.",
    )


@router.get(
    "/{rule_id}/history",
    summary="Get transformation rule audit history",
)
def transformation_rule_history(
    rule_id: uuid.UUID,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id
    rows = rule_service.transformation_rule_history(db, tenant_id=target_tenant, rule_id=rule_id)
    return ok(
        data=[
            {
                "audit_id": r.audit_id,
                "operation_type": r.operation_type,
                "old_value": r.old_value,
                "new_value": r.new_value,
                "performed_by": r.performed_by,
                "performed_at": r.performed_at,
            }
            for r in rows
        ],
        message=f"{len(rows)} history event(s) found.",
    )
