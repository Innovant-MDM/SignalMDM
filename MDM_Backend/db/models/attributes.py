"""
MDM_Backend/signalmdm/models/attributes.py
--------------------
Entity attribute store and full change-history trail:
    EntityAttribute         — key-value attribute store with effective dating
    EntityAttributeHistory  — immutable change log for every attribute mutation
"""

import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base


class EntityAttribute(Base):
    """
    Flexible attribute bag for entity master data.

    Design decisions:
      • attribute_value is JSONB — handles scalar, list, and nested structures.
      • effective_from / effective_to allow bi-temporal attribute versioning.
      • is_critical_data_element (CDE) flags attributes subject to enhanced DQ.
      • GIN index on attribute_value enables fast JSONB containment queries.
    """

    __tablename__ = "entity_attribute"

    attribute_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entity.entity_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attribute_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
        comment="Canonical attribute name (snake_case recommended).",
    )
    attribute_value: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Value stored as JSONB — scalars, arrays, and nested objects supported.",
    )
    attribute_category: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="CORE, FINANCIAL, CONTACT, REGULATORY, OPERATIONAL, CUSTOM.",
    )
    effective_from: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Start date for bi-temporal validity window.",
    )
    effective_to: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="End date for bi-temporal validity window. NULL = currently active.",
    )
    source_system: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Origin system of this attribute value.",
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="0.00–100.00 data quality confidence from source system.",
    )
    is_critical_data_element: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="TRUE = subject to enhanced DQ rules and governance tracking.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    entity: Mapped["Entity"] = relationship(back_populates="attributes")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<EntityAttribute name={self.attribute_name!r} "
            f"entity={self.entity_id} cde={self.is_critical_data_element}>"
        )


class EntityAttributeHistory(Base):
    """
    Immutable, append-only change log for every attribute mutation.

    This table is written by application triggers / service logic —
    never updated or deleted directly.
    """

    __tablename__ = "entity_attribute_history"

    history_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entity.entity_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attribute_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )
    old_value: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Snapshot before the change.",
    )
    new_value: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Snapshot after the change.",
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    changed_by: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        comment="Username or system identity that triggered the change.",
    )
    change_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Free-text business justification for the change.",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    entity: Mapped["Entity"] = relationship(back_populates="attr_history")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<EntityAttributeHistory attr={self.attribute_name!r} "
            f"by={self.changed_by!r} at={self.changed_at}>"
        )
