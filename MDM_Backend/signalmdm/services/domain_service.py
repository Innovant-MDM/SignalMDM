"""
signalmdm/services/domain_service.py
--------------------------------------
Business logic for Domain CRUD.

Rules:
  • `domain_name` must be unique per tenant.
  • Every create/update/delete emits an audit log entry.
  • All queries MUST filter by `tenant_id`.

Security:
  • domain_name and description are sanitized via sanitize_string.
  • skip/limit are bounds-checked.
"""

from __future__ import annotations

import uuid
from typing import Optional, Union

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from signalmdm.models.domain import Domain
from signalmdm.schemas.domain_schema import DomainCreate, DomainUpdate
from signalmdm.enums import OperationTypeEnum
from signalmdm.utils.sanitize import sanitize_string
import signalmdm.services.audit_service as audit_svc


class DomainService:
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

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------
    def create_domain(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        data: DomainCreate,
        performed_by: str = "system",
    ) -> Domain:
        """
        Create a new domain for the tenant.

        Raises 409 if `domain_name` already exists for this tenant.
        Raises 422 if input validation fails.
        """
        target_uuid = self._parse_tenant(tenant_id)
        if target_uuid is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A specific tenant_id is required for domain creation.",
            )

        # Sanitize inputs
        clean_name = sanitize_string(
            data.domain_name, "domain_name", max_length=100, required=True
        )
        clean_desc = sanitize_string(
            data.description, "description", max_length=2000, required=False
        ) if data.description else None

        # Check for duplicate domain name within tenant
        existing = (
            db.query(Domain)
            .filter(
                Domain.tenant_id == target_uuid,
                Domain.domain_name == clean_name,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A domain with name '{clean_name}' already exists for this tenant.",
            )

        domain = Domain(
            id=uuid.uuid4(),
            tenant_id=target_uuid,
            domain_name=clean_name,
            description=clean_desc,
            status=data.status or "ACTIVE",
        )
        db.add(domain)
        db.flush()

        audit_svc.log_action(
            db,
            tenant_id=target_uuid,
            entity_name="domains",
            entity_id=domain.id,
            operation_type=OperationTypeEnum.INSERT,
            new_value={
                "domain_name": domain.domain_name,
                "description": domain.description,
                "status": domain.status,
            },
            performed_by=performed_by,
            autocommit=False,
        )

        db.commit()
        db.refresh(domain)
        return domain

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    def list_domains(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        skip: int = 0,
        limit: int = 100,
    ) -> list[Domain]:
        """Return all domains for the tenant (or all if platform)."""
        skip = max(0, int(skip))
        limit = max(1, min(int(limit), 500))

        target_uuid = self._parse_tenant(tenant_id)
        query = db.query(Domain)
        if target_uuid:
            query = query.filter(Domain.tenant_id == target_uuid)

        return (
            query.order_by(Domain.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_domain(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        domain_id: uuid.UUID,
    ) -> Domain:
        """Fetch a single domain; raise 404 if not found for this tenant."""
        target_uuid = self._parse_tenant(tenant_id)
        query = db.query(Domain).filter(Domain.id == domain_id)
        if target_uuid:
            query = query.filter(Domain.tenant_id == target_uuid)

        domain = query.first()
        if not domain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Domain not found.",
            )
        return domain

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update_domain(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        domain_id: uuid.UUID,
        data: DomainUpdate,
        performed_by: str = "system",
    ) -> Domain:
        """Update a domain's fields."""
        domain = self.get_domain(db, tenant_id, domain_id)
        target_uuid = self._parse_tenant(tenant_id) or domain.tenant_id

        old_val = {
            "domain_name": domain.domain_name,
            "description": domain.description,
            "status": domain.status,
        }

        if data.domain_name is not None:
            clean_name = sanitize_string(
                data.domain_name, "domain_name", max_length=100, required=True
            )
            # Check uniqueness within tenant for the new name
            existing = (
                db.query(Domain)
                .filter(
                    Domain.tenant_id == target_uuid,
                    Domain.domain_name == clean_name,
                    Domain.id != domain_id,
                )
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A domain with name '{clean_name}' already exists for this tenant.",
                )
            domain.domain_name = clean_name

        if data.description is not None:
            domain.description = sanitize_string(
                data.description, "description", max_length=2000, required=False
            )

        if data.status is not None:
            domain.status = data.status

        db.flush()

        audit_svc.log_action(
            db,
            tenant_id=target_uuid,
            entity_name="domains",
            entity_id=domain.id,
            operation_type=OperationTypeEnum.UPDATE,
            old_value=old_val,
            new_value={
                "domain_name": domain.domain_name,
                "description": domain.description,
                "status": domain.status,
            },
            performed_by=performed_by,
            autocommit=False,
        )

        db.commit()
        db.refresh(domain)
        return domain

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------
    def delete_domain(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        domain_id: uuid.UUID,
        performed_by: str = "system",
    ) -> Domain:
        """Soft-delete a domain by setting status to DEACTIVATED."""
        domain = self.get_domain(db, tenant_id, domain_id)
        target_uuid = self._parse_tenant(tenant_id) or domain.tenant_id

        old_val = {"status": domain.status}
        domain.status = "DEACTIVATED"
        db.flush()

        audit_svc.log_action(
            db,
            tenant_id=target_uuid,
            entity_name="domains",
            entity_id=domain.id,
            operation_type=OperationTypeEnum.DELETE,
            old_value=old_val,
            new_value={"status": "DEACTIVATED"},
            performed_by=performed_by,
            autocommit=False,
        )

        db.commit()
        db.refresh(domain)
        return domain


# Singleton
domain_service = DomainService()
