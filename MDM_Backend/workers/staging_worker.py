"""
signalmdm/workers/staging_worker.py
--------------------------------------
Celery task: create staging_entities from raw_records.

Called automatically by raw_worker on success, or can be triggered
manually to re-run staging for a run already in RAW_LOADED state.
"""

from __future__ import annotations

import uuid
import logging
import time

from celery.exceptions import MaxRetriesExceededError

from workers.celery_app import celery
from db.sessions.database import SessionLocal
from db.models.ingestion_run import IngestionRun
from services.staging.staging_service   import staging_service
from services.ingestion.ingestion_service import ingestion_service
from db.enums import IngestionStateEnum
from core.config import settings

logger = logging.getLogger(__name__)


@celery.task(
    bind=True,
    name="workers.staging_worker.create_staging_task",
    max_retries=3,
    default_retry_delay=30,
)
def create_staging_task(self, run_id_str: str, tenant_id_str: str) -> dict:
    """
    Read all RawRecords for `run_id` and create StagingEntity rows.

    Transitions:
        RAW_LOADED → STAGING_CREATED → COMPLETED

    Args:
        run_id_str:    IngestionRun UUID as string.
        tenant_id_str: Tenant UUID as string.

    Returns:
        dict with run_id and staging_count on success.
    """
    run_id    = uuid.UUID(run_id_str)
    tenant_id = uuid.UUID(tenant_id_str)

    db = SessionLocal()
    try:
        logger.info("[staging_worker] Starting staging for run=%s", run_id)

        run: IngestionRun = db.query(IngestionRun).filter(
            IngestionRun.run_id == run_id,
            IngestionRun.tenant_id == tenant_id,
        ).first()

        if not run:
            raise ValueError(f"IngestionRun {run_id} not found.")

        delay = max(0, settings.ingestion_pipeline_stage_delay_seconds)
        if delay:
            logger.info("[staging_worker] Pacing %ss in RAW_LOADED (run=%s)", delay, run_id)
            time.sleep(delay)

        # Create staging entities (chunked for memory efficiency)
        staging_count = staging_service.create_staging_from_run(
            db,
            run_id=run_id,
            tenant_id=tenant_id,
            source_system_id=run.source_system_id,
        )

        logger.info("[staging_worker] Created %d staging entities for run=%s", staging_count, run_id)

        # Transition: RAW_LOADED → STAGING_CREATED
        ingestion_service.transition_state(
            db,
            run_id=run_id,
            tenant_id=tenant_id,
            new_state=IngestionStateEnum.STAGING_CREATED,
            performed_by="staging_worker",
        )

        if delay:
            logger.info("[staging_worker] Pacing %ss in STAGING_CREATED (run=%s)", delay, run_id)
            time.sleep(delay)

        # Transition: STAGING_CREATED → COMPLETED
        ingestion_service.transition_state(
            db,
            run_id=run_id,
            tenant_id=tenant_id,
            new_state=IngestionStateEnum.COMPLETED,
            performed_by="staging_worker",
        )

        logger.info("[staging_worker] Run=%s now COMPLETED. Staging count=%d", run_id, staging_count)
        return {"run_id": run_id_str, "staging_count": staging_count}

    except Exception as exc:
        logger.exception("[staging_worker] Error on run=%s: %s", run_id, exc)
        try:
            ingestion_service.transition_state(
                db,
                run_id=run_id,
                tenant_id=tenant_id,
                new_state=IngestionStateEnum.FAILED,
                error_message=str(exc),
                performed_by="staging_worker",
            )
        except Exception:
            pass

        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("[staging_worker] Max retries exceeded for run=%s", run_id)
            raise
    finally:
        db.close()
