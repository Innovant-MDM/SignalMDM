"""
signalmdm/routers/upload_router.py
-------------------------------------
REST API for the standalone Upload Session workflow.

Endpoints
---------
POST   /uploads/sessions               — create a new session (folder)
GET    /uploads/sessions               — list sessions for tenant
GET    /uploads/sessions/{session_id}  — get session + its files
POST   /uploads/sessions/{session_id}/files  — upload one or more files into a session
DELETE /uploads/sessions/{session_id}/files/{file_id} — remove a file

Notes
-----
- A session_name must be unique per tenant.
- record_count is populated server-side by counting CSV data rows.
- Files are stored under  storage/uploads/sessions/<session_id>/<uuid>_<original_name>
"""

from __future__ import annotations

import csv
import hashlib
import io
import logging
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Header, Query, UploadFile, status, Request
from fastapi.encoders import jsonable_encoder
from fastapi import Form
from sqlalchemy.orm import Session

from db.sessions.database import get_db
from middleware.auth import TokenPayload, require_auth
from db.models.upload_session import UploadSession, UploadSessionFile
from services.audit.audit_service import log_action
from schemas.common import ok
from schemas.upload_schema import (
    UploadSessionCreate,
    UploadSessionFileRead,
    UploadSessionRead,
    UploadSessionWithFiles,
)
from core.config import settings

router = APIRouter(prefix="/uploads", tags=["Upload Sessions"])

logger = logging.getLogger(__name__)

_MAX_FILE_MB = 100  # generous limit for upload-only (no immediate processing)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_tenant(auth: TokenPayload, x_tenant_id: str | None) -> str | uuid.UUID:
    """
    Returns the tenant UUID or the string "platform".
    """
    raw_tid = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        raw_tid = x_tenant_id
    
    if raw_tid == "platform":
        return "platform"
        
    try:
        return uuid.UUID(str(raw_tid))
    except (ValueError, TypeError):
        return raw_tid


def _count_csv_rows(file_bytes: bytes) -> int:
    """Return number of data rows (header excluded) in a CSV."""
    try:
        text = file_bytes.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        # Subtract 1 for header row; guard against empty files
        return max(0, len(rows) - 1)
    except Exception:
        return 0


def _session_read(session: UploadSession) -> dict:
    return UploadSessionRead(
        session_id=session.session_id,
        tenant_id=session.tenant_id,
        session_name=session.session_name,
        domain=session.domain,
        status=session.status,
        created_by=session.created_by,
        created_at=session.created_at,
        updated_at=session.updated_at,
        file_count=len(session.files),
    ).model_dump()


def _file_read(f: UploadSessionFile) -> dict:
    return UploadSessionFileRead(
        file_id=f.file_id,
        session_id=f.session_id,
        tenant_id=f.tenant_id,
        file_label=f.file_label,
        original_filename=f.original_filename,
        file_size_bytes=f.file_size_bytes,
        content_type=f.content_type,
        record_count=f.record_count,
        uploaded_by=f.uploaded_by,
        uploaded_at=f.uploaded_at,
    ).model_dump(mode="json")


def _enrich_session_files_with_duplicates(
    db: Session,
    tenant_id: str | uuid.UUID,
    files: list[UploadSessionFile],
) -> list[dict]:
    if not files:
        return []

    target_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
    checksums = [f.checksum_md5 for f in files if f.checksum_md5]
    
    first_seen_by_checksum = {}
    if checksums:
        candidates = (
            db.query(UploadSessionFile)
            .filter(
                UploadSessionFile.tenant_id == target_uuid,
                UploadSessionFile.checksum_md5.in_(checksums),
            )
            .order_by(UploadSessionFile.uploaded_at.asc())
            .all()
        )
        for c in candidates:
            key = c.checksum_md5
            if key and key not in first_seen_by_checksum:
                first_seen_by_checksum[key] = c

    enriched = []
    for f in files:
        origin = first_seen_by_checksum.get(f.checksum_md5)
        is_dup = origin is not None and origin.file_id != f.file_id

        read_obj = UploadSessionFileRead(
            file_id=f.file_id,
            session_id=f.session_id,
            tenant_id=f.tenant_id,
            file_label=f.file_label,
            original_filename=f.original_filename,
            file_size_bytes=f.file_size_bytes,
            content_type=f.content_type,
            record_count=f.record_count,
            uploaded_by=f.uploaded_by,
            uploaded_at=f.uploaded_at,
            is_duplicate=is_dup,
            first_uploaded_by=origin.uploaded_by if (is_dup and origin) else None,
            first_uploaded_at=origin.uploaded_at if (is_dup and origin) else None,
        )
        enriched.append(read_obj.model_dump(mode="json"))

    return enriched


