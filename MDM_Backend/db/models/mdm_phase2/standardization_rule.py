from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base

if TYPE_CHECKING:
    from db.models.tenant import Tenant


class StandardizationRule(Base):
    """
    ORM Model for `standardization_rules` table.
    Stores reusable key-value mapping logic for address/name/country standardization (e.g. COUNTRY_CODE_STD).
    """

    __tablename__ = "standardization_rules"

    rule_id: Mapped[uuid.UUID] = mapped_column(
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
    rule_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    rule_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    standardization_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    mappings_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
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

    __table_args__ = (
        UniqueConstraint("tenant_id", "rule_code", name="uq_tenant_std_rule_code"),
    )

    def __repr__(self) -> str:
        return f"<StandardizationRule id={self.rule_id} code={self.rule_code!r} type={self.standardization_type!r}>"
