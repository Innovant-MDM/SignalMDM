import React, { useEffect, useMemo, useState } from 'react';
import '../../styles/theme.css';
import '../../styles/mdm_phase2/StandardizationRulesPage.css';
import { useTenantConfig } from '../../context/TenantConfigContext';
import {
  ruleService,
  canManageRules,
  type RuleHistoryItem,
  type StandardizationRuleRead,
  type StandardizationRuleCreate,
  type StandardizationRuleUpdate,
} from '../../services/mdm_phase2/ruleService';

type RuleStatus = 'ACTIVE' | 'INACTIVE';
type EditorMode = 'create' | 'edit';
type KVPair = { id: string; key: string; value: string };
const STANDARDIZATION_TYPES = ['NAME', 'EMAIL', 'PHONE', 'ADDRESS', 'COUNTRY', 'STATE', 'CITY', 'DATE', 'CODE', 'TEXT', 'CUSTOM'];

const toJsonText = (obj: Record<string, unknown>) => JSON.stringify(obj ?? {}, null, 2);
const toKV = (obj: Record<string, unknown>): KVPair[] =>
  Object.entries(obj ?? {}).map(([key, value]) => ({ id: crypto.randomUUID(), key, value: String(value ?? '') }));
const kvToObj = (rows: KVPair[]): Record<string, string> =>
  rows.reduce<Record<string, string>>((acc, r) => {
    if (r.key.trim()) acc[r.key.trim()] = r.value;
    return acc;
  }, {});

const downloadCsv = (filename: string, rows: string[][]) => {
  const esc = (s: string) => `"${s.replace(/"/g, '""')}"`;
  const blob = new Blob([rows.map((r) => r.map(esc).join(',')).join('\n')], { type: 'text/csv;charset=utf-8;' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
};

const pretty = (v: unknown) => JSON.stringify(v ?? {}, null, 2);
type DiffRow = { path: string; type: 'ADDED' | 'REMOVED' | 'CHANGED'; oldValue: string; newValue: string };
const flattenObject = (obj: unknown, prefix = ''): Record<string, unknown> => {
  if (obj === null || typeof obj !== 'object' || Array.isArray(obj)) {
    return { [prefix || '$']: obj };
  }
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    const next = prefix ? `${prefix}.${k}` : k;
    if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
      Object.assign(out, flattenObject(v, next));
    } else {
      out[next] = v;
    }
  }
  return out;
};
const buildDiffRows = (oldVal: Record<string, unknown> | null, newVal: Record<string, unknown> | null): DiffRow[] => {
  const a = flattenObject(oldVal ?? {});
  const b = flattenObject(newVal ?? {});
  const paths = Array.from(new Set([...Object.keys(a), ...Object.keys(b)])).sort();
  const rows: DiffRow[] = [];
  for (const p of paths) {
    const hasA = Object.prototype.hasOwnProperty.call(a, p);
    const hasB = Object.prototype.hasOwnProperty.call(b, p);
    if (!hasA && hasB) {
      rows.push({ path: p, type: 'ADDED', oldValue: '—', newValue: pretty(b[p]) });
    } else if (hasA && !hasB) {
      rows.push({ path: p, type: 'REMOVED', oldValue: pretty(a[p]), newValue: '—' });
    } else if (JSON.stringify(a[p]) !== JSON.stringify(b[p])) {
      rows.push({ path: p, type: 'CHANGED', oldValue: pretty(a[p]), newValue: pretty(b[p]) });
    }
  }
  return rows;
};

