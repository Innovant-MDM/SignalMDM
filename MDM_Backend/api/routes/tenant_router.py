from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from db.sessions.database import get_db
from middleware.auth import get_current_active_user, is_super_admin
from schemas.tenant_schema import TenantRead, TenantCreate, TenantUpdate
from services.auth.tenant_service import tenant_service

router = APIRouter(
    prefix="/tenants",
    tags=["Tenants"],
    dependencies=[Depends(get_current_active_user), Depends(is_super_admin)]
)

@router.get("/", response_model=list[TenantRead])
def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    """List all tenants in the system (Platform Admin only)."""
    return tenant_service.list_tenants(db, skip=skip, limit=limit)

@router.post("/", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
def create_tenant(
    data: TenantCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Register a new root tenant (Platform Admin only)."""
    return tenant_service.create_tenant(db, data, performed_by=current_user.email)

@router.get("/{tenant_id}", response_model=TenantRead)
def get_tenant(tenant_id: UUID, db: Session = Depends(get_db)):
    """Fetch details of a specific tenant."""
    return tenant_service.get_tenant(db, tenant_id)

@router.patch("/{tenant_id}", response_model=TenantRead)
def update_tenant(
    tenant_id: UUID,
    data: TenantUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Update tenant configuration (Platform Admin only)."""
    return tenant_service.update_tenant(db, tenant_id, data, performed_by=current_user.email)
