r"""
MDM_Backend\signalmdm\schemas\source_schema.py
------------------------------------
Pydantic v2 schemas for SourceSystem request / response.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from db.enums import ConnectionTypeEnum, SourceTypeEnum, StatusEnum


class SourceSystemCreate(BaseModel):
    """Request body for POST /sources/register."""

    source_name: str = Field(..., min_length=1, max_length=255, example="Salesforce CRM")
    source_code: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9_\-]+$",
        example="salesforce_crm",
        description="Lowercase slug — must be globally unique.",
    )
    source_type: SourceTypeEnum = Field(default=SourceTypeEnum.OTHER)
    connection_type: ConnectionTypeEnum = Field(default=ConnectionTypeEnum.OTHER)
    config_json: Optional[dict[str, Any]] = Field(
        default=None,
        description="Non-sensitive connection parameters.",
    )

    model_config = {"from_attributes": True}


class SourceSystemRead(BaseModel):
    """Response schema for a single SourceSystem."""

    source_system_id: uuid.UUID
    tenant_id: uuid.UUID
    source_name: str
    source_code: str
    source_type: str
    connection_type: str
    config_json: Optional[dict[str, Any]]
    is_active: bool
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
