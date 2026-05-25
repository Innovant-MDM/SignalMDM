"""
signalmdm/models/domain.py
----------------------------
ORM model for the `domains` table.

A Domain represents a logical data classification category (e.g. Customer,
Finance, HR) within a tenant's MDM ecosystem.  Upload sessions are associated
with a domain name; this table provides the canonical registry of valid
domains per tenant.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from signalmdm.database import Base

if TYPE_CHECKING:
    from signalmdm.models.tenant import Tenant


class Domain(Base):
    """
    Registered data domain for a tenant (e.g. Customer, Finance, HR).

    Rules:
      • `domain_name` should be unique per tenant (enforced at service layer).
      • `status` defaults to ACTIVE; valid values mirror StatusEnum.
    """

    __tablename__ = "domains"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Surrogate primary key.",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Human-readable domain name (e.g. Customer, Finance).",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description of the domain.",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ACTIVE",
        comment="Domain lifecycle status: ACTIVE, SUSPENDED, ARCHIVED, DEACTIVATED.",
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
    tenant: Mapped["Tenant"] = relationship(back_populates="domains")

    def __repr__(self) -> str:
        return f"<Domain name={self.domain_name!r} tenant={self.tenant_id!r}>"
