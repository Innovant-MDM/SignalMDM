from __future__ import annotations

import uuid
import logging
from datetime import datetime

from workers.celery_app import celery
from db.sessions.database import SessionLocal
from db.models.mdm_phase2.normalization_run import NormalizationRun
from db.models.staging_entity import StagingEntity
from db.models.mdm_phase2.field_mapping import FieldMapping
from db.models.mdm_phase2.canonical_field import CanonicalField
from db.models.mdm_phase2.transformation_rule import TransformationRule
from db.models.mdm_phase2.standardization_rule import StandardizationRule
from services.mdm_phase2.normalization.normalization_service import normalization_service

logger = logging.getLogger(__name__)


@celery.task(
    bind=True,
    name="workers.mdm_phase2.normalization_worker.run_normalization_task",
    max_retries=3,
    default_retry_delay=30,
)
def run_normalization_task(self, run_id_str: str) -> dict:
    """
    Asynchronously processes normalization rules for all eligible staging records
    under the specified normalization run.
    """
    run_id = uuid.UUID(run_id_str)
    db = SessionLocal()

    try:
        logger.info("[normalization_worker] Starting normalization for run=%s", run_id)

        # 1. Fetch NormalizationRun
        run = db.query(NormalizationRun).filter(NormalizationRun.run_id == run_id).first()
        if not run:
            raise ValueError(f"NormalizationRun {run_id} not found.")

        # Update status to RUNNING if not already
        if run.status != "RUNNING":
            run.status = "RUNNING"
            db.commit()

        # 2. Fetch Staging records associated with this run
        staging_records = db.query(StagingEntity).filter(
            StagingEntity.normalization_run_id == run_id
        ).all()

        if not staging_records:
            logger.info("[normalization_worker] No staging records found for run=%s", run_id)
            run.status = "COMPLETED"
            run.ended_at = datetime.utcnow()
            db.commit()
            return {"run_id": run_id_str, "processed": 0, "success": 0, "failed": 0}

        # 3. Cache mappings, canonical fields, transformation and standardization rules for efficiency
        tenant_id = run.tenant_id
        source_system_id = run.source_system_id
        entity_type = run.entity_type

        mappings = db.query(FieldMapping).filter(
            FieldMapping.tenant_id == tenant_id,
            FieldMapping.source_system_id == source_system_id,
            FieldMapping.entity_type == entity_type,
            FieldMapping.status == "ACTIVE",
        ).all()

        canonical_fields = db.query(CanonicalField).filter(
            CanonicalField.tenant_id == tenant_id,
            CanonicalField.entity_type == entity_type,
            CanonicalField.status == "ACTIVE",
        ).all()

        t_rules = db.query(TransformationRule).filter(
            TransformationRule.tenant_id == tenant_id,
            TransformationRule.status == "ACTIVE",
        ).all()
        trans_rules = {r.rule_id: r for r in t_rules}

        s_rules = db.query(StandardizationRule).filter(
            StandardizationRule.tenant_id == tenant_id,
            StandardizationRule.status == "ACTIVE",
        ).all()
        std_rules = {r.rule_id: r for r in s_rules}

        # 4. Process records one by one
        success_count = 0
        failed_count = 0

        for rec in staging_records:
            success = normalization_service.process_record(
                db=db,
                tenant_id=tenant_id,
                staging_entity=rec,
                run_id=run_id,
                mappings=mappings,
                canonical_fields=canonical_fields,
                trans_rules=trans_rules,
                std_rules=std_rules,
            )
            if success:
                success_count += 1
            else:
                failed_count += 1

        # 5. Update Run stats
        run.processed_records = len(staging_records)
        run.successful_records = success_count
        run.failed_records = failed_count
        run.status = "COMPLETED" if failed_count < len(staging_records) else "FAILED"
        if failed_count > 0 and success_count > 0:
            run.status = "COMPLETED_WITH_ERRORS"
        run.ended_at = datetime.utcnow()

        db.commit()
        logger.info(
            "[normalization_worker] Normalization completed for run=%s. Success: %d, Failed: %d",
            run_id,
            success_count,
            failed_count,
        )

        return {
            "run_id": run_id_str,
            "processed": len(staging_records),
            "success": success_count,
            "failed": failed_count,
        }

    except Exception as exc:
        logger.exception("[normalization_worker] Normalization run failed: %s", exc)
        try:
            run = db.query(NormalizationRun).filter(NormalizationRun.run_id == run_id).first()
            if run:
                run.status = "FAILED"
                run.error_message = str(exc)
                run.ended_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
        raise self.retry(exc=exc)
    finally:
        db.close()
