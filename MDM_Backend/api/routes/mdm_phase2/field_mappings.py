from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from db.sessions.database import get_db
from schemas.mdm_phase2.field_mapping_schema import FieldMappingCreate, FieldMappingRead
from schemas.common import ok
from services.mdm_phase2.mapping.mapping_service import mapping_service
from middleware.auth import TokenPayload, require_auth

router = APIRouter(prefix="/mdm/field-mappings", tags=["MDM Phase 2 — Field Mappings"])


@router.post(
    "/",
    summary="Create a new field mapping configuration",
    status_code=status.HTTP_201_CREATED,
)
def create_field_mapping(
    body: FieldMappingCreate,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    mapping = mapping_service.create_field_mapping(
        db,
        tenant_id=target_tenant,
        data=body,
        performed_by=auth.user_id,
    )
    return ok(
        data=FieldMappingRead.model_validate(mapping).model_dump(),
        message="Field mapping created successfully.",
    )


@router.get(
    "/",
    summary="List all field mapping configurations",
)
def list_field_mappings(
    source_system_id: Optional[uuid.UUID] = None,
    entity_type: Optional[str] = None,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    mappings = mapping_service.list_field_mappings(
        db,
        tenant_id=target_tenant,
        source_system_id=source_system_id,
        entity_type=entity_type,
    )
    return ok(
        data=[FieldMappingRead.model_validate(m).model_dump() for m in mappings],
        message=f"{len(mappings)} field mapping(s) found.",
    )


@router.put(
    "/{mapping_id}",
    summary="Update a field mapping configuration",
)
def update_field_mapping(
    mapping_id: uuid.UUID,
    body: FieldMappingCreate,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    mapping = mapping_service.update_field_mapping(
        db,
        tenant_id=target_tenant,
        mapping_id=mapping_id,
        data=body,
        performed_by=auth.user_id,
    )
    return ok(
        data=FieldMappingRead.model_validate(mapping).model_dump(),
        message="Field mapping updated successfully.",
    )


@router.delete(
    "/{mapping_id}",
    summary="Delete a field mapping configuration",
)
def delete_field_mapping(
    mapping_id: uuid.UUID,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    result = mapping_service.delete_field_mapping(
        db,
        tenant_id=target_tenant,
        mapping_id=mapping_id,
        performed_by=auth.user_id,
    )
    return ok(message=result["message"])
