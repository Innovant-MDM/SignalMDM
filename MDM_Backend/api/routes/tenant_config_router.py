"""
signalmdm/routers/tenant_config_router.py
------------------------------------------
Per-admin active tenant scope stored in Redis.

Redis key:  tcfg:{admin_id}         (compact to save memory)
Redis TTL:  28800 s  (8 hours — one working session)
Value:      compact JSON string

Structure stored:
    {"m":"ALL"}                                    – see everything
    {"m":"S","tid":"<uuid>","tn":"<name>"}         – single tenant scope

Endpoints:
    GET  /api/v1/admin/tenant-config  → current scope
    PUT  /api/v1/admin/tenant-config  → set scope
    DELETE /api/v1/admin/tenant-config → reset to ALL
"""

from __future__ import annotations

import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.redis_client import get_redis
from db.sessions.database import get_db
from middleware.auth import require_auth, TokenPayload
from db.models.tenant import Tenant

router = APIRouter(prefix="/admin", tags=["Admin Config"])

# ── Constants ──────────────────────────────────────────────────
_TTL    = 28_800        # 8 hours in seconds
_PREFIX = "tcfg:"       # short prefix for memory efficiency

# ── Helpers ────────────────────────────────────────────────────

def _key(admin_id: str) -> str:
    return f"{_PREFIX}{admin_id}"


def _read(admin_id: str) -> dict:
    """Read current config; returns {'m':'ALL'} if not set."""
    try:
        raw = get_redis().get(_key(admin_id))
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return {"m": "ALL"}


def _write(admin_id: str, payload: dict) -> None:
    """Persist config with TTL refresh."""
    get_redis().setex(_key(admin_id), _TTL, json.dumps(payload, separators=(",", ":")))


def _delete(admin_id: str) -> None:
    try:
        get_redis().delete(_key(admin_id))
    except Exception:
        pass


def _to_response(cfg: dict) -> dict:
    """Expand compact internal format to full API response."""
    if cfg.get("m") == "S":
        return {
            "mode":        "SPECIFIC",
            "tenant_id":   cfg.get("tid"),
            "tenant_name": cfg.get("tn"),
        }
    return {"mode": "ALL", "tenant_id": None, "tenant_name": None}


# ── Schemas ────────────────────────────────────────────────────

class TenantConfigResponse(BaseModel):
    mode:        str            # "ALL" | "SPECIFIC"
    tenant_id:   Optional[str]
    tenant_name: Optional[str]


class TenantConfigSet(BaseModel):
    mode:      str            # "ALL" | "SPECIFIC"
    tenant_id: Optional[str] = None   # required when mode == "SPECIFIC"


# ── Endpoints ──────────────────────────────────────────────────

@router.get("/tenant-config", response_model=TenantConfigResponse)
def get_tenant_config(
    auth: TokenPayload = Depends(require_auth),
) -> TenantConfigResponse:
    """Return the active tenant scope for the current admin session."""
    cfg = _read(auth.user_id)
    return TenantConfigResponse(**_to_response(cfg))


@router.put("/tenant-config", response_model=TenantConfigResponse)
def set_tenant_config(
    body: TenantConfigSet,
    auth: TokenPayload = Depends(require_auth),
    db: Session = Depends(get_db),
) -> TenantConfigResponse:
    """
    Set the active tenant scope.
    - mode='ALL'      → see data across all tenants (platform admin only)
    - mode='SPECIFIC' → scope all data views to tenant_id
    """
    if body.mode not in ("ALL", "SPECIFIC"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="mode must be 'ALL' or 'SPECIFIC'.")

    if body.mode == "SPECIFIC":
        if not body.tenant_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="tenant_id is required when mode is SPECIFIC.")
        try:
            tid_uuid = uuid.UUID(body.tenant_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="tenant_id must be a valid UUID.")

        # Verify tenant exists
        tenant = db.query(Tenant).filter(Tenant.tenant_id == tid_uuid).first()
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Tenant not found.")

        payload = {"m": "S", "tid": str(tid_uuid), "tn": tenant.tenant_name}
        _write(auth.user_id, payload)
        return TenantConfigResponse(**_to_response(payload))

    # mode == "ALL"
    _delete(auth.user_id)   # no record needed — default is ALL
    return TenantConfigResponse(mode="ALL", tenant_id=None, tenant_name=None)


@router.delete("/tenant-config", status_code=status.HTTP_204_NO_CONTENT)
def reset_tenant_config(auth: TokenPayload = Depends(require_auth)) -> None:
    """Reset scope to ALL (removes the Redis key)."""
    _delete(auth.user_id)
