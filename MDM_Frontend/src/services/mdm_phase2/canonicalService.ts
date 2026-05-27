/**
 * src/services/mdm_phase2/canonicalService.ts
 * -------------------------------------------
 * Frontend service wrapper for Canonical Models / Fields API endpoints.
 */

import { api } from '../api';

export interface CanonicalFieldRead {
  field_id: string;
  tenant_id: string;
  entity_type: string;
  canonical_field_name: string;
  data_type: string;
  is_required: boolean;
  validation_type: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface CanonicalFieldCreate {
  entity_type: string;
  canonical_field_name: string;
  data_type: string;
  is_required: boolean;
  validation_type?: string | null;
}

export const canonicalService = {
  /**
   * List all canonical fields.
   */
  async listFields(tenantId?: string): Promise<CanonicalFieldRead[]> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.get<CanonicalFieldRead[]>('/mdm/canonical-models/', headers);
    return res.data ?? [];
  },

  /**
   * Create a new canonical field.
   */
  async createField(payload: CanonicalFieldCreate, tenantId?: string): Promise<CanonicalFieldRead> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.post<CanonicalFieldRead>('/mdm/canonical-models/', payload, headers);
    if (!res.data) throw new Error('No data returned from server after field creation.');
    return res.data;
  },
};
