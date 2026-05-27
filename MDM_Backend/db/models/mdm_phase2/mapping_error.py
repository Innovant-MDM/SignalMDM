from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, func, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base

if TYPE_CHECKING:
    from db.models.tenant import Tenant
    from db.models.mdm_phase2.normalization_run import NormalizationRun
    from db.models.staging_entity import StagingEntity


class MappingError(Base):
    """
    ORM Model for `mapping_errors` table.
    Tracks issues during mapping, transformation, or standardization, with retry capabilities.
    """

    __tablename__ = "mapping_errors"

    error_id: Mapped[uuid.UUID] = mapped_column(
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
    normalization_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("normalization_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    staging_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staging_entities.staging_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    error_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    source_field: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    source_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    error_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="OPEN",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_by: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship()
    normalization_run: Mapped["NormalizationRun"] = relationship(back_populates="mapping_errors")
    staging_entity: Mapped["StagingEntity"] = relationship()

    def __repr__(self) -> str:
        return f"<MappingError id={self.error_id} type={self.error_type!r} status={self.status!r}>"
