/**
 * src/services/mdm_phase2/mappingService.ts
 * -----------------------------------------
 * Frontend service wrapper for Field Mappings API endpoints.
 */

import { api } from '../api';

export interface FieldMappingRead {
  mapping_id: string;
  tenant_id: string;
  source_system_id: string;
  entity_type: string;
  source_field_name: string;
  canonical_field_id: string;
  transformation_rule_ids: string[] | null;
  standardization_rule_id: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface FieldMappingCreate {
  source_system_id: string;
  entity_type: string;
  source_field_name: string;
  canonical_field_id: string;
  transformation_rule_ids?: string[] | null;
  standardization_rule_id?: string | null;
}

export const mappingService = {
  /**
   * List all field mappings.
   */
  async listMappings(tenantId?: string): Promise<FieldMappingRead[]> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.get<FieldMappingRead[]>('/mdm/field-mappings/', headers);
    return res.data ?? [];
  },

  /**
   * Create a new field mapping.
   */
  async createMapping(payload: FieldMappingCreate, tenantId?: string): Promise<FieldMappingRead> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.post<FieldMappingRead>('/mdm/field-mappings/', payload, headers);
    if (!res.data) throw new Error('No data returned from server after field mapping creation.');
    return res.data;
  },
};
