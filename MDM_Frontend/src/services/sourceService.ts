/**
 * src/services/sourceService.ts
 * ------------------------------
 * Service layer for Source System API endpoints.
 *
 * Integrated with the SignalMDM backend:
 *   - Handles AES-encrypted JWT via httpOnly cookies.
 *   - Sends X-Device-ID for fingerprint validation.
 *   - Maps backend models (SourceSystemRead) to frontend display records.
 */

import { api, ApiError } from './api';

// ─── Backend enum constants (mirrors signalmdm/enums.py) ───────────────────

export const SOURCE_TYPES = [
  'CRM', 'ERP', 'DATABASE', 'FILE', 'API', 'STREAMING', 'OTHER',
] as const;
export type SourceType = typeof SOURCE_TYPES[number];

export const CONNECTION_TYPES = [
  'CSV', 'JSON', 'REST_API', 'JDBC', 'SFTP', 'S3', 'OTHER',
] as const;
export type ConnectionType = typeof CONNECTION_TYPES[number];

export const ENTITY_TYPES = [
  'CUSTOMER', 'PRODUCT', 'SUPPLIER', 'EMPLOYEE', 'LOCATION', 'ACCOUNT', 'ASSET', 'OTHER',
] as const;
export type EntityType = typeof ENTITY_TYPES[number];

export const STATUS_ENUM = [
  'ACTIVE', 'SUSPENDED', 'ARCHIVED', 'DEACTIVATED',
] as const;
export type StatusType = typeof STATUS_ENUM[number];

// ─── Backend response shape (SourceSystemRead) ────────────────────────────

export interface SourceSystemRead {
  source_system_id: string;
  tenant_id: string;
  source_name: string;
  source_code: string;
  source_type: string;
  connection_type: string;
  config_json: Record<string, unknown> | null;
  is_active: boolean;
  status: string;           // ACTIVE | SUSPENDED | ARCHIVED
  created_at: string;       // ISO datetime string
  updated_at: string;
}

// ─── Frontend display model ────────────────────────────────────────────────

/**
 * SourceRecord is the shape used throughout the frontend UI.
 * It is derived from SourceSystemRead and hides backend naming conventions.
 */
export interface SourceRecord {
  id: string;                          // ← source_system_id
  tenantId: string;                    // ← tenant_id
  sourceName: string;                  // ← source_name
  sourceCode: string;                  // ← source_code (lowercase slug)
  sourceType: string;                  // ← source_type
  connection_type: string;             // ← connection_type (Fix: was missing in some views)
  connectionType: string;              // ← connection_type
  configJson: Record<string, unknown>; // ← config_json (never null here)
  supportedEntities: string[];         // ← config_json.supported_entities
  status: 'ACTIVE' | 'INACTIVE' | 'SUSPENDED' | 'ARCHIVED';
  isActive: boolean;
  createdDate: string;                 // YYYY-MM-DD slice of created_at
  updatedDate: string;
}

// ─── Create request payload ────────────────────────────────────────────────

export interface SourceSystemCreatePayload {
  source_name: string;
  source_code: string;
  source_type: SourceType;
  connection_type: ConnectionType;
  config_json?: Record<string, unknown> | null;
}

// ─── Mapping helpers ───────────────────────────────────────────────────────

function mapStatus(
  isActive: boolean,
  backendStatus: string,
): SourceRecord['status'] {
  if (!isActive || backendStatus === 'DEACTIVATED') return 'INACTIVE';
  if (backendStatus === 'SUSPENDED') return 'SUSPENDED';
  if (backendStatus === 'ARCHIVED') return 'ARCHIVED';
  return 'ACTIVE';
}

function toSourceRecord(raw: SourceSystemRead): SourceRecord {
  const cfg = raw.config_json ?? {};
  // supported_entities is typically stored in config_json in Phase 1
  const supportedEntities = Array.isArray(cfg['supported_entities'])
    ? (cfg['supported_entities'] as string[])
    : [];

  return {
    id: raw.source_system_id,
    tenantId: raw.tenant_id,
    sourceName: raw.source_name,
    sourceCode: raw.source_code,
    sourceType: raw.source_type,
    connection_type: raw.connection_type,
    connectionType: raw.connection_type,
    configJson: cfg,
    supportedEntities,
    status: mapStatus(raw.is_active, raw.status),
    isActive: raw.is_active,
    createdDate: raw.created_at.slice(0, 10),
    updatedDate: raw.updated_at.slice(0, 10),
  };
}

// ─── Service ──────────────────────────────────────────────────────────────

export const sourceService = {
  /**
   * Fetch all active source systems for the authenticated tenant.
   * GET /api/v1/sources/?skip=<skip>&limit=<limit>
   */
  async listSources(skip = 0, limit = 100, tenantId?: string): Promise<SourceRecord[]> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.get<SourceSystemRead[]>(
      `/sources/?skip=${skip}&limit=${limit}`,
      headers
    );
    return (res.data ?? []).map(toSourceRecord);
  },

  /**
   * Fetch a single source system by its UUID.
   * GET /api/v1/sources/{source_id}
   */
  async getSource(sourceId: string): Promise<SourceRecord> {
    const res = await api.get<SourceSystemRead>(`/sources/${sourceId}`);
    if (!res.data) throw new Error('Source system not found in response.');
    return toSourceRecord(res.data);
  },

  /**
   * Register a new source system.
   * POST /api/v1/sources
   * 
   * @param tenantId Optional tenant UUID if calling as SuperAdmin
   */
  async registerSource(payload: SourceSystemCreatePayload, tenantId?: string): Promise<SourceRecord> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.post<SourceSystemRead>('/sources', payload, headers);
    if (!res.data) throw new Error('No data returned from server after registration.');
    return toSourceRecord(res.data);
  },

  /**
   * Soft-deactivate a source system (admin only).
   * DELETE /api/v1/sources/{source_id}
   */
  async deactivateSource(sourceId: string): Promise<SourceRecord> {
    const res = await api.delete<SourceSystemRead>(`/sources/${sourceId}`);
    if (!res.data) throw new Error('No data returned from server after deactivation.');
    return toSourceRecord(res.data);
  },

  /**
   * Update source status (Admin only).
   * PATCH /api/v1/sources/{source_id}/status?status={new_status}
   */
  async updateSourceStatus(sourceId: string, status: StatusType): Promise<SourceRecord> {
    const res = await api.patch<SourceSystemRead>(`/sources/${sourceId}/status?status=${status}`, {});
    if (!res.data) throw new Error('No data returned from server after status update.');
    return toSourceRecord(res.data);
  },
};

// Re-export for consumers
export { ApiError };
