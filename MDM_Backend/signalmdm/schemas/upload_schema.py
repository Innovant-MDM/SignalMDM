"""
signalmdm/schemas/upload_schema.py
------------------------------------
Pydantic v2 schemas for the Upload Session workflow.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Upload Session
# ---------------------------------------------------------------------------

class UploadSessionCreate(BaseModel):
    """Request body for POST /uploads/sessions."""

    session_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Unique name for this upload session / folder.",
        example="StudentDataUploadSession1",
    )
    domain: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Subject-area label, e.g. Student, Finance.",
        example="Student",
    )
    tenant_id: Optional[uuid.UUID] = Field(
        None,
        description="Optional tenant ID (used by platform admins as a fallback for the header)."
    )

    model_config = {"from_attributes": True}


class UploadSessionRead(BaseModel):
    """Response schema for a single UploadSession."""

    session_id: uuid.UUID
    tenant_id: uuid.UUID
    session_name: str
    domain: str
    status: str
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    file_count: int = 0          # computed/populated by service

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Upload Session File
# ---------------------------------------------------------------------------

class UploadSessionFileRead(BaseModel):
    """Response schema for a single file inside a session."""

    file_id: uuid.UUID
    session_id: uuid.UUID
    tenant_id: uuid.UUID
    file_label: str
    original_filename: str
    file_size_bytes: Optional[int]
    content_type: Optional[str]
    record_count: Optional[int]
    uploaded_by: Optional[str]
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class UploadSessionWithFiles(UploadSessionRead):
    """Session + its child files (used in GET /uploads/sessions/{id})."""

    files: list[UploadSessionFileRead] = []
