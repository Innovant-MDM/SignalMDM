"""
signalmdm/schemas/raw_schema.py
---------------------------------
Pydantic schemas for Raw Landing (read-only list of raw_records).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class RawRecordListItem(BaseModel):
    """One row for the Raw Landing UI."""

    raw_record_id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: Optional[str] = None
    run_id: uuid.UUID
    source_system_id: uuid.UUID
    source_name: str = Field(description="Display name from source_systems.")
    ingestion_run_state: str
    row_index: Optional[int] = None
    raw_data: dict[str, Any]
    checksum_md5: str
    created_at: datetime
    processing_status: str = Field(
        description="PENDING | PROCESSING | COMPLETED | FAILED | DUPLICATE (UI)",
    )
    source_record_id: str = Field(
        description="Business key from payload (id / externalId) or row index fallback.",
    )
    ingestion_entity_type: Optional[str] = Field(
        default=None,
        description="Entity resolved at ingestion start (from upload session domain).",
    )
    run_type: Optional[str] = None
    entity_display: str = Field(
        default="RECORD",
        description="Best label: staging mapped type, ingestion entity, or source default.",
    )
    has_staging: bool = False
    mapped_entity_type: Optional[str] = None
    # Duplicate-record context (cross-run within the same tenant)
    is_duplicate: bool = False
    duplicate_scope: Optional[str] = Field(
        default=None,
        description="WITHIN_RUN | CROSS_RUN — only set when is_duplicate is true.",
    )
    duplicate_of_raw_record_id: Optional[uuid.UUID] = None
    duplicate_of_run_id: Optional[uuid.UUID] = None
    first_seen_by: Optional[str] = Field(
        default=None,
        description="Username who initiated the run that first inserted this checksum for the tenant.",
    )
    first_seen_at: Optional[datetime] = None

    model_config = {"from_attributes": False}
