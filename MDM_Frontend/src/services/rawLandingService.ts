/**
 * src/services/rawLandingService.ts
 * -----------------------------------
 * Raw Landing — lists immutable raw_records from the backend.
 *
 * Mirrors sourceService / ingestionRunService: StandardResponse, cookies, X-Tenant-ID.
 */

import { api, ApiError } from './api';

export type RawProcessingStatus =
  | 'PENDING'
  | 'PROCESSING'
  | 'COMPLETED'
  | 'FAILED'
  | 'DUPLICATE';

/** One row from GET /api/v1/raw-records/ */
export interface RawRecordListRead {
  raw_record_id: string;
  tenant_id: string;
  tenant_name?: string | null;
  run_id: string;
  source_system_id: string;
  source_name: string;
  ingestion_run_state: string;
  row_index: number | null;
  raw_data: Record<string, unknown>;
  checksum_md5: string;
  created_at: string;
  processing_status: RawProcessingStatus;
  ingestion_entity_type: string | null;
  run_type: string | null;
  entity_display: string;
  has_staging: boolean;
  mapped_entity_type: string | null;
  source_record_id: string;
  is_duplicate?: boolean;
  duplicate_scope?: 'WITHIN_RUN' | 'CROSS_RUN' | null;
  duplicate_of_raw_record_id?: string | null;
  duplicate_of_run_id?: string | null;
  first_seen_by?: string | null;
  first_seen_at?: string | null;
}

export interface RawLandingListResponse {
  items: RawRecordListRead[];
  total: number;
  skip: number;
  limit: number;
}

/** UI row derived from API (stable for table + modal). */
export interface RawLandingRecord {
  id: string;
  tenantId: string;
  tenantName: string | null;
  srcId: string;
  entity: string;
  ingestionEntity: string | null;
  runType: string | null;
  source: string;
  runShort: string;
  runId: string;
  status: RawProcessingStatus;
  receivedAt: string;
  payload: Record<string, string | number | boolean | null>;
  checksum: string;
  ingestionRunState: string;
  hasStaging: boolean;
  isDuplicate: boolean;
  duplicateScope: 'WITHIN_RUN' | 'CROSS_RUN' | null;
  duplicateOfRawId: string | null;
  duplicateOfRunId: string | null;
  firstSeenBy: string | null;
  firstSeenAt: string | null;
}

function asPayload(data: Record<string, unknown>): Record<string, string | number | boolean | null> {
  const out: Record<string, string | number | boolean | null> = {};
  for (const [k, v] of Object.entries(data)) {
    if (v === null || typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') {
      out[k] = v;
    } else {
      out[k] = JSON.stringify(v);
    }
  }
  return out;
}

function fmtTs(iso: string | null | undefined): string | null {
  if (!iso) return null;
  return iso.includes('T') ? iso.replace('T', ' ').slice(0, 19) : iso;
}

export function toRawLandingRecord(r: RawRecordListRead): RawLandingRecord {
  return {
    id: r.raw_record_id,
    tenantId: r.tenant_id,
    tenantName: r.tenant_name ?? null,
    srcId: r.source_record_id,
    entity: r.ingestion_entity_type || r.entity_display,
    ingestionEntity: r.ingestion_entity_type,
    runType: r.run_type,
    source: r.source_name,
    runShort: `${r.run_id.slice(0, 8)}…`,
    runId: r.run_id,
    status: r.processing_status,
    receivedAt: fmtTs(r.created_at) ?? '',
    payload: asPayload(r.raw_data),
    checksum: r.checksum_md5,
    ingestionRunState: r.ingestion_run_state,
    hasStaging: r.has_staging,
    isDuplicate: r.is_duplicate ?? r.processing_status === 'DUPLICATE',
    duplicateScope: r.duplicate_scope ?? null,
    duplicateOfRawId: r.duplicate_of_raw_record_id ?? null,
    duplicateOfRunId: r.duplicate_of_run_id ?? null,
    firstSeenBy: r.first_seen_by ?? null,
    firstSeenAt: fmtTs(r.first_seen_at),
  };
}

export const rawLandingService = {
  /**
   * GET /api/v1/raw-records/
   */
  async listRecords(params: {
    skip?: number;
    limit?: number;
    tenantId?: string;
    runId?: string;
    sourceSystemId?: string;
    entityType?: string;
    excludeDuplicates?: boolean;
    search?: string;
  }): Promise<RawLandingListResponse> {
    const q = new URLSearchParams();
    if (params.skip != null) q.set('skip', String(params.skip));
    if (params.limit != null) q.set('limit', String(params.limit));
    if (params.runId) q.set('run_id', params.runId);
    if (params.sourceSystemId) q.set('source_system_id', params.sourceSystemId);
    if (params.entityType) q.set('entity_type', params.entityType);
    if (params.excludeDuplicates) q.set('exclude_duplicates', 'true');
    if (params.search?.trim()) q.set('search', params.search.trim());
    const qs = q.toString();
    const path = qs ? `/raw-records/?${qs}` : '/raw-records/';
    const headers = params.tenantId ? { 'X-Tenant-ID': params.tenantId } : undefined;
    const res = await api.get<RawLandingListResponse>(path, headers);
    if (!res.data) {
      throw new ApiError(res.message || 'No raw records payload', 400, res.errors ?? []);
    }
    return res.data;
  },
};

export { ApiError };
