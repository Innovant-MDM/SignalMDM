from __future__ import annotations

import uuid
from datetime import datetime
from typing import Union

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from db.models.staging_entity import StagingEntity
from db.models.mdm_phase2.canonical_field import CanonicalField
from db.models.mdm_phase2.field_mapping import FieldMapping
from db.models.mdm_phase2.transformation_rule import TransformationRule
from db.models.mdm_phase2.standardization_rule import StandardizationRule
from db.models.mdm_phase2.mapping_error import MappingError
from db.models.mdm_phase2.normalization_run import NormalizationRun
from services.mdm_phase2.normalization.normalization_service import normalization_service
from db.enums import OperationTypeEnum
import services.audit.audit_service as audit_svc


class RetryService:

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

    def list_mapping_errors(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        status_val: str = "OPEN",
    ) -> list[MappingError]:
        """Fetch mapping errors for the tenant, with optional status filter."""
        target_tenant = self._parse_tenant(tenant_id)
        return db.query(MappingError).filter(
            MappingError.tenant_id == target_tenant,
            MappingError.status == status_val.upper(),
        ).order_by(MappingError.created_at.desc()).all()

    def get_mapping_error(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        error_id: uuid.UUID,
    ) -> MappingError:
        """Fetch a single mapping error details."""
        target_tenant = self._parse_tenant(tenant_id)
        err = db.query(MappingError).filter(
            MappingError.error_id == error_id,
            MappingError.tenant_id == target_tenant,
        ).first()
        if not err:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mapping error log not found.",
            )
        return err

    def retry_mapping_error(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        error_id: uuid.UUID,
        performed_by: str = "system",
    ) -> dict:
        """
        Retries mapping and processing on a failed staging record.
        Fetches fresh field mapping configurations and applies normalization transformation chains.
        On success, flags mapping error RESOLVED and updates stats in DB.
        """
        target_tenant = self._parse_tenant(tenant_id)

        # 1. Fetch Mapping Error Log
        err = self.get_mapping_error(db, target_tenant, error_id)
        if err.status == "RESOLVED":
            return {
                "success": True,
                "message": "This mapping error is already resolved.",
                "staging_id": err.staging_id,
                "new_status": "NORMALIZED"
            }

        # 2. Fetch Staging Record
        staging_entity = db.query(StagingEntity).filter(
            StagingEntity.staging_id == err.staging_id,
            StagingEntity.tenant_id == target_tenant,
        ).first()
        if not staging_entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Staging entity associated with this error not found.",
            )

        # 3. Load active mappings, canonical models, and rules
        mappings = db.query(FieldMapping).filter(
            FieldMapping.tenant_id == target_tenant,
            FieldMapping.source_system_id == staging_entity.source_system_id,
            FieldMapping.entity_type == staging_entity.mapped_entity_type.upper(),
            FieldMapping.status == "ACTIVE",
        ).all()

        canonical_fields = db.query(CanonicalField).filter(
            CanonicalField.tenant_id == target_tenant,
            CanonicalField.entity_type == staging_entity.mapped_entity_type.upper(),
            CanonicalField.status == "ACTIVE",
        ).all()

        t_list = db.query(TransformationRule).filter(TransformationRule.tenant_id == target_tenant).all()
        trans_rules = {r.rule_id: r for r in t_list}

        s_list = db.query(StandardizationRule).filter(StandardizationRule.tenant_id == target_tenant).all()
        std_rules = {r.rule_id: r for r in s_list}

        # 4. Trigger reprocessing on the record
        success = normalization_service.process_record(
            db, target_tenant, staging_entity, err.normalization_run_id,
            mappings, canonical_fields, trans_rules, std_rules
        )

        if success:
            # Update Error log
            err.status = "RESOLVED"
            err.resolved_at = datetime.utcnow()
            err.resolved_by = performed_by
            
            # Increment success stats on Normalization Run
            run = db.query(NormalizationRun).filter(NormalizationRun.run_id == err.normalization_run_id).first()
            if run:
                run.successful_records += 1
                if run.failed_records > 0:
                    run.failed_records -= 1

            # Log audit trail
            audit_svc.log_action(
                db,
                tenant_id=target_tenant,
                entity_name="mapping_errors",
                entity_id=error_id,
                operation_type=OperationTypeEnum.UPDATE,
                old_value={"status": "OPEN"},
                new_value={"status": "RESOLVED"},
                performed_by=performed_by,
                autocommit=False,
            )

            db.commit()
            return {
                "success": True,
                "message": "Staging record reprocessed and normalized successfully.",
                "staging_id": staging_entity.staging_id,
                "new_status": "NORMALIZED"
            }
        else:
            # Keep error log open and update message
            err.error_message = staging_entity.normalization_error or "Reprocessing failed again."
            db.commit()
            return {
                "success": False,
                "message": f"Reprocessing failed: {err.error_message}",
                "staging_id": staging_entity.staging_id,
                "new_status": "NORMALIZATION_FAILED"
            }


retry_service = RetryService()
