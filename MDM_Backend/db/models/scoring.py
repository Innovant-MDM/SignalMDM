"""
models/scoring.py
-----------------
Risk, drift, governance, and alerting models:
    EntityRiskScore    — composite risk score broken down by dimension
    EntityDrift        — data / behavioural drift detection records
    EntityGovernance   — stewardship and data-quality governance record
    EntityAlert        — threshold-triggered alert events
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey,
    Integer, Numeric, String, Text, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.sessions.database import Base


class EntityRiskScore(Base):
    """
    Versioned risk score snapshots per entity.

    risk_version increments on each recalculation; the latest version is active.
    Scores are split into four orthogonal risk dimensions to support
    drill-down analysis.
    """

    __tablename__ = "entity_risk_score"

    risk_score_id: Mapped[uuid.UUID] = mapped_column(
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
    overall_risk_score: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Weighted composite of all four risk dimensions (0–100).",
    )
    risk_category: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="LOW, MODERATE, HIGH, CRITICAL.",
    )
    structural_risk: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Risk from entity structure / hierarchy anomalies.",
    )
    behavioral_risk: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Risk derived from signal and activity patterns.",
    )
    external_risk: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Risk from external feeds (sanctions lists, adverse news, etc.).",
    )
    governance_risk: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Risk from governance gaps and SLA breaches.",
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    risk_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    entity: Mapped["Entity"] = relationship(back_populates="risk_scores")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<EntityRiskScore entity={self.entity_id} "
            f"score={self.overall_risk_score} category={self.risk_category!r} "
            f"v{self.risk_version}>"
        )


class EntityDrift(Base):
    """
    Records of detected drift events on MDM entities.

    drift_velocity measures the rate of change of drift_score over time.
    resolved=TRUE once a steward has acknowledged and remediated the drift.
    """

    __tablename__ = "entity_drift"

    drift_id: Mapped[uuid.UUID] = mapped_column(
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
    drift_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="e.g. ATTRIBUTE_DRIFT, BEHAVIOURAL_DRIFT, RELATIONSHIP_DRIFT.",
    )
    drift_score: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Magnitude of detected drift (0–100).",
    )
    drift_velocity: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Rate of change of drift score over time.",
    )
    drift_start_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )
    drift_severity: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="LOW, MODERATE, HIGH, CRITICAL.",
    )
    root_cause: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable root-cause analysis.",
    )
    resolved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    entity: Mapped["Entity"] = relationship(back_populates="drift_records")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<EntityDrift entity={self.entity_id} type={self.drift_type!r} "
            f"severity={self.drift_severity!r} resolved={self.resolved}>"
        )


class EntityGovernance(Base):
    """
    Governance health and data stewardship metrics per entity.

    steward_id references AppUser — represents the assigned data steward.
    governance_score is an aggregate of data_quality_score,
    sla_compliance_rate, and escalation_count.
    """

    __tablename__ = "entity_governance"

    governance_id: Mapped[uuid.UUID] = mapped_column(
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
    steward_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_user.user_id", ondelete="SET NULL"),
        nullable=True,
        comment="AppUser responsible for data stewardship of this entity.",
    )
    data_quality_score: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Overall DQ score (0–100).",
    )
    open_issues: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Count of unresolved DQ or governance issues.",
    )
    sla_compliance_rate: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Percentage of SLA targets met (0–100).",
    )
    escalation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    governance_score: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Composite governance health score (0–100).",
    )
    last_review_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
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
    entity:  Mapped["Entity"]  = relationship(back_populates="governance")          # noqa: F821
    steward: Mapped[Optional["AppUser"]] = relationship(                             # noqa: F821
        back_populates="steward_governance",
        foreign_keys=[steward_id],
    )

    def __repr__(self) -> str:
        return (
            f"<EntityGovernance entity={self.entity_id} "
            f"dq_score={self.data_quality_score} issues={self.open_issues}>"
        )


class EntityAlert(Base):
    """
    System-generated alerts triggered by risk, drift, or governance thresholds.

    Lifecycle: alert created (acknowledged=FALSE, resolved=FALSE)
      → steward acknowledges → acknowledged=TRUE
      → steward resolves    → resolved=TRUE
    """

    __tablename__ = "entity_alert"

    alert_id: Mapped[uuid.UUID] = mapped_column(
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
    alert_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="e.g. RISK_THRESHOLD, DRIFT_DETECTED, SLA_BREACH, DQ_FAILURE.",
    )
    alert_severity: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="INFO, WARNING, HIGH, CRITICAL.",
    )
    triggered_by: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        comment="Rule name or system component that triggered this alert.",
    )
    trigger_value: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4),
        nullable=True,
        comment="The metric value that breached the threshold.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    acknowledged: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    resolved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    entity: Mapped["Entity"] = relationship(back_populates="alerts")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<EntityAlert type={self.alert_type!r} "
            f"severity={self.alert_severity!r} resolved={self.resolved}>"
        )
