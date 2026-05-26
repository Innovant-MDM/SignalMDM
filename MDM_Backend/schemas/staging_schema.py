"""
signalmdm/schemas/staging_schema.py
-----------------------------------
Pydantic schemas for Staging screen (read-only list of staging_entities).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class StagingRecordListItem(BaseModel):
    """One row for the Staging Records UI."""

    staging_id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: Optional[str] = None
    run_id: uuid.UUID
    raw_record_id: uuid.UUID
    source_system_id: uuid.UUID
    source_name: str
    state: str = Field(description="READY_FOR_MAPPING | MAPPED | REJECTED")
    mapped_entity_type: Optional[str] = None
    ingestion_entity_type: Optional[str] = None
    run_type: Optional[str] = None
    entity_display: str
    entity_data: dict[str, Any]
    raw_data: dict[str, Any]
    created_at: datetime
    ingestion_run_state: str
    source_record_id: str
    dq_score: int = Field(description="Placeholder until real DQ (Phase 1).")
    validation_status: str = Field(description="PASSED | FAILED | PENDING (UI).")
    # Duplicate-record context (mirrored from underlying raw_record duplicate detection)
    is_duplicate: bool = False
    duplicate_scope: Optional[str] = Field(
        default=None,
        description="WITHIN_RUN | CROSS_RUN — only set when is_duplicate is true.",
    )
    duplicate_of_raw_record_id: Optional[uuid.UUID] = None
    duplicate_of_run_id: Optional[uuid.UUID] = None
    duplicate_of_staging_id: Optional[uuid.UUID] = None
    first_seen_by: Optional[str] = None
    first_seen_at: Optional[datetime] = None

    model_config = {"from_attributes": False}