export const StandardizationRulesPage: React.FC = () => {
  const { activeTenantId, activeTenantName } = useTenantConfig();
  const [rules, setRules] = useState<StandardizationRuleRead[]>([]);
  const [selected, setSelected] = useState<StandardizationRuleRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [mode, setMode] = useState<EditorMode>('create');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [jsonText, setJsonText] = useState('{}');
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [pairs, setPairs] = useState<KVPair[]>([]);
  const [history, setHistory] = useState<RuleHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyDetail, setHistoryDetail] = useState<RuleHistoryItem | null>(null);
  const [diffFilter, setDiffFilter] = useState<'ALL' | 'ADDED' | 'REMOVED' | 'CHANGED'>('ALL');
  const [expandedPaths, setExpandedPaths] = useState<Record<string, boolean>>({});
  const [diffPathSearch, setDiffPathSearch] = useState('');
  const canManage = canManageRules();
  const [form, setForm] = useState({
    rule_name: '',
    rule_code: '',
    standardization_type: 'COUNTRY',
    status: 'ACTIVE' as RuleStatus,
  });

  const loadRules = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await ruleService.listStandardizationRules(activeTenantId ?? undefined);
      setRules(data);
      if (data.length > 0 && !selected) setSelected(data[0]);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load standardization rules');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadRules();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTenantId]);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return rules.filter((r) => {
      const inSearch = q === '' || r.rule_name.toLowerCase().includes(q) || r.rule_code.toLowerCase().includes(q) || r.standardization_type.toLowerCase().includes(q);
      return inSearch && (statusFilter === 'ALL' || r.status === statusFilter) && (typeFilter === 'ALL' || r.standardization_type === typeFilter);
    });
  }, [rules, search, statusFilter, typeFilter]);

  const resetCreate = () => {
    setMode('create');
    setForm({ rule_name: '', rule_code: '', standardization_type: 'COUNTRY', status: 'ACTIVE' });
    setPairs([]);
    setJsonText('{}');
    setJsonError(null);
  };

  const beginEdit = (rule: StandardizationRuleRead) => {
    if (!canManage) return;
    setMode('edit');
    setSelected(rule);
    setForm({
      rule_name: rule.rule_name,
      rule_code: rule.rule_code,
      standardization_type: rule.standardization_type,
      status: (rule.status as RuleStatus) || 'ACTIVE',
    });
    setPairs(toKV(rule.mappings_json));
    setJsonText(toJsonText(rule.mappings_json));
    setJsonError(null);
  };

  const syncFromKV = (nextPairs: KVPair[]) => {
    setPairs(nextPairs);
    setJsonText(toJsonText(kvToObj(nextPairs)));
    setJsonError(null);
  };

  const syncFromJson = (text: string) => {
    setJsonText(text);
    try {
      const parsed = JSON.parse(text) as Record<string, unknown>;
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        setJsonError('Mappings must be a JSON object');
        return;
      }
      setPairs(toKV(parsed));
      setJsonError(null);
    } catch {
      setJsonError('Invalid JSON format');
    }
  };

  const validate = (): string | null => {
    if (!form.rule_name.trim()) return 'Rule name is required';
    if (!form.rule_code.trim()) return 'Rule code is required';
    if (!/^[A-Z0-9_]+$/.test(form.rule_code.trim().toUpperCase())) return 'Rule code must use only A-Z, 0-9, and underscore';
    if (!form.standardization_type.trim()) return 'Standardization type is required';
    if (jsonError) return jsonError;
    return null;
  };

  const onSubmit = async () => {
    if (!canManage) return;
    const v = validate();
    if (v) {
      setError(v);
      return;
    }
    const mappings_json = kvToObj(pairs);
    setSubmitting(true);
    setError(null);
    try {
      if (mode === 'create') {
        const payload: StandardizationRuleCreate = {
          rule_name: form.rule_name.trim(),
          rule_code: form.rule_code.trim().toUpperCase(),
          standardization_type: form.standardization_type.trim().toUpperCase(),
          mappings_json,
          status: form.status,
        };
        await ruleService.createStandardizationRule(payload, activeTenantId ?? undefined);
      } else if (selected) {
        const payload: StandardizationRuleUpdate = {
          rule_name: form.rule_name.trim(),
          standardization_type: form.standardization_type.trim().toUpperCase(),
          mappings_json,
          status: form.status,
        };
        await ruleService.updateStandardizationRule(selected.rule_id, payload, activeTenantId ?? undefined);
      }
      await loadRules();
      resetCreate();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save standardization rule');
    } finally {
      setSubmitting(false);
    }
  };

  const toggleArchive = async (rule: StandardizationRuleRead) => {
    if (!canManage) return;
    const next = rule.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    try {
      await ruleService.patchStandardizationRuleStatus(rule.rule_id, next, activeTenantId ?? undefined);
      await loadRules();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update rule status');
    }
  };

  useEffect(() => {
    const run = async () => {
      if (!selected) {
        setHistory([]);
        return;
      }
      setHistoryLoading(true);
      try {
        const rows = await ruleService.standardizationRuleHistory(selected.rule_id, activeTenantId ?? undefined);
        setHistory(rows);
      } catch {
        setHistory([]);
      } finally {
        setHistoryLoading(false);
      }
    };
    void run();
  }, [selected, activeTenantId]);

  useEffect(() => {
    if (!historyDetail) {
      setDiffFilter('ALL');
      setExpandedPaths({});
      setDiffPathSearch('');
    }
  }, [historyDetail]);

  return (
    <div className="mdm-rules-page">
      <div className="mdm-rules-header">
        <div>
          <h1>Standardization Rules</h1>
          <p>Configure value standardization mappings and view saved rule configurations.</p>
        </div>
        {activeTenantName && <span className="mdm-rules-tenant">Tenant: {activeTenantName}</span>}
      </div>

      <div className="mdm-rules-toolbar">
        <input className="mdm-rules-input" placeholder="Search by name, code, type..." value={search} onChange={(e) => setSearch(e.target.value)} />
        <select className="mdm-rules-select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="ALL">All Statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="INACTIVE">Inactive</option>
        </select>
        <select className="mdm-rules-select" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
          <option value="ALL">All Types</option>
          {STANDARDIZATION_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <button
          type="button"
          className="mdm-rules-btn"
          onClick={() => downloadCsv('standardization_rules.csv', [
            ['Rule Name', 'Rule Code', 'Type', 'Status', 'Mappings JSON', 'Updated At'],
            ...filtered.map((r) => [r.rule_name, r.rule_code, r.standardization_type, r.status, JSON.stringify(r.mappings_json), r.updated_at]),
          ])}
        >
          Export CSV
        </button>
        <button type="button" className="mdm-rules-btn mdm-rules-btn-secondary" onClick={resetCreate} disabled={!canManage}>+ Create New</button>
      </div>
      {!canManage && <div className="mdm-rules-error">Read-only mode: only admins can create/edit/archive rules.</div>}

      {error && <div className="mdm-rules-error">✕ {error}</div>}
      {loading ? (
        <div className="mdm-rules-card">Loading standardization rules...</div>
      ) : (
        <div className="mdm-rules-grid">
          <div className="mdm-rules-card">
            <h3>Saved Rules ({filtered.length})</h3>
            <div className="mdm-rules-table-wrap">
              <table className="mdm-rules-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Code</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((r) => (
                    <tr key={r.rule_id} className={selected?.rule_id === r.rule_id ? 'active' : ''}>
                      <td>{r.rule_name}</td>
                      <td><code>{r.rule_code}</code></td>
                      <td>{r.standardization_type}</td>
                      <td><span className={`mdm-badge ${r.status === 'ACTIVE' ? 'ok' : 'muted'}`}>{r.status}</span></td>
                      <td>
                        <button type="button" className="mdm-link-btn" onClick={() => beginEdit(r)} disabled={!canManage}>Edit</button>
                        <button type="button" className="mdm-link-btn" onClick={() => void toggleArchive(r)} disabled={!canManage}>
                          {r.status === 'ACTIVE' ? 'Archive' : 'Unarchive'}
                        </button>
                        <button type="button" className="mdm-link-btn" onClick={() => setSelected(r)}>View</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="mdm-rules-card">
            <h3>{mode === 'create' ? 'Create Rule' : 'Edit Rule'}</h3>
            <div className="mdm-rules-form">
              <input className="mdm-rules-input" placeholder="Rule name" value={form.rule_name} onChange={(e) => setForm((p) => ({ ...p, rule_name: e.target.value }))} />
              <input className="mdm-rules-input" placeholder="Rule code (e.g. COUNTRY_STD)" value={form.rule_code} disabled={mode === 'edit' || !canManage} onChange={(e) => setForm((p) => ({ ...p, rule_code: e.target.value.toUpperCase() }))} />
              <select className="mdm-rules-select" value={form.standardization_type} onChange={(e) => setForm((p) => ({ ...p, standardization_type: e.target.value }))} disabled={!canManage}>
                {STANDARDIZATION_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
              <select className="mdm-rules-select" value={form.status} onChange={(e) => setForm((p) => ({ ...p, status: e.target.value as RuleStatus }))} disabled={!canManage}>
                <option value="ACTIVE">ACTIVE</option>
                <option value="INACTIVE">INACTIVE</option>
              </select>
            </div>

            <h4>Mappings (Source Value → Standard Value)</h4>
            <div className="mdm-kv-list">
              {pairs.map((p) => (
                <div className="mdm-kv-row" key={p.id}>
                  <input className="mdm-rules-input" placeholder="source value" value={p.key} onChange={(e) => syncFromKV(pairs.map((x) => x.id === p.id ? { ...x, key: e.target.value } : x))} disabled={!canManage} />
                  <input className="mdm-rules-input" placeholder="standard value" value={p.value} onChange={(e) => syncFromKV(pairs.map((x) => x.id === p.id ? { ...x, value: e.target.value } : x))} disabled={!canManage} />
                  <button type="button" className="mdm-link-btn" onClick={() => syncFromKV(pairs.filter((x) => x.id !== p.id))} disabled={!canManage}>Remove</button>
                </div>
              ))}
              <button type="button" className="mdm-rules-btn mdm-rules-btn-secondary" onClick={() => syncFromKV([...pairs, { id: crypto.randomUUID(), key: '', value: '' }])} disabled={!canManage}>
                + Add Mapping
              </button>
            </div>

            <h4>JSON Editor</h4>
            <textarea className="mdm-rules-json" value={jsonText} onChange={(e) => syncFromJson(e.target.value)} rows={9} disabled={!canManage} />
            {jsonError && <div className="mdm-rules-error">✕ {jsonError}</div>}

            <div className="mdm-rules-actions">
              <button type="button" className="mdm-rules-btn" disabled={submitting || !canManage} onClick={onSubmit}>
                {submitting ? 'Saving...' : mode === 'create' ? 'Create Rule' : 'Update Rule'}
              </button>
            </div>
          </div>
        </div>
      )}

      {selected && (
        <div className="mdm-rules-card">
          <h3>Saved Configuration Preview: {selected.rule_name}</h3>
          <pre className="mdm-rules-pre">{JSON.stringify(selected.mappings_json, null, 2)}</pre>
          <h4 style={{ marginTop: 12 }}>Version History</h4>
          {historyLoading ? (
            <div className="mdm-rules-error">Loading history...</div>
          ) : history.length === 0 ? (
            <div className="mdm-rules-error">No history available.</div>
          ) : (
            <div className="mdm-rules-table-wrap">
              <table className="mdm-rules-table">
                <thead>
                  <tr><th>When</th><th>By</th><th>Operation</th></tr>
                </thead>
                <tbody>
                  {history.map((h) => (
                    <tr key={h.audit_id}>
                      <td>{new Date(h.performed_at).toLocaleString()}</td>
                      <td>{h.performed_by || 'system'}</td>
                      <td>{h.operation_type}</td>
                      <td>
                        <button type="button" className="mdm-link-btn" onClick={() => setHistoryDetail(h)}>
                          Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {historyDetail && (
        <div className="mdm-modal-overlay" onClick={() => setHistoryDetail(null)}>
          <div className="mdm-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="mdm-modal-header">
              <h3>History Detail</h3>
              <button type="button" className="mdm-link-btn" onClick={() => setHistoryDetail(null)}>Close</button>
            </div>
            <div className="mdm-modal-meta">
              <span>{new Date(historyDetail.performed_at).toLocaleString()}</span>
              <span>{historyDetail.performed_by || 'system'}</span>
              <span>{historyDetail.operation_type}</span>
            </div>
            <div className="mdm-modal-diff">
              <div>
                <h4>Old Value</h4>
                <pre className="mdm-rules-pre">{pretty(historyDetail.old_value)}</pre>
              </div>
              <div>
                <h4>New Value</h4>
                <pre className="mdm-rules-pre">{pretty(historyDetail.new_value)}</pre>
              </div>
            </div>
            <div>
              <h4>Line-by-line JSON Diff</h4>
              {buildDiffRows(historyDetail.old_value, historyDetail.new_value).length === 0 ? (
                <div className="mdm-rules-error">No field-level changes captured.</div>
              ) : (
                <div className="mdm-rules-table-wrap">
                  <div className="mdm-diff-filters">
                    {(['ALL', 'ADDED', 'REMOVED', 'CHANGED'] as const).map((f) => (
                      <button
                        key={f}
                        type="button"
                        className={`mdm-diff-filter-btn${diffFilter === f ? ' active' : ''}`}
                        onClick={() => setDiffFilter(f)}
                      >
                        {f}
                      </button>
                    ))}
                  </div>
                  <input
                    className="mdm-rules-input"
                    placeholder="Search diff path (e.g. mappings_json.us)"
                    value={diffPathSearch}
                    onChange={(e) => setDiffPathSearch(e.target.value)}
                    style={{ marginBottom: 8 }}
                  />
                  <table className="mdm-rules-table mdm-diff-table">
                    <thead>
                      <tr><th>Path</th><th>Type</th><th>Old</th><th>New</th></tr>
                    </thead>
                    <tbody>
                      {buildDiffRows(historyDetail.old_value, historyDetail.new_value)
                        .filter((r) => diffFilter === 'ALL' || r.type === diffFilter)
                        .filter((r) => {
                          const q = diffPathSearch.trim().toLowerCase();
                          return q === '' || r.path.toLowerCase().includes(q);
                        })
                        .map((r) => {
                          const key = `${r.path}-${r.type}`;
                          const expanded = !!expandedPaths[key];
                          return (
                        <tr key={key} className={`mdm-diff-row mdm-diff-row--${r.type.toLowerCase()}`}>
                          <td><code>{r.path}</code></td>
                          <td><span className={`mdm-badge ${r.type === 'ADDED' ? 'ok' : r.type === 'REMOVED' ? 'muted' : ''}`}>{r.type}</span></td>
                          <td>
                            <code className={`mdm-diff-val${expanded ? ' expanded' : ''}`}>{r.oldValue}</code>
                          </td>
                          <td>
                            <code className={`mdm-diff-val${expanded ? ' expanded' : ''}`}>{r.newValue}</code>
                            <button
                              type="button"
                              className="mdm-link-btn"
                              onClick={() => setExpandedPaths((p) => ({ ...p, [key]: !expanded }))}
                            >
                              {expanded ? 'Collapse' : 'Expand'}
                            </button>
                          </td>
                        </tr>
                      )})}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StandardizationRulesPage;
