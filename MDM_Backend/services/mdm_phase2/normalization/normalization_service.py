from __future__ import annotations

import uuid
import logging
from datetime import datetime
from typing import Optional, Union, Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from db.models.staging_entity import StagingEntity
from db.models.mdm_phase2.canonical_field import CanonicalField
from db.models.mdm_phase2.field_mapping import FieldMapping
from db.models.mdm_phase2.transformation_rule import TransformationRule
from db.models.mdm_phase2.standardization_rule import StandardizationRule
from db.models.mdm_phase2.normalization_run import NormalizationRun
from db.models.mdm_phase2.mapping_error import MappingError
from schemas.mdm_phase2.normalization_run_schema import NormalizationRunCreate
from db.enums import StagingStateEnum, OperationTypeEnum
from utils.mdm_phase2.transformers import apply_transformation_chain
from utils.mdm_phase2.standardizers import standardize_value
from utils.mdm_phase2.validators import validate_field_value
import services.audit.audit_service as audit_svc

logger = logging.getLogger(__name__)


class NormalizationService:

    def _parse_tenant(self, tenant_id: Union[str, uuid.UUID]) -> uuid.UUID:
        if isinstance(tenant_id, uuid.UUID):
            return tenant_id
        try:
            return uuid.UUID(str(tenant_id))
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant_id format — must be a valid UUID.",
            )

    def run_normalization(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        data: NormalizationRunCreate,
        performed_by: str = "system",
    ) -> NormalizationRun:
        """
        Triggers a normalization execution batch.
        Gathers eligible staging_entities, initializes status in DB, and launches asynchronous worker task.
        """
        target_tenant = self._parse_tenant(tenant_id)

        # 1. Fetch eligible staging_entities matching source and entity type
        query = db.query(StagingEntity).filter(
            StagingEntity.tenant_id == target_tenant,
            StagingEntity.source_system_id == data.source_system_id,
            StagingEntity.state == StagingStateEnum.READY_FOR_MAPPING.value,
        )
        if data.ingestion_run_id:
            query = query.filter(StagingEntity.run_id == data.ingestion_run_id)

        staging_records = query.all()
        total_count = len(staging_records)

        if total_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No eligible records found in READY_FOR_MAPPING state for this source system/run.",
            )

        # 2. Verify active mappings exist before starting run
        mappings_exist = db.query(FieldMapping).filter(
            FieldMapping.tenant_id == target_tenant,
            FieldMapping.source_system_id == data.source_system_id,
            FieldMapping.entity_type == data.entity_type.upper(),
            FieldMapping.status == "ACTIVE",
        ).first()

        if not mappings_exist:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No active field mappings defined for entity '{data.entity_type}' on this source system.",
            )

        # 3. Create Normalization Run
        run = NormalizationRun(
            run_id=uuid.uuid4(),
            tenant_id=target_tenant,
            ingestion_run_id=data.ingestion_run_id,
            source_system_id=data.source_system_id,
            entity_type=data.entity_type.upper(),
            status="CREATED",
            total_records=total_count,
            processed_records=0,
            successful_records=0,
            failed_records=0,
            started_at=datetime.utcnow(),
            created_by=performed_by,
        )
        db.add(run)
        db.flush()

        # Update staging entities with run reference and change state to MAPPING_IN_PROGRESS
        for rec in staging_records:
            rec.normalization_run_id = run.run_id
            rec.normalization_status = "PROCESSING"
            rec.state = "MAPPING_IN_PROGRESS"

        db.commit()

        # 4. Enqueue normalization background worker task via Celery
        try:
            from workers.mdm_phase2.normalization_worker import run_normalization_task
            run_normalization_task.delay(str(run.run_id))
            run.status = "RUNNING"
            db.commit()
        except Exception as e:
            logger.error(f"Failed to dispatch Celery normalization task: {e}")
            run.status = "FAILED"
            run.error_message = f"Failed to enqueue background worker: {e}"
            db.commit()

        return run

    def list_normalization_runs(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
    ) -> list[NormalizationRun]:
        """Fetch all normalization run history logs."""
        target_tenant = self._parse_tenant(tenant_id)
        return db.query(NormalizationRun).filter(
            NormalizationRun.tenant_id == target_tenant
        ).order_by(NormalizationRun.created_at.desc()).all()

    def get_normalization_run(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        run_id: uuid.UUID,
    ) -> NormalizationRun:
        """Fetch a single normalization run log details."""
        target_tenant = self._parse_tenant(tenant_id)
        run = db.query(NormalizationRun).filter(
            NormalizationRun.run_id == run_id,
            NormalizationRun.tenant_id == target_tenant,
        ).first()
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Normalization run not found.",
            )
        return run

    def process_record(
        self,
        db: Session,
        tenant_id: uuid.UUID,
        staging_entity: StagingEntity,
        run_id: uuid.UUID,
        mappings: list[FieldMapping],
        canonical_fields: list[CanonicalField],
        trans_rules: dict[uuid.UUID, TransformationRule],
        std_rules: dict[uuid.UUID, StandardizationRule],
    ) -> bool:
        """
        Core Ingestion Pipeline Normalization Logic for a single record.
        Maps fields, executes sequential transformation rules chain, applies standardization lookup maps,
        validates constraints, and writes errors or marks record READY_FOR_DQ.
        """
        try:
            raw_payload = staging_entity.entity_data or {}
            mapped_payload = {}
            standardized_payload = {}
            
            # Map canonical_fields list into quick-lookup definitions
            cf_map = {cf.field_id: cf for cf in canonical_fields}
            cf_by_name = {cf.canonical_field_name: cf for cf in canonical_fields}
            
            # Apply all active field mappings
            for mapping in mappings:
                src_field = mapping.source_field_name
                
                # Check if field exists in raw payload (allow case-insensitive match for robust mappings)
                raw_value = None
                src_field_found = None
                for key in raw_payload.keys():
                    if key.lower() == src_field.lower():
                        raw_value = raw_payload[key]
                        src_field_found = key
                        break
                        
                if src_field_found is None:
                    # Missing source field in this specific record payload — skip or handle below if required
                    continue
                    
                target_cf = cf_map.get(mapping.canonical_field_id)
                if not target_cf:
                    self.handle_mapping_error(
                        db, tenant_id, run_id, staging_entity.staging_id,
                        error_type="INVALID_CANONICAL_FIELD",
                        source_field=src_field, source_value=str(raw_value),
                        error_message=f"Referenced canonical field ID '{mapping.canonical_field_id}' does not exist."
                    )
                    return False

                target_name = target_cf.canonical_field_name
                
                # Apply transformation chain
                transformed_value = raw_value
                if mapping.transformation_rule_ids:
                    chain_configs = []
                    for r_id in mapping.transformation_rule_ids:
                        rule = trans_rules.get(r_id)
                        if rule:
                            chain_configs.append({
                                "type": rule.transformation_type,
                                "config": rule.config_json
                            })
                    transformed_value = apply_transformation_chain(raw_value, chain_configs)

                mapped_payload[target_name] = transformed_value
                
                # Apply standardization rule mapping if configured
                standardized_value = transformed_value
                if mapping.standardization_rule_id:
                    std_rule = std_rules.get(mapping.standardization_rule_id)
                    if std_rule:
                        standardized_value = standardize_value(transformed_value, std_rule.mappings_json)
                        
                standardized_payload[target_name] = standardized_value

                # Perform field-level validation (e.g. EMAIL check, GSTIN structure, URL format)
                if not validate_field_value(standardized_value, target_cf.validation_type):
                    self.handle_mapping_error(
                        db, tenant_id, run_id, staging_entity.staging_id,
                        error_type="STANDARDIZATION_FAILED",
                        source_field=src_field, source_value=str(raw_value),
                        error_message=f"Validation failed for canonical field '{target_name}' with value '{standardized_value}' against validator type '{target_cf.validation_type}'."
                    )
                    return False

            # Ensure all required canonical fields exist in standardized payload
            for cf in canonical_fields:
                if cf.is_required and (cf.canonical_field_name not in standardized_payload or standardized_payload[cf.canonical_field_name] in [None, ""]):
                    self.handle_mapping_error(
                        db, tenant_id, run_id, staging_entity.staging_id,
                        error_type="PAYLOAD_ERROR",
                        source_field=None, source_value=None,
                        error_message=f"Required canonical field '{cf.canonical_field_name}' is missing or empty in final payload."
                    )
                    return False

            # Mapping Success — Save Standardized Outputs & Transition Status
            staging_entity.mapped_payload_json = mapped_payload
            staging_entity.standardized_payload_json = standardized_payload
            staging_entity.normalization_status = "NORMALIZED"
            staging_entity.state = "READY_FOR_DQ" # Phase 2 standard final state
            staging_entity.normalized_at = datetime.utcnow()
            staging_entity.normalization_error = None
            db.flush()
            return True

        except Exception as ex:
            logger.exception(f"Unexpected normalization failure on staging_id {staging_entity.staging_id}")
            self.handle_mapping_error(
                db, tenant_id, run_id, staging_entity.staging_id,
                error_type="PAYLOAD_ERROR",
                source_field=None, source_value=None,
                error_message=f"Unhandled system exception: {ex}"
            )
            return False

    def handle_mapping_error(
        self,
        db: Session,
        tenant_id: uuid.UUID,
        run_id: uuid.UUID,
        staging_id: uuid.UUID,
        error_type: str,
        source_field: Optional[str],
        source_value: Optional[str],
        error_message: str,
    ) -> None:
        """Saves a mapping processing issue log and flags record failure state."""
        # Create error log record
        err_log = MappingError(
            error_id=uuid.uuid4(),
            tenant_id=tenant_id,
            normalization_run_id=run_id,
            staging_id=staging_id,
            error_type=error_type,
            source_field=source_field,
            source_value=source_value,
            error_message=error_message,
            status="OPEN",
        )
        db.add(err_log)

        # Flag staging record state
        stg = db.query(StagingEntity).filter(StagingEntity.staging_id == staging_id).first()
        if stg:
            stg.normalization_status = "NORMALIZATION_FAILED"
            stg.state = "NORMALIZATION_FAILED"
            stg.normalization_error = error_message
            
        db.flush()


normalization_service = NormalizationService()
