from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, func, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base

if TYPE_CHECKING:
    from db.models.tenant import Tenant
    from db.models.mdm_phase2.field_mapping import FieldMapping


class CanonicalField(Base):
    """
    ORM Model for `canonical_fields` table.
    Defines the standardized fields for each entity domain (CUSTOMER, PRODUCT, etc.) under a tenant.
    """

    __tablename__ = "canonical_fields"

    field_id: Mapped[uuid.UUID] = mapped_column(
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
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    canonical_field_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    data_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    validation_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="TEXT",
    )
    standardization_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="TEXT",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ACTIVE",
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

    # Relationships
    tenant: Mapped["Tenant"] = relationship()
    field_mappings: Mapped[list["FieldMapping"]] = relationship(back_populates="canonical_field")

    __table_args__ = (
        UniqueConstraint("tenant_id", "entity_type", "canonical_field_name", name="uq_tenant_entity_field"),
    )

    def __repr__(self) -> str:
        return f"<CanonicalField id={self.field_id} name={self.canonical_field_name!r} type={self.entity_type!r}>"
