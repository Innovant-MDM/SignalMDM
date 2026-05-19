/**
 * src/services/stagingService.ts
 * -------------------------------
 * Staging Records — lists staging_entities from the backend.
 *
 * Same patterns as rawLandingService: StandardResponse, cookies, X-Tenant-ID.
 */

import { api, ApiError } from './api';

/** Backend staging state (Phase 1). */
export type StagingStateApi = 'READY_FOR_MAPPING' | 'MAPPED' | 'REJECTED';

/** One row from GET /api/v1/staging-records/ */
export interface StagingRecordListRead {
  staging_id: string;
  tenant_id: string;
  tenant_name?: string | null;
  run_id: string;
  raw_record_id: string;
  source_system_id: string;
  source_name: string;
  state: StagingStateApi;
  mapped_entity_type: string | null;
  ingestion_entity_type: string | null;
  run_type: string | null;
  entity_display: string;
  entity_data: Record<string, unknown>;
  raw_data: Record<string, unknown>;
  created_at: string;
  ingestion_run_state: string;
  source_record_id: string;
  dq_score: number;
  validation_status: string;
  is_duplicate?: boolean;
  duplicate_scope?: 'WITHIN_RUN' | 'CROSS_RUN' | null;
  duplicate_of_raw_record_id?: string | null;
  duplicate_of_run_id?: string | null;
  duplicate_of_staging_id?: string | null;
  first_seen_by?: string | null;
  first_seen_at?: string | null;
}

export interface StagingListResponse {
  items: StagingRecordListRead[];
  total: number;
  skip: number;
  limit: number;
}

export type StagingBadgeClass = 'READY' | 'VALIDATED' | 'FAILED' | 'CREATED';

export type ValidationStatusUi = 'PASSED' | 'FAILED' | 'PARTIAL' | 'PENDING';

export type ValidationRuleResult = 'PASS' | 'FAIL' | 'WARN' | 'PENDING';

export interface ValidationRuleUi {
  rule: string;
  result: ValidationRuleResult;
}

/** UI row for table + drawer (stable shape). */
export interface StagingUiRecord {
  id: string;
  tenantId: string;
  tenantName: string | null;
  rawId: string;
  srcId: string;
  entity: string;
  ingestionEntity: string | null;
  runType: string | null;
  stgState: string;
  stgBadgeClass: StagingBadgeClass;
  valStatus: ValidationStatusUi;
  dqScore: number;
  createdAt: string;
  source: string;
  runId: string;
  runShort: string;
  ingestionRunState: string;
  rawPayload: Record<string, unknown>;
  canonicalPayload: Record<string, unknown>;
  validationRules: ValidationRuleUi[];
  isDuplicate: boolean;
  duplicateScope: 'WITHIN_RUN' | 'CROSS_RUN' | null;
  duplicateOfRawId: string | null;
  duplicateOfRunId: string | null;
  duplicateOfStagingId: string | null;
  firstSeenBy: string | null;
  firstSeenAt: string | null;
}

function stagingBadgeClass(state: string): StagingBadgeClass {
  if (state === 'READY_FOR_MAPPING') return 'READY';
  if (state === 'MAPPED') return 'VALIDATED';
  if (state === 'REJECTED') return 'FAILED';
  return 'CREATED';
}

function normalizeValStatus(s: string): ValidationStatusUi {
  if (s === 'FAILED') return 'FAILED';
  if (s === 'PARTIAL') return 'PARTIAL';
  if (s === 'PENDING') return 'PENDING';
  return 'PASSED';
}

function deriveValidationRules(val: ValidationStatusUi): ValidationRuleUi[] {
  const base: ValidationRuleUi[] = [
    { rule: 'Payload not empty', result: 'PASS' },
    { rule: 'Source key present', result: 'PASS' },
    { rule: 'Tenant scope', result: 'PASS' },
    { rule: 'Run consistency', result: 'PASS' },
    { rule: 'Duplicate check (Phase 2)', result: 'PENDING' },
  ];
  if (val === 'FAILED') base[1] = { rule: 'Source key present', result: 'FAIL' };
  if (val === 'PARTIAL') base[3] = { rule: 'Run consistency', result: 'WARN' };
  return base;
}

function fmtTs(iso: string | null | undefined): string | null {
  if (!iso) return null;
  return iso.includes('T') ? iso.replace('T', ' ').slice(0, 19) : iso;
}

export function toStagingUiRecord(r: StagingRecordListRead): StagingUiRecord {
  const val = normalizeValStatus(r.validation_status);
  return {
    id: r.staging_id,
    tenantId: r.tenant_id,
    tenantName: r.tenant_name ?? null,
    rawId: r.raw_record_id,
    srcId: r.source_record_id,
    entity: r.ingestion_entity_type || r.entity_display,
    ingestionEntity: r.ingestion_entity_type,
    runType: r.run_type,
    stgState: r.state,
    stgBadgeClass: stagingBadgeClass(r.state),
    valStatus: val,
    dqScore: r.dq_score,
    createdAt: fmtTs(r.created_at) ?? '',
    source: r.source_name,
    runId: r.run_id,
    runShort: `${r.run_id.slice(0, 8)}…`,
    ingestionRunState: r.ingestion_run_state,
    rawPayload: { ...r.raw_data },
    canonicalPayload: { ...r.entity_data },
    validationRules: deriveValidationRules(val),
    isDuplicate: r.is_duplicate ?? false,
    duplicateScope: r.duplicate_scope ?? null,
    duplicateOfRawId: r.duplicate_of_raw_record_id ?? null,
    duplicateOfRunId: r.duplicate_of_run_id ?? null,
    duplicateOfStagingId: r.duplicate_of_staging_id ?? null,
    firstSeenBy: r.first_seen_by ?? null,
    firstSeenAt: fmtTs(r.first_seen_at),
  };
}

export const stagingService = {
  /**
   * GET /api/v1/staging-records/
   */
  async listRecords(params: {
    skip?: number;
    limit?: number;
    tenantId?: string;
    runId?: string;
    sourceSystemId?: string;
    entityType?: string;
    search?: string;
  }): Promise<StagingListResponse> {
    const q = new URLSearchParams();
    if (params.skip != null) q.set('skip', String(params.skip));
    if (params.limit != null) q.set('limit', String(params.limit));
    if (params.runId) q.set('run_id', params.runId);
    if (params.sourceSystemId) q.set('source_system_id', params.sourceSystemId);
    if (params.entityType) q.set('entity_type', params.entityType);
    if (params.search?.trim()) q.set('search', params.search.trim());
    const qs = q.toString();
    const path = qs ? `/staging-records/?${qs}` : '/staging-records/';
    const headers = params.tenantId ? { 'X-Tenant-ID': params.tenantId } : undefined;
    const res = await api.get<StagingListResponse>(path, headers);
    if (!res.data) {
      throw new ApiError(res.message || 'No staging records payload', 400, res.errors ?? []);
    }
    return res.data;
  },
};

export { ApiError };
