"""
signalmdm/services/staging_service.py
----------------------------------------
Service layer for StagingEntity creation.

Phase 1 behaviour:
  • Read all RawRecords for a given run.
  • Create one StagingEntity per RawRecord (1-to-1 lineage).
  • entity_data = raw_data (verbatim copy — no transformation in Phase 1).
  • state = READY_FOR_MAPPING.

Security:
  • search / entity_type inputs are LIKE-escaped and injection-scanned.
  • Pagination is bounds-checked.

Data Quality (create_staging_from_run):
  • Skips raw records that already have a staging entity (idempotent).
  • Validates source_system_id consistency between raw record and the run.
  • Detects rows where entity_data is entirely null/empty (flags them).
  • Returns (count, quality_summary) instead of bare int.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional, Union

from sqlalchemy import String, cast, or_, insert, func
from sqlalchemy.orm import Session

from db.models.raw_record import RawRecord
from db.models.staging_entity import StagingEntity
from db.models.source_system import SourceSystem
from db.models.ingestion_run import IngestionRun
from db.models.tenant import Tenant
from db.enums import StagingStateEnum
from schemas.ingestion_schema import parse_run_metadata
from utils.sanitize import sanitize_search, escape_like

logger = logging.getLogger(__name__)

# Values we treat as "missing" when checking entity_data quality
_NULL_LIKE = frozenset({"", "null", "none", "n/a", "na", "nil", "undefined", "-"})


class StagingService:

    def create_staging_from_run(
        self,
        db: Session,
        *,
        run_id: uuid.UUID,
        tenant_id: uuid.UUID,
        source_system_id: uuid.UUID,
    ) -> tuple[int, dict[str, Any]]:
        """
        Read all RawRecords for `run_id` and create corresponding StagingEntities.

        Idempotent — raw records that already have a staging entity are skipped.

        Data quality checks applied per row:
          • source_system_id consistency: raw record's source must match the
            run's source; mismatches are counted and logged (not inserted).
          • Empty / all-null entity_data: rows where every field is null/empty
            are flagged in the quality summary (still inserted so lineage is
            preserved, but state is not overridden).

        Returns:
            (total_staging_created, quality_summary_dict)

        quality_summary keys:
            created                 int   — rows successfully staged
            skipped_already_staged  int   — rows skipped (already had staging)
            skipped_source_mismatch int   — rows skipped (wrong source_system_id)
            rows_all_missing_values int   — staged rows where all values are null
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
        run_source_system_id = run.source_system_id if run else source_system_id

        # Pre-fetch raw_record_ids that already have staging for idempotency
        already_staged_ids: set[uuid.UUID] = set(
            row[0]
            for row in db.query(StagingEntity.raw_record_id)
            .filter(
                StagingEntity.run_id == run_id,
                StagingEntity.tenant_id == tenant_id,
            )
            .all()
        )
        if already_staged_ids:
            logger.info(
                "[staging_service] %d raw records already staged for run=%s — will skip them.",
                len(already_staged_ids),
                run_id,
            )

        quality: dict[str, Any] = {
            "created": 0,
            "skipped_already_staged": len(already_staged_ids),
            "skipped_source_mismatch": 0,
            "rows_all_missing_values": 0,
        }

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

            staging_batch: list[dict[str, Any]] = []
            for raw in raw_batch:
                # Idempotency: skip already staged
                if raw.raw_record_id in already_staged_ids:
                    continue

                # Referential integrity: source_system_id must match the run
                if raw.source_system_id != run_source_system_id:
                    logger.warning(
                        "[staging_service] source_system_id mismatch on raw_record=%s "
                        "(raw has %s, run expects %s). Skipping.",
                        raw.raw_record_id,
                        raw.source_system_id,
                        run_source_system_id,
                    )
                    quality["skipped_source_mismatch"] += 1
                    continue

                # Data quality: detect all-null entity_data
                entity_data = raw.raw_data or {}
                all_missing = all(
                    v is None or (isinstance(v, str) and v.strip().lower() in _NULL_LIKE)
                    for v in entity_data.values()
                ) if entity_data else True

                if all_missing:
                    quality["rows_all_missing_values"] += 1
                    logger.debug(
                        "[staging_service] raw_record=%s has all-null/empty values. "
                        "Staging anyway for lineage preservation.",
                        raw.raw_record_id,
                    )

                staging_batch.append(
                    {
                        "staging_id": uuid.uuid4(),
                        "tenant_id": tenant_id,
                        "run_id": run_id,
                        "raw_record_id": raw.raw_record_id,
                        "source_system_id": source_system_id,
                        "entity_data": raw.raw_data,  # verbatim copy in Phase 1
                        "mapped_entity_type": entity_type,
                        "state": StagingStateEnum.READY_FOR_MAPPING,
                    }
                )

            if staging_batch:
                # Insert only Phase-1-safe columns so older DBs without Phase-2
                # columns (e.g. normalization_* fields) still work.
                db.execute(insert(StagingEntity.__table__), staging_batch)
                db.commit()
                total_created += len(staging_batch)

            offset += chunk_size

        quality["created"] = total_created

        if quality["skipped_source_mismatch"] or quality["rows_all_missing_values"]:
            logger.warning(
                "[staging_service] run=%s quality summary: %s", run_id, quality
            )

        return total_created, quality

    def count_staging_for_run(
        self,
        db: Session,
        run_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> int:
        """Return the number of staging entities created for this run."""
        # Count only by primary key column. Querying the full ORM entity can
        # attempt to reference newer optional columns not present in older DBs.
        return (
            db.query(func.count(StagingEntity.staging_id))
            .filter(
                StagingEntity.run_id == run_id,
                StagingEntity.tenant_id == tenant_id,
            )
            .scalar()
            or 0
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
        """Deterministic 70–99 score from payload shape (Phase 1 placeholder)."""
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
        if s in (StagingStateEnum.MAPPED.value, StagingStateEnum.READY_FOR_MAPPING.value):
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
        """
        Paginated staging entities for the Staging screen (newest first).

        Security:
          - `search` is LIKE-escaped and injection-scanned.
          - `entity_type` is stripped/uppercased and LIKE-escaped.
          - Pagination is bounds-checked.
        """
        # Bounds-check pagination
        skip  = max(0, int(skip))
        limit = max(1, min(int(limit), 500))

        # Sanitize inputs
        safe_search = sanitize_search(search)
        safe_entity: Optional[str] = None
        if entity_type and entity_type.strip():
            safe_entity = escape_like(entity_type.strip().upper()[:50])

        tid = self._parse_tenant_id(tenant_id)
        q = (
            db.query(
                StagingEntity.staging_id,
                StagingEntity.tenant_id,
                StagingEntity.run_id,
                StagingEntity.raw_record_id,
                StagingEntity.source_system_id,
                StagingEntity.entity_data,
                StagingEntity.state,
                StagingEntity.mapped_entity_type,
                StagingEntity.created_at,
                SourceSystem.source_name,
                RawRecord.tenant_id,
                RawRecord.source_system_id,
                RawRecord.row_index,
                RawRecord.raw_data,
                RawRecord.checksum_md5,
                RawRecord.run_id,
                IngestionRun.state,
                IngestionRun.triggered_by,
            )
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
        if safe_entity:
            q = q.filter(
                IngestionRun.triggered_by.ilike(f"%entity:{safe_entity}%", escape="\\")
            )
        if safe_search:
            term = f"%{safe_search}%"
            q = q.filter(
                or_(
                    cast(StagingEntity.staging_id, String).ilike(term, escape="\\"),
                    cast(StagingEntity.raw_record_id, String).ilike(term, escape="\\"),
                    cast(RawRecord.raw_data, String).ilike(term, escape="\\"),
                    cast(StagingEntity.entity_data, String).ilike(term, escape="\\"),
                )
            )

        total = q.count()
        rows = (
            q.order_by(StagingEntity.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        if not rows:
            return [], total

        # Tenant name lookup
        page_tenant_ids = {r[1] for r in rows}
        tenant_name_by_id: dict[uuid.UUID, str] = {}
        if page_tenant_ids:
            tenant_name_by_id = {
                t_id: name
                for t_id, name in db.query(Tenant.tenant_id, Tenant.tenant_name)
                .filter(Tenant.tenant_id.in_(page_tenant_ids))
                .all()
            }

        # Cross-run duplicate detection
        page_keys: set[tuple[uuid.UUID, str]] = {
            (r[10], r[14])
            for r in rows
            if r[14]
        }
        originals: dict[tuple[uuid.UUID, str], RawRecord] = {}
        if page_keys:
            tenants_on_page  = {k[0] for k in page_keys}
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

        first_seen_run_ids = {o.run_id for o in originals.values()}
        first_seen_meta: dict[uuid.UUID, dict[str, Any]] = {}
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

        original_raw_ids = {o.raw_record_id for o in originals.values()}
        staging_by_original_raw: dict[uuid.UUID, StagingEntity] = {}
        if original_raw_ids:
            for s in (
                db.query(StagingEntity)
                .filter(StagingEntity.raw_record_id.in_(original_raw_ids))
                .all()
            ):
                staging_by_original_raw[s.raw_record_id] = s

        out: list[dict[str, Any]] = []
        for row in rows:
            st_staging_id = row[0]
            st_tenant_id = row[1]
            st_run_id = row[2]
            st_raw_record_id = row[3]
            st_source_system_id = row[4]
            st_entity_data = row[5]
            st_state = row[6]
            st_mapped_entity_type = row[7]
            st_created_at = row[8]

            source_name = row[9]

            raw_tenant_id = row[10]
            raw_source_system_id = row[11]
            raw_row_index = row[12]
            raw_data = row[13]
            raw_checksum_md5 = row[14]
            raw_run_id = row[15]

            run_state = row[16]
            run_triggered_by = row[17]

            run_meta = parse_run_metadata(run_triggered_by)
            ingestion_entity = run_meta.get("entity_type")
            hint = (
                st_mapped_entity_type
                or ingestion_entity
                or "RECORD"
            )
            src_id = self._derive_source_record_id(raw_data, raw_row_index)
            dq = self._dq_score_placeholder(st_entity_data)
            state_val = st_state.value if isinstance(st_state, StagingStateEnum) else str(st_state)

            origin = originals.get((raw_tenant_id, raw_checksum_md5))
            is_dup = bool(origin) and origin.raw_record_id != st_raw_record_id
            dup_scope: Optional[str] = None
            dup_of_raw: Optional[uuid.UUID] = None
            dup_of_run: Optional[uuid.UUID] = None
            dup_of_staging: Optional[uuid.UUID] = None
            first_seen_by: Optional[str] = None
            first_seen_at = None
            if is_dup and origin is not None:
                dup_scope     = "CROSS_RUN" if origin.run_id != raw_run_id else "WITHIN_RUN"
                dup_of_raw    = origin.raw_record_id
                dup_of_run    = origin.run_id
                origin_st     = staging_by_original_raw.get(origin.raw_record_id)
                dup_of_staging = origin_st.staging_id if origin_st else None
                meta          = first_seen_meta.get(origin.run_id, {})
                first_seen_by = meta.get("initiated_by")
                first_seen_at = meta.get("created_at") or origin.created_at

            # Missing-value flag for this staging row
            entity_data = st_entity_data or {}
            has_missing_values = any(
                v is None or (isinstance(v, str) and v.strip().lower() in _NULL_LIKE)
                for v in entity_data.values()
            )

            # Invalid reference check: staging source_system_id must match raw record's
            has_invalid_reference = (
                st_source_system_id != raw_source_system_id
            )
            if has_invalid_reference:
                logger.warning(
                    "[staging_service] Inconsistent source_system_id: staging=%s raw=%s "
                    "on staging_id=%s.",
                    st_source_system_id, raw_source_system_id, st_staging_id,
                )

            out.append(
                {
                    "staging_id":                  st_staging_id,
                    "tenant_id":                   st_tenant_id,
                    "tenant_name":                 tenant_name_by_id.get(st_tenant_id),
                    "run_id":                      st_run_id,
                    "raw_record_id":               st_raw_record_id,
                    "source_system_id":            st_source_system_id,
                    "source_name":                 source_name,
                    "state":                       state_val,
                    "mapped_entity_type":          st_mapped_entity_type,
                    "ingestion_entity_type":       ingestion_entity,
                    "entity_display":              hint,
                    "run_type":                    run_meta.get("run_type"),
                    "entity_data":                 st_entity_data,
                    "raw_data":                    raw_data,
                    "created_at":                  st_created_at,
                    "ingestion_run_state":         str(run_state),
                    "source_record_id":            src_id,
                    "dq_score":                    dq,
                    "validation_status":           self._validation_status(st_state),
                    "has_missing_values":          has_missing_values,
                    "has_invalid_reference":       has_invalid_reference,
                    "is_duplicate":                is_dup,
                    "duplicate_scope":             dup_scope,
                    "duplicate_of_raw_record_id":  dup_of_raw,
                    "duplicate_of_run_id":         dup_of_run,
                    "duplicate_of_staging_id":     dup_of_staging,
                    "first_seen_by":               first_seen_by,
                    "first_seen_at":               first_seen_at,
                }
            )
        return out, total


# Singleton
staging_service = StagingService()
