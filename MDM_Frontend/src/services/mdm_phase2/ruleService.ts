/**
 * src/services/mdm_phase2/ruleService.ts
 * -------------------------------------
 * Frontend service wrapper for Transformation and Standardization Rules API endpoints.
 */

import { api } from '../api';

export interface TransformationRuleRead {
  rule_id: string;
  tenant_id: string;
  rule_name: string;
  transformation_type: string;
  config_json: Record<string, unknown>;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface TransformationRuleCreate {
  rule_name: string;
  transformation_type: string;
  config_json: Record<string, unknown>;
}

export interface StandardizationRuleRead {
  rule_id: string;
  tenant_id: string;
  rule_name: string;
  mappings_json: Record<string, string>;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface StandardizationRuleCreate {
  rule_name: string;
  mappings_json: Record<string, string>;
}

export const ruleService = {
  /**
   * List all transformation rules.
   */
  async listTransformationRules(tenantId?: string): Promise<TransformationRuleRead[]> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.get<TransformationRuleRead[]>('/mdm/transformation-rules/', headers);
    return res.data ?? [];
  },

  /**
   * Create a new transformation rule.
   */
  async createTransformationRule(payload: TransformationRuleCreate, tenantId?: string): Promise<TransformationRuleRead> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.post<TransformationRuleRead>('/mdm/transformation-rules/', payload, headers);
    if (!res.data) throw new Error('No data returned from server after transformation rule creation.');
    return res.data;
  },

  /**
   * List all standardization rules.
   */
  async listStandardizationRules(tenantId?: string): Promise<StandardizationRuleRead[]> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.get<StandardizationRuleRead[]>('/mdm/standardization-rules/', headers);
    return res.data ?? [];
  },

  /**
   * Create a new standardization rule.
   */
  async createStandardizationRule(payload: StandardizationRuleCreate, tenantId?: string): Promise<StandardizationRuleRead> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.post<StandardizationRuleRead>('/mdm/standardization-rules/', payload, headers);
    if (!res.data) throw new Error('No data returned from server after standardization rule creation.');
    return res.data;
  },
};
