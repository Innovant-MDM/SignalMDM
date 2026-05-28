from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FieldMappingCreate(BaseModel):
    source_system_id: uuid.UUID
    entity_type: str = Field(..., min_length=1, max_length=50, example="CUSTOMER")
    source_field_name: str = Field(..., min_length=1, max_length=100, example="custName")
    canonical_field_id: uuid.UUID
    transformation_rule_ids: list[uuid.UUID] = Field(default_factory=list)
    standardization_rule_id: Optional[uuid.UUID] = Field(default=None)
    status: Optional[str] = Field(default="ACTIVE")

    model_config = {"from_attributes": True}


class FieldMappingRead(BaseModel):
    mapping_id: uuid.UUID
    tenant_id: uuid.UUID
    source_system_id: uuid.UUID
    entity_type: str
    source_field_name: str
    canonical_field_id: uuid.UUID
    transformation_rule_ids: list[uuid.UUID]
    standardization_rule_id: Optional[uuid.UUID]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
