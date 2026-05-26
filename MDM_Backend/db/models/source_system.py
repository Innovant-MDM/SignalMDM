"""
signalmdm/models/source_system.py
----------------------------------
ORM model for the `source_systems` table.

A SourceSystem is the registered origin of data flowing into the MDM platform.
Each source is scoped to a tenant and has a unique `source_code` slug.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base
from db.enums import ConnectionTypeEnum, SourceTypeEnum, StatusEnum

if TYPE_CHECKING:
    from db.models.tenant import Tenant
    from db.models.ingestion_run import IngestionRun


class SourceSystem(Base):
    """
    Registered source system (e.g. Salesforce CRM, SAP ERP, a CSV feed).

    Rules:
      • `source_code` is globally unique per tenant.
      • `config_json` holds connection parameters (passwords should be
         vault-referenced, never stored plain).
      • Deleting a source is restricted while ingestion runs reference it.
    """

    __tablename__ = "source_systems"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    source_system_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Surrogate primary key.",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenant_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable display name.",
    )
    source_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment="Slug identifier — must be unique globally.",
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=SourceTypeEnum.OTHER,
        comment="Domain category: CRM, ERP, FILE, API, etc.",
    )
    connection_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ConnectionTypeEnum.OTHER,
        comment="Transport/format: CSV, JSON, REST_API, JDBC, etc.",
    )
    config_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Connection configuration (non-sensitive fields only).",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=StatusEnum.ACTIVE,
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
    tenant: Mapped["Tenant"] = relationship(back_populates="source_systems")
    ingestion_runs: Mapped[list["IngestionRun"]] = relationship(
        back_populates="source_system",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<SourceSystem code={self.source_code!r} type={self.source_type!r}>"
