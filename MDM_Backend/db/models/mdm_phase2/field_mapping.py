from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base

if TYPE_CHECKING:
    from db.models.tenant import Tenant
    from db.models.source_system import SourceSystem
    from db.models.mdm_phase2.canonical_field import CanonicalField
    from db.models.mdm_phase2.standardization_rule import StandardizationRule


class FieldMapping(Base):
    """
    ORM Model for `field_mappings` table.
    Links an incoming source field from a source system to a standardized canonical field under a tenant,
    with an ordered list of transformation rules and an optional standardization rule.
    """

    __tablename__ = "field_mappings"

    mapping_id: Mapped[uuid.UUID] = mapped_column(
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
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    source_field_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    canonical_field_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("canonical_fields.field_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    transformation_rule_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=False,
        default=list,
    )
    standardization_rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("standardization_rules.rule_id", ondelete="SET NULL"),
        nullable=True,
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
    source_system: Mapped["SourceSystem"] = relationship()
    canonical_field: Mapped["CanonicalField"] = relationship(back_populates="field_mappings")
    standardization_rule: Mapped[Optional["StandardizationRule"]] = relationship()

    __table_args__ = (
        UniqueConstraint("tenant_id", "source_system_id", "entity_type", "source_field_name", name="uq_tenant_src_entity_field"),
    )

    def __repr__(self) -> str:
        return f"<FieldMapping id={self.mapping_id} source={self.source_field_name!r} entity={self.entity_type!r}>"
