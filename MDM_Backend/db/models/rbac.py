"""
models/rbac.py
--------------
Role-Based Access Control models:
    AppUser, Role, Permission, RolePermission, UserRole
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, String, Text,
    Table, Column, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base
from db.enums import StatusEnum


# ---------------------------------------------------------------------------
# Association tables (pure junction — no extra columns)
# ---------------------------------------------------------------------------

role_permission_table = Table(
    "role_permission",
    Base.metadata,
    Column(
        "role_id",
        UUID(as_uuid=True),
        ForeignKey("role.role_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        UUID(as_uuid=True),
        ForeignKey("permission.permission_id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

user_role_table = Table(
    "user_role",
    Base.metadata,
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("app_user.user_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        UUID(as_uuid=True),
        ForeignKey("role.role_id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


# ---------------------------------------------------------------------------
# AppUser
# ---------------------------------------------------------------------------
class AppUser(Base):
    """
    Platform user scoped to a specific tenant.

    password_hash must contain a bcrypt / Argon2 digest — never plain text.
    is_deleted supports soft-delete; authentication must reject deleted users.
    """

    __tablename__ = "app_user"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenant_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        nullable=False,
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    password_hash: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="bcrypt / Argon2 hash. NEVER store plaintext.",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=StatusEnum.ACTIVE,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    tenant: Mapped["Tenant"] = relationship(back_populates="app_users")  # noqa: F821
    roles:  Mapped[list["Role"]] = relationship(
        secondary=user_role_table,
        back_populates="users",
    )
    steward_governance: Mapped[list["EntityGovernance"]] = relationship(  # noqa: F821
        back_populates="steward",
        foreign_keys="EntityGovernance.steward_id",
    )

    def __repr__(self) -> str:
        return f"<AppUser username={self.username!r} tenant={self.tenant_id}>"


# ---------------------------------------------------------------------------
# Role
# ---------------------------------------------------------------------------
class Role(Base):
    """Named role scoped to a tenant."""

    __tablename__ = "role"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenant_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    role_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    role_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    tenant:      Mapped["Tenant"]          = relationship(back_populates="roles")    # noqa: F821
    permissions: Mapped[list["Permission"]] = relationship(
        secondary=role_permission_table,
        back_populates="roles",
    )
    users: Mapped[list["AppUser"]] = relationship(
        secondary=user_role_table,
        back_populates="roles",
    )

    def __repr__(self) -> str:
        return f"<Role name={self.role_name!r}>"


# ---------------------------------------------------------------------------
# Permission
# ---------------------------------------------------------------------------
class Permission(Base):
    """Atomic permission representing a single action on a resource."""

    __tablename__ = "permission"

    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    permission_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
        comment="Convention: <resource>:<action> e.g. entity:read",
    )
    permission_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    roles: Mapped[list["Role"]] = relationship(
        secondary=role_permission_table,
        back_populates="permissions",
    )

    def __repr__(self) -> str:
        return f"<Permission name={self.permission_name!r}>"
