from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NormalizationRunCreate(BaseModel):
    ingestion_run_id: Optional[uuid.UUID] = Field(default=None)
    source_system_id: uuid.UUID
    entity_type: str = Field(..., min_length=1, max_length=50, example="CUSTOMER")

    model_config = {"from_attributes": True}


class NormalizationRunRead(BaseModel):
    run_id: uuid.UUID
    tenant_id: uuid.UUID
    ingestion_run_id: Optional[uuid.UUID]
    source_system_id: uuid.UUID
    entity_type: str
    status: str
    total_records: int
    processed_records: int
    successful_records: int
    failed_records: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    created_by: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
