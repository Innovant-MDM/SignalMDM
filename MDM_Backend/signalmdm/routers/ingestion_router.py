"""
signalmdm/routers/ingestion_router.py
---------------------------------------
API endpoints for the ingestion pipeline.

Flow:
  1. POST /ingestion/start              → create IngestionRun (CREATED)
  2. POST /ingestion/{run_id}/upload    → upload file → trigger async raw worker
  3. GET  /ingestion/{run_id}/status    → poll state + counts

Security:
  All endpoints require a valid encrypted JWT (via require_auth).
  tenant_id is extracted from the verified JWT payload.
"""

from __future__ import annotations

import io
import json
import logging
import os
import time
import uuid
import csv
import traceback

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Header, status, Request
from sqlalchemy.orm import Session

from signalmdm.database import SessionLocal, get_db
from signalmdm.services.audit_service import log_action
from signalmdm.schemas.ingestion_schema import (
    IngestionRunCreate,
    IngestionRunFromSessionCreate,
    IngestionRunRead,
    IngestionLineageRunSummary,
    IngestionResolveConfigRead,
    IngestionStatusRead,
    IngestionRunFileItem,
)
from signalmdm.models.upload_session import UploadSessionFile
from signalmdm.models.tenant import Tenant
from signalmdm.schemas.common import ok
from signalmdm.services.ingestion_service import ingestion_service
from signalmdm.services.raw_service import raw_service
from signalmdm.services.staging_service import staging_service
from signalmdm.enums import IngestionStateEnum
from signalmdm.middleware.auth import TokenPayload, require_auth
from core.config import settings

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])

logger = logging.getLogger(__name__)

_MAX_FILE_MB = 50


# ---------------------------------------------------------------------------
# 1. Start ingestion run
# ---------------------------------------------------------------------------

