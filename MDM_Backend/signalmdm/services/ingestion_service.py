"""
signalmdm/services/ingestion_service.py
-----------------------------------------
Business logic for IngestionRun lifecycle management.

State machine enforced here:
    CREATED → RUNNING → RAW_LOADED → STAGING_CREATED → COMPLETED
    RUNNING → RUNNING (extra file), RAW_LOADED → RUNNING (extra file before staging)
    Any state → FAILED
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from signalmdm.models.ingestion_run  import IngestionRun
from signalmdm.models.source_system  import SourceSystem
from signalmdm.schemas.ingestion_schema import (
    IngestionRunCreate,
    IngestionRunFromSessionCreate,
    IngestionResolveConfigRead,
)
from signalmdm.models.upload_session import UploadSession
from signalmdm.models.raw_record import RawRecord
from signalmdm.models.staging_entity import StagingEntity
from signalmdm.schemas.ingestion_schema import parse_run_metadata
from signalmdm.enums import IngestionStateEnum, OperationTypeEnum
import signalmdm.services.audit_service as audit_svc
from typing import Union


# Valid forward transitions in the state machine
# RUNNING → RUNNING: additional file while ingestion still active (same run).
# RAW_LOADED → RUNNING: additional file before staging completes / between paced steps.
_VALID_TRANSITIONS: dict[str, list[str]] = {
    IngestionStateEnum.CREATED:         [IngestionStateEnum.RUNNING],
    IngestionStateEnum.RUNNING:         [
        IngestionStateEnum.RUNNING,
        IngestionStateEnum.RAW_LOADED,
        IngestionStateEnum.FAILED,
    ],
    IngestionStateEnum.RAW_LOADED:      [
        IngestionStateEnum.RUNNING,
        IngestionStateEnum.STAGING_CREATED,
        IngestionStateEnum.FAILED,
    ],
    IngestionStateEnum.STAGING_CREATED: [IngestionStateEnum.COMPLETED, IngestionStateEnum.FAILED],
    IngestionStateEnum.COMPLETED:       [],
    IngestionStateEnum.FAILED:          [],
}


_KNOWN_ENTITY_TYPES = frozenset({
    "CUSTOMER", "SUPPLIER", "PRODUCT", "ACCOUNT", "ASSET", "LOCATION", "EMPLOYEE", "OTHER",
})


class IngestionService:
    @staticmethod
    def normalize_entity_type(raw: str) -> str:
        """Map session domain / free text to a canonical entity label."""
        normalized = raw.strip().upper().replace(" ", "_").replace("-", "_")
        if normalized in _KNOWN_ENTITY_TYPES:
            return normalized
        if normalized.endswith("S"):
            singular = normalized[:-1]
            if singular in _KNOWN_ENTITY_TYPES:
                return singular
        return normalized or "RECORD"

    @staticmethod
    def supported_entities_from_source(source: SourceSystem) -> list[str]:
        cfg = source.config_json or {}
        ents = cfg.get("supported_entities")
        if isinstance(ents, list) and ents:
            return [str(e).strip().upper() for e in ents if str(e).strip()]
        return []

    def resolve_entity_type(
        self,
        *,
        session_domain: str,
        source: SourceSystem,
        override: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Pick entity type: explicit override → session domain → sole supported entity on source.
        Returns (entity_type, resolved_from).
        """
        if override and override.strip():
            return self.normalize_entity_type(override), "override"

        from_domain = self.normalize_entity_type(session_domain)
        supported = self.supported_entities_from_source(source)

        if supported:
            if from_domain in supported:
                return from_domain, "session_domain"
            if len(supported) == 1:
                return supported[0], "source_supported_entities"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Upload session domain '{session_domain}' maps to '{from_domain}', "
                    f"but source '{source.source_name}' supports: {', '.join(supported)}. "
                    "Align the session domain on Upload Data or update the source's supported entities."
                ),
            )

        return from_domain, "session_domain"

    def resolve_run_type(
        self,
        db: Session,
        *,
        tenant_id: uuid.UUID,
        source_system_id: uuid.UUID,
        entity_type: str,
        override: Optional[str] = None,
    ) -> tuple[str, str]:
        """INITIAL_LOAD when no prior completed run for this source; else DELTA_LOAD."""
        if override and override.strip():
            return override.strip().upper(), "explicit"

        prior = (
            db.query(IngestionRun)
            .filter(
                IngestionRun.tenant_id == tenant_id,
                IngestionRun.source_system_id == source_system_id,
                IngestionRun.state == IngestionStateEnum.COMPLETED,
            )
            .count()
        )
        if prior > 0:
            return "DELTA_LOAD", "prior_completed_run_exists"
        return "INITIAL_LOAD", "first_run_for_source"

    @staticmethod
    def resolve_trigger_type(override: Optional[str] = None) -> tuple[str, str]:
        """UI-started runs are MANUAL unless explicitly overridden (API/scheduler later)."""
        if override and override.strip():
            return override.strip().upper(), "explicit"
        return "MANUAL", "user_started_from_ui"

    def resolve_config_for_session(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        *,
        upload_session_id: uuid.UUID,
        source_system_id: uuid.UUID,
        entity_type: Optional[str] = None,
        run_type: Optional[str] = None,
        trigger_type: Optional[str] = None,
    ) -> IngestionResolveConfigRead:
        """Preview or compute full ingestion settings for session + source."""
        target_uuid = self._parse_tenant(tenant_id)
        if target_uuid is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SuperAdmin must provide a specific tenant_id (X-Tenant-ID).",
            )

        session = (
            db.query(UploadSession)
            .filter(
                UploadSession.session_id == upload_session_id,
                UploadSession.tenant_id == target_uuid,
            )
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Upload session not found.")
        if not session.files:
            raise HTTPException(status_code=400, detail="Upload session has no files.")

        source = (
            db.query(SourceSystem)
            .filter(
                SourceSystem.source_system_id == source_system_id,
                SourceSystem.tenant_id == target_uuid,
                SourceSystem.is_active.is_(True),
            )
            .first()
        )
        if not source:
            raise HTTPException(status_code=404, detail="Active source system not found.")

        entity, entity_from = self.resolve_entity_type(
            session_domain=session.domain,
            source=source,
            override=entity_type,
        )
        run_t, run_reason = self.resolve_run_type(
            db,
            tenant_id=target_uuid,
            source_system_id=source_system_id,
            entity_type=entity,
            override=run_type,
        )
        trigger, trigger_reason = self.resolve_trigger_type(trigger_type)

        return IngestionResolveConfigRead(
            upload_session_id=session.session_id,
            source_system_id=source.source_system_id,
            session_name=session.session_name,
            session_domain=session.domain,
            entity_type=entity,
            entity_resolved_from=entity_from,
            run_type=run_t,
            run_type_reason=run_reason,
            trigger_type=trigger,
            trigger_type_reason=trigger_reason,
            file_count=len(session.files),
            supported_entities=self.supported_entities_from_source(source),
        )

    @staticmethod
    def build_triggered_by(
        *,
        upload_session_id: uuid.UUID,
        entity_type: str,
        run_type: str,
        trigger_type: str,
        initiated_by: str,
    ) -> str:
        """Compact metadata stored on ingestion_runs.triggered_by (max 150 chars)."""
        return (
            f"session:{upload_session_id}|entity:{entity_type}|"
            f"run_type:{run_type}|trigger:{trigger_type}|by:{initiated_by}"[:150]
        )

    def _parse_tenant(self, tenant_id: Union[str, uuid.UUID]) -> Optional[uuid.UUID]:
        """Convert string/uuid to UUID object. Returns None if 'platform'."""
        if tenant_id == "platform":
            return None
        if isinstance(tenant_id, uuid.UUID):
            return tenant_id
        try:
            return uuid.UUID(tenant_id)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tenant_id format: {tenant_id}",
            )

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_run(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        data: IngestionRunCreate,
        performed_by: str = "system",
    ) -> IngestionRun:
        """
        Create a new IngestionRun in CREATED state.

        Validates that the referenced SourceSystem belongs to this tenant.
        """
        target_uuid = self._parse_tenant(tenant_id)
        if target_uuid is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SuperAdmin must provide a specific tenant_id (X-Tenant-ID) for ingestion.",
            )

        source = (
            db.query(SourceSystem)
            .filter(
                SourceSystem.source_system_id == data.source_system_id,
                SourceSystem.tenant_id == target_uuid,
                SourceSystem.is_active.is_(True),
            )
            .first()
        )
        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Active source system {data.source_system_id} not found for this tenant.",
            )

        run = IngestionRun(
            run_id=uuid.uuid4(),
            tenant_id=target_uuid,
            source_system_id=data.source_system_id,
            state=IngestionStateEnum.CREATED,
            triggered_by=data.triggered_by,
        )
        db.add(run)
        db.flush()

        audit_svc.log_action(
            db,
            tenant_id=target_uuid,
            entity_name="ingestion_runs",
            entity_id=run.run_id,
            operation_type=OperationTypeEnum.INSERT,
            new_value={"state": run.state, "source_system_id": str(run.source_system_id)},
            performed_by=performed_by,
            autocommit=False,
        )

        db.commit()
        db.refresh(run)
        return run

    def create_run_from_session(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        data: IngestionRunFromSessionCreate,
        performed_by: str = "system",
    ) -> tuple[IngestionRun, list]:
        """
        Create a run linked to an upload session that already has files on disk.

        Returns (run, list of UploadSessionFile rows).
        """
        target_uuid = self._parse_tenant(tenant_id)
        if target_uuid is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SuperAdmin must provide a specific tenant_id (X-Tenant-ID) for ingestion.",
            )

        session = (
            db.query(UploadSession)
            .filter(
                UploadSession.session_id == data.upload_session_id,
                UploadSession.tenant_id == target_uuid,
            )
            .first()
        )
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload session {data.upload_session_id} not found for this tenant.",
            )
        if not session.files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upload session has no files. Add files on Upload Data first.",
            )

        source = (
            db.query(SourceSystem)
            .filter(
                SourceSystem.source_system_id == data.source_system_id,
                SourceSystem.tenant_id == target_uuid,
                SourceSystem.is_active.is_(True),
            )
            .first()
        )
        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Active source system {data.source_system_id} not found for this tenant.",
            )

        resolved = self.resolve_config_for_session(
            db,
            tenant_id,
            upload_session_id=data.upload_session_id,
            source_system_id=data.source_system_id,
            entity_type=data.entity_type,
            run_type=data.run_type,
            trigger_type=data.trigger_type,
        )

        initiated = data.triggered_by or performed_by
        triggered = self.build_triggered_by(
            upload_session_id=data.upload_session_id,
            entity_type=resolved.entity_type,
            run_type=resolved.run_type,
            trigger_type=resolved.trigger_type,
            initiated_by=initiated,
        )

        run = IngestionRun(
            run_id=uuid.uuid4(),
            tenant_id=target_uuid,
            source_system_id=data.source_system_id,
            state=IngestionStateEnum.CREATED,
            triggered_by=triggered,
        )
        db.add(run)
        db.flush()

        audit_svc.log_action(
            db,
            tenant_id=target_uuid,
            entity_name="ingestion_runs",
            entity_id=run.run_id,
            operation_type=OperationTypeEnum.INSERT,
            new_value={
                "state": run.state,
                "source_system_id": str(run.source_system_id),
                "upload_session_id": str(data.upload_session_id),
                "entity_type": resolved.entity_type,
                "run_type": resolved.run_type,
            },
            performed_by=performed_by,
            autocommit=False,
        )

        db.commit()
        db.refresh(run)
        db.refresh(session)
        return run, list(session.files)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_run(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        run_id: uuid.UUID,
    ) -> IngestionRun:
        """Fetch a run; raise 404 if not found for this tenant."""
        target_uuid = self._parse_tenant(tenant_id)
        
        query = db.query(IngestionRun).filter(IngestionRun.run_id == run_id)
        if target_uuid:
            query = query.filter(IngestionRun.tenant_id == target_uuid)
            
        run = query.first()
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ingestion run {run_id} not found.",
            )
        return run

    @staticmethod
    def entity_type_for_run(run: IngestionRun) -> Optional[str]:
        return parse_run_metadata(run.triggered_by).get("entity_type")

    def lineage_summary(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        limit: int = 50,
    ) -> list[dict]:
        """
        Per ingestion run: entity label + raw vs staging counts (explains screen differences).
        """
        from signalmdm.models.source_system import SourceSystem

        target_uuid = self._parse_tenant(tenant_id)
        q = db.query(IngestionRun, SourceSystem.source_name).join(
            SourceSystem,
            SourceSystem.source_system_id == IngestionRun.source_system_id,
        )
        if target_uuid:
            q = q.filter(IngestionRun.tenant_id == target_uuid)

        rows = (
            q.order_by(IngestionRun.created_at.desc())
            .limit(limit)
            .all()
        )
        out: list[dict] = []
        for run, source_name in rows:
            raw_n = (
                db.query(RawRecord)
                .filter(RawRecord.run_id == run.run_id)
                .count()
            )
            stg_n = (
                db.query(StagingEntity)
                .filter(StagingEntity.run_id == run.run_id)
                .count()
            )
            meta = parse_run_metadata(run.triggered_by)
            aligned = raw_n == stg_n
            note = ""
            if run.state == IngestionStateEnum.FAILED:
                note = "Run failed — staging may be incomplete."
            elif run.state in (IngestionStateEnum.RUNNING, IngestionStateEnum.CREATED):
                note = "Pipeline still running — counts may change."
            elif raw_n > stg_n:
                note = "Fewer staging rows: pipeline stopped before staging or partial failure."
            elif raw_n < stg_n:
                note = "Unexpected: more staging than raw (contact support)."
            elif raw_n == 0:
                note = "No raw records yet for this run."
            elif aligned:
                note = "1:1 lineage — each raw row has one staging row."

            out.append(
                {
                    "run_id": run.run_id,
                    "source_system_id": run.source_system_id,
                    "source_name": source_name,
                    "entity_type": meta.get("entity_type"),
                    "run_type": meta.get("run_type"),
                    "state": run.state,
                    "raw_record_count": raw_n,
                    "staging_record_count": stg_n,
                    "counts_aligned": aligned and raw_n > 0,
                    "pipeline_note": note,
                    "created_at": run.created_at,
                }
            )
        return out

    def list_runs(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        skip: int = 0,
        limit: int = 20,
    ) -> list[IngestionRun]:
        """List ingestion runs scoped to the tenant (or all if platform)."""
        target_uuid = self._parse_tenant(tenant_id)
        query = db.query(IngestionRun)
        if target_uuid:
            query = query.filter(IngestionRun.tenant_id == target_uuid)

        return (
            query.order_by(IngestionRun.created_at.desc())
            .offset(skip).limit(limit).all()
        )

    # ------------------------------------------------------------------
    # State transition
    # ------------------------------------------------------------------

    def transition_state(
        self,
        db: Session,
        run_id: uuid.UUID,
        tenant_id: Union[str, uuid.UUID],
        new_state: str,
        error_message: Optional[str] = None,
        performed_by: str = "system",
        record_count: Optional[int] = None,
        file_count: Optional[int] = None,
    ) -> IngestionRun:
        """
        Advance the run to `new_state`, enforcing the state machine.

        Raises 400 if the transition is invalid.
        """
        run = self.get_run(db, tenant_id, run_id)
        allowed = _VALID_TRANSITIONS.get(run.state, [])

        if new_state not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot transition from {run.state!r} to {new_state!r}. "
                    f"Allowed: {allowed}"
                ),
            )

        old_state = run.state
        run.state = new_state

        if new_state == IngestionStateEnum.RUNNING:
            run.started_at = datetime.now(timezone.utc)
        if new_state in (IngestionStateEnum.COMPLETED, IngestionStateEnum.FAILED):
            run.completed_at = datetime.now(timezone.utc)
        if error_message is not None:
            run.error_message = error_message
        if record_count is not None:
            run.record_count = record_count
        if file_count is not None:
            run.file_count = file_count

        db.flush()

        audit_svc.log_action(
            db,
            tenant_id=self._parse_tenant(tenant_id) or run.tenant_id,
            entity_name="ingestion_runs",
            entity_id=run.run_id,
            operation_type=OperationTypeEnum.UPDATE,
            old_value={"state": old_state},
            new_value={"state": new_state},
            performed_by=performed_by,
            autocommit=False,
        )

        db.commit()
        db.refresh(run)
        return run

    def delete_run(
        self,
        db: Session,
        tenant_id: Union[str, uuid.UUID],
        run_id: uuid.UUID,
        performed_by: str = "system",
    ) -> None:
        """
        Remove an ingestion run and all dependent rows (files, raw, staging) via ORM cascade.
        """
        import os
        import shutil

        from core.config import settings

        run = self.get_run(db, tenant_id, run_id)
        if run.state == IngestionStateEnum.RUNNING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a run while the pipeline is running. Wait for completion or cancel first.",
            )

        snapshot = {
            "state": run.state,
            "source_system_id": str(run.source_system_id),
            "file_count": run.file_count,
            "record_count": run.record_count,
        }
        tenant_for_audit = self._parse_tenant(tenant_id) or run.tenant_id

        db.delete(run)
        db.flush()

        audit_svc.log_action(
            db,
            tenant_id=tenant_for_audit,
            entity_name="ingestion_runs",
            entity_id=run_id,
            operation_type=OperationTypeEnum.DELETE,
            old_value=snapshot,
            new_value=None,
            performed_by=performed_by,
            autocommit=False,
        )
        db.commit()

        upload_dir = os.path.join(os.getcwd(), settings.upload_dir, str(run_id))
        if os.path.isdir(upload_dir):
            try:
                shutil.rmtree(upload_dir)
            except OSError:
                pass


# Singleton
ingestion_service = IngestionService()
