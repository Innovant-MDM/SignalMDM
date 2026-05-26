"""
signalmdm/services/audit_service.py
-------------------------------------
Service for inserting records into the immutable audit_log table.

RULES:
  • Only INSERT — never UPDATE or DELETE audit rows.
  • Caller provides `performed_by`; defaults to "system" for worker jobs.
  • `old_value` / `new_value` must be plain dicts (or None).

Security:
  • performed_by, entity_name, source_ip, trace_id are sanitized before storage.
  • search terms in list_api_logs_page are LIKE-escaped.
  • operation_type filter uses exact-match (no LIKE) against an allowlist.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional, Union

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from db.models.audit import AuditLog
from db.models.tenant import Tenant
from db.enums import OperationTypeEnum
from utils.sanitize import (
    sanitize_string,
    sanitize_ip,
    sanitize_search,
    sanitize_entity_name,
    _MAX_PERFORMED_BY,
    _MAX_TRACE_ID,
)

import logging
logger = logging.getLogger(__name__)

# Allowlist for operation_type filter (prevents arbitrary values being passed)
_ALLOWED_OPERATION_TYPES: frozenset[str] = frozenset(
    v for v in vars(OperationTypeEnum).values()
    if isinstance(v, str) and not v.startswith("_")
)


def log_action(
    db: Session,
    *,
    tenant_id: Optional[uuid.UUID],
    entity_name: str,
    entity_id: Optional[uuid.UUID] = None,
    operation_type: str = OperationTypeEnum.INSERT,
    old_value: Optional[dict[str, Any]] = None,
    new_value: Optional[dict[str, Any]] = None,
    performed_by: str = "system",
    source_ip: Optional[str] = None,
    trace_id: Optional[str] = None,
    approved_by: Optional[str] = None,
    approval_reason: Optional[str] = None,
    autocommit: bool = True,
) -> AuditLog:
    """
    Insert a single audit log entry.

    All string control fields are sanitized before persistence.

    Args:
        db:             Active SQLAlchemy session.
        tenant_id:      Tenant UUID (None for platform-level events).
        entity_name:    Name of the table / domain object changed.
        entity_id:      PK of the changed record (stored, not a real FK).
        operation_type: INSERT / UPDATE / DELETE / MERGE.
        old_value:      Row snapshot before the operation.
        new_value:      Row snapshot after the operation.
        performed_by:   Username or "system".
        source_ip:      Optional client IP address.
        trace_id:       Optional distributed trace correlation ID.
        autocommit:     Flush + commit immediately (default True).
                        Set False when batching inside a transaction.

    Returns:
        The inserted AuditLog instance.
    """
    # --- Sanitize control fields -------------------------------------------
    try:
        clean_entity_name = sanitize_entity_name(entity_name)
    except ValueError:
        # Never block an audit write over a naming issue — fall back gracefully
        logger.warning("[audit_service] Unexpected entity_name %r — using as-is", entity_name)
        clean_entity_name = str(entity_name)[:_MAX_TRACE_ID]

    clean_performed_by = sanitize_string(
        performed_by, "performed_by",
        max_length=_MAX_PERFORMED_BY,
        required=False,
    ) or "system"

    clean_source_ip = sanitize_ip(source_ip)

    clean_trace_id = sanitize_string(
        trace_id, "trace_id",
        max_length=_MAX_TRACE_ID,
        required=False,
    ) or None
    
    clean_approved_by = sanitize_string(
        approved_by, "approved_by",
        max_length=150,
        required=False,
    ) or None
    
    clean_approval_reason = sanitize_string(
        approval_reason, "approval_reason",
        max_length=500,
        required=False,
    ) or None

    log = AuditLog(
        audit_id=uuid.uuid4(),
        tenant_id=tenant_id,
        entity_name=clean_entity_name,
        entity_id=entity_id,
        operation_type=operation_type,
        old_value=old_value,
        new_value=new_value,
        performed_by=clean_performed_by,
        source_ip=clean_source_ip,
        trace_id=clean_trace_id,
        approved_by=clean_approved_by,
        approval_reason=clean_approval_reason,
    )
    db.add(log)
    if autocommit:
        db.commit()
        db.refresh(log)
    return log


def _parse_tenant_id(tenant_id: Union[str, uuid.UUID]) -> Optional[uuid.UUID]:
    if tenant_id == "platform":
        return None
    if isinstance(tenant_id, uuid.UUID):
        return tenant_id
    return uuid.UUID(str(tenant_id))


def list_api_logs_page(
    db: Session,
    *,
    tenant_id: Union[str, uuid.UUID],
    skip: int = 0,
    limit: int = 100,
    operation_type: Optional[str] = None,
    entity_name: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[dict[str, Any]], int]:
    """
    Paginated audit_log rows for the API Logs admin screen (newest first).

    Security:
      - `search` is LIKE-escaped and injection-scanned.
      - `operation_type` is validated against the allowlist.
      - `entity_name` is injection-scanned.
      - `skip` / `limit` are bounds-checked.
    """
    # Bounds-check pagination
    skip  = max(0, int(skip))
    limit = max(1, min(int(limit), 500))

    # Sanitize filter inputs
    safe_search = sanitize_search(search)

    clean_operation_type: Optional[str] = None
    if operation_type and operation_type.strip():
        candidate = operation_type.strip().upper()
        if candidate in _ALLOWED_OPERATION_TYPES:
            clean_operation_type = candidate
        else:
            logger.warning("[audit_service] Unknown operation_type filter: %r", candidate)

    clean_entity_name: Optional[str] = None
    if entity_name and entity_name.strip():
        try:
            clean_entity_name = sanitize_entity_name(entity_name.strip())
        except ValueError:
            logger.warning("[audit_service] Invalid entity_name filter: %r", entity_name)

    tid = _parse_tenant_id(tenant_id)
    q = db.query(AuditLog, Tenant.tenant_name).outerjoin(
        Tenant, Tenant.tenant_id == AuditLog.tenant_id
    )
    if tid is not None:
        q = q.filter(AuditLog.tenant_id == tid)
    if clean_operation_type:
        q = q.filter(AuditLog.operation_type == clean_operation_type)
    if clean_entity_name:
        q = q.filter(AuditLog.entity_name == clean_entity_name)
    if safe_search:
        term = f"%{safe_search}%"
        q = q.filter(
            or_(
                cast(AuditLog.audit_id, String).ilike(term),
                cast(AuditLog.entity_id, String).ilike(term),
                AuditLog.entity_name.ilike(term),
                AuditLog.performed_by.ilike(term),
                AuditLog.source_ip.ilike(term),
                AuditLog.trace_id.ilike(term),
            )
        )

    total = q.count()
    rows = (
        q.order_by(AuditLog.performed_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    out: list[dict[str, Any]] = []
    for log, tenant_name in rows:
        out.append(
            {
                "audit_id":       log.audit_id,
                "tenant_id":      log.tenant_id,
                "tenant_name":    tenant_name,
                "entity_name":    log.entity_name,
                "entity_id":      log.entity_id,
                "operation_type": log.operation_type,
                "old_value":      log.old_value,
                "new_value":      log.new_value,
                "performed_by":   log.performed_by,
                "performed_at":   log.performed_at,
                "source_ip":      log.source_ip,
                "trace_id":       log.trace_id,
                "approved_by":    log.approved_by,
                "approval_reason": log.approval_reason,
            }
        )
    return out, total
