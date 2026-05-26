"""
models/entity.py
----------------
ORM model for the `entity` table — the central polymorphic MDM object.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, func, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base
from db.enums import StatusEnum, EntityTypeEnum, LifecycleStageEnum


class Entity(Base):
    """
    Core MDM entity — polymorphic across all domain types.

    Supports:
      • Soft-delete (is_deleted flag)
      • Optimistic versioning (version_number)
      • Hierarchical parent-child (parent_entity_id self-reference)
      • Domain tagging (domain_tag)
    """

    __tablename__ = "entity"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    entity_id: Mapped[uuid.UUID] = mapped_column(
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
        index=True,
        comment="Domain discriminator e.g. CUSTOMER, PRODUCT, SUPPLIER.",
    )
    entity_code: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Business / source-system identifier.",
    )
    entity_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=StatusEnum.ACTIVE,
    )
    lifecycle_stage: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="ONBOARDING, ACTIVE, DORMANT, OFFBOARDED, SUSPENDED.",
    )
    parent_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entity.entity_id", ondelete="SET NULL"),
        nullable=True,
    )
    domain_tag: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Optional cross-domain classification tag.",
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Incremented on every meaningful update.",
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Soft-delete flag — rows are never physically removed.",
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
    tenant:           Mapped["Tenant"]                      = relationship(back_populates="entities")                          # noqa: F821
    parent:           Mapped[Optional["Entity"]]            = relationship("Entity", remote_side="Entity.entity_id", foreign_keys=[parent_entity_id], back_populates="children")
    children:         Mapped[list["Entity"]]                = relationship("Entity", foreign_keys=[parent_entity_id], back_populates="parent")
    attributes:       Mapped[list["EntityAttribute"]]       = relationship(back_populates="entity", cascade="all, delete-orphan")  # noqa: F821
    attr_history:     Mapped[list["EntityAttributeHistory"]]= relationship(back_populates="entity", cascade="all, delete-orphan")  # noqa: F821
    signals:          Mapped[list["EntitySignal"]]          = relationship(back_populates="entity", cascade="all, delete-orphan")  # noqa: F821
    risk_scores:      Mapped[list["EntityRiskScore"]]       = relationship(back_populates="entity", cascade="all, delete-orphan")  # noqa: F821
    drift_records:    Mapped[list["EntityDrift"]]           = relationship(back_populates="entity", cascade="all, delete-orphan")  # noqa: F821
    governance:       Mapped[list["EntityGovernance"]]      = relationship(back_populates="entity", cascade="all, delete-orphan")  # noqa: F821
    alerts:           Mapped[list["EntityAlert"]]           = relationship(back_populates="entity", cascade="all, delete-orphan")  # noqa: F821
    feature_store:    Mapped[list["EntityFeatureStore"]]    = relationship(back_populates="entity", cascade="all, delete-orphan")  # noqa: F821
    source_relations: Mapped[list["EntityRelationship"]]    = relationship("EntityRelationship", foreign_keys="EntityRelationship.source_entity_id", back_populates="source_entity", cascade="all, delete-orphan")  # noqa: F821
    target_relations: Mapped[list["EntityRelationship"]]    = relationship("EntityRelationship", foreign_keys="EntityRelationship.target_entity_id", back_populates="target_entity", cascade="all, delete-orphan")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Entity id={self.entity_id} type={self.entity_type!r} name={self.entity_name!r}>"
