"""
signalmdm/models/platform_admin.py
------------------------------------
SQLAlchemy ORM model for the `platform_admin` table.

Platform-level super-admin accounts — NOT scoped to any tenant.
Separate from AppUser (which requires a tenant_id FK).

Fields:
    admin_id             UUID PK
    email                unique login identifier
    username             display name
    password_hash        bcrypt hash (cost ≥ 12)
    is_active            soft-disable without deletion
    two_fa_enabled       whether TOTP 2FA is turned on for this admin
    two_fa_secret        base32 TOTP secret (null until setup)
    two_fa_setup_complete  True after first successful TOTP verification
    last_login_at        updated on every successful login
    created_at / updated_at  audit timestamps
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base

if TYPE_CHECKING:
    from db.models.platform_role import PlatformRole


class PlatformAdmin(Base):
    """
    Platform-wide super-admin.

    Authentication rules enforced at the service layer:
      • Password must be bcrypt-hashed before storage.
      • Two-FA flow: generate TOTP secret → verify first code →
        set two_fa_setup_complete = True.
      • is_active = False → login rejected even with valid credentials.
    """

    __tablename__ = "platform_admin"

    # ── Primary key ──────────────────────────────────────────
    admin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Identity ─────────────────────────────────────────────
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Login email — globally unique across all platform admins.",
    )
    username: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        comment="Display name shown in the UI.",
    )

    # ── Credentials ───────────────────────────────────────────
    password_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="bcrypt hash (cost ≥ 12). NEVER store plaintext.",
    )

    # ── Status ───────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="False = account disabled. Login rejected even with correct credentials.",
    )

    # ── Two-Factor Authentication ─────────────────────────────
    two_fa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether TOTP 2FA is required for this admin.",
    )
    two_fa_secret: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Base32-encoded TOTP secret. NULL until 2FA setup is completed.",
    )
    two_fa_setup_complete: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True after the admin has scanned QR and verified first TOTP code.",
    )

    # ── Audit timestamps ──────────────────────────────────────
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Updated on every successful authentication.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ── Platform RBAC ─────────────────────────────────────────
    role_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_role.role_id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to platform_role — determines permissions.",
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="Full display name."
    )
    is_blocked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="Blocked users cannot log in even with correct credentials."
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="Force password reset on next login."
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_admin.admin_id", ondelete="SET NULL"),
        nullable=True,
        comment="Which platform admin created this account."
    )

    # ── Relationships ──────────────────────────────────────────
    role: Mapped[Optional["PlatformRole"]] = relationship(back_populates="admins")

    def __repr__(self) -> str:
        return (
            f"<PlatformAdmin email={self.email!r} "
            f"active={self.is_active} 2fa={self.two_fa_enabled}>"
        )
