r"""
MDM_Backend\signalmdm\models\platform_role.py
----------------------------------
Platform-level RBAC: roles + permissions for high-level stakeholders.
Separate from tenant-scoped RBAC (models/rbac.py).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base

if TYPE_CHECKING:
    from db.models.platform_admin import PlatformAdmin


class PlatformRole(Base):
    """
    A named role for platform-level administrators.
    System roles (is_system=True) cannot be deleted.
    """
    __tablename__ = "platform_role"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    role_key: Mapped[str] = mapped_column(
        String(80), nullable=False, unique=True,
        comment="Machine-readable key, e.g. 'super_admin', 'data_architect'."
    )
    role_label: Mapped[str] = mapped_column(
        String(150), nullable=False, comment="Human-readable display name."
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="System roles cannot be deleted."
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── Relationships ──────────────────────────────────────────
    admins: Mapped[list["PlatformAdmin"]] = relationship(back_populates="role")
    permissions: Mapped[list["PlatformRolePermission"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PlatformRole key={self.role_key!r}>"


class PlatformPermission(Base):
    """
    A granular permission defined by (screen_key, feature_key).
    Example: screen_key='ingestion', feature_key='start'.
    """
    __tablename__ = "platform_permission"

    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    screen_key: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Identifies the frontend screen."
    )
    feature_key: Mapped[str] = mapped_column(
        String(150), nullable=False, comment="Identifies a specific action/feature within the screen."
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    role_links: Mapped[list["PlatformRolePermission"]] = relationship(
        back_populates="permission", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PlatformPermission {self.screen_key}.{self.feature_key}>"


class PlatformRolePermission(Base):
    """Join table: PlatformRole ↔ PlatformPermission."""
    __tablename__ = "platform_role_permission"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        __import__("sqlalchemy").ForeignKey("platform_role.role_id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        __import__("sqlalchemy").ForeignKey("platform_permission.permission_id", ondelete="CASCADE"),
        primary_key=True,
    )

    role: Mapped["PlatformRole"]       = relationship(back_populates="permissions")
    permission: Mapped["PlatformPermission"] = relationship(back_populates="role_links")
