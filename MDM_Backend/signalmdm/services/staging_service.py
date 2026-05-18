"""
signalmdm/services/staging_service.py
----------------------------------------
Service layer for StagingEntity creation.

Phase 1 behaviour:
  • Read all RawRecords for a given run.
  • Create one StagingEntity per RawRecord (1-to-1 lineage).
  • entity_data = raw_data (verbatim copy — no transformation in Phase 1).
  • state = READY_FOR_MAPPING.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional, Union

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from signalmdm.models.raw_record import RawRecord
from signalmdm.models.staging_entity import StagingEntity
from signalmdm.models.source_system import SourceSystem
from signalmdm.models.ingestion_run import IngestionRun
from signalmdm.enums import StagingStateEnum
from signalmdm.schemas.ingestion_schema import parse_run_metadata


class StagingService:

    def create_staging_from_run(
        self,
        db: Session,
        *,
        run_id: uuid.UUID,
        tenant_id: uuid.UUID,
        source_system_id: uuid.UUID,
    ) -> int:
        """
        Read all RawRecords for `run_id` and create corresponding StagingEntities.

        Returns the number of staging records created.

        Design note:
            We do NOT load all raw_records into Python memory at once for large
            datasets — we process in chunks of 500.
        """
        run = (
            db.query(IngestionRun)
            .filter(
                IngestionRun.run_id == run_id,
                IngestionRun.tenant_id == tenant_id,
            )
            .first()
        )
        entity_type = (
            parse_run_metadata(run.triggered_by).get("entity_type") if run else None
        )

        chunk_size = 500
        offset = 0
        total_created = 0

        while True:
            raw_batch: list[RawRecord] = (
                db.query(RawRecord)
                .filter(
                    RawRecord.run_id == run_id,
                    RawRecord.tenant_id == tenant_id,
                )
                .order_by(RawRecord.row_index)
                .offset(offset)
                .limit(chunk_size)
                .all()
            )

            if not raw_batch:
                break

            staging_batch = [
                StagingEntity(
                    staging_id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    run_id=run_id,
                    raw_record_id=raw.raw_record_id,
                    source_system_id=source_system_id,
                    entity_data=raw.raw_data,  # verbatim copy in Phase 1
                    mapped_entity_type=entity_type,
                    state=StagingStateEnum.READY_FOR_MAPPING,
                )
                for raw in raw_batch
            ]

            db.bulk_save_objects(staging_batch)
            db.commit()

            total_created += len(staging_batch)
            offset += chunk_size

        return total_created

    def count_staging_for_run(
        self,
        db: Session,
        run_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> int:
        """Return the number of staging entities created for this run."""
        return (
            db.query(StagingEntity)
            .filter(
                StagingEntity.run_id == run_id,
                StagingEntity.tenant_id == tenant_id,
            )
            .count()
        )

    # ------------------------------------------------------------------
    # Staging screen — read-only list
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_tenant_id(tenant_id: Union[str, uuid.UUID]) -> Optional[uuid.UUID]:
        if tenant_id == "platform":
            return None
        if isinstance(tenant_id, uuid.UUID):
            return tenant_id
        return uuid.UUID(str(tenant_id))

    @staticmethod
    def _entity_hint_from_source(source: SourceSystem) -> str:
        cfg = source.config_json or {}
        ents = cfg.get("supported_entities")
        if isinstance(ents, list) and ents:
            return str(ents[0])
        return "RECORD"

    @staticmethod
    def _derive_source_record_id(raw_data: dict[str, Any], row_index: Optional[int]) -> str:
        for key in ("id", "externalId", "external_id", "source_record_id", "recordId"):
            v = raw_data.get(key)
            if v is not None and str(v).strip():
                return str(v)
        return f"row-{row_index if row_index is not None else '?'}"

    @staticmethod
    def _dq_score_placeholder(entity_data: dict[str, Any]) -> int:
        """Deterministic 70–99 score from payload shape (Phase 1 has no real DQ yet)."""
        n = len(entity_data) if entity_data else 0
        return min(99, 72 + (n % 28))

    @staticmethod
    def _validation_status(staging_state: StagingStateEnum | str) -> str:
        s = (
            staging_state.value
            if isinstance(staging_state, StagingStateEnum)
            else str(staging_state)
        )
        if s == StagingStateEnum.REJECTED.value:
            return "FAILED"
        if s == StagingStateEnum.MAPPED.value:
            return "PASSED"
        if s == StagingStateEnum.READY_FOR_MAPPING.value:
            return "PASSED"
        return "PENDING"

    def list_landing_page(
        self,
        db: Session,
        *,
        tenant_id: Union[str, uuid.UUID],
        skip: int = 0,
        limit: int = 100,
        run_id: Optional[uuid.UUID] = None,
        source_system_id: Optional[uuid.UUID] = None,
        entity_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], int]:
        tid = self._parse_tenant_id(tenant_id)
        q = (
            db.query(StagingEntity, SourceSystem, RawRecord, IngestionRun)
            .join(SourceSystem, SourceSystem.source_system_id == StagingEntity.source_system_id)
            .join(RawRecord, RawRecord.raw_record_id == StagingEntity.raw_record_id)
            .join(IngestionRun, IngestionRun.run_id == StagingEntity.run_id)
        )
        if tid is not None:
            q = q.filter(StagingEntity.tenant_id == tid)
        if run_id is not None:
            q = q.filter(StagingEntity.run_id == run_id)
        if source_system_id is not None:
            q = q.filter(StagingEntity.source_system_id == source_system_id)
        if entity_type and entity_type.strip():
            ent = entity_type.strip().upper()
            q = q.filter(IngestionRun.triggered_by.ilike(f"%entity:{ent}%"))
        if search and search.strip():
            term = f"%{search.strip()}%"
            q = q.filter(
                or_(
                    cast(StagingEntity.staging_id, String).ilike(term),
                    cast(StagingEntity.raw_record_id, String).ilike(term),
                    cast(RawRecord.raw_data, String).ilike(term),
                    cast(StagingEntity.entity_data, String).ilike(term),
                )
            )

        total = q.count()
        rows = (
            q.order_by(StagingEntity.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        out: list[dict[str, Any]] = []
        for st, src, raw, run in rows:
            run_meta = parse_run_metadata(run.triggered_by)
            ingestion_entity = run_meta.get("entity_type")
            hint = (
                st.mapped_entity_type
                or ingestion_entity
                or self._entity_hint_from_source(src)
            )
            src_id = self._derive_source_record_id(raw.raw_data, raw.row_index)
            dq = self._dq_score_placeholder(st.entity_data)
            state_val = st.state.value if isinstance(st.state, StagingStateEnum) else str(st.state)
            out.append(
                {
                    "staging_id": st.staging_id,
                    "tenant_id": st.tenant_id,
                    "run_id": st.run_id,
                    "raw_record_id": st.raw_record_id,
                    "source_system_id": st.source_system_id,
                    "source_name": src.source_name,
                    "state": state_val,
                    "mapped_entity_type": st.mapped_entity_type,
                    "ingestion_entity_type": ingestion_entity,
                    "entity_display": hint,
                    "run_type": run_meta.get("run_type"),
                    "entity_data": st.entity_data,
                    "raw_data": raw.raw_data,
                    "created_at": st.created_at,
                    "ingestion_run_state": str(run.state),
                    "source_record_id": src_id,
                    "dq_score": dq,
                    "validation_status": self._validation_status(st.state),
                }
            )
        return out, total


# Singleton
staging_service = StagingService()
