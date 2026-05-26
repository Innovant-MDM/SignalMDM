"""
signalmdm/services/source_service.py
--------------------------------------
Business logic for SourceSystem CRUD.

Rules:
  • `source_code` must be unique per tenant (slug: a-z0-9_-).
  • Every create/update emits an audit log entry.
  • All queries MUST filter by `tenant_id`.

Security:
  • source_code is slug-validated (allowlist characters only).
  • source_name is length-limited and injection-scanned.
  • config_json depth, key count, and value content are validated.
  • skip/limit are bounds-checked.
"""

from __future__ import annotations

import uuid
from typing import Optional, Union

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from db.models.source_system import SourceSystem
from schemas.source_schema import SourceSystemCreate
from db.enums import OperationTypeEnum, StatusEnum
from utils.sanitize import (
    sanitize_slug,
    sanitize_string,
    sanitize_config_json,
)
import services.audit.audit_service as audit_svc


class SourceService:
    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------
    def _parse_tenant(self, tenant_id: Union[str, uuid.UUID]) -> Optional[uuid.UUID]:
        """Convert string/uuid to UUID object. Returns None if 'platform'."""
        if tenant_id == "platform":
            return None
        if isinstance(tenant_id, uuid.UUID):
            return tenant_id
        try:
            return uuid.UUID(str(tenant_id))
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant_id format — must be a valid UUID.",
            )

    def _sanitize_create_input(self, data: SourceSystemCreate) -> SourceSystemCreate:
        """
        Validate and sanitize all user-supplied fields on a source registration.

        Raises HTTPException(422) on any violation so the response is consistent
        with Pydantic validation errors.
        """
        errors: list[str] = []

        try:
            clean_code = sanitize_slug(data.source_code, "source_code")
        except ValueError as e:
            errors.append(str(e))
            clean_code = data.source_code  # keep original so we can continue collecting errors

        try:
            clean_name = sanitize_string(
                data.source_name, "source_name", max_length=200, required=True
            )
        except ValueError as e:
            errors.append(str(e))
            clean_name = data.source_name

        try:
            clean_config = sanitize_config_json(data.config_json)
        except ValueError as e:
            errors.append(str(e))
            clean_config = data.config_json or {}

        if errors:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"message": "Input validation failed.", "errors": errors},
            )

        # Return a copy with sanitized values
        return SourceSystemCreate(
            source_name=clean_name,
            source_code=clean_code,
            source_type=data.source_type,
            connection_type=data.connection_type,
            config_json=clean_config,
        )

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_source(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        data: SourceSystemCreate,
        performed_by: str = "system",
    ) -> SourceSystem:
        """
        Register a new source system.

        Raises 409 if `source_code` already exists for this tenant.
        Raises 422 if input validation fails.
        """
        target_uuid = self._parse_tenant(tenant_id)
        if target_uuid is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A specific tenant_id is required for source registration.",
            )

        # Sanitize all inputs before any DB interaction
        clean_data = self._sanitize_create_input(data)

        existing = (
            db.query(SourceSystem)
            .filter(
                SourceSystem.tenant_id == target_uuid,
                SourceSystem.source_code == clean_data.source_code,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A source with code '{clean_data.source_code}' already exists for this tenant.",
            )

        source = SourceSystem(
            source_system_id=uuid.uuid4(),
            tenant_id=target_uuid,
            source_name=clean_data.source_name,
            source_code=clean_data.source_code,
            source_type=clean_data.source_type,
            connection_type=clean_data.connection_type,
            config_json=clean_data.config_json,
        )
        db.add(source)
        db.flush()

        audit_svc.log_action(
            db,
            tenant_id=target_uuid,
            entity_name="source_systems",
            entity_id=source.source_system_id,
            operation_type=OperationTypeEnum.INSERT,
            new_value={
                "source_code":      source.source_code,
                "source_type":      source.source_type,
                "connection_type":  source.connection_type,
            },
            performed_by=performed_by,
            autocommit=False,
        )

        db.commit()
        db.refresh(source)
        return source

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def list_sources(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        skip: int = 0,
        limit: int = 100,
    ) -> list[SourceSystem]:
        """Return all active source systems for the tenant (or all if platform)."""
        # Bounds-check pagination
        skip  = max(0, int(skip))
        limit = max(1, min(int(limit), 500))

        target_uuid = self._parse_tenant(tenant_id)
        query = db.query(SourceSystem)
        if target_uuid:
            query = query.filter(SourceSystem.tenant_id == target_uuid)

        return (
            query.order_by(SourceSystem.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_source(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        source_system_id: uuid.UUID,
    ) -> SourceSystem:
        """Fetch a single source system; raise 404 if not found for this tenant."""
        target_uuid = self._parse_tenant(tenant_id)
        query = db.query(SourceSystem).filter(
            SourceSystem.source_system_id == source_system_id
        )
        if target_uuid:
            query = query.filter(SourceSystem.tenant_id == target_uuid)

        source = query.first()
        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source system not found.",
            )
        return source

    # ------------------------------------------------------------------
    # Deactivate
    # ------------------------------------------------------------------

    def deactivate_source(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        source_system_id: uuid.UUID,
        performed_by: str = "system",
    ) -> SourceSystem:
        """Soft-deactivate a source system (is_active = False)."""
        source = self.get_source(db, tenant_id, source_system_id)
        target_uuid = self._parse_tenant(tenant_id) or source.tenant_id

        old_val = {"is_active": source.is_active, "status": source.status}
        source.is_active = False
        source.status = StatusEnum.DEACTIVATED.value
        db.flush()

        audit_svc.log_action(
            db,
            tenant_id=target_uuid,
            entity_name="source_systems",
            entity_id=source.source_system_id,
            operation_type=OperationTypeEnum.UPDATE,
            old_value=old_val,
            new_value={"is_active": False, "status": "DEACTIVATED"},
            performed_by=performed_by,
            autocommit=False,
        )

        db.commit()
        db.refresh(source)
        return source

    # ------------------------------------------------------------------
    # Update Status
    # ------------------------------------------------------------------

    def update_source_status(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        source_system_id: uuid.UUID,
        new_status: StatusEnum,
        performed_by: str = "system",
    ) -> SourceSystem:
        """Update the status of a source system (ACTIVE, SUSPENDED, ARCHIVED, etc.)."""
        source = self.get_source(db, tenant_id, source_system_id)
        target_uuid = self._parse_tenant(tenant_id) or source.tenant_id

        old_val = {"status": source.status, "is_active": source.is_active}

        if new_status == StatusEnum.DEACTIVATED:
            source.is_active = False
        elif new_status == StatusEnum.ACTIVE:
            source.is_active = True

        source.status = new_status.value
        db.flush()

        audit_svc.log_action(
            db,
            tenant_id=target_uuid,
            entity_name="source_systems",
            entity_id=source.source_system_id,
            operation_type=OperationTypeEnum.UPDATE,
            old_value=old_val,
            new_value={"status": source.status, "is_active": source.is_active},
            performed_by=performed_by,
            autocommit=False,
        )

        db.commit()
        db.refresh(source)
        return source


# Singleton
source_service = SourceService()
