/**
 * src/services/ingestionRunService.ts
 * -----------------------------------
 * Service layer for Ingestion Run API endpoints.
 */

import { api, ApiError } from './api';

// ─── Backend response shape (IngestionRunRead) ─────────────────────────────
export interface IngestionRunRead {
  run_id: string;
  tenant_id: string;
  source_system_id: string;
  state: string;
  triggered_by: string | null;
  file_count: number;
  record_count: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  upload_session_id?: string | null;
  entity_type?: string | null;
  run_type?: string | null;
  trigger_type?: string | null;
}

export type RunStatus = "CREATED" | "RUNNING" | "RAW_LOADED" | "STAGING_CREATED" | "FAILED" | "COMPLETED";

export interface IngestionRunRecord {
  id: string;
  tenantId: string;
  sourceId: string;
  sourceName: string;
  state: RunStatus;
  triggeredBy: string;
  fileCount: number;
  recordCount: number;
  errorMessage: string | null;
  startedAt: string | null;
  completedAt: string | null;
  createdAt: string;
  uploadSessionId: string | null;
  entityType: string | null;
  runType: string | null;
  triggerType: string | null;
}

/** Server resolves entity / run type / trigger when omitted. */
export interface StartFromSessionPayload {
  source_system_id: string;
  upload_session_id: string;
  triggered_by?: string;
}

export interface IngestionLineageRunSummary {
  run_id: string;
  source_system_id: string;
  source_name: string;
  entity_type: string | null;
  run_type: string | null;
  state: string;
  raw_record_count: number;
  staging_record_count: number;
  counts_aligned: boolean;
  pipeline_note: string;
  created_at: string;
}

export interface IngestionResolvedConfig {
  upload_session_id: string;
  source_system_id: string;
  session_name: string;
  session_domain: string;
  entity_type: string;
  entity_resolved_from: 'session_domain' | 'source_supported_entities' | 'override';
  run_type: string;
  run_type_reason: string;
  trigger_type: string;
  trigger_type_reason: string;
  file_count: number;
  supported_entities: string[];
}

const RUN_TYPE_LABELS: Record<string, string> = {
  initial_load: 'Initial load (first ingestion for this source)',
  prior_completed_run_exists: 'Delta load (prior completed run exists for this source)',
  explicit: 'Explicit override',
  first_run_for_source: 'Initial load (first run for this source)',
};

const TRIGGER_LABELS: Record<string, string> = {
  user_started_from_ui: 'Manual — started from Ingestion Runs screen',
  explicit: 'Explicit override',
};

const ENTITY_FROM_LABELS: Record<string, string> = {
  session_domain: 'From upload session domain',
  source_supported_entities: 'From source supported entities',
  override: 'Manual override',
};

export function describeResolvedConfig(cfg: IngestionResolvedConfig): {
  entityHint: string;
  runTypeHint: string;
  triggerHint: string;
} {
  return {
    entityHint: ENTITY_FROM_LABELS[cfg.entity_resolved_from] ?? cfg.entity_resolved_from,
    runTypeHint: RUN_TYPE_LABELS[cfg.run_type_reason] ?? cfg.run_type_reason,
    triggerHint: TRIGGER_LABELS[cfg.trigger_type_reason] ?? cfg.trigger_type_reason,
  };
}

const TERMINAL_STATES: RunStatus[] = ["COMPLETED", "FAILED"];

function formatTs(iso: string | null): string | null {
  if (!iso) return null;
  return iso.replace('T', ' ').slice(0, 16);
}

function toIngestionRunRecord(raw: IngestionRunRead, sourceNameMap: Record<string, string> = {}): IngestionRunRecord {
  return {
    id: raw.run_id,
    tenantId: raw.tenant_id,
    sourceId: raw.source_system_id,
    sourceName: sourceNameMap[raw.source_system_id] || raw.source_system_id,
    state: raw.state as RunStatus,
    triggeredBy: raw.triggered_by || 'system',
    fileCount: raw.file_count,
    recordCount: raw.record_count,
    errorMessage: raw.error_message,
    startedAt: formatTs(raw.started_at),
    completedAt: formatTs(raw.completed_at),
    createdAt: formatTs(raw.created_at) ?? '',
    uploadSessionId: raw.upload_session_id ?? null,
    entityType: raw.entity_type ?? null,
    runType: raw.run_type ?? null,
    triggerType: raw.trigger_type ?? null,
  };
}