@router.post(
    "/start",
    summary="Initiate a new ingestion run",
    status_code=status.HTTP_201_CREATED,
)
def start_ingestion(
    body: IngestionRunCreate,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """
    Start a new run for a specific SourceSystem.
    
    - If logged in as SuperAdmin (platform), must specify X-Tenant-ID.
    """
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    run = ingestion_service.create_run(
        db,
        tenant_id=target_tenant,
        data=body,
        performed_by=auth.user_id,
    )
    tenant_names = ingestion_service.tenant_names_for(db, [run.tenant_id])
    return ok(
        data=IngestionRunRead.from_orm_run(
            run, tenant_name=tenant_names.get(run.tenant_id)
        ).model_dump(),
        message="Ingestion run started.",
    )


@router.get(
    "/lineage-summary",
    summary="Per-run raw vs staging counts and entity labels",
)
def ingestion_lineage_summary(
    limit: int = 50,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """
    Use this to compare Raw Landing and Staging when multiple ingestion runs exist.

    Each run is tagged with ``entity_type`` from its upload session. Staging should be
    1:1 with raw for completed pipelines.
    """
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    rows = ingestion_service.lineage_summary(db, target_tenant, limit=limit)
    data = [IngestionLineageRunSummary.model_validate(r).model_dump(mode="json") for r in rows]
    return ok(data=data, message=f"{len(data)} run(s) in lineage summary.")


@router.get(
    "/resolve-config",
    summary="Preview auto-resolved entity, run type, and trigger for a session + source",
)
def resolve_ingestion_config(
    upload_session_id: uuid.UUID,
    source_system_id: uuid.UUID,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """
    Returns how the server will configure an ingestion run — no manual dropdowns needed.

    Entity comes from the upload session **domain** (validated against source supported entities).
    Run type is **INITIAL_LOAD** or **DELTA_LOAD** based on prior completed runs for that source.
    Trigger is **MANUAL** when started from the UI.
    """
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    resolved = ingestion_service.resolve_config_for_session(
        db,
        target_tenant,
        upload_session_id=upload_session_id,
        source_system_id=source_system_id,
    )
    return ok(
        data=IngestionResolveConfigRead.model_validate(resolved).model_dump(),
        message="Ingestion settings resolved from session and source.",
    )


@router.post(
    "/start-from-session",
    summary="Start ingestion from a completed upload session",
    status_code=status.HTTP_201_CREATED,
)
def start_ingestion_from_session(
    body: IngestionRunFromSessionCreate,
    background_tasks: BackgroundTasks,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """
    Create an ingestion run and process all files already stored in an upload session.

  Use this after files are uploaded on the Upload Data screen.
    """
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    run, session_files = ingestion_service.create_run_from_session(
        db,
        tenant_id=target_tenant,
        data=body,
        performed_by=auth.user_id,
    )

    ingestion_service.transition_state(
        db,
        run_id=run.run_id,
        tenant_id=target_tenant,
        new_state=IngestionStateEnum.RUNNING,
        file_count=len(session_files),
        performed_by=auth.user_id,
    )

    background_tasks.add_task(
        _ingest_session_files_pipeline,
        run.run_id,
        target_tenant,
        [str(f.file_id) for f in session_files],
    )

    delay = settings.ingestion_pipeline_stage_delay_seconds
    tenant_names = ingestion_service.tenant_names_for(db, [run.tenant_id])
    return ok(
        data=IngestionRunRead.from_orm_run(
            run, tenant_name=tenant_names.get(run.tenant_id)
        ).model_dump(),
        message=(
            f"Ingestion started from upload session ({len(session_files)} file(s)). "
            f"Pipeline running in background (~{delay}s between major states)."
        ),
    )


# ---------------------------------------------------------------------------
# 2. Upload file and trigger async processing
# ---------------------------------------------------------------------------

@router.post(
    "/{run_id}/upload",
    summary="Upload a CSV or JSON file for an ingestion run",
)
def upload_file(
    run_id: uuid.UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """
    Upload a data file (CSV or JSON) to an existing ingestion run.

    **Triggers the async raw-processing worker** which will:
    1. Parse the file rows
    2. Insert raw_records with checksums
    3. Transition run → RAW_LOADED
    4. Chain staging worker → STAGING_CREATED → COMPLETED
    """
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    # Verify run exists and is in an acceptable state
    run = ingestion_service.get_run(db, tenant_id=target_tenant, run_id=run_id)
    # Allow uploads while run is still accepting files (including paced RAW_LOADED window)
    if run.state not in (
        IngestionStateEnum.CREATED,
        IngestionStateEnum.RUNNING,
        IngestionStateEnum.RAW_LOADED,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot upload to a run in state '{run.state}'.",
        )

    # Read file bytes
    file_bytes = file.file.read()
    file_size_mb = len(file_bytes) / (1024 * 1024)
    if file_size_mb > _MAX_FILE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {_MAX_FILE_MB} MB limit.",
        )

    # Ensure storage directory exists
    upload_dir = os.path.join(os.getcwd(), settings.upload_dir, str(run_id))
    os.makedirs(upload_dir, exist_ok=True)

    # Save file to disk (UUID-prefixed to avoid collisions)
    safe_filename = f"{uuid.uuid4()}_{file.filename}"
    stored_path = os.path.join(upload_dir, safe_filename)
    with open(stored_path, "wb") as f:
        f.write(file_bytes)

    # Persist file metadata
    file_upload = raw_service.save_file_upload(
        db,
        tenant_id=target_tenant,
        run_id=run_id,
        original_filename=file.filename or "upload",
        stored_path=stored_path,
        file_bytes=file_bytes,
        content_type=file.content_type or "application/octet-stream",
    )

    try:
        log_action(
            db,
            tenant_id=uuid.UUID(str(target_tenant)) if target_tenant != "platform" else None,
            entity_name="IngestionUpload",
            entity_id=file_upload.file_id,
            operation_type="UPLOAD",
            new_value={"filename": file.filename, "size": len(file_bytes), "status": "Success"},
            performed_by=auth.username,
            source_ip=request.client.host if request.client else None,
        )
    except Exception as e:
        logger.error(f"Failed to log upload action: {e}")

    # Transition run → RUNNING and increment file count
    ingestion_service.transition_state(
        db,
        run_id=run_id,
        tenant_id=target_tenant,
        new_state=IngestionStateEnum.RUNNING,
        file_count=run.file_count + 1,
        performed_by=auth.user_id,
    )

    # Trigger processing
    async_triggered = False
    if settings.celery_enabled:
        try:
            from signalmdm.workers.raw_worker import process_raw_upload
            process_raw_upload.delay(
                str(run_id),
                str(file_upload.file_id),
                str(target_tenant),
            )
            async_triggered = True
        except Exception:
            async_triggered = False

    if not async_triggered:
        # Return immediately in RUNNING; finish RAW → STAGING → COMPLETED in background with pacing
        background_tasks.add_task(
            _paced_sync_pipeline,
            run_id,
            file_upload.file_id,
            target_tenant,
            file_bytes,
            file.filename or "upload",
        )

    delay = settings.ingestion_pipeline_stage_delay_seconds
    return ok(
        data={
            "run_id": str(run_id),
            "file_id": str(file_upload.file_id),
            "filename": file.filename,
            "size_bytes": len(file_bytes),
            "async_processing": async_triggered,
            "stage_delay_seconds": delay,
        },
        message=(
            f"File uploaded. Celery pipeline started (~{delay}s pacing between major states)."
            if async_triggered
            else (
                f"File uploaded. Pipeline running in background (~{delay}s between "
                f"RUNNING → RAW_LOADED → STAGING_CREATED → COMPLETED)."
            )
        ),
    )


def _paced_sync_pipeline(
    run_id: uuid.UUID,
    file_id: uuid.UUID,
    tenant_id: str,
    file_bytes: bytes,
    filename: str,
) -> None:
    """
    Finish ingestion after HTTP response (run already RUNNING).

    Inserts pauses between transitions so clients can observe each state
    (default ~20s each stage ≈ 1 minute total before COMPLETED).
    """
    delay = max(0, settings.ingestion_pipeline_stage_delay_seconds)
    db = SessionLocal()
    try:
        from signalmdm.models.ingestion_run import IngestionRun

        time.sleep(delay)
        run = db.query(IngestionRun).filter(IngestionRun.run_id == run_id).first()
        if not run:
            logger.warning("[ingestion] paced sync: run %s gone", run_id)
            return

        rows = _parse_file(file_bytes, filename)
        result = raw_service.bulk_insert_raw_records(
            db,
            tenant_id=tenant_id,
            run_id=run_id,
            source_system_id=run.source_system_id,
            file_id=file_id,
            rows=rows,
        )
        record_count = result.inserted_count
        
        try:
            log_action(
                db,
                tenant_id=uuid.UUID(str(tenant_id)) if tenant_id != "platform" else None,
                entity_name="IngestionPipeline",
                entity_id=run_id,
                operation_type="PROCESS_RAW",
                new_value={"status": "Success", "records_processed": record_count},
                performed_by="system",
            )
        except Exception:
            pass

        ingestion_service.transition_state(
            db,
            run_id=run_id,
            tenant_id=tenant_id,
            new_state=IngestionStateEnum.RAW_LOADED,
            record_count=record_count,
            performed_by="sync_pipeline",
        )

        time.sleep(delay)
        staging_service.create_staging_from_run(
            db,
            run_id=run_id,
            tenant_id=tenant_id,
            source_system_id=run.source_system_id,
        )
        ingestion_service.transition_state(
            db,
            run_id=run_id,
            tenant_id=tenant_id,
            new_state=IngestionStateEnum.STAGING_CREATED,
            performed_by="sync_pipeline",
        )

        time.sleep(delay)
        ingestion_service.transition_state(
            db,
            run_id=run_id,
            tenant_id=tenant_id,
            new_state=IngestionStateEnum.COMPLETED,
            performed_by="sync_pipeline",
        )
    except Exception as exc:
        logger.exception("[ingestion] paced sync failed run=%s: %s", run_id, exc)
        try:
            log_action(
                db,
                tenant_id=uuid.UUID(str(tenant_id)) if tenant_id != "platform" else None,
                entity_name="IngestionPipeline",
                entity_id=run_id,
                operation_type="PROCESS_ERROR",
                new_value={"error": str(exc), "traceback": traceback.format_exc()},
                performed_by="system",
            )
        except Exception:
            pass
        try:
            ingestion_service.transition_state(
                db,
                run_id=run_id,
                tenant_id=tenant_id,
                new_state=IngestionStateEnum.FAILED,
                error_message=str(exc),
                performed_by="sync_pipeline",
            )
        except Exception:
            pass
    finally:
        db.close()


def _parse_file(file_bytes: bytes, filename: str) -> list[dict]:
    if filename.lower().endswith(".json"):
        data = json.loads(file_bytes.decode("utf-8"))
        return data if isinstance(data, list) else [data]
    text = file_bytes.decode("utf-8")
    return [dict(row) for row in csv.DictReader(io.StringIO(text))]


def _parse_file_from_path(stored_path: str, filename: str) -> list[dict]:
    with open(stored_path, "rb") as fh:
        return _parse_file(fh.read(), filename)


def _ingest_session_files_pipeline(
    run_id: uuid.UUID,
    tenant_id: str,
    session_file_ids: list[str],
) -> None:
    """
    Read upload-session files from disk, insert raw records, then staging + complete.
    """
    delay = max(0, settings.ingestion_pipeline_stage_delay_seconds)
    db = SessionLocal()
    try:
        from signalmdm.models.ingestion_run import IngestionRun

        time.sleep(delay)
        run = db.query(IngestionRun).filter(IngestionRun.run_id == run_id).first()
        if not run:
            logger.warning("[ingestion] session pipeline: run %s gone", run_id)
            return

        tenant_uuid = uuid.UUID(str(tenant_id))
        total_records = 0
        files_processed = 0

        for file_id_str in session_file_ids:
            sf: UploadSessionFile | None = (
                db.query(UploadSessionFile)
                .filter(UploadSessionFile.file_id == uuid.UUID(file_id_str))
                .first()
            )
            if not sf or not os.path.isfile(sf.stored_path):
                logger.warning("[ingestion] session file missing: %s", file_id_str)
                continue

            with open(sf.stored_path, "rb") as fh:
                file_bytes = fh.read()

            upload_dir = os.path.join(os.getcwd(), settings.upload_dir, str(run_id))
            os.makedirs(upload_dir, exist_ok=True)
            safe_name = f"{uuid.uuid4()}_{sf.original_filename}"
            run_stored_path = os.path.join(upload_dir, safe_name)
            with open(run_stored_path, "wb") as out:
                out.write(file_bytes)

            file_upload = raw_service.save_file_upload(
                db,
                tenant_id=tenant_uuid,
                run_id=run_id,
                original_filename=sf.original_filename,
                stored_path=run_stored_path,
                file_bytes=file_bytes,
                content_type=sf.content_type or "application/octet-stream",
            )

            rows = _parse_file_from_path(sf.stored_path, sf.original_filename)
            if not rows:
                logger.warning("[ingestion] no rows parsed from %s", sf.original_filename)
                continue

            result = raw_service.bulk_insert_raw_records(
                db,
                tenant_id=tenant_uuid,
                run_id=run_id,
                source_system_id=run.source_system_id,
                file_id=file_upload.file_id,
                rows=rows,
            )
            count = result.inserted_count
            total_records += count
            files_processed += 1

            try:
                log_action(
                    db,
                    tenant_id=tenant_uuid if tenant_id != "platform" else None,
                    entity_name="IngestionPipeline",
                    entity_id=run_id,
                    operation_type="PROCESS_RAW",
                    new_value={"status": "Success", "records_processed": count, "filename": sf.original_filename},
                    performed_by="system",
                )
            except Exception:
                pass

        if files_processed == 0:
            raise ValueError("No session files could be parsed into raw records.")

        ingestion_service.transition_state(
            db,
            run_id=run_id,
            tenant_id=tenant_id,
            new_state=IngestionStateEnum.RAW_LOADED,
            record_count=total_records,
            file_count=files_processed,
            performed_by="session_pipeline",
        )

        time.sleep(delay)
        staging_service.create_staging_from_run(
            db,
            run_id=run_id,
            tenant_id=tenant_id,
            source_system_id=run.source_system_id,
        )
        ingestion_service.transition_state(
            db,
            run_id=run_id,
            tenant_id=tenant_id,
            new_state=IngestionStateEnum.STAGING_CREATED,
            performed_by="session_pipeline",
        )

        time.sleep(delay)
        ingestion_service.transition_state(
            db,
            run_id=run_id,
            tenant_id=tenant_id,
            new_state=IngestionStateEnum.COMPLETED,
            performed_by="session_pipeline",
        )
    except Exception as exc:
        logger.exception("[ingestion] session pipeline failed run=%s: %s", run_id, exc)
        try:
            log_action(
                db,
                tenant_id=uuid.UUID(str(tenant_id)) if tenant_id != "platform" else None,
                entity_name="IngestionPipeline",
                entity_id=run_id,
                operation_type="PROCESS_ERROR",
                new_value={"error": str(exc), "traceback": traceback.format_exc()},
                performed_by="system",
            )
        except Exception:
            pass
        try:
            ingestion_service.transition_state(
                db,
                run_id=run_id,
                tenant_id=tenant_id,
                new_state=IngestionStateEnum.FAILED,
                error_message=str(exc),
                performed_by="session_pipeline",
            )
        except Exception:
            pass
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 3. Status endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/{run_id}/status",
    summary="Get the status of an ingestion run",
)
def get_status(
    run_id: uuid.UUID,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """Poll the current state of an ingestion run."""
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id
        
    run = ingestion_service.get_run(db, tenant_id=target_tenant, run_id=run_id)
    staging_count = staging_service.count_staging_for_run(
        db, run_id=run_id, tenant_id=target_tenant)
    tenant_names = ingestion_service.tenant_names_for(db, [run.tenant_id])
    payload = IngestionRunRead.from_orm_run(
        run, tenant_name=tenant_names.get(run.tenant_id)
    ).model_dump()
    payload["staging_count"] = staging_count
    return ok(
        data=payload,
        message=f"Run is {run.state}.",
    )


@router.delete(
    "/{run_id}",
    summary="Delete an ingestion run and all raw/staging data for that run",
)
def delete_ingestion_run(
    run_id: uuid.UUID,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """Permanently remove the run and cascaded file, raw, and staging records."""
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    ingestion_service.delete_run(
        db,
        tenant_id=target_tenant,
        run_id=run_id,
        performed_by=auth.user_id,
    )
    return ok(message="Ingestion run deleted.")


@router.post(
    "/{run_id}/cancel",
    summary="Cancel an ongoing ingestion run",
)
def cancel_run(
    run_id: uuid.UUID,
    request: Request,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """Transition a run to FAILED state manually."""
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id
        
    run = ingestion_service.transition_state(
        db,
        run_id=run_id,
        tenant_id=target_tenant,
        new_state=IngestionStateEnum.FAILED,
        error_message="Cancelled by user",
        performed_by=auth.user_id,
    )
    
    try:
        log_action(
            db,
            tenant_id=uuid.UUID(str(target_tenant)) if target_tenant != "platform" else None,
            entity_name="IngestionRun",
            entity_id=run_id,
            operation_type="CANCEL",
            new_value={"status": "FAILED", "reason": "Cancelled by user"},
            performed_by=auth.username,
            source_ip=request.client.host if request.client else None,
        )
    except Exception as e:
        logger.error(f"Failed to log cancel action: {e}")
        
    return ok(message="Ingestion run cancelled.")


@router.get(
    "/",
    summary="List all ingestion runs for the authenticated tenant",
)
def list_runs(
    skip: int = 0,
    limit: int = 20,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """List recent ingestion runs for the tenant, newest first."""
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    runs = ingestion_service.list_runs(db, tenant_id=target_tenant, skip=skip, limit=limit)
    tenant_names = ingestion_service.tenant_names_for(db, [r.tenant_id for r in runs])
    return ok(
        data=[
            IngestionRunRead.from_orm_run(
                r, tenant_name=tenant_names.get(r.tenant_id)
            ).model_dump()
            for r in runs
        ],
        message=f"{len(runs)} ingestion run(s) found.",
    )


@router.get(
    "/{run_id}/files",
    summary="List files attached to an ingestion run with upload/delete history and duplicate flags",
)
def list_run_files(
    run_id: uuid.UUID,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
    auth: TokenPayload = Depends(require_auth),
):
    """
    Returns FileUpload rows for the run, enriched with:
      * uploaded_by / uploaded_at (resolved from audit log when available)
      * deleted_by / deleted_at (resolved from DELETE entries in audit log)
      * is_duplicate + first_uploaded_by / first_uploaded_at when the
        file's checksum_md5 was already seen earlier within this tenant.
    """
    target_tenant = auth.tenant_id
    if auth.tenant_id == "platform" and x_tenant_id:
        target_tenant = x_tenant_id

    rows = ingestion_service.run_files_with_audit(
        db,
        tenant_id=target_tenant,
        run_id=run_id,
    )
    data = [IngestionRunFileItem.model_validate(r).model_dump(mode="json") for r in rows]
    return ok(
        data=data,
        message=f"{len(data)} file(s) for run {run_id}.",
    )
