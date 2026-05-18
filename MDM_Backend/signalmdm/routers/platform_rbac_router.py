"""
signalmdm/routers/platform_rbac_router.py
-------------------------------------------
Platform RBAC endpoints.

All endpoints require:
  - Valid accessToken cookie (require_auth)
  - tenant_id == 'platform' (is_super_admin OR is_admin depending on action)

Routes:
  GET    /platform/roles                   — list roles        (admin+)
  POST   /platform/roles                   — create role       (super_admin only)
  PATCH  /platform/roles/{role_id}         — update role       (super_admin only)
  DELETE /platform/roles/{role_id}         — delete role       (super_admin only)
  GET    /platform/permissions             — list all perms    (admin+)
  GET    /platform/roles/{role_id}/permissions
  PUT    /platform/roles/{role_id}/permissions — set perms     (super_admin only)
  GET    /platform/users                   — list users        (admin+)
  POST   /platform/users                   — create user       (admin+)
  GET    /platform/users/{admin_id}        — get user          (admin+)
  PATCH  /platform/users/{admin_id}        — update user       (admin+)
  POST   /platform/users/{admin_id}/block  — block user        (admin+)
  POST   /platform/users/{admin_id}/unblock
  POST   /platform/users/{admin_id}/reset-password
  DELETE /platform/users/{admin_id}        — delete user       (super_admin only)
"""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from signalmdm.database import get_db
from signalmdm.middleware.auth import require_auth, is_super_admin, TokenPayload
from signalmdm.schemas.platform_rbac_schema import (
    RoleRead, RoleCreate, RoleUpdate,
    PermissionRead, RolePermissionUpdate,
    PlatformUserRead, PlatformUserCreate, PlatformUserUpdate, PlatformUserResetPassword,
)
from signalmdm.services.platform_rbac_service import platform_rbac_service as svc

router = APIRouter(prefix="/platform", tags=["Platform RBAC"])


def _admin_required(auth: TokenPayload = Depends(require_auth)) -> TokenPayload:
    """Platform-level access (super_admin or admin)."""
    if auth.tenant_id != "platform":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Platform-level access required.")
    return auth


# ─── My permissions (current session) ────────────────────────

