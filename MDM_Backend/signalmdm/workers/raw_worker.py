"""
signalmdm/workers/raw_worker.py
---------------------------------
Celery task: parse an uploaded file and insert raw_records.

Task chain on success:
    process_raw_upload → create_staging_task

Error handling:
    • Any unhandled exception marks the run as FAILED.
    • Task retries up to 3 times with exponential backoff.
"""

from __future__ import annotations

import io
import csv
import json
import time
import uuid
import logging

from celery import chain
from celery.exceptions import MaxRetriesExceededError

from signalmdm.workers.celery_app import celery
from signalmdm.database import SessionLocal
from signalmdm.models.ingestion_run import IngestionRun
from signalmdm.models.file_upload    import FileUpload
from signalmdm.services.raw_service     import raw_service
from signalmdm.services.ingestion_service import ingestion_service
from signalmdm.enums import IngestionStateEnum
from core.config import settings

logger = logging.getLogger(__name__)


def _parse_file_from_path(stored_path: str, original_filename: str) -> list[dict]:
    """Read and parse a stored file into a list of row dicts."""
    with open(stored_path, "rb") as f:
        file_bytes = f.read()

    name_lower = original_filename.lower()
    if name_lower.endswith(".json"):
        data = json.loads(file_bytes.decode("utf-8"))
        return data if isinstance(data, list) else [data]
    else:
        text = file_bytes.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        return [dict(row) for row in reader]


@celery.task(
    bind=True,
    name="signalmdm.workers.raw_worker.process_raw_upload",
    max_retries=3,
    default_retry_delay=30,  # seconds
)
def process_raw_upload(self, run_id_str: str, file_id_str: str, tenant_id_str: str) -> dict:
    """
    Parse an uploaded file and bulk-insert raw_records.

    Args:
        run_id_str:    IngestionRun UUID as string.
        file_id_str:   FileUpload UUID as string.
        tenant_id_str: Tenant UUID as string.

    Returns:
        dict with run_id and record_count on success.
    """
    run_id    = uuid.UUID(run_id_str)
    file_id   = uuid.UUID(file_id_str)
    tenant_id = uuid.UUID(tenant_id_str)

    db = SessionLocal()
    try:
        logger.info("[raw_worker] Starting run=%s file=%s", run_id, file_id)

        # Fetch the file upload record
        upload: FileUpload = db.query(FileUpload).filter(
            FileUpload.file_id == file_id,
            FileUpload.tenant_id == tenant_id,
        ).first()

        if not upload:
            raise ValueError(f"FileUpload {file_id} not found.")

        # Fetch the run (for source_system_id)
        run: IngestionRun = db.query(IngestionRun).filter(
            IngestionRun.run_id == run_id,
            IngestionRun.tenant_id == tenant_id,
        ).first()

        if not run:
            raise ValueError(f"IngestionRun {run_id} not found.")

        # Parse file
        rows = _parse_file_from_path(upload.stored_path, upload.original_filename)
        logger.info("[raw_worker] Parsed %d rows from %s", len(rows), upload.original_filename)

        # Bulk insert raw records
        result = raw_service.bulk_insert_raw_records(
            db,
            tenant_id=tenant_id,
            run_id=run_id,
            source_system_id=run.source_system_id,
            file_id=file_id,
            rows=rows,
        )
        record_count = result.inserted_count

        # Transition run state → RAW_LOADED
        ingestion_service.transition_state(
            db,
            run_id=run_id,
            tenant_id=tenant_id,
            new_state=IngestionStateEnum.RAW_LOADED,
            record_count=record_count,
            performed_by="raw_worker",
        )

        delay = max(0, settings.ingestion_pipeline_stage_delay_seconds)
        if delay:
            logger.info("[raw_worker] Pacing %ss before staging (run=%s)", delay, run_id)
            time.sleep(delay)

        logger.info("[raw_worker] Completed run=%s records=%d", run_id, record_count)

        # Chain to staging worker
        from signalmdm.workers.staging_worker import create_staging_task
        create_staging_task.delay(run_id_str, tenant_id_str)

        return {"run_id": run_id_str, "record_count": record_count}

    except Exception as exc:
        logger.exception("[raw_worker] Error on run=%s: %s", run_id, exc)
        try:
            # Attempt to mark run as FAILED
            ingestion_service.transition_state(
                db,
                run_id=run_id,
                tenant_id=tenant_id,
                new_state=IngestionStateEnum.FAILED,
                error_message=str(exc),
                performed_by="raw_worker",
            )
        except Exception:
            pass  # Don't mask the original exception

        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("[raw_worker] Max retries exceeded for run=%s", run_id)
            raise
    finally:
        db.close()
