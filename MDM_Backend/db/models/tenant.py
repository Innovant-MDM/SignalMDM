"""
signalmdm/models/tenant.py
--------------------------
ORM model for the `tenant` table — root of every multi-tenant record.

Updated for Phase 1 to include ingestion pipeline back-references:
  source_systems, ingestion_runs, file_uploads, raw_records, staging_entities
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base
from db.enums import StatusEnum

if TYPE_CHECKING:
    from db.models.entity        import Entity
    from db.models.rbac          import AppUser, Role
    from db.models.audit         import AuditLog
    from db.models.signals       import SignalStreamBuffer, EntitySignal
    from db.models.features      import EntityFeatureStore
    from db.models.source_system import SourceSystem
    from db.models.ingestion_run import IngestionRun
    from db.models.file_upload   import FileUpload
    from db.models.raw_record    import RawRecord
    from db.models.staging_entity import StagingEntity
    from db.models.upload_session import UploadSession, UploadSessionFile
    from db.models.domain         import Domain


class Tenant(Base):
    """
    Root tenant / organisation record.

    Every other table that carries a `tenant_id` column references this.
    Deleting a tenant is restricted — all child records must be cleared first.
    """

    __tablename__ = "tenant"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Surrogate primary key.",
    )
    tenant_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Full display name of the tenant organisation.",
    )
    tenant_code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="Short slug used in routing, logging, and API headers.",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=StatusEnum.ACTIVE,
        comment="Allowed: ACTIVE, SUSPENDED, ARCHIVED.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ------------------------------------------------------------------
    # Relationships — core platform
    # ------------------------------------------------------------------
    entities:        Mapped[list["Entity"]]             = relationship(back_populates="tenant")
    app_users:       Mapped[list["AppUser"]]            = relationship(back_populates="tenant")
    roles:           Mapped[list["Role"]]               = relationship(back_populates="tenant")
    audit_logs:      Mapped[list["AuditLog"]]           = relationship(back_populates="tenant")
    signal_buffers:  Mapped[list["SignalStreamBuffer"]] = relationship(back_populates="tenant")
    entity_signals:  Mapped[list["EntitySignal"]]       = relationship(back_populates="tenant")
    feature_store:   Mapped[list["EntityFeatureStore"]] = relationship(back_populates="tenant")

    # ------------------------------------------------------------------
    # Relationships — Phase 1 ingestion pipeline
    # ------------------------------------------------------------------
    source_systems:   Mapped[list["SourceSystem"]]   = relationship(back_populates="tenant")
    ingestion_runs:   Mapped[list["IngestionRun"]]   = relationship(back_populates="tenant")
    file_uploads:     Mapped[list["FileUpload"]]     = relationship(back_populates="tenant")
    raw_records:      Mapped[list["RawRecord"]]      = relationship(back_populates="tenant")
    staging_entities: Mapped[list["StagingEntity"]]  = relationship(back_populates="tenant")
    upload_sessions:  Mapped[list["UploadSession"]]  = relationship(back_populates="tenant")
    domains:          Mapped[list["Domain"]]          = relationship(back_populates="tenant")

    def __repr__(self) -> str:
        return f"<Tenant code={self.tenant_code!r} status={self.status!r}>"