@router.get("/my-permissions")
def my_permissions(
    auth: TokenPayload = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    """
    Return the screen_key → [feature_key, ...] map for the calling admin.
    Non-platform admins get an empty map (they are tenant-scoped).
    """
    if auth.tenant_id != "platform":
        return {"permissions": {}}

    import uuid as _uuid
    from signalmdm.models.platform_admin import PlatformAdmin
    admin = db.query(PlatformAdmin).filter(
        PlatformAdmin.admin_id == _uuid.UUID(auth.user_id)
    ).first()

    if not admin or not admin.role_id:
        return {"permissions": {}}

    perms = svc.get_role_permissions(db, admin.role_id)
    perm_map: dict[str, list[str]] = {}
    for p in perms:
        perm_map.setdefault(p.screen_key, []).append(p.feature_key)

    return {"permissions": perm_map}


# ─── Roles ────────────────────────────────────────────────────

@router.get("/roles", response_model=List[RoleRead])
def list_roles(auth: TokenPayload = Depends(_admin_required), db: Session = Depends(get_db)):
    return svc.list_roles(db)


@router.post("/roles", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
def create_role(
    data: RoleCreate,
    auth: TokenPayload = Depends(is_super_admin),
    db: Session = Depends(get_db),
):
    return svc.create_role(db, data)


@router.patch("/roles/{role_id}", response_model=RoleRead)
def update_role(
    role_id: uuid.UUID,
    data: RoleUpdate,
    auth: TokenPayload = Depends(is_super_admin),
    db: Session = Depends(get_db),
):
    return svc.update_role(db, role_id, data)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: uuid.UUID,
    auth: TokenPayload = Depends(is_super_admin),
    db: Session = Depends(get_db),
):
    svc.delete_role(db, role_id)


# ─── Permissions ──────────────────────────────────────────────

@router.get("/permissions", response_model=List[PermissionRead])
def list_permissions(auth: TokenPayload = Depends(_admin_required), db: Session = Depends(get_db)):
    return svc.list_permissions(db)


@router.get("/roles/{role_id}/permissions", response_model=List[PermissionRead])
def get_role_permissions(
    role_id: uuid.UUID,
    auth: TokenPayload = Depends(_admin_required),
    db: Session = Depends(get_db),
):
    return svc.get_role_permissions(db, role_id)


@router.put("/roles/{role_id}/permissions", response_model=List[PermissionRead])
def set_role_permissions(
    role_id: uuid.UUID,
    data: RolePermissionUpdate,
    auth: TokenPayload = Depends(is_super_admin),
    db: Session = Depends(get_db),
):
    return svc.set_role_permissions(db, role_id, data)


# ─── Platform Users ───────────────────────────────────────────

@router.get("/users", response_model=List[PlatformUserRead])
def list_users(auth: TokenPayload = Depends(_admin_required), db: Session = Depends(get_db)):
    users = svc.list_users(db)
    result = []
    for u in users:
        r = PlatformUserRead.model_validate(u)
        if u.role:
            r.role_key   = u.role.role_key
            r.role_label = u.role.role_label
        result.append(r)
    return result


@router.post("/users", response_model=PlatformUserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    data: PlatformUserCreate,
    auth: TokenPayload = Depends(_admin_required),
    db: Session = Depends(get_db),
):
    user = svc.create_user(db, data, created_by=uuid.UUID(auth.user_id))
    r = PlatformUserRead.model_validate(user)
    if user.role:
        r.role_key   = user.role.role_key
        r.role_label = user.role.role_label
    return r


@router.get("/users/{admin_id}", response_model=PlatformUserRead)
def get_user(
    admin_id: uuid.UUID,
    auth: TokenPayload = Depends(_admin_required),
    db: Session = Depends(get_db),
):
    user = svc.get_user(db, admin_id)
    r = PlatformUserRead.model_validate(user)
    if user.role:
        r.role_key   = user.role.role_key
        r.role_label = user.role.role_label
    return r


@router.patch("/users/{admin_id}", response_model=PlatformUserRead)
def update_user(
    admin_id: uuid.UUID,
    data: PlatformUserUpdate,
    auth: TokenPayload = Depends(_admin_required),
    db: Session = Depends(get_db),
):
    user = svc.update_user(db, admin_id, data)
    r = PlatformUserRead.model_validate(user)
    if user.role:
        r.role_key   = user.role.role_key
        r.role_label = user.role.role_label
    return r


@router.post("/users/{admin_id}/block", response_model=PlatformUserRead)
def block_user(
    admin_id: uuid.UUID,
    auth: TokenPayload = Depends(_admin_required),
    db: Session = Depends(get_db),
):
    return PlatformUserRead.model_validate(svc.block_user(db, admin_id))


@router.post("/users/{admin_id}/unblock", response_model=PlatformUserRead)
def unblock_user(
    admin_id: uuid.UUID,
    auth: TokenPayload = Depends(_admin_required),
    db: Session = Depends(get_db),
):
    return PlatformUserRead.model_validate(svc.unblock_user(db, admin_id))


@router.post("/users/{admin_id}/reset-password", response_model=PlatformUserRead)
def reset_password(
    admin_id: uuid.UUID,
    data: PlatformUserResetPassword,
    auth: TokenPayload = Depends(_admin_required),
    db: Session = Depends(get_db),
):
    return PlatformUserRead.model_validate(
        svc.reset_password(db, admin_id, data.new_password)
    )


@router.delete("/users/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    admin_id: uuid.UUID,
    auth: TokenPayload = Depends(is_super_admin),
    db: Session = Depends(get_db),
):
    svc.delete_user(db, admin_id, requesting_admin_id=uuid.UUID(auth.user_id))
