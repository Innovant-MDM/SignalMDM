/**
 * src/services/apiLogsService.ts
 * --------------------------------
 * API Logs — lists immutable audit_log entries from the backend.
 *
 * Same patterns as rawLandingService / stagingService.
 */

import { api, ApiError } from './api';

export type OperationType = 'INSERT' | 'UPDATE' | 'DELETE' | 'MERGE' | 'UPLOAD' | 'CANCEL' | 'PROCESS_RAW' | 'PROCESS_ERROR';

/** One row from GET /api/v1/api-logs/ */
export interface ApiLogListRead {
  audit_id: string;
  tenant_id: string | null;
  tenant_name: string | null;
  entity_name: string | null;
  entity_id: string | null;
  operation_type: OperationType | string | null;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  performed_by: string | null;
  performed_at: string;
  source_ip: string | null;
  trace_id: string | null;
}

export interface ApiLogsListResponse {
  items: ApiLogListRead[];
  total: number;
  skip: number;
  limit: number;
}

/** UI row for table + drawer. */
export interface ApiLogUiRecord {
  id: string;
  tenantId: string | null;
  tenantName: string;
  entityName: string;
  entityId: string | null;
  operation: string;
  performedBy: string;
  performedAt: string;
  sourceIp: string | null;
  traceId: string | null;
  oldValue: Record<string, unknown> | null;
  newValue: Record<string, unknown> | null;
}

export function toApiLogUiRecord(r: ApiLogListRead): ApiLogUiRecord {
  const performed = r.performed_at.includes('T')
    ? r.performed_at.replace('T', ' ').slice(0, 19)
    : r.performed_at;
  return {
    id: r.audit_id,
    tenantId: r.tenant_id,
    tenantName: r.tenant_name ?? (r.tenant_id ? '—' : 'Platform'),
    entityName: r.entity_name ?? '—',
    entityId: r.entity_id,
    operation: r.operation_type ?? '—',
    performedBy: r.performed_by ?? 'system',
    performedAt: performed,
    sourceIp: r.source_ip,
    traceId: r.trace_id,
    oldValue: r.old_value,
    newValue: r.new_value,
  };
}

export const apiLogsService = {
  /**
   * GET /api/v1/api-logs/
   */
  async listLogs(params: {
    skip?: number;
    limit?: number;
    tenantId?: string;
    operationType?: string;
    entityName?: string;
    search?: string;
  }): Promise<ApiLogsListResponse> {
    const q = new URLSearchParams();
    if (params.skip != null) q.set('skip', String(params.skip));
    if (params.limit != null) q.set('limit', String(params.limit));
    if (params.operationType) q.set('operation_type', params.operationType);
    if (params.entityName) q.set('entity_name', params.entityName);
    if (params.search?.trim()) q.set('search', params.search.trim());
    const qs = q.toString();
    const path = qs ? `/api-logs/?${qs}` : '/api-logs/';
    const headers = params.tenantId ? { 'X-Tenant-ID': params.tenantId } : undefined;
    const res = await api.get<ApiLogsListResponse>(path, headers);
    if (!res.data) {
      throw new ApiError(res.message || 'No API logs payload', 400, res.errors ?? []);
    }
    return res.data;
  },
};

export { ApiError };
