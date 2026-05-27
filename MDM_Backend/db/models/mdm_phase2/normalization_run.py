from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, func, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base

if TYPE_CHECKING:
    from db.models.tenant import Tenant
    from db.models.ingestion_run import IngestionRun
    from db.models.source_system import SourceSystem
    from db.models.staging_entity import StagingEntity
    from db.models.mdm_phase2.mapping_error import MappingError


class NormalizationRun(Base):
    """
    ORM Model for `normalization_runs` table.
    Tracks normalization executions.
    """

    __tablename__ = "normalization_runs"

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
    ingestion_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_runs.run_id", ondelete="SET NULL"),
        nullable=True,
    )
    source_system_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_systems.source_system_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="CREATED",
    )
    total_records: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    processed_records: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    successful_records: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    failed_records: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
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

    # Relationships
    tenant: Mapped["Tenant"] = relationship()
    ingestion_run: Mapped[Optional["IngestionRun"]] = relationship()
    source_system: Mapped["SourceSystem"] = relationship()
    staging_entities: Mapped[list["StagingEntity"]] = relationship(back_populates="normalization_run")
    mapping_errors: Mapped[list["MappingError"]] = relationship(back_populates="normalization_run")

    def __repr__(self) -> str:
        return f"<NormalizationRun id={self.run_id} status={self.status!r} total={self.total_records}>"
