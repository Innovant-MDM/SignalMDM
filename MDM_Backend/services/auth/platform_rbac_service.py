"""
signalmdm/services/platform_rbac_service.py
---------------------------------------------
Business logic for Platform RBAC:
  - Role management (create / read / update / delete)
  - Permission management (read / assign to role)
  - Platform user management (create / read / update / block / reset-password / delete)
"""

from __future__ import annotations

import uuid
from typing import List, Optional

import bcrypt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from db.models.platform_admin import PlatformAdmin
from db.models.platform_role  import PlatformRole, PlatformPermission, PlatformRolePermission
from schemas.platform_rbac_schema import (
    RoleCreate, RoleUpdate, RolePermissionUpdate,
    PlatformUserCreate, PlatformUserUpdate,
)


# ════════════════════════════════════════════════════════════
# Roles
# ════════════════════════════════════════════════════════════

def list_roles(db: Session) -> List[PlatformRole]:
    return db.query(PlatformRole).order_by(PlatformRole.created_at).all()


def get_role(db: Session, role_id: uuid.UUID) -> PlatformRole:
    role = db.get(PlatformRole, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found.")
    return role


def create_role(db: Session, data: RoleCreate) -> PlatformRole:
    existing = db.query(PlatformRole).filter(PlatformRole.role_key == data.role_key).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Role key '{data.role_key}' already exists.")
    role = PlatformRole(
        role_id=uuid.uuid4(),
        role_key=data.role_key,
        role_label=data.role_label,
        description=data.description,
        is_system=False,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def update_role(db: Session, role_id: uuid.UUID, data: RoleUpdate) -> PlatformRole:
    role = get_role(db, role_id)
    if data.role_label is not None:
        role.role_label = data.role_label
    if data.description is not None:
        role.description = data.description
    db.commit()
    db.refresh(role)
    return role


def delete_role(db: Session, role_id: uuid.UUID) -> None:
    role = get_role(db, role_id)
    if role.is_system:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="System roles cannot be deleted.")
    db.delete(role)
    db.commit()


# ════════════════════════════════════════════════════════════
# Permissions
# ════════════════════════════════════════════════════════════

def list_permissions(db: Session) -> List[PlatformPermission]:
    return db.query(PlatformPermission).order_by(
        PlatformPermission.screen_key, PlatformPermission.feature_key
    ).all()


def get_role_permissions(db: Session, role_id: uuid.UUID) -> List[PlatformPermission]:
    role = get_role(db, role_id)
    return [link.permission for link in role.permissions]


def set_role_permissions(db: Session, role_id: uuid.UUID, data: RolePermissionUpdate) -> List[PlatformPermission]:
    """Replace the full permission set for a role."""
    role = get_role(db, role_id)

    # Validate all permission_ids exist
    perms = db.query(PlatformPermission).filter(
        PlatformPermission.permission_id.in_(data.permission_ids)
    ).all()
    if len(perms) != len(data.permission_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="One or more permission IDs not found.")

    # Delete old links
    db.query(PlatformRolePermission).filter(
        PlatformRolePermission.role_id == role_id
    ).delete()

    # Insert new links
    for perm in perms:
        db.add(PlatformRolePermission(role_id=role.role_id, permission_id=perm.permission_id))

    db.commit()
    return perms


# ════════════════════════════════════════════════════════════
# Platform Users
# ════════════════════════════════════════════════════════════

def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(12)).decode()


def list_users(db: Session) -> List[PlatformAdmin]:
    return db.query(PlatformAdmin).options(joinedload(PlatformAdmin.role)).order_by(
        PlatformAdmin.created_at
    ).all()


