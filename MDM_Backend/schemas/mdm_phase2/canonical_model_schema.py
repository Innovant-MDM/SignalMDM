from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CanonicalFieldCreate(BaseModel):
    entity_type: str = Field(..., min_length=1, max_length=50, example="CUSTOMER")
    canonical_field_name: str = Field(..., min_length=1, max_length=100, example="primary_email")
    data_type: str = Field(..., min_length=1, max_length=50, example="EMAIL")
    is_required: bool = Field(default=False)
    validation_type: str = Field(default="TEXT")
    standardization_type: str = Field(default="TEXT")
    status: Optional[str] = Field(default="ACTIVE")

    model_config = {"from_attributes": True}


class CanonicalFieldRead(BaseModel):
    field_id: uuid.UUID
    tenant_id: uuid.UUID
    entity_type: str
    canonical_field_name: str
    data_type: str
    is_required: bool
    validation_type: str
    standardization_type: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
