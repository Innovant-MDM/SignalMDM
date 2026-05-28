from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field


class MappingErrorRead(BaseModel):
    error_id: uuid.UUID
    tenant_id: uuid.UUID
    normalization_run_id: uuid.UUID
    staging_id: uuid.UUID
    error_type: str
    source_field: Optional[str]
    source_value: Optional[str]
    error_message: str
    status: str
    created_at: datetime
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]

    model_config = {"from_attributes": True}


class MappingErrorResolve(BaseModel):
    correction_payload: Optional[dict[str, Any]] = Field(default=None)

    model_config = {"from_attributes": True}


class MappingErrorRetryResponse(BaseModel):
    success: bool
    message: str
    staging_id: uuid.UUID
    new_status: str

    model_config = {"from_attributes": True}
