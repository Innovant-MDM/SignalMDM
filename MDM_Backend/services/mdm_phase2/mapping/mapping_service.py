from __future__ import annotations

import uuid
from typing import Optional, Union

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from db.models.source_system import SourceSystem
from db.models.mdm_phase2.canonical_field import CanonicalField
from db.models.mdm_phase2.field_mapping import FieldMapping
from schemas.mdm_phase2.field_mapping_schema import FieldMappingCreate
from db.enums import OperationTypeEnum
import services.audit.audit_service as audit_svc


class MappingService:

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

    def create_field_mapping(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        data: FieldMappingCreate,
        performed_by: str = "system",
    ) -> FieldMapping:
        """
        Creates a new field mapping configuration.
        Validates referenced canonical fields, source systems, and duplicate configurations.
        """
        target_tenant = self._parse_tenant(tenant_id)

        # 1. Validate Source System exists
        src = db.query(SourceSystem).filter(
            SourceSystem.source_system_id == data.source_system_id,
            SourceSystem.tenant_id == target_tenant,
        ).first()
        if not src:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source system with ID '{data.source_system_id}' not found.",
            )

        # 2. Validate Canonical Field exists
        cf = db.query(CanonicalField).filter(
            CanonicalField.field_id == data.canonical_field_id,
            CanonicalField.tenant_id == target_tenant,
        ).first()
        if not cf:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Canonical field with ID '{data.canonical_field_id}' not found.",
            )

        # 3. Prevent duplicate active mappings
        existing = db.query(FieldMapping).filter(
            FieldMapping.tenant_id == target_tenant,
            FieldMapping.source_system_id == data.source_system_id,
            FieldMapping.entity_type == data.entity_type.upper(),
            FieldMapping.source_field_name == data.source_field_name,
            FieldMapping.status == "ACTIVE",
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An active mapping for source field '{data.source_field_name}' already exists on this source system for '{data.entity_type}'.",
            )

        mapping = FieldMapping(
            mapping_id=uuid.uuid4(),
            tenant_id=target_tenant,
            source_system_id=data.source_system_id,
            entity_type=data.entity_type.upper(),
            source_field_name=data.source_field_name,
            canonical_field_id=data.canonical_field_id,
            transformation_rule_ids=data.transformation_rule_ids,
            standardization_rule_id=data.standardization_rule_id,
            status=data.status or "ACTIVE",
        )
        db.add(mapping)
        db.flush()

        # Audit Log
        audit_svc.log_action(
            db,
            tenant_id=target_tenant,
            entity_name="field_mappings",
            entity_id=mapping.mapping_id,
            operation_type=OperationTypeEnum.INSERT,
            new_value={
                "source_system_id": str(mapping.source_system_id),
                "entity_type": mapping.entity_type,
                "source_field_name": mapping.source_field_name,
                "canonical_field_id": str(mapping.canonical_field_id),
            },
            performed_by=performed_by,
            autocommit=False,
        )

        db.commit()
        db.refresh(mapping)
        return mapping

    def list_field_mappings(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        source_system_id: Optional[uuid.UUID] = None,
        entity_type: Optional[str] = None,
    ) -> list[FieldMapping]:
        """Fetch field mappings for the tenant, with optional source system or entity type filters."""
        target_tenant = self._parse_tenant(tenant_id)
        query = db.query(FieldMapping).filter(FieldMapping.tenant_id == target_tenant)
        if source_system_id:
            query = query.filter(FieldMapping.source_system_id == source_system_id)
        if entity_type:
            query = query.filter(FieldMapping.entity_type == entity_type.upper())
        return query.order_by(FieldMapping.source_field_name.asc()).all()

    def get_field_mapping(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        mapping_id: uuid.UUID,
    ) -> FieldMapping:
        """Fetch a single field mapping definition."""
        target_tenant = self._parse_tenant(tenant_id)
        mapping = db.query(FieldMapping).filter(
            FieldMapping.mapping_id == mapping_id,
            FieldMapping.tenant_id == target_tenant,
        ).first()
        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Field mapping configuration not found.",
            )
        return mapping

    def update_field_mapping(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        mapping_id: uuid.UUID,
        data: FieldMappingCreate,
        performed_by: str = "system",
    ) -> FieldMapping:
        """Update an existing field mapping configuration."""
        mapping = self.get_field_mapping(db, tenant_id, mapping_id)
        target_tenant = self._parse_tenant(tenant_id)

        old_val = {
            "canonical_field_id": str(mapping.canonical_field_id),
            "transformation_rule_ids": [str(rid) for rid in mapping.transformation_rule_ids],
            "standardization_rule_id": str(mapping.standardization_rule_id) if mapping.standardization_rule_id else None,
            "status": mapping.status,
        }

        # Validate Canonical Field existence if updated
        if data.canonical_field_id != mapping.canonical_field_id:
            cf = db.query(CanonicalField).filter(
                CanonicalField.field_id == data.canonical_field_id,
                CanonicalField.tenant_id == target_tenant,
            ).first()
            if not cf:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Canonical field with ID '{data.canonical_field_id}' not found.",
                )
            mapping.canonical_field_id = data.canonical_field_id

        mapping.transformation_rule_ids = data.transformation_rule_ids
        mapping.standardization_rule_id = data.standardization_rule_id
        if data.status:
            mapping.status = data.status.upper()

        db.flush()

        audit_svc.log_action(
            db,
            tenant_id=target_tenant,
            entity_name="field_mappings",
            entity_id=mapping.mapping_id,
            operation_type=OperationTypeEnum.UPDATE,
            old_value=old_val,
            new_value={
                "canonical_field_id": str(mapping.canonical_field_id),
                "transformation_rule_ids": [str(rid) for rid in mapping.transformation_rule_ids],
                "standardization_rule_id": str(mapping.standardization_rule_id) if mapping.standardization_rule_id else None,
                "status": mapping.status,
            },
            performed_by=performed_by,
            autocommit=False,
        )

        db.commit()
        db.refresh(mapping)
        return mapping

    def delete_field_mapping(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        mapping_id: uuid.UUID,
        performed_by: str = "system",
    ) -> dict:
        """Deletes/Removes a field mapping configuration."""
        mapping = self.get_field_mapping(db, tenant_id, mapping_id)
        target_tenant = self._parse_tenant(tenant_id)

        old_val = {
            "source_field_name": mapping.source_field_name,
            "entity_type": mapping.entity_type,
        }

        db.delete(mapping)
        db.flush()

        audit_svc.log_action(
            db,
            tenant_id=target_tenant,
            entity_name="field_mappings",
            entity_id=mapping_id,
            operation_type=OperationTypeEnum.DELETE,
            old_value=old_val,
            performed_by=performed_by,
            autocommit=False,
        )

        db.commit()
        return {"success": True, "message": "Field mapping deleted successfully."}


mapping_service = MappingService()