def get_user(db: Session, admin_id: uuid.UUID) -> PlatformAdmin:
    user = db.query(PlatformAdmin).options(joinedload(PlatformAdmin.role)).get(admin_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


def create_user(
    db: Session,
    data: PlatformUserCreate,
    created_by: Optional[uuid.UUID] = None,
) -> PlatformAdmin:
    # Verify email uniqueness
    if db.query(PlatformAdmin).filter(PlatformAdmin.email == str(data.email)).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Email '{data.email}' is already registered.")

    # Verify role exists
    role = db.get(PlatformRole, data.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found.")

    admin = PlatformAdmin(
        admin_id=uuid.uuid4(),
        email=str(data.email),
        username=data.username,
        full_name=data.full_name,
        password_hash=_hash_password(data.password),
        role_id=data.role_id,
        is_active=data.is_active,
        is_blocked=False,
        two_fa_enabled=data.two_fa_enabled,
        two_fa_setup_complete=False,
        must_change_password=data.must_change_password,
        created_by=created_by,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def update_user(db: Session, admin_id: uuid.UUID, data: PlatformUserUpdate) -> PlatformAdmin:
    user = get_user(db, admin_id)

    if data.username is not None:
        user.username = data.username
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.role_id is not None:
        role = db.get(PlatformRole, data.role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found.")
        user.role_id = data.role_id
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.is_blocked is not None:
        user.is_blocked = data.is_blocked
    if data.two_fa_enabled is not None:
        user.two_fa_enabled = data.two_fa_enabled
        if not data.two_fa_enabled:
            user.two_fa_secret = None
            user.two_fa_setup_complete = False
    if data.must_change_password is not None:
        user.must_change_password = data.must_change_password

    db.commit()
    db.refresh(user)
    return user


def block_user(db: Session, admin_id: uuid.UUID) -> PlatformAdmin:
    user = get_user(db, admin_id)
    user.is_blocked = True
    db.commit()
    db.refresh(user)
    return user


def unblock_user(db: Session, admin_id: uuid.UUID) -> PlatformAdmin:
    user = get_user(db, admin_id)
    user.is_blocked = False
    db.commit()
    db.refresh(user)
    return user


def reset_password(db: Session, admin_id: uuid.UUID, new_password: str) -> PlatformAdmin:
    user = get_user(db, admin_id)
    user.password_hash = _hash_password(new_password)
    user.must_change_password = True
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, admin_id: uuid.UUID, requesting_admin_id: uuid.UUID) -> None:
    if admin_id == requesting_admin_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="You cannot delete your own account.")
    user = get_user(db, admin_id)
    db.delete(user)
    db.commit()


# ════════════════════════════════════════════════════════════
# Permission lookup helper (used by auth middleware)
# ════════════════════════════════════════════════════════════

def get_permissions_for_admin(db: Session, admin_id: uuid.UUID) -> set[str]:
    """
    Returns a set of 'screen_key.feature_key' strings for the given admin.
    Example: {'dashboard.view', 'sources.view', 'ingestion.start'}
    """
    user = db.query(PlatformAdmin).options(
        joinedload(PlatformAdmin.role).joinedload(PlatformRole.permissions).joinedload(
            PlatformRolePermission.permission
        )
    ).get(admin_id)

    if not user or not user.role:
        return set()

    return {
        f"{link.permission.screen_key}.{link.permission.feature_key}"
        for link in user.role.permissions
    }


platform_rbac_service = type("PlatformRBACService", (), {
    "list_roles":             staticmethod(list_roles),
    "get_role":               staticmethod(get_role),
    "create_role":            staticmethod(create_role),
    "update_role":            staticmethod(update_role),
    "delete_role":            staticmethod(delete_role),
    "list_permissions":       staticmethod(list_permissions),
    "get_role_permissions":   staticmethod(get_role_permissions),
    "set_role_permissions":   staticmethod(set_role_permissions),
    "list_users":             staticmethod(list_users),
    "get_user":               staticmethod(get_user),
    "create_user":            staticmethod(create_user),
    "update_user":            staticmethod(update_user),
    "block_user":             staticmethod(block_user),
    "unblock_user":           staticmethod(unblock_user),
    "reset_password":         staticmethod(reset_password),
    "delete_user":            staticmethod(delete_user),
    "get_permissions_for_admin": staticmethod(get_permissions_for_admin),
})()
