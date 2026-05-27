from __future__ import annotations

import uuid
from typing import Optional, Union

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from db.models.mdm_phase2.transformation_rule import TransformationRule
from db.models.mdm_phase2.standardization_rule import StandardizationRule
from schemas.mdm_phase2.transformation_rule_schema import TransformationRuleCreate
from schemas.mdm_phase2.standardization_rule_schema import StandardizationRuleCreate
from db.enums import OperationTypeEnum
import services.audit.audit_service as audit_svc


class RuleService:

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

    # ------------------------------------------------------------------
    # Transformation Rules CRUD
    # ------------------------------------------------------------------

    def create_transformation_rule(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        data: TransformationRuleCreate,
        performed_by: str = "system",
    ) -> TransformationRule:
        """Create a new transformation rule definition."""
        target_tenant = self._parse_tenant(tenant_id)

        existing = db.query(TransformationRule).filter(
            TransformationRule.tenant_id == target_tenant,
            TransformationRule.rule_code == data.rule_code.upper(),
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Transformation rule with code '{data.rule_code}' already exists for this tenant.",
            )

        rule = TransformationRule(
            rule_id=uuid.uuid4(),
            tenant_id=target_tenant,
            rule_name=data.rule_name,
            rule_code=data.rule_code.upper(),
            transformation_type=data.transformation_type.upper(),
            config_json=data.config_json,
            status=data.status or "ACTIVE",
        )
        db.add(rule)
        db.flush()

        audit_svc.log_action(
            db,
            tenant_id=target_tenant,
            entity_name="transformation_rules",
            entity_id=rule.rule_id,
            operation_type=OperationTypeEnum.INSERT,
            new_value={
                "rule_code": rule.rule_code,
                "transformation_type": rule.transformation_type,
            },
            performed_by=performed_by,
            autocommit=False,
        )

        db.commit()
        db.refresh(rule)
        return rule

    def list_transformation_rules(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
    ) -> list[TransformationRule]:
        """Fetch all transformation rules for the tenant."""
        target_tenant = self._parse_tenant(tenant_id)
        return db.query(TransformationRule).filter(
            TransformationRule.tenant_id == target_tenant
        ).order_by(TransformationRule.rule_name.asc()).all()

    # ------------------------------------------------------------------
    # Standardization Rules CRUD
    # ------------------------------------------------------------------

    def create_standardization_rule(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        data: StandardizationRuleCreate,
        performed_by: str = "system",
    ) -> StandardizationRule:
        """Create a new standardization rule definition."""
        target_tenant = self._parse_tenant(tenant_id)

        existing = db.query(StandardizationRule).filter(
            StandardizationRule.tenant_id == target_tenant,
            StandardizationRule.rule_code == data.rule_code.upper(),
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Standardization rule with code '{data.rule_code}' already exists for this tenant.",
            )

        rule = StandardizationRule(
            rule_id=uuid.uuid4(),
            tenant_id=target_tenant,
            rule_name=data.rule_name,
            rule_code=data.rule_code.upper(),
            standardization_type=data.standardization_type.upper(),
            mappings_json=data.mappings_json,
            status=data.status or "ACTIVE",
        )
        db.add(rule)
        db.flush()

        audit_svc.log_action(
            db,
            tenant_id=target_tenant,
            entity_name="standardization_rules",
            entity_id=rule.rule_id,
            operation_type=OperationTypeEnum.INSERT,
            new_value={
                "rule_code": rule.rule_code,
                "standardization_type": rule.standardization_type,
            },
            performed_by=performed_by,
            autocommit=False,
        )

        db.commit()
        db.refresh(rule)
        return rule

    def list_standardization_rules(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
    ) -> list[StandardizationRule]:
        """Fetch all standardization rules for the tenant."""
        target_tenant = self._parse_tenant(tenant_id)
        return db.query(StandardizationRule).filter(
            StandardizationRule.tenant_id == target_tenant
        ).order_by(StandardizationRule.rule_name.asc()).all()


rule_service = RuleService()
