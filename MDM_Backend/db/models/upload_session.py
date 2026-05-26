"""
signalmdm/models/upload_session.py
------------------------------------
ORM models for the upload-session workflow.

Architecture:
  upload_sessions  — one per logical "folder" / upload batch
                     (user-defined session name, must be unique per tenant)
  upload_session_files — individual files inside a session,
                         carrying domain, display label, record count, path, etc.

This is intentionally decoupled from ingestion_runs so that uploads can exist
and be browsed before an ingestion run is created.  When a run is eventually
triggered it can reference one or more upload_session_files.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base

if TYPE_CHECKING:
    from db.models.tenant import Tenant


class UploadSession(Base):
    """
    Logical folder that groups one or more uploaded files.

    Rules
    -----
    • ``session_name`` is unique per tenant (enforced by DB unique constraint).
    • ``domain`` is a free-text label (e.g. "Student", "Finance").
    • Status: OPEN (accepting uploads) | CLOSED (locked)
    """

    __tablename__ = "upload_sessions"

    __table_args__ = (
        UniqueConstraint("tenant_id", "session_name", name="uq_upload_session_name_per_tenant"),
    )

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    session_id: Mapped[uuid.UUID] = mapped_column(
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
    session_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="User-defined unique name for this upload session / folder.",
    )
    domain: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Subject-area label, e.g. Student, Finance, HR.",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="OPEN",
        comment="OPEN | CLOSED",
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
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

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    tenant: Mapped["Tenant"] = relationship(back_populates="upload_sessions")
    files: Mapped[list["UploadSessionFile"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<UploadSession name={self.session_name!r} domain={self.domain!r}>"


class UploadSessionFile(Base):
    """
    One physical file inside an UploadSession.

    ``file_label`` is the human-readable name the user assigns
    (not necessarily the OS filename).
    ``record_count`` is populated server-side by counting CSV rows.
    """

    __tablename__ = "upload_session_files"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("upload_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenant_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    file_label: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="User-assigned display name for this file, e.g. 'Student Data Set1'.",
    )
    original_filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Original OS filename as uploaded by the client.",
    )
    stored_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment="Server-side relative path under storage/uploads/sessions/.",
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )
    content_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="MIME type e.g. text/csv.",
    )
    record_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of data rows (CSV rows minus header).",
    )
    checksum_md5: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    uploaded_by: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        comment="Username or ID of the person who uploaded this file.",
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    session: Mapped["UploadSession"] = relationship(back_populates="files")

    def __repr__(self) -> str:
        return f"<UploadSessionFile label={self.file_label!r} session={self.session_id}>"
