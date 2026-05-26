"""
signalmdm/models/ingestion_run.py
----------------------------------
ORM model for the `ingestion_runs` table.

An IngestionRun represents one execution of the data ingestion pipeline
for a specific SourceSystem. It is the root of the ingestion lineage:

    IngestionRun → FileUpload(s) → RawRecord(s) → StagingEntity(ies)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base
from db.enums import IngestionStateEnum

if TYPE_CHECKING:
    from db.models.tenant import Tenant
    from db.models.source_system import SourceSystem
    from db.models.file_upload import FileUpload
    from db.models.raw_record import RawRecord
    from db.models.staging_entity import StagingEntity


class IngestionRun(Base):
    """
    One execution of the ingestion pipeline for a source system.

    State machine:
        CREATED → RUNNING → RAW_LOADED → STAGING_CREATED → COMPLETED
        Any state → FAILED

    The `record_count` is updated by the async worker after parsing.
    """

    __tablename__ = "ingestion_runs"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    run_id: Mapped[uuid.UUID] = mapped_column(
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
    source_system_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_systems.source_system_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=IngestionStateEnum.CREATED,
        index=True,
        comment="Current pipeline state — see IngestionStateEnum.",
    )
    triggered_by: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        comment="Username or system that initiated this run.",
    )
    file_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of files uploaded in this run.",
    )
    record_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total raw records parsed across all files.",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Populated when state=FAILED.",
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Set when the async worker begins processing.",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Set when state reaches COMPLETED or FAILED.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    tenant: Mapped["Tenant"] = relationship(back_populates="ingestion_runs")
    source_system: Mapped["SourceSystem"] = relationship(back_populates="ingestion_runs")
    file_uploads: Mapped[list["FileUpload"]] = relationship(
        back_populates="ingestion_run",
        cascade="all, delete-orphan",
    )
    raw_records: Mapped[list["RawRecord"]] = relationship(
        back_populates="ingestion_run",
        cascade="all, delete-orphan",
    )
    staging_entities: Mapped[list["StagingEntity"]] = relationship(
        back_populates="ingestion_run",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<IngestionRun id={self.run_id} state={self.state!r}>"
