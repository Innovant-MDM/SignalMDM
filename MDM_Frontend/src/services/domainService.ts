/**
 * src/services/domainService.ts
 * ------------------------------
 * Service layer for Domain API endpoints.
 *
 * Integrated with the SignalMDM backend:
 *   - Handles AES-encrypted JWT via httpOnly cookies.
 *   - Sends X-Device-ID for fingerprint validation.
 *   - Maps backend models (DomainRead) to frontend display records.
 */

import { api, ApiError } from './api';

// ─── Backend response shape (DomainRead) ──────────────────────────────────

export interface DomainRead {
  id: string;
  tenant_id: string;
  domain_name: string;
  description: string | null;
  status: string;
  created_at: string;       // ISO datetime string
  updated_at: string;
}

// ─── Frontend display model ───────────────────────────────────────────────

export interface DomainRecord {
  id: string;
  tenantId: string;
  domainName: string;
  description: string;
  status: 'ACTIVE' | 'SUSPENDED' | 'ARCHIVED' | 'DEACTIVATED';
  createdDate: string;
  updatedDate: string;
}

// ─── Create/Update payloads ───────────────────────────────────────────────

export interface DomainCreatePayload {
  domain_name: string;
  description?: string | null;
  status?: string;
}

export interface DomainUpdatePayload {
  domain_name?: string;
  description?: string | null;
  status?: string;
}

// ─── Mapping helpers ──────────────────────────────────────────────────────

function mapStatus(status: string): DomainRecord['status'] {
  if (status === 'SUSPENDED') return 'SUSPENDED';
  if (status === 'ARCHIVED') return 'ARCHIVED';
  if (status === 'DEACTIVATED') return 'DEACTIVATED';
  return 'ACTIVE';
}

function toDomainRecord(raw: DomainRead): DomainRecord {
  return {
    id: raw.id,
    tenantId: raw.tenant_id,
    domainName: raw.domain_name,
    description: raw.description ?? '',
    status: mapStatus(raw.status),
    createdDate: raw.created_at.slice(0, 10),
    updatedDate: raw.updated_at.slice(0, 10),
  };
}

// ─── Service ──────────────────────────────────────────────────────────────

export const domainService = {
  /**
   * Fetch all domains for the authenticated tenant.
   * GET /api/v1/domains/?skip=<skip>&limit=<limit>
   */
  async listDomains(skip = 0, limit = 100, tenantId?: string): Promise<DomainRecord[]> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.get<DomainRead[]>(
      `/domains/?skip=${skip}&limit=${limit}`,
      headers
    );
    return (res.data ?? []).map(toDomainRecord);
  },

  /**
   * Fetch a single domain by its UUID.
   * GET /api/v1/domains/{domain_id}
   */
  async getDomain(domainId: string): Promise<DomainRecord> {
    const res = await api.get<DomainRead>(`/domains/${domainId}`);
    if (!res.data) throw new Error('Domain not found in response.');
    return toDomainRecord(res.data);
  },

  /**
   * Create a new domain.
   * POST /api/v1/domains
   */
  async createDomain(payload: DomainCreatePayload, tenantId?: string): Promise<DomainRecord> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.post<DomainRead>('/domains/', payload, headers);
    if (!res.data) throw new Error('No data returned from server after creation.');
    return toDomainRecord(res.data);
  },

  /**
   * Update an existing domain.
   * PATCH /api/v1/domains/{domain_id}
   */
  async updateDomain(domainId: string, payload: DomainUpdatePayload): Promise<DomainRecord> {
    const res = await api.patch<DomainRead>(`/domains/${domainId}`, payload);
    if (!res.data) throw new Error('No data returned from server after update.');
    return toDomainRecord(res.data);
  },

  /**
   * Deactivate (soft-delete) a domain. Admin only.
   * DELETE /api/v1/domains/{domain_id}
   */
  async deleteDomain(domainId: string): Promise<DomainRecord> {
    const res = await api.delete<DomainRead>(`/domains/${domainId}`);
    if (!res.data) throw new Error('No data returned from server after deactivation.');
    return toDomainRecord(res.data);
  },
};

// Re-export for consumers
export { ApiError };
