/**
 * src/services/mdm_phase2/ruleService.ts
 * -------------------------------------
 * Frontend service wrapper for Transformation and Standardization Rules API endpoints.
 */

import { api } from '../api';
import { authService } from '../authService';

export interface RuleHistoryItem {
  audit_id: string;
  operation_type: string;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  performed_by: string | null;
  performed_at: string;
}

export const canManageRules = (): boolean => {
  const info = authService.getAdminInfoFromCookie();
  const role = String(info?.role || '').toLowerCase();
  const tenant = String(info?.tenant_id || '').toLowerCase();
  return role === 'admin' || tenant === 'platform';
};

export interface TransformationRuleRead {
  rule_id: string;
  tenant_id: string;
  rule_name: string;
  rule_code: string;
  transformation_type: string;
  config_json: Record<string, unknown>;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface TransformationRuleCreate {
  rule_name: string;
  rule_code: string;
  transformation_type: string;
  config_json: Record<string, unknown>;
  status?: string;
}

export interface TransformationRuleUpdate {
  rule_name: string;
  transformation_type: string;
  config_json: Record<string, unknown>;
  status?: string;
}

export interface StandardizationRuleRead {
  rule_id: string;
  tenant_id: string;
  rule_name: string;
  rule_code: string;
  standardization_type: string;
  mappings_json: Record<string, string | number | boolean>;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface StandardizationRuleCreate {
  rule_name: string;
  rule_code: string;
  standardization_type: string;
  mappings_json: Record<string, string | number | boolean>;
  status?: string;
}

export interface StandardizationRuleUpdate {
  rule_name: string;
  standardization_type: string;
  mappings_json: Record<string, string | number | boolean>;
  status?: string;
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

  async updateTransformationRule(
    ruleId: string,
    payload: TransformationRuleUpdate,
    tenantId?: string,
  ): Promise<TransformationRuleRead> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.put<TransformationRuleRead>(`/mdm/transformation-rules/${ruleId}`, payload, headers);
    if (!res.data) throw new Error('No data returned from server after transformation rule update.');
    return res.data;
  },

  async patchTransformationRuleStatus(
    ruleId: string,
    statusVal: string,
    tenantId?: string,
  ): Promise<TransformationRuleRead> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.patch<TransformationRuleRead>(
      `/mdm/transformation-rules/${ruleId}/status?status_val=${encodeURIComponent(statusVal)}`,
      {},
      headers,
    );
    if (!res.data) throw new Error('No data returned from server after transformation status update.');
    return res.data;
  },

  async transformationRuleHistory(ruleId: string, tenantId?: string): Promise<RuleHistoryItem[]> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.get<RuleHistoryItem[]>(`/mdm/transformation-rules/${ruleId}/history`, headers);
    return res.data ?? [];
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

  async updateStandardizationRule(
    ruleId: string,
    payload: StandardizationRuleUpdate,
    tenantId?: string,
  ): Promise<StandardizationRuleRead> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.put<StandardizationRuleRead>(`/mdm/standardization-rules/${ruleId}`, payload, headers);
    if (!res.data) throw new Error('No data returned from server after standardization rule update.');
    return res.data;
  },

  async patchStandardizationRuleStatus(
    ruleId: string,
    statusVal: string,
    tenantId?: string,
  ): Promise<StandardizationRuleRead> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.patch<StandardizationRuleRead>(
      `/mdm/standardization-rules/${ruleId}/status?status_val=${encodeURIComponent(statusVal)}`,
      {},
      headers,
    );
    if (!res.data) throw new Error('No data returned from server after standardization status update.');
    return res.data;
  },

  async standardizationRuleHistory(ruleId: string, tenantId?: string): Promise<RuleHistoryItem[]> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.get<RuleHistoryItem[]>(`/mdm/standardization-rules/${ruleId}/history`, headers);
    return res.data ?? [];
  },
};
