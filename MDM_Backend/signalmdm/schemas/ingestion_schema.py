"""
signalmdm/schemas/ingestion_schema.py
---------------------------------------
Pydantic v2 schemas for IngestionRun and related request/response.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from signalmdm.enums import IngestionStateEnum


class IngestionRunCreate(BaseModel):
    """Request body for POST /ingestion/start."""

    source_system_id: uuid.UUID = Field(
        ...,
        description="UUID of the registered source system for this run.",
    )
    triggered_by: Optional[str] = Field(
        default=None,
        max_length=150,
        description="Username or system identifier initiating the run.",
    )

    model_config = {"from_attributes": True}


class IngestionRunFromSessionCreate(BaseModel):
    """
    Request body for POST /ingestion/start-from-session (after Upload Data).

    entity_type, run_type, and trigger_type are optional — the server resolves them
    from the upload session domain and source system when omitted.
    """

    source_system_id: uuid.UUID
    upload_session_id: uuid.UUID
    entity_type: Optional[str] = Field(default=None, max_length=50)
    run_type: Optional[str] = Field(default=None, max_length=50)
    trigger_type: Optional[str] = Field(default=None, max_length=50)
    triggered_by: Optional[str] = Field(default=None, max_length=150)

    model_config = {"from_attributes": True}


class IngestionLineageRunSummary(BaseModel):
    """Per-run counts for comparing Raw Landing vs Staging (1:1 per completed pipeline)."""

    run_id: uuid.UUID
    source_system_id: uuid.UUID
    source_name: str
    entity_type: Optional[str] = None
    run_type: Optional[str] = None
    state: str
    raw_record_count: int
    staging_record_count: int
    counts_aligned: bool = Field(
        description="True when raw and staging counts match for this run.",
    )
    pipeline_note: str = ""
    created_at: datetime

    model_config = {"from_attributes": False}


class IngestionResolveConfigRead(BaseModel):
    """Resolved ingestion settings for a session + source pair (preview before start)."""

    upload_session_id: uuid.UUID
    source_system_id: uuid.UUID
    session_name: str
    session_domain: str
    entity_type: str
    entity_resolved_from: str = Field(
        description="session_domain | source_supported_entities | override",
    )
    run_type: str
    run_type_reason: str
    trigger_type: str
    trigger_type_reason: str
    file_count: int
    supported_entities: list[str] = Field(default_factory=list)


def parse_run_metadata(triggered_by: Optional[str]) -> dict[str, Optional[str]]:
    """Decode session|entity|run_type|trigger markers stored in triggered_by."""
    out: dict[str, Optional[str]] = {
        "upload_session_id": None,
        "entity_type": None,
        "run_type": None,
        "trigger_type": None,
        "initiated_by": None,
    }
    if not triggered_by:
        return out
    for part in triggered_by.split("|"):
        if part.startswith("session:"):
            out["upload_session_id"] = part[8:] or None
        elif part.startswith("entity:"):
            out["entity_type"] = part[7:] or None
        elif part.startswith("run_type:"):
            out["run_type"] = part[9:] or None
        elif part.startswith("trigger:"):
            out["trigger_type"] = part[8:] or None
        elif part.startswith("by:"):
            out["initiated_by"] = part[3:] or None
    return out


class IngestionRunRead(BaseModel):
    """Full ingestion run response."""

    run_id: uuid.UUID
    tenant_id: uuid.UUID
    source_system_id: uuid.UUID
    state: str
    triggered_by: Optional[str]
    file_count: int
    record_count: int
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    upload_session_id: Optional[uuid.UUID] = None
    entity_type: Optional[str] = None
    run_type: Optional[str] = None
    trigger_type: Optional[str] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_run(cls, run) -> "IngestionRunRead":
        meta = parse_run_metadata(run.triggered_by)
        session_raw = meta.get("upload_session_id")
        session_id = None
        if session_raw:
            try:
                session_id = uuid.UUID(session_raw)
            except ValueError:
                session_id = None
        return cls(
            run_id=run.run_id,
            tenant_id=run.tenant_id,
            source_system_id=run.source_system_id,
            state=run.state,
            triggered_by=run.triggered_by,
            file_count=run.file_count,
            record_count=run.record_count,
            error_message=run.error_message,
            started_at=run.started_at,
            completed_at=run.completed_at,
            created_at=run.created_at,
            upload_session_id=session_id,
            entity_type=meta.get("entity_type"),
            run_type=meta.get("run_type"),
            trigger_type=meta.get("trigger_type"),
        )


class IngestionStatusRead(BaseModel):
    """Lightweight status response for GET /ingestion/{run_id}/status."""

    run_id: uuid.UUID
    state: str
    file_count: int
    record_count: int
    staging_count: Optional[int] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class TenantCreate(BaseModel):
    """Request body for POST /tenants/ (bootstrap endpoint)."""

    tenant_name: str = Field(..., min_length=1, max_length=255, example="Acme Corporation")
    tenant_code: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9_\-]+$",
        example="acme_corp",
        description="Unique slug for this tenant.",
    )

    model_config = {"from_attributes": True}


class TenantRead(BaseModel):
    """Response for a single Tenant."""

    tenant_id: uuid.UUID
    tenant_name: str
    tenant_code: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
