from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class StandardizationRuleCreate(BaseModel):
    rule_name: str = Field(..., min_length=1, max_length=100, example="Standardize Country Codes")
    rule_code: str = Field(..., min_length=1, max_length=50, example="COUNTRY_CODE_STD")
    standardization_type: str = Field(..., min_length=1, max_length=50, example="COUNTRY")
    mappings_json: dict[str, Any] = Field(default_factory=dict)
    status: Optional[str] = Field(default="ACTIVE")

    model_config = {"from_attributes": True}


class StandardizationRuleRead(BaseModel):
    rule_id: uuid.UUID
    tenant_id: uuid.UUID
    rule_name: str
    rule_code: str
    standardization_type: str
    mappings_json: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
