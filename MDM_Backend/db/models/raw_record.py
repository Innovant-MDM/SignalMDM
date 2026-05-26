"""
signalmdm/models/raw_record.py
--------------------------------
ORM model for the `raw_records` table.

IMMUTABILITY GUARANTEE:
  Raw records are NEVER modified after insertion. They represent the
  exact data received from the source system, preserved for full lineage
  auditability.

`raw_data` (JSONB) stores the complete row as parsed from the uploaded
file. `checksum_md5` is computed from `raw_data` at insert time.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base

if TYPE_CHECKING:
    from db.models.tenant import Tenant
    from db.models.ingestion_run import IngestionRun
    from db.models.file_upload import FileUpload
    from db.models.staging_entity import StagingEntity


class RawRecord(Base):
    """
    Immutable snapshot of one parsed row from a source file or API response.

    Design constraints enforced at the application layer:
      • No UPDATE statements on this table.
      • No DELETE except full run teardown (CASCADE from IngestionRun).
      • `raw_data` is the verbatim parsed dict — no field cleaning.
    """

    __tablename__ = "raw_records"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    raw_record_id: Mapped[uuid.UUID] = mapped_column(
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
    file_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("file_uploads.file_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="NULL when record arrived via direct API push (no file).",
    )
    source_system_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_systems.source_system_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Denormalised for fast lineage queries.",
    )
    row_index: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="0-based row position in the source file.",
    )
    raw_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Verbatim parsed row — NEVER modify after insert.",
    )
    checksum_md5: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="MD5 of JSON-serialised raw_data for dedup detection.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    tenant: Mapped["Tenant"] = relationship(back_populates="raw_records")
    ingestion_run: Mapped["IngestionRun"] = relationship(back_populates="raw_records")
    file_upload: Mapped[Optional["FileUpload"]] = relationship(back_populates="raw_records")
    staging_entity: Mapped[Optional["StagingEntity"]] = relationship(
        back_populates="raw_record",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<RawRecord id={self.raw_record_id} row={self.row_index} run={self.run_id}>"
