"""
signalmdm/services/raw_service.py
-----------------------------------
Service layer for FileUpload and RawRecord operations.

Immutability guarantee: this service only performs INSERT on raw_records.
No UPDATE or DELETE is allowed on that table.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional, Union

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from signalmdm.enums import IngestionStateEnum
from signalmdm.schemas.ingestion_schema import parse_run_metadata
from signalmdm.models.file_upload import FileUpload
from signalmdm.models.ingestion_run import IngestionRun
from signalmdm.models.raw_record import RawRecord
from signalmdm.models.source_system import SourceSystem
from signalmdm.models.staging_entity import StagingEntity
from signalmdm.models.tenant import Tenant
from utils.checksum import generate_checksum, generate_file_checksum


class RawService:

    # ------------------------------------------------------------------
    # File metadata
    # ------------------------------------------------------------------

    def save_file_upload(
        self,
        db: Session,
        *,
        tenant_id: uuid.UUID,
        run_id: uuid.UUID,
        original_filename: str,
        stored_path: str,
        file_bytes: bytes,
        content_type: str = "application/octet-stream",
    ) -> FileUpload:
        """
        Persist file metadata after a successful disk write.

        The checksum is computed from the raw bytes.
        """
        checksum = generate_file_checksum(file_bytes)
        upload = FileUpload(
            file_id=uuid.uuid4(),
            tenant_id=tenant_id,
            run_id=run_id,
            original_filename=original_filename,
            stored_path=stored_path,
            file_size_bytes=len(file_bytes),
            content_type=content_type,
            checksum_md5=checksum,
        )
        db.add(upload)
        db.commit()
        db.refresh(upload)
        return upload

    # ------------------------------------------------------------------
    # Raw records
    # ------------------------------------------------------------------

    def bulk_insert_raw_records(
        self,
        db: Session,
        *,
        tenant_id: uuid.UUID,
        run_id: uuid.UUID,
        source_system_id: uuid.UUID,
        file_id: uuid.UUID | None,
        rows: list[dict[str, Any]],
    ) -> int:
        """
        Insert a batch of raw records from parsed file rows.

        Returns the number of records inserted.
        Commits in a single transaction for performance.
        """
        records = []
        for idx, row in enumerate(rows):
            checksum = generate_checksum(row)
            records.append(
                RawRecord(
                    raw_record_id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    run_id=run_id,
                    file_id=file_id,
                    source_system_id=source_system_id,
                    row_index=idx,
                    raw_data=row,
                    checksum_md5=checksum,
                )
            )

        db.bulk_save_objects(records)
        db.commit()
        return len(records)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_raw_records_for_run(
        self,
        db: Session,
        run_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[RawRecord]:
        """Return all raw records for a given run (for staging worker)."""
        return (
            db.query(RawRecord)
            .filter(
                RawRecord.run_id == run_id,
                RawRecord.tenant_id == tenant_id,
            )
            .order_by(RawRecord.row_index)
            .all()
        )

    # ------------------------------------------------------------------
    # Raw Landing — read-only list (joins source + run state)
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
    def _processing_status(run_state: str, has_staging: bool) -> str:
        if run_state == IngestionStateEnum.FAILED:
            return "FAILED"
        if has_staging or run_state == IngestionStateEnum.COMPLETED:
            return "COMPLETED"
        if run_state in (
            IngestionStateEnum.RUNNING,
            IngestionStateEnum.RAW_LOADED,
            IngestionStateEnum.STAGING_CREATED,
        ):
            return "PROCESSING"
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
        exclude_duplicates: bool = False,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Paginated raw records for Raw Landing (newest first).

        Returns (list of dicts ready for RawRecordListItem, total matching count).
        """
        tid = self._parse_tenant_id(tenant_id)
        q = (
            db.query(RawRecord, SourceSystem, IngestionRun)
            .join(SourceSystem, SourceSystem.source_system_id == RawRecord.source_system_id)
            .join(IngestionRun, IngestionRun.run_id == RawRecord.run_id)
        )
        if tid is not None:
            q = q.filter(RawRecord.tenant_id == tid)
        if run_id is not None:
            q = q.filter(RawRecord.run_id == run_id)
        if source_system_id is not None:
            q = q.filter(RawRecord.source_system_id == source_system_id)
        if entity_type and entity_type.strip():
            ent = entity_type.strip().upper()
            q = q.filter(IngestionRun.triggered_by.ilike(f"%entity:{ent}%"))
        if search and search.strip():
            term = f"%{search.strip()}%"
            q = q.filter(
                or_(
                    cast(RawRecord.raw_record_id, String).ilike(term),
                    RawRecord.checksum_md5.ilike(term),
                    cast(RawRecord.raw_data, String).ilike(term),
                )
            )

        total = q.count()
        rows = (
            q.order_by(IngestionRun.created_at.desc(), RawRecord.run_id, RawRecord.row_index)
            .offset(skip)
            .limit(limit)
            .all()
        )
        if not rows:
            return [], total

        raw_ids = [r[0].raw_record_id for r in rows]
        staging_list = (
            db.query(StagingEntity)
            .filter(StagingEntity.raw_record_id.in_(raw_ids))
            .all()
        )
        staging_by_raw = {s.raw_record_id: s for s in staging_list}

        # ── tenant name lookup (for platform-admin row chips) ──
        page_tenant_ids = {r[0].tenant_id for r in rows}
        tenant_name_by_id: dict[uuid.UUID, str] = {}
        if page_tenant_ids:
            tenant_name_by_id = {
                tid: name
                for tid, name in db.query(Tenant.tenant_id, Tenant.tenant_name)
                .filter(Tenant.tenant_id.in_(page_tenant_ids))
                .all()
            }

        # ── cross-run duplicate detection (tenant + checksum) ──
        # For every (tenant_id, checksum) on this page, find the earliest
        # raw_record_id in the whole tenant — that's the original. Any later
        # record with the same checksum is a duplicate (CROSS_RUN when it
        # lives in a different run than the original; WITHIN_RUN otherwise).
        page_keys: set[tuple[uuid.UUID, str]] = {
            (r[0].tenant_id, r[0].checksum_md5)
            for r in rows
            if r[0].checksum_md5
        }
        originals: dict[tuple[uuid.UUID, str], RawRecord] = {}
        if page_keys:
            tenants_on_page = {k[0] for k in page_keys}
            checksums_on_page = {k[1] for k in page_keys}
            candidates: list[RawRecord] = (
                db.query(RawRecord)
                .filter(
                    RawRecord.tenant_id.in_(tenants_on_page),
                    RawRecord.checksum_md5.in_(checksums_on_page),
                )
                .order_by(RawRecord.created_at.asc(), RawRecord.row_index.asc())
                .all()
            )
            for c in candidates:
                key = (c.tenant_id, c.checksum_md5)
                if key in page_keys and key not in originals:
                    originals[key] = c

        # Map original_run_id → metadata for "first_seen_by"
        first_seen_run_ids = {o.run_id for o in originals.values()}
        first_seen_meta: dict[uuid.UUID, dict[str, Optional[str]]] = {}
        if first_seen_run_ids:
            origin_runs = (
                db.query(IngestionRun)
                .filter(IngestionRun.run_id.in_(first_seen_run_ids))
                .all()
            )
            for r in origin_runs:
                meta = parse_run_metadata(r.triggered_by)
                first_seen_meta[r.run_id] = {
                    "initiated_by": meta.get("initiated_by"),
                    "created_at": r.created_at,
                }

        out: list[dict[str, Any]] = []
        for rr, src, run in rows:
            st = staging_by_raw.get(rr.raw_record_id)
            has_staging = st is not None
            mapped = st.mapped_entity_type if st else None
            run_meta = parse_run_metadata(run.triggered_by)
            ingestion_entity = run_meta.get("entity_type")
            hint = mapped or ingestion_entity or self._entity_hint_from_source(src)
            run_state = str(run.state)
            status = self._processing_status(run_state, has_staging)

            origin = originals.get((rr.tenant_id, rr.checksum_md5))
            is_dup = bool(origin) and origin.raw_record_id != rr.raw_record_id
            dup_scope: Optional[str] = None
            dup_of_raw: Optional[uuid.UUID] = None
            dup_of_run: Optional[uuid.UUID] = None
            first_seen_by: Optional[str] = None
            first_seen_at = None
            if is_dup and origin is not None:
                dup_scope = "CROSS_RUN" if origin.run_id != rr.run_id else "WITHIN_RUN"
                dup_of_raw = origin.raw_record_id
                dup_of_run = origin.run_id
                meta = first_seen_meta.get(origin.run_id, {})
                first_seen_by = meta.get("initiated_by")
                first_seen_at = meta.get("created_at") or origin.created_at

            out.append(
                {
                    "raw_record_id": rr.raw_record_id,
                    "tenant_id": rr.tenant_id,
                    "tenant_name": tenant_name_by_id.get(rr.tenant_id),
                    "run_id": rr.run_id,
                    "source_system_id": rr.source_system_id,
                    "source_name": src.source_name,
                    "ingestion_run_state": run_state,
                    "ingestion_entity_type": ingestion_entity,
                    "run_type": run_meta.get("run_type"),
                    "row_index": rr.row_index,
                    "raw_data": rr.raw_data,
                    "checksum_md5": rr.checksum_md5,
                    "created_at": rr.created_at,
                    "processing_status": status,
                    "entity_display": hint,
                    "has_staging": has_staging,
                    "mapped_entity_type": mapped,
                    "is_duplicate": is_dup,
                    "duplicate_scope": dup_scope,
                    "duplicate_of_raw_record_id": dup_of_raw,
                    "duplicate_of_run_id": dup_of_run,
                    "first_seen_by": first_seen_by,
                    "first_seen_at": first_seen_at,
                    "_src_id": self._derive_source_record_id(rr.raw_data, rr.row_index),
                }
            )

        # Reflect duplicates in the legacy processing_status badge
        for item in out:
            if item["is_duplicate"]:
                item["processing_status"] = "DUPLICATE"

        # Drop helper key from public payload
        for item in out:
            item["source_record_id"] = item.pop("_src_id")

        if exclude_duplicates:
            out = [i for i in out if not i["is_duplicate"]]

        return out, total


# Singleton
raw_service = RawService()
