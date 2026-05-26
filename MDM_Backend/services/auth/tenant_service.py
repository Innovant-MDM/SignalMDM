from __future__ import annotations

import uuid
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from db.models.tenant import Tenant
from schemas.tenant_schema import TenantCreate, TenantUpdate
from db.enums import OperationTypeEnum, StatusEnum
import services.audit.audit_service as audit_svc

class TenantService:
    def create_tenant(
        self,
        db: Session,
        data: TenantCreate,
        performed_by: str = "system"
    ) -> Tenant:
        """Create a new root tenant."""
        existing = db.query(Tenant).filter(Tenant.tenant_code == data.tenant_code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Tenant code '{data.tenant_code}' already exists."
            )

        tenant = Tenant(
            tenant_id=uuid.uuid4(),
            tenant_name=data.tenant_name,
            tenant_code=data.tenant_code,
            status=StatusEnum.ACTIVE
        )
        db.add(tenant)
        db.flush()

        # Audit log (self-attributed)
        audit_svc.log_action(
            db,
            tenant_id=tenant.tenant_id,
            entity_name="tenant",
            entity_id=tenant.tenant_id,
            operation_type=OperationTypeEnum.INSERT,
            new_value=data.model_dump(),
            performed_by=performed_by,
            autocommit=False
        )
        
        db.commit()
        db.refresh(tenant)
        return tenant

    def list_tenants(self, db: Session, skip: int = 0, limit: int = 100) -> list[Tenant]:
        return db.query(Tenant).offset(skip).limit(limit).all()

    def get_tenant(self, db: Session, tenant_id: uuid.UUID) -> Tenant:
        tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found."
            )
        return tenant

    def update_tenant(
        self,
        db: Session,
        tenant_id: uuid.UUID,
        data: TenantUpdate,
        performed_by: str = "system"
    ) -> Tenant:
        tenant = self.get_tenant(db, tenant_id)
        
        old_val = {k: getattr(tenant, k) for k in data.model_dump(exclude_unset=True)}
        
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(tenant, key, value)
            
        db.flush()
        
        audit_svc.log_action(
            db,
            tenant_id=tenant.tenant_id,
            entity_name="tenant",
            entity_id=tenant.tenant_id,
            operation_type=OperationTypeEnum.UPDATE,
            old_value=old_val,
            new_value=data.model_dump(exclude_unset=True),
            performed_by=performed_by,
            autocommit=False
        )
        
        db.commit()
        db.refresh(tenant)
        return tenant

tenant_service = TenantService()
