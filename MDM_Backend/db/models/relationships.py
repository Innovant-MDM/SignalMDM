"""
models/relationships.py
-----------------------
Weighted, directional, time-bounded links between entities.
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base


class EntityRelationship(Base):
    """
    Graph-style relationships between MDM entities.

    Key design decisions:
      • Directional: source_entity → target_entity.
      • weight supports graph-traversal algorithms (e.g. PageRank, shortest path).
      • relationship_strength is the human-readable business score (0–100).
      • effective_from / effective_to enable time-scoped relationship queries.
    """

    __tablename__ = "entity_relationship"

    relationship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entity.entity_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entity.entity_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="PARENT_CHILD, SUBSIDIARY, PARTNER, SUPPLIER, CUSTOMER, etc.",
    )
    weight: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Numeric edge weight for graph-traversal algorithms.",
    )
    relationship_strength: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Business-level strength score (0.00 – 100.00).",
    )
    effective_from: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )
    effective_to: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="NULL = currently active.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    source_entity: Mapped["Entity"] = relationship(  # noqa: F821
        "Entity",
        foreign_keys=[source_entity_id],
        back_populates="source_relations",
    )
    target_entity: Mapped["Entity"] = relationship(  # noqa: F821
        "Entity",
        foreign_keys=[target_entity_id],
        back_populates="target_relations",
    )

    def __repr__(self) -> str:
        return (
            f"<EntityRelationship {self.source_entity_id} "
            f"--[{self.relationship_type}]--> {self.target_entity_id}>"
        )
