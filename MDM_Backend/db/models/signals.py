"""
models/signals.py
-----------------
Signal ingestion pipeline models:
    SignalStreamBuffer  — raw inbound queue before enrichment
    EntitySignal        — enriched, entity-linked signal events
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base
from db.enums import ProcessingStatusEnum, SeverityEnum, SignalCategoryEnum


class SignalStreamBuffer(Base):
    """
    Raw inbound signal queue — landing pad before enrichment / processing.

    Workers poll this table on `processed = FALSE`.
    On success: set processed=TRUE, processing_status='COMPLETED'.
    On failure: set processing_status='FAILED', error_message=<detail>.
    """

    __tablename__ = "signal_stream_buffer"

    buffer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenant_id", ondelete="RESTRICT"),
        nullable=False,
    )
    entity_reference: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Source-side entity identifier before entity resolution.",
    )
    signal_type: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
    )
    raw_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Original payload exactly as received — never modified.",
    )
    ingestion_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    processed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="FALSE = awaiting processing; TRUE = consumed by worker.",
    )
    processing_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="PENDING, PROCESSING, COMPLETED, FAILED, SKIPPED.",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Worker error detail when processing_status='FAILED'.",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    tenant: Mapped["Tenant"] = relationship(back_populates="signal_buffers")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<SignalStreamBuffer id={self.buffer_id} "
            f"processed={self.processed} status={self.processing_status!r}>"
        )


class EntitySignal(Base):
    """
    Enriched, entity-resolved signal events.

    Canonical version — includes tenant_id, is_deleted, and full metadata.
    Workers promote records from SignalStreamBuffer into this table after
    entity resolution and enrichment.
    """

    __tablename__ = "entity_signal"

    signal_id: Mapped[uuid.UUID] = mapped_column(
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
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entity.entity_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    signal_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    signal_category: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="INTERNAL (system-generated) or EXTERNAL (third-party feed).",
    )
    signal_source: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
    )
    signal_value: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4),
        nullable=True,
    )
    signal_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    signal_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Business timestamp of when the signal occurred.",
    )
    severity: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="LOW, MEDIUM, HIGH, CRITICAL.",
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="0.00 – 100.00 confidence in signal accuracy.",
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
    tenant: Mapped["Tenant"] = relationship(back_populates="entity_signals")  # noqa: F821
    entity: Mapped["Entity"] = relationship(back_populates="signals")         # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<EntitySignal type={self.signal_type!r} "
            f"severity={self.severity!r} entity={self.entity_id}>"
        )
