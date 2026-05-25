"""
signalmdm/schemas/domain_schema.py
-------------------------------------
Pydantic v2 schemas for Domain request / response.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DomainCreate(BaseModel):
    """Request body for POST /domains."""

    domain_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable domain name (e.g. Customer, Finance, HR).",
        examples=["Customer"],
    )
    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional description of the domain.",
    )
    status: str = Field(
        default="ACTIVE",
        max_length=50,
        description="Domain lifecycle status (defaults to ACTIVE).",
    )

    model_config = {"from_attributes": True}


class DomainUpdate(BaseModel):
    """Request body for PATCH /domains/{domain_id}."""

    domain_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Updated domain name.",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Updated description.",
    )
    status: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Updated status (ACTIVE, SUSPENDED, ARCHIVED, DEACTIVATED).",
    )

    model_config = {"from_attributes": True}


class DomainRead(BaseModel):
    """Response schema for a single Domain."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    domain_name: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