export const ingestionRunService = {
  async listRuns(skip = 0, limit = 50, sourceNameMap: Record<string, string> = {}, tenantId?: string): Promise<IngestionRunRecord[]> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.get<IngestionRunRead[]>(`/ingestion/?skip=${skip}&limit=${limit}`, headers);
    return (res.data ?? []).map(raw => toIngestionRunRecord(raw, sourceNameMap));
  },

  async getRunStatus(runId: string, tenantId?: string): Promise<IngestionRunRecord> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.get<IngestionRunRead>(`/ingestion/${runId}/status`, headers);
    if (!res.data) throw new Error('Ingestion run status not found.');
    return toIngestionRunRecord(res.data);
  },

  async deleteRun(runId: string, tenantId?: string): Promise<void> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.delete<null>(`/ingestion/${runId}`, headers);
    if (!res.success) {
      throw new ApiError(res.message || 'Failed to delete ingestion run', 400, res.errors ?? []);
    }
  },

  async startRun(sourceSystemId: string, triggeredBy?: string, tenantId?: string): Promise<IngestionRunRecord> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.post<IngestionRunRead>('/ingestion/start', {
      source_system_id: sourceSystemId,
      triggered_by: triggeredBy || 'user',
    }, headers);
    if (!res.data) throw new Error('No data returned after starting ingestion run.');
    return toIngestionRunRecord(res.data);
  },

  /**
   * Start ingestion using files already uploaded in an Upload Data session.
   * POST /api/v1/ingestion/start-from-session
   */
  async fetchLineageSummary(tenantId?: string, limit = 50): Promise<IngestionLineageRunSummary[]> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.get<IngestionLineageRunSummary[]>(
      `/ingestion/lineage-summary?limit=${limit}`,
      headers,
    );
    return res.data ?? [];
  },

  async resolveConfig(
    uploadSessionId: string,
    sourceSystemId: string,
    tenantId?: string,
  ): Promise<IngestionResolvedConfig> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const q = new URLSearchParams({
      upload_session_id: uploadSessionId,
      source_system_id: sourceSystemId,
    });
    const res = await api.get<IngestionResolvedConfig>(
      `/ingestion/resolve-config?${q.toString()}`,
      headers,
    );
    if (!res.data) throw new Error('Could not resolve ingestion settings.');
    return res.data;
  },

  async startRunFromSession(
    payload: StartFromSessionPayload,
    tenantId?: string,
  ): Promise<IngestionRunRecord> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.post<IngestionRunRead>('/ingestion/start-from-session', payload, headers);
    if (!res.data) throw new Error('No data returned after starting ingestion from session.');
    return toIngestionRunRecord(res.data);
  },

  /**
   * Poll until the run reaches a terminal state or timeout (ms).
   */
  async waitForRun(
    runId: string,
    tenantId: string | undefined,
    options: { intervalMs?: number; timeoutMs?: number; onTick?: (run: IngestionRunRecord) => void } = {},
  ): Promise<IngestionRunRecord> {
    const intervalMs = options.intervalMs ?? 3000;
    const timeoutMs = options.timeoutMs ?? 180_000;
    const started = Date.now();
    let last: IngestionRunRecord | null = null;

    while (Date.now() - started < timeoutMs) {
      last = await this.getRunStatus(runId, tenantId);
      options.onTick?.(last);
      if (TERMINAL_STATES.includes(last.state)) {
        return last;
      }
      await new Promise((r) => setTimeout(r, intervalMs));
    }

    if (last) return last;
    throw new Error('Timed out waiting for ingestion run to finish.');
  },

  async cancelRun(runId: string, tenantId?: string): Promise<void> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    await api.post(`/ingestion/${runId}/cancel`, {}, headers);
  },
};

export { ApiError };
