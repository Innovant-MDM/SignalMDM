"""
signalmdm/routers/domain_router.py
-------------------------------------
API endpoints for Domain management.

Security:
  All endpoints require a valid encrypted JWT (via require_auth).
  tenant_id is extracted from the verified JWT — NOT a raw header.
  DELETE is restricted to admin role.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from db.sessions.database import get_db
from schemas.domain_schema import DomainCreate, DomainUpdate, DomainRead
from schemas.common import ok
from services.source.domain_service import domain_service
from middleware.auth import TokenPayload, require_auth, require_admin

router = APIRouter(prefix="/domains", tags=["Domains"])


@router.post(
    "/",
    summary="Create a new domain",
    status_code=status.HTTP_201_CREATED,
)
def create_domain(
    body: DomainCreate,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """
    Create a new domain for the authenticated tenant.

    - `domain_name` must be unique per tenant.
    - `tenant_id`:
        - For standard users, it comes from the verified JWT.
        - For SuperAdmins (platform tenant), it can be overridden via `X-Tenant-ID` header.
    """
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    domain = domain_service.create_domain(
        db,
        tenant_id=target_tenant,
        data=body,
        performed_by=auth.user_id,
    )
    return ok(
        data=DomainRead.model_validate(domain).model_dump(),
        message="Domain created successfully.",
    )


@router.get(
    "/",
    summary="List all domains for the authenticated tenant",
)
def list_domains(
    skip: int = 0,
    limit: int = 50,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """Return all domains scoped to the authenticated tenant."""
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    domains = domain_service.list_domains(db, tenant_id=target_tenant, skip=skip, limit=limit)
    return ok(
        data=[DomainRead.model_validate(d).model_dump() for d in domains],
        message=f"{len(domains)} domain(s) found.",
    )


@router.get(
    "/{domain_id}",
    summary="Get a domain by ID",
)
def get_domain(
    domain_id: uuid.UUID,
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """Fetch a single domain scoped to the authenticated tenant."""
    domain = domain_service.get_domain(db, tenant_id=auth.tenant_id, domain_id=domain_id)
    return ok(data=DomainRead.model_validate(domain).model_dump())


@router.patch(
    "/{domain_id}",
    summary="Update a domain",
)
def update_domain(
    domain_id: uuid.UUID,
    body: DomainUpdate,
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """Update a domain's name, description, or status."""
    domain = domain_service.update_domain(
        db,
        tenant_id=auth.tenant_id,
        domain_id=domain_id,
        data=body,
        performed_by=auth.user_id,
    )
    return ok(
        data=DomainRead.model_validate(domain).model_dump(),
        message="Domain updated successfully.",
    )


@router.delete(
    "/{domain_id}",
    summary="Deactivate a domain (admin only)",
)
def delete_domain(
    domain_id: uuid.UUID,
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_admin),  # admin only
):
    """Soft-deactivate a domain (status → DEACTIVATED). Restricted to admin role."""
    domain = domain_service.delete_domain(
        db,
        tenant_id=auth.tenant_id,
        domain_id=domain_id,
        performed_by=auth.user_id,
    )
    return ok(
        data=DomainRead.model_validate(domain).model_dump(),
        message="Domain deactivated.",
    )
