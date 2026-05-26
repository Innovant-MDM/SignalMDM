"""
signalmdm/schemas/platform_rbac_schema.py
-------------------------------------------
Pydantic v2 schemas for Platform RBAC endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ─── Roles ────────────────────────────────────────────────────

class RoleRead(BaseModel):
    role_id:     uuid.UUID
    role_key:    str
    role_label:  str
    description: Optional[str] = None
    is_system:   bool
    created_at:  datetime

    model_config = ConfigDict(from_attributes=True)


class RoleCreate(BaseModel):
    role_key:    str   = Field(..., min_length=2, max_length=80, pattern=r"^[a-z_]+$")
    role_label:  str   = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None


class RoleUpdate(BaseModel):
    role_label:  Optional[str] = None
    description: Optional[str] = None


# ─── Permissions ──────────────────────────────────────────────

class PermissionRead(BaseModel):
    permission_id: uuid.UUID
    screen_key:    str
    feature_key:   str
    label:         str
    description:   Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RolePermissionUpdate(BaseModel):
    """Replace ALL permissions for a role with this list."""
    permission_ids: List[uuid.UUID]


# ─── Platform Users (PlatformAdmin) ───────────────────────────

class PlatformUserRead(BaseModel):
    admin_id:             uuid.UUID
    email:                str
    username:             str
    full_name:            Optional[str]
    role_id:              Optional[uuid.UUID]
    role_key:             Optional[str] = None       # populated by service
    role_label:           Optional[str] = None
    is_active:            bool
    is_blocked:           bool
    must_change_password: bool
    two_fa_enabled:       bool
    two_fa_setup_complete: bool
    last_login_at:        Optional[datetime]
    created_at:           datetime
    created_by:           Optional[uuid.UUID]

    model_config = ConfigDict(from_attributes=True)


class PlatformUserCreate(BaseModel):
    email:                EmailStr
    username:             str   = Field(..., min_length=2, max_length=150)
    full_name:            Optional[str] = None
    password:             str   = Field(..., min_length=8)
    role_id:              uuid.UUID
    is_active:            bool  = True
    two_fa_enabled:       bool  = False
    must_change_password: bool  = True


class PlatformUserUpdate(BaseModel):
    username:             Optional[str]       = None
    full_name:            Optional[str]       = None
    role_id:              Optional[uuid.UUID] = None
    is_active:            Optional[bool]      = None
    is_blocked:           Optional[bool]      = None
    two_fa_enabled:       Optional[bool]      = None
    must_change_password: Optional[bool]      = None


class PlatformUserResetPassword(BaseModel):
    new_password: str = Field(..., min_length=8)
