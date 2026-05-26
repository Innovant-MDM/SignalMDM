"""
signalmdm/models/staging_entity.py
------------------------------------
ORM model for the `staging_entities` table.

A StagingEntity is a structured, tenant-scoped entity produced from a
RawRecord. It carries `entity_data` (JSONB) that mirrors the raw_data
of its source record but is the insertion point for Phase 2 mapping.

Phase 1 final state: READY_FOR_MAPPING
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base
from db.enums import StagingStateEnum

if TYPE_CHECKING:
    from db.models.tenant import Tenant
    from db.models.ingestion_run import IngestionRun
    from db.models.raw_record import RawRecord


class StagingEntity(Base):
    """
    One entity staged for mapping, produced 1-to-1 from a RawRecord.

    Lineage chain:
        IngestionRun → RawRecord → StagingEntity

    Phase 1 always leaves `state = READY_FOR_MAPPING`.
    Phase 2 will transition it to MAPPED or REJECTED.
    """

    __tablename__ = "staging_entities"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    staging_id: Mapped[uuid.UUID] = mapped_column(
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
    raw_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_records.raw_record_id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        comment="1-to-1 link back to the source raw record.",
    )
    source_system_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_systems.source_system_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Denormalised for fast lineage queries.",
    )
    entity_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Data payload ready for mapping — mirrors raw_data in Phase 1.",
    )
    state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=StagingStateEnum.READY_FOR_MAPPING,
        index=True,
        comment="Phase 1 always: READY_FOR_MAPPING. Phase 2 transitions to MAPPED.",
    )
    mapped_entity_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Set in Phase 2 when the entity domain is resolved.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    tenant: Mapped["Tenant"] = relationship(back_populates="staging_entities")
    ingestion_run: Mapped["IngestionRun"] = relationship(back_populates="staging_entities")
    raw_record: Mapped["RawRecord"] = relationship(back_populates="staging_entity")

    def __repr__(self) -> str:
        return f"<StagingEntity id={self.staging_id} state={self.state!r} run={self.run_id}>"
