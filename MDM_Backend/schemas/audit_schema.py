"""
signalmdm/schemas/audit_schema.py
-----------------------------------
Pydantic schemas for API Logs (read-only audit_log list).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ApiLogListItem(BaseModel):
    """One row for the API Logs UI (backed by audit_log)."""

    audit_id: uuid.UUID
    tenant_id: Optional[uuid.UUID] = None
    tenant_name: Optional[str] = Field(None, description="Resolved from tenant join.")
    entity_name: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None
    operation_type: Optional[str] = Field(None, description="INSERT | UPDATE | DELETE | MERGE")
    old_value: Optional[dict[str, Any]] = None
    new_value: Optional[dict[str, Any]] = None
    performed_by: Optional[str] = None
    performed_at: datetime
    source_ip: Optional[str] = None
    trace_id: Optional[str] = None
    approved_by: Optional[str] = None
    approval_reason: Optional[str] = None

    model_config = {"from_attributes": False}
