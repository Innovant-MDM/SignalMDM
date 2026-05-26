"""
models/audit.py
---------------
Immutable, append-only audit trail for every data mutation.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base
from db.enums import OperationTypeEnum


class AuditLog(Base):
    """
    Platform-wide immutable audit trail.

    Rules enforced at the application layer:
      • No UPDATE or DELETE on this table — only INSERTs.
      • old_value / new_value capture full row snapshots as JSONB.
      • trace_id enables distributed tracing correlation.
    """

    __tablename__ = "audit_log"

    audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenant_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    entity_name: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        comment="Table / domain object that was changed.",
    )
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="PK of the changed record (not a FK — immutability constraint).",
    )
    operation_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="INSERT, UPDATE, DELETE, or MERGE.",
    )
    old_value: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Full row snapshot before the operation.",
    )
    new_value: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Full row snapshot after the operation.",
    )
    performed_by: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        comment="Username or system identifier that triggered the change.",
    )
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    source_ip: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    trace_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Distributed tracing correlation ID (e.g. W3C traceparent).",
    )
    approved_by: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        comment="Who approved the override, if manual intervention occurred.",
    )
    approval_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Why the override was approved.",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    tenant: Mapped["Tenant"] = relationship(back_populates="audit_logs")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<AuditLog op={self.operation_type!r} entity={self.entity_name!r} "
            f"by={self.performed_by!r} at={self.performed_at}>"
        )
