"""
signalmdm/models/file_upload.py
--------------------------------
ORM model for the `file_uploads` table.

Tracks every file uploaded during an ingestion run. The file itself is
stored locally under `storage/uploads/` (S3 in a future phase). The
`checksum_md5` validates file integrity.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base

if TYPE_CHECKING:
    from db.models.tenant import Tenant
    from db.models.ingestion_run import IngestionRun
    from db.models.raw_record import RawRecord


class FileUpload(Base):
    """
    One uploaded file attached to an ingestion run.

    `stored_path` is the server-side relative path under `storage/uploads/`.
    Raw records parsed from this file carry a `file_id` back-reference.
    """

    __tablename__ = "file_uploads"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    file_id: Mapped[uuid.UUID] = mapped_column(
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
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Original name as uploaded by the client.",
    )
    stored_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment="Server-side path relative to the storage root.",
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )
    content_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="MIME type e.g. text/csv, application/json.",
    )
    checksum_md5: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="MD5 hex digest of the raw file bytes.",
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    tenant: Mapped["Tenant"] = relationship(back_populates="file_uploads")
    ingestion_run: Mapped["IngestionRun"] = relationship(back_populates="file_uploads")
    raw_records: Mapped[list["RawRecord"]] = relationship(
        back_populates="file_upload",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<FileUpload file={self.original_filename!r} run={self.run_id}>"