# ---------------------------------------------------------------------------
# 1. Create upload session
# ---------------------------------------------------------------------------

@router.post(
    "/sessions",
    summary="Create a new upload session (folder)",
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    body: UploadSessionCreate,
    tenant_id_query: str | None = Query(None, alias="tenant_id"),
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """
    Create a named upload session (analogous to a folder).

    `session_name` must be unique per tenant — duplicate names return 409.
    """
    # DEBUG LOGS (Temporary)
    print(f"[DEBUG] create_session | Query tenant_id: {tenant_id_query}")
    print(f"[DEBUG] create_session | Header X-Tenant-ID: {x_tenant_id}")
    print(f"[DEBUG] create_session | Body: {body.model_dump()}")
    print(f"[DEBUG] create_session | auth.tenant_id: {auth.tenant_id}")

    # Priority: URL query param > X-Tenant-ID header > body tenant_id > JWT tenant_id
    raw_tid = (
        tenant_id_query
        or x_tenant_id
        or (str(body.tenant_id) if body.tenant_id else None)
        or (auth.tenant_id if auth.tenant_id != "platform" else None)
    )

    print(f"[DEBUG] create_session | raw_tid resolved: {raw_tid}")

    if not raw_tid or raw_tid == "platform":
        raise HTTPException(
            status_code=400,
            detail="[v1.0.4] No valid tenant ID found. Please select a tenant first.",
        )

    try:
        target_tenant = uuid.UUID(str(raw_tid))
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid tenant ID: {raw_tid}")

    # Uniqueness check
    existing = (
        db.query(UploadSession)
        .filter(
            UploadSession.tenant_id == target_tenant,
            UploadSession.session_name == body.session_name,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session name '{body.session_name}' already exists for this tenant.",
        )

    session = UploadSession(
        tenant_id=target_tenant,
        session_name=body.session_name,
        domain=body.domain,
        status="OPEN",
        created_by=auth.username,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return ok(data=_session_read(session), message="Upload session created.")


# ---------------------------------------------------------------------------
# 2. List upload sessions
# ---------------------------------------------------------------------------

@router.get(
    "/sessions",
    summary="List upload sessions for the tenant",
)
def list_sessions(
    skip: int = 0,
    limit: int = 50,
    tenant_id_query: str | None = Query(None, alias="tenant_id"),
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    raw_tid = (
        tenant_id_query
        or x_tenant_id
        or (auth.tenant_id if auth.tenant_id != "platform" else None)
    )
    target_tenant = _resolve_tenant(auth, raw_tid)

    query = db.query(UploadSession)
    
    # If not platform admin, or if specific tenant is selected, filter by tenant
    if target_tenant != "platform":
        query = query.filter(UploadSession.tenant_id == target_tenant)
    
    sessions = (
        query.order_by(UploadSession.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return ok(
        data=[_session_read(s) for s in sessions],
        message=f"{len(sessions)} session(s) found.",
    )


# ---------------------------------------------------------------------------
# 3. Get session + files
# ---------------------------------------------------------------------------

@router.get(
    "/sessions/{session_id}",
    summary="Get a single upload session with its files",
)
def get_session(
    session_id: uuid.UUID,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = _resolve_tenant(auth, x_tenant_id)
    
    query = db.query(UploadSession).filter(UploadSession.session_id == session_id)
    if target_tenant != "platform":
        query = query.filter(UploadSession.tenant_id == target_tenant)

    session = query.first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    enriched_files = _enrich_session_files_with_duplicates(db, session.tenant_id, session.files)
    result_dict = {
        "session_id": session.session_id,
        "tenant_id": session.tenant_id,
        "session_name": session.session_name,
        "domain": session.domain,
        "status": session.status,
        "created_by": session.created_by,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "file_count": len(session.files),
        "files": enriched_files,
    }
    return ok(data=jsonable_encoder(result_dict), message="Session loaded.")


# ---------------------------------------------------------------------------
# 4. Delete a session
# ---------------------------------------------------------------------------

@router.delete(
    "/sessions/{session_id}",
    summary="Delete an upload session and all files",
)
def delete_session(
    session_id: uuid.UUID,
    request: Request,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = _resolve_tenant(auth, x_tenant_id)

    query = db.query(UploadSession).filter(UploadSession.session_id == session_id)
    if target_tenant != "platform":
        query = query.filter(UploadSession.tenant_id == target_tenant)

    session = query.first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Best-effort disk cleanup for all files in this session.
    for f in session.files:
        try:
            if os.path.exists(f.stored_path):
                os.remove(f.stored_path)
        except OSError as exc:
            logger.warning("[upload] Could not delete session file from disk: %s", exc)

    old_val = jsonable_encoder(_session_read(session))
    db.delete(session)

    try:
        with db.begin_nested():
            log_action(
                db,
                tenant_id=uuid.UUID(str(target_tenant)) if target_tenant != "platform" else None,
                entity_name="UploadSession",
                entity_id=session_id,
                operation_type="DELETE",
                old_value=old_val,
                performed_by=auth.username,
                source_ip=request.client.host if request.client else None,
                autocommit=False,
            )
            db.flush()
    except Exception as e:
        logger.error("Failed to write audit log for UploadSession delete: %s", e)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Failed to commit UploadSession delete: %s", e)
        raise HTTPException(status_code=500, detail="Could not delete session.") from e

    return ok(message="Session removed.")


# ---------------------------------------------------------------------------
# 5. Upload files into a session
# ---------------------------------------------------------------------------

@router.post(
    "/sessions/{session_id}/files",
    summary="Upload one or more files into an upload session",
    status_code=status.HTTP_201_CREATED,
)
async def upload_files_to_session(
    session_id: uuid.UUID,
    request: Request,
    files: list[UploadFile] = File(...),
    file_labels: list[str] = Form(..., description="Labels for each file (same order as files)"),
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """
    Upload one or more CSV/JSON files into an existing session.

    `file_labels` is a comma-separated string, one label per file
    (same positional order as the multipart `files` list).
    """
    target_tenant = _resolve_tenant(auth, x_tenant_id)

    # Platform admins MUST specify a tenant to upload files or see details
    if target_tenant == "platform":
         raise HTTPException(status_code=400, detail="Platform admin must provide X-Tenant-ID header.")

    session = (
        db.query(UploadSession)
        .filter(
            UploadSession.session_id == session_id,
            UploadSession.tenant_id == target_tenant,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.status != "OPEN":
        raise HTTPException(status_code=400, detail="Session is closed; cannot upload more files.")

    labels = [lbl.strip() for lbl in file_labels]
    if len(labels) != len(files):
        raise HTTPException(
            status_code=400,
            detail=f"Mismatch: {len(files)} file(s) but {len(labels)} label(s) provided.",
        )

    upload_dir = os.path.join(
        os.getcwd(),
        getattr(settings, "upload_dir", "storage/uploads"),
        "sessions",
        str(session_id),
    )
    os.makedirs(upload_dir, exist_ok=True)

    uploaded_objs: list[UploadSessionFile] = []

    for upload_file, label in zip(files, labels):
        file_bytes = await upload_file.read()

        # Sanitization
        raw_filename = upload_file.filename or "upload"
        fname = os.path.basename(raw_filename)
        if not fname or fname in (".", ".."):
            fname = "upload"

        # Size check
        size_mb = len(file_bytes) / (1024 * 1024)
        if size_mb > _MAX_FILE_MB:
            raise HTTPException(
                status_code=413,
                detail=f"File '{fname}' exceeds {_MAX_FILE_MB} MB limit.",
            )
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail=f"File '{fname}' is empty.")

        # Detect file type
        ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
        if ext not in ("csv", "json", "xlsx"):
            raise HTTPException(
                status_code=400,
                detail=f"File '{fname}' is not CSV, JSON, or XLSX.",
            )

        # Count records
        record_count = _count_csv_rows(file_bytes) if ext == "csv" else None

        # Checksum
        md5 = hashlib.md5(file_bytes).hexdigest()

        # Save to disk
        safe_name = f"{uuid.uuid4()}_{fname}"
        stored_path = os.path.join(upload_dir, safe_name)
        with open(stored_path, "wb") as fh:
            fh.write(file_bytes)

        # Persist metadata
        sf = UploadSessionFile(
            session_id=session.session_id,
            tenant_id=uuid.UUID(target_tenant) if isinstance(target_tenant, str) else target_tenant,
            file_label=label,
            original_filename=fname,
            stored_path=stored_path,
            file_size_bytes=len(file_bytes),
            content_type=upload_file.content_type or "application/octet-stream",
            record_count=record_count,
            checksum_md5=md5,
            uploaded_by=auth.username,
        )
        db.add(sf)
        db.flush()  # get file_id without committing
        uploaded_objs.append(sf)

        try:
            log_action(
                db,
                tenant_id=uuid.UUID(str(target_tenant)) if target_tenant != "platform" else None,
                entity_name="UploadSessionFile",
                entity_id=sf.file_id,
                operation_type="UPLOAD",
                new_value={"filename": fname, "size": len(file_bytes), "status": "Success"},
                performed_by=auth.username,
                source_ip=request.client.host if request.client else None,
                autocommit=False,
            )
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    db.commit()

    enriched_uploaded = _enrich_session_files_with_duplicates(db, session.tenant_id, uploaded_objs)

    return ok(
        data={"session_id": str(session_id), "uploaded": enriched_uploaded},
        message=f"{len(enriched_uploaded)} file(s) uploaded to session '{session.session_name}'.",
    )


# ---------------------------------------------------------------------------
# 6. Delete a file from a session
# ---------------------------------------------------------------------------

@router.delete(
    "/sessions/{session_id}/files/{file_id}",
    summary="Remove a file from an upload session",
)
def delete_file(
    session_id: uuid.UUID,
    file_id: uuid.UUID,
    request: Request,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    target_tenant = _resolve_tenant(auth, x_tenant_id)
    
    query = (
        db.query(UploadSessionFile)
        .join(UploadSession)
        .filter(
            UploadSessionFile.file_id == file_id,
            UploadSessionFile.session_id == session_id,
        )
    )
    if target_tenant != "platform":
        query = query.filter(UploadSession.tenant_id == target_tenant)

    sf = query.first()
    if not sf:
        raise HTTPException(status_code=404, detail="File not found in session.")

    # Attempt to remove from disk (best-effort)
    try:
        if os.path.exists(sf.stored_path):
            os.remove(sf.stored_path)
    except OSError as exc:
        logger.warning("[upload] Could not delete file from disk: %s", exc)

    old_val = jsonable_encoder(_file_read(sf))
    db.delete(sf)

    # Best-effort audit. Isolated in a SAVEPOINT so any failure on the
    # audit_log write (schema drift, constraint, etc.) cannot fail the
    # user-facing file deletion. The outer transaction stays valid.
    try:
        with db.begin_nested():
            log_action(
                db,
                tenant_id=uuid.UUID(str(target_tenant)) if target_tenant != "platform" else None,
                entity_name="UploadSessionFile",
                entity_id=file_id,
                operation_type="DELETE",
                old_value=old_val,
                performed_by=auth.username,
                source_ip=request.client.host if request.client else None,
                autocommit=False,
            )
            db.flush()
    except Exception as e:
        logger.error("Failed to write audit log for UploadSessionFile delete: %s", e)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Failed to commit UploadSessionFile delete: %s", e)
        raise HTTPException(status_code=500, detail="Could not delete file.") from e

    return ok(message="File removed from session.")
