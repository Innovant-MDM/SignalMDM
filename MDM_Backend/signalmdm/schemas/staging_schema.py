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

    model_config = {"from_attributes": False}
