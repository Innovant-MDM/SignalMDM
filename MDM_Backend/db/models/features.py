"""
models/features.py
------------------
ML / analytics feature store and domain configuration:
    EntityFeatureStore   — versioned pre-computed feature vectors
    EntityDomainConfig   — per-entity-type scoring and governance config
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base


class EntityFeatureStore(Base):
    """
    Versioned feature vectors computed for ML / risk-scoring pipelines.

    feature_version increments on each recompute; the latest version is active.
    feature_metadata can carry provenance, pipeline run IDs, and model version.
    """

    __tablename__ = "entity_feature_store"

    feature_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenant_id", ondelete="RESTRICT"),
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entity.entity_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
        comment="Canonical feature name (snake_case, e.g. txn_velocity_30d).",
    )
    feature_value: Mapped[Optional[float]] = mapped_column(
        Numeric(15, 6),
        nullable=True,
        comment="Computed numeric feature value.",
    )
    feature_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Pipeline run ID, model version, provenance metadata.",
    )
    feature_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Increments on each recompute. Latest version is the active one.",
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    tenant: Mapped["Tenant"] = relationship(back_populates="feature_store")  # noqa: F821
    entity: Mapped["Entity"] = relationship(back_populates="feature_store")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<EntityFeatureStore feature={self.feature_name!r} "
            f"entity={self.entity_id} v{self.feature_version}>"
        )


class EntityDomainConfig(Base):
    """
    Domain-level configuration driving scoring and governance per entity type.

    Stores all domain rules as JSONB so config can evolve without migrations:
      • risk_weight_config    — weights for each risk dimension
      • drift_threshold_config — per-attribute drift alert thresholds
      • governance_rules      — SLA targets and escalation rules
      • critical_attributes   — list of CDE attribute names for this domain
    """

    __tablename__ = "entity_domain_config"

    domain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        comment="Must exactly match entity.entity_type values (e.g. CUSTOMER).",
    )
    risk_weight_config: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "e.g. {structural: 0.25, behavioral: 0.30, "
            "external: 0.30, governance: 0.15}"
        ),
    )
    drift_threshold_config: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Per-attribute drift alert thresholds.",
    )
    governance_rules: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="SLA targets, review frequencies, escalation rules.",
    )
    critical_attributes: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment='List of CDE attribute names, e.g. ["tax_id", "legal_name"].',
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<EntityDomainConfig entity_type={self.entity_type!r}>"
