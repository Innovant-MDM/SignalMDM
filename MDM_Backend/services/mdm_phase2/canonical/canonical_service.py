from __future__ import annotations

import uuid
from typing import Optional, Union

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from db.models.mdm_phase2.canonical_field import CanonicalField
from schemas.mdm_phase2.canonical_model_schema import CanonicalFieldCreate
from db.enums import OperationTypeEnum
from utils.mdm_phase2.validators import is_snake_case
import services.audit.audit_service as audit_svc


class CanonicalService:

    def _parse_tenant(self, tenant_id: Union[str, uuid.UUID]) -> uuid.UUID:
        if isinstance(tenant_id, uuid.UUID):
            return tenant_id
        try:
            return uuid.UUID(str(tenant_id))
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant_id format — must be a valid UUID.",
            )

    def create_canonical_field(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        data: CanonicalFieldCreate,
        performed_by: str = "system",
    ) -> CanonicalField:
        """
        Creates a new canonical field definition for an entity type.
        Validates strict snake_case naming and prevents duplicate records.
        """
        target_tenant = self._parse_tenant(tenant_id)

        # 1. Enforce strict snake_case naming validation
        if not is_snake_case(data.canonical_field_name):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Field name '{data.canonical_field_name}' must be strict snake_case.",
            )

        # 2. Check for duplicate canonical fields
        existing = (
            db.query(CanonicalField)
            .filter(
                CanonicalField.tenant_id == target_tenant,
                CanonicalField.entity_type == data.entity_type.upper(),
                CanonicalField.canonical_field_name == data.canonical_field_name,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Canonical field '{data.canonical_field_name}' already exists for entity type '{data.entity_type}'.",
            )

        field = CanonicalField(
            field_id=uuid.uuid4(),
            tenant_id=target_tenant,
            entity_type=data.entity_type.upper(),
            canonical_field_name=data.canonical_field_name,
            data_type=data.data_type.upper(),
            is_required=data.is_required,
            validation_type=data.validation_type.upper(),
            standardization_type=data.standardization_type.upper(),
            status=data.status or "ACTIVE",
        )
        db.add(field)
        db.flush()

        # Write audit event
        audit_svc.log_action(
            db,
            tenant_id=target_tenant,
            entity_name="canonical_fields",
            entity_id=field.field_id,
            operation_type=OperationTypeEnum.INSERT,
            new_value={
                "entity_type": field.entity_type,
                "canonical_field_name": field.canonical_field_name,
                "data_type": field.data_type,
                "is_required": field.is_required,
            },
            performed_by=performed_by,
            autocommit=False,
        )

        db.commit()
        db.refresh(field)
        return field

    def list_canonical_fields(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        entity_type: Optional[str] = None,
    ) -> list[CanonicalField]:
        """Fetch all canonical field definitions for the tenant, optionally filtered by entity type."""
        target_tenant = self._parse_tenant(tenant_id)
        query = db.query(CanonicalField).filter(CanonicalField.tenant_id == target_tenant)
        if entity_type:
            query = query.filter(CanonicalField.entity_type == entity_type.upper())
        return query.order_by(CanonicalField.canonical_field_name.asc()).all()

    def get_canonical_field(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        field_id: uuid.UUID,
    ) -> CanonicalField:
        """Fetch a single canonical field definition by ID."""
        target_tenant = self._parse_tenant(tenant_id)
        field = db.query(CanonicalField).filter(
            CanonicalField.field_id == field_id,
            CanonicalField.tenant_id == target_tenant,
        ).first()
        if not field:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Canonical field definition not found.",
            )
        return field

    def update_canonical_field(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        field_id: uuid.UUID,
        data: CanonicalFieldCreate,
        performed_by: str = "system",
    ) -> CanonicalField:
        """Update an existing canonical field definition."""
        field = self.get_canonical_field(db, tenant_id, field_id)
        target_tenant = self._parse_tenant(tenant_id)

        old_val = {
            "is_required": field.is_required,
            "validation_type": field.validation_type,
            "standardization_type": field.standardization_type,
            "status": field.status,
        }

        field.is_required = data.is_required
        field.validation_type = data.validation_type.upper()
        field.standardization_type = data.standardization_type.upper()
        if data.status:
            field.status = data.status.upper()

        db.flush()

        audit_svc.log_action(
            db,
            tenant_id=target_tenant,
            entity_name="canonical_fields",
            entity_id=field.field_id,
            operation_type=OperationTypeEnum.UPDATE,
            old_value=old_val,
            new_value={
                "is_required": field.is_required,
                "validation_type": field.validation_type,
                "standardization_type": field.standardization_type,
                "status": field.status,
            },
            performed_by=performed_by,
            autocommit=False,
        )

        db.commit()
        db.refresh(field)
        return field

    def patch_canonical_field_status(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        field_id: uuid.UUID,
        status_val: str,
        performed_by: str = "system",
    ) -> CanonicalField:
        """Quickly patch the status of a canonical field (e.g. ACTIVE, INACTIVE)."""
        field = self.get_canonical_field(db, tenant_id, field_id)
        target_tenant = self._parse_tenant(tenant_id)

        old_val = {"status": field.status}
        field.status = status_val.upper()
        db.flush()

        audit_svc.log_action(
            db,
            tenant_id=target_tenant,
            entity_name="canonical_fields",
            entity_id=field.field_id,
            operation_type=OperationTypeEnum.UPDATE,
            old_value=old_val,
            new_value={"status": field.status},
            performed_by=performed_by,
            autocommit=False,
        )

        db.commit()
        db.refresh(field)
        return field


canonical_service = CanonicalService()
