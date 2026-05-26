from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional
from db.enums import StatusEnum

class TenantBase(BaseModel):
    tenant_name: str = Field(..., min_length=2, max_length=255)
    tenant_code: str = Field(..., min_length=2, max_length=100, pattern="^[a-z0-9_-]+$")

class TenantCreate(TenantBase):
    pass

class TenantRead(TenantBase):
    tenant_id: UUID
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TenantUpdate(BaseModel):
    tenant_name: Optional[str] = None
    status: Optional[str] = None
