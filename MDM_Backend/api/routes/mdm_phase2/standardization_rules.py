from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from db.sessions.database import get_db
import uuid

from schemas.mdm_phase2.standardization_rule_schema import (
    StandardizationRuleCreate,
    StandardizationRuleRead,
    StandardizationRuleUpdate,
)
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


@router.put(
    "/{rule_id}",
    summary="Update an existing standardization rule definition",
)
def update_standardization_rule(
    rule_id: uuid.UUID,
    body: StandardizationRuleUpdate,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    rule = rule_service.update_standardization_rule(
        db,
        tenant_id=target_tenant,
        rule_id=rule_id,
        data=body,
        performed_by=auth.user_id,
    )
    return ok(
        data=StandardizationRuleRead.model_validate(rule).model_dump(),
        message="Standardization rule updated successfully.",
    )


@router.patch(
    "/{rule_id}/status",
    summary="Patch standardization rule status",
)
def patch_standardization_rule_status(
    rule_id: uuid.UUID,
    status_val: str,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id
    rule = rule_service.patch_standardization_rule_status(
        db,
        tenant_id=target_tenant,
        rule_id=rule_id,
        status_val=status_val,
        performed_by=auth.user_id,
    )
    return ok(
        data=StandardizationRuleRead.model_validate(rule).model_dump(),
        message="Standardization rule status updated successfully.",
    )


@router.get(
    "/{rule_id}/history",
    summary="Get standardization rule audit history",
)
def standardization_rule_history(
    rule_id: uuid.UUID,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id
    rows = rule_service.standardization_rule_history(db, tenant_id=target_tenant, rule_id=rule_id)
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
