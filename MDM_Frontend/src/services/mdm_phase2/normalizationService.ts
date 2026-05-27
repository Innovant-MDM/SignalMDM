/**
 * src/services/mdm_phase2/normalizationService.ts
 * -----------------------------------------------
 * Frontend service wrapper for Normalization Runs and Mapping Errors API endpoints.
 */

import { api } from '../api';

export interface NormalizationRunRead {
  run_id: string;
  tenant_id: string;
  ingestion_run_id: string | null;
  source_system_id: string;
  entity_type: string;
  status: string;
  total_records: number;
  processed_records: number;
  successful_records: number;
  failed_records: number;
  error_message: string | null;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface NormalizationRunCreate {
  source_system_id: string;
  entity_type: string;
  ingestion_run_id?: string | null;
}

export interface MappingErrorRead {
  error_id: string;
  tenant_id: string;
  normalization_run_id: string;
  staging_id: string;
  error_type: string;
  source_field: string | null;
  source_value: string | null;
  error_message: string;
  status: string;
  resolved_at: string | null;
  resolved_by: string | null;
  created_at: string;
  updated_at: string;
}

export const normalizationService = {
  /**
   * List all normalization runs.
   */
  async listRuns(tenantId?: string): Promise<NormalizationRunRead[]> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.get<NormalizationRunRead[]>('/mdm/normalization-runs/', headers);
    return res.data ?? [];
  },

  /**
   * Get details/status of a specific normalization run.
   */
  async getRunStatus(runId: string): Promise<NormalizationRunRead> {
    const res = await api.get<NormalizationRunRead>(`/mdm/normalization-runs/${runId}/status`);
    if (!res.data) throw new Error('No data returned from server for normalization run status.');
    return res.data;
  },

  /**
   * Trigger a new normalization run.
   */
  async triggerRun(payload: NormalizationRunCreate, tenantId?: string): Promise<NormalizationRunRead> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.post<NormalizationRunRead>('/mdm/normalization-runs/', payload, headers);
    if (!res.data) throw new Error('No data returned from server after triggering normalization run.');
    return res.data;
  },

  /**
   * List all mapping errors.
   */
  async listErrors(status = 'OPEN', tenantId?: string): Promise<MappingErrorRead[]> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.get<MappingErrorRead[]>(`/mdm/mapping-errors/?status_val=${status}`, headers);
    return res.data ?? [];
  },

  /**
   * Retry processing for a specific failed mapping error record.
   */
  async retryError(errorId: string): Promise<{ success: boolean; message: string }> {
    const res = await api.post<{ success: boolean; message: string }>(`/mdm/mapping-errors/${errorId}/retry`, {});
    if (!res.data) throw new Error('No status message returned from server after retry.');
    return res.data;
  },
};
