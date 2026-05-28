import React, { useEffect, useMemo, useState } from 'react';
import '../../styles/theme.css';
import '../../styles/mdm_phase2/CanonicalModelsPage.css';
import { useTenantConfig } from '../../context/TenantConfigContext';
import { canonicalService, type CanonicalFieldCreate, type CanonicalFieldRead } from '../../services/mdm_phase2/canonicalService';

type Mode = 'create' | 'edit';
type FieldStatus = 'ACTIVE' | 'INACTIVE' | 'ARCHIVED';
const DATA_TYPES = ['TEXT', 'EMAIL', 'PHONE', 'NUMBER', 'DATE', 'BOOLEAN', 'JSON'];
const VALIDATION_TYPES = ['TEXT', 'EMAIL', 'PHONE', 'REGEX', 'DATE', 'NONE'];
const STANDARDIZATION_TYPES = ['TEXT', 'COUNTRY', 'STATE', 'CITY', 'PHONE', 'EMAIL', 'NONE'];

const csvDownload = (name: string, rows: string[][]) => {
  const esc = (s: string) => `"${s.replace(/"/g, '""')}"`;
  const blob = new Blob([rows.map((r) => r.map(esc).join(',')).join('\n')], { type: 'text/csv;charset=utf-8;' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
};

export const CanonicalModelsPage: React.FC = () => {
  const { activeTenantId, activeTenantName } = useTenantConfig();
  const [fields, setFields] = useState<CanonicalFieldRead[]>([]);
  const [selected, setSelected] = useState<CanonicalFieldRead | null>(null);
  const [viewField, setViewField] = useState<CanonicalFieldRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>('create');
  const [showEditor, setShowEditor] = useState(false);
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [entityFilter, setEntityFilter] = useState('ALL');
  const [form, setForm] = useState({
    entity_type: 'CUSTOMER',
    canonical_field_name: '',
    data_type: 'TEXT',
    is_required: false,
    validation_type: 'TEXT',
    standardization_type: 'TEXT',
    status: 'ACTIVE' as FieldStatus,
  });

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await canonicalService.listFields(activeTenantId ?? undefined);
      setFields(data);
      if (data.length && !selected) setSelected(data[0]);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load canonical fields');
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTenantId]);

  const entities = useMemo(() => Array.from(new Set(fields.map((f) => f.entity_type))).sort(), [fields]);
  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim();
    return fields.filter((f) => {
      const matchQ = q === '' || f.canonical_field_name.toLowerCase().includes(q) || f.entity_type.toLowerCase().includes(q) || f.data_type.toLowerCase().includes(q);
      const matchS = statusFilter === 'ALL' || f.status === statusFilter;
      const matchE = entityFilter === 'ALL' || f.entity_type === entityFilter;
      return matchQ && matchS && matchE;
    });
  }, [fields, search, statusFilter, entityFilter]);
  const activeCount = fields.filter((f) => f.status === 'ACTIVE').length;
  const inactiveCount = fields.filter((f) => f.status === 'INACTIVE').length;
  const archivedCount = fields.filter((f) => f.status === 'ARCHIVED').length;

  const reset = () => {
    setMode('create');
    setForm({
      entity_type: 'CUSTOMER',
      canonical_field_name: '',
      data_type: 'TEXT',
      is_required: false,
      validation_type: 'TEXT',
      standardization_type: 'TEXT',
      status: 'ACTIVE',
    });
  };

  const openCreateModal = () => {
    reset();
    setShowEditor(true);
  };

  const edit = (f: CanonicalFieldRead) => {
    setMode('edit');
    setSelected(f);
    setForm({
      entity_type: f.entity_type,
      canonical_field_name: f.canonical_field_name,
      data_type: f.data_type,
      is_required: f.is_required,
      validation_type: f.validation_type || 'TEXT',
      standardization_type: f.standardization_type || 'TEXT',
        status: (f.status as FieldStatus) || 'ACTIVE',
    });
    setShowEditor(true);
  };

  const validate = (): string | null => {
    if (!form.entity_type.trim()) return 'Entity type is required';
    if (!/^[A-Z_]+$/.test(form.entity_type.trim().toUpperCase())) return 'Entity type must use uppercase letters and underscore';
    if (!form.canonical_field_name.trim()) return 'Canonical field name is required';
    if (!/^[a-z0-9_]+$/.test(form.canonical_field_name.trim())) return 'Canonical field name must be strict snake_case';
    return null;
  };

  const save = async () => {
    const v = validate();
    if (v) {
      setError(v);
      return;
    }
    setSaving(true);
    setError(null);
    const payload: CanonicalFieldCreate = {
      entity_type: form.entity_type.trim().toUpperCase(),
      canonical_field_name: form.canonical_field_name.trim(),
      data_type: form.data_type.trim().toUpperCase(),
      is_required: form.is_required,
      validation_type: form.validation_type.trim().toUpperCase(),
      standardization_type: form.standardization_type.trim().toUpperCase(),
      status: form.status,
    };
    try {
      if (mode === 'create') {
        await canonicalService.createField(payload, activeTenantId ?? undefined);
      } else if (selected) {
        await canonicalService.updateField(selected.field_id, payload, activeTenantId ?? undefined);
      }
      await load();
      reset();
      setShowEditor(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save canonical field');
    } finally {
      setSaving(false);
    }
  };

  const archiveField = async (f: CanonicalFieldRead) => {
    const next = f.status === 'ARCHIVED' ? 'ACTIVE' : 'ARCHIVED';
    const ok = window.confirm(`${next === 'ARCHIVED' ? 'Archive' : 'Unarchive'} canonical field "${f.canonical_field_name}"?`);
    if (!ok) return;
    try {
      await canonicalService.patchStatus(f.field_id, next, activeTenantId ?? undefined);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update canonical field status');
    }
  };

  const deleteField = async (f: CanonicalFieldRead) => {
    if (f.status === 'INACTIVE') {
      setError('Field is already deleted (inactive).');
      return;
    }
    const ok = window.confirm(`Delete canonical field "${f.canonical_field_name}"? This will mark it as inactive.`);
    if (!ok) return;
    try {
      await canonicalService.patchStatus(f.field_id, 'INACTIVE', activeTenantId ?? undefined);
      if (selected?.field_id === f.field_id) {
        setSelected(null);
      }
      await load();
      setMode('create');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete canonical field');
    }
  };

  return (
    <div className="mdm-canon-page">
      <div className="mdm-canon-header">
        <div>
          <h1 className="mdm-canon-title">◫ Canonical Models & Fields</h1>
          <p>Define and manage canonical fields with validation and standardization settings.</p>
        </div>
        <div className="mdm-canon-header-actions">
          <button type="button" className="mdm-canon-btn mdm-canon-btn-secondary" onClick={() => void load()} disabled={loading}>
            {loading ? '…' : '↻'} Refresh
          </button>
          <button type="button" className="mdm-canon-btn" onClick={openCreateModal}>+ New Canonical Field</button>
          {activeTenantName && <span className="mdm-canon-tenant">Tenant: {activeTenantName}</span>}
        </div>
      </div>

      <div className="mdm-canon-stats-row">
        <div className="mdm-canon-stat-card">
          <span className="mdm-canon-stat-value">{fields.length}</span>
          <span className="mdm-canon-stat-label">Total Fields</span>
        </div>
        <div className="mdm-canon-stat-card mdm-canon-stat-card--green">
          <span className="mdm-canon-stat-value">{activeCount}</span>
          <span className="mdm-canon-stat-label">Active</span>
        </div>
        <div className="mdm-canon-stat-card mdm-canon-stat-card--red">
          <span className="mdm-canon-stat-value">{inactiveCount}</span>
          <span className="mdm-canon-stat-label">Inactive</span>
        </div>
        <div className="mdm-canon-stat-card mdm-canon-stat-card--purple">
          <span className="mdm-canon-stat-value">{archivedCount}</span>
          <span className="mdm-canon-stat-label">Archived</span>
        </div>
        <div className="mdm-canon-stat-card mdm-canon-stat-card--cyan">
          <span className="mdm-canon-stat-value">{entities.length}</span>
          <span className="mdm-canon-stat-label">Entity Types</span>
        </div>
      </div>

      <div className="mdm-canon-toolbar">
        <div className="mdm-canon-search-wrap">
          <span className="mdm-canon-search-icon">🔍</span>
          <input className="mdm-canon-search-input" placeholder="Search by field, entity, data type..." value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <select className="mdm-canon-select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="ALL">All Statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="INACTIVE">Inactive</option>
          <option value="ARCHIVED">Archived</option>
        </select>
        <select className="mdm-canon-select" value={entityFilter} onChange={(e) => setEntityFilter(e.target.value)}>
          <option value="ALL">All Entities</option>
          {entities.map((e) => <option key={e} value={e}>{e}</option>)}
        </select>
        <button
          type="button"
          className="mdm-canon-btn"
          onClick={() => csvDownload('canonical_fields.csv', [
            ['Entity', 'Field Name', 'Data Type', 'Required', 'Validation', 'Standardization', 'Status', 'Updated At'],
            ...filtered.map((f) => [f.entity_type, f.canonical_field_name, f.data_type, String(f.is_required), f.validation_type, f.standardization_type, f.status, f.updated_at]),
          ])}
        >
          Export CSV
        </button>
      </div>

      {error && <div className="mdm-canon-error">✕ {error}</div>}
      {loading ? (
        <div className="mdm-canon-card">Loading canonical fields...</div>
      ) : (
        <div className="mdm-canon-card mdm-canon-table-card">
          <h3>Canonical Fields ({filtered.length})</h3>
          <div className="mdm-canon-table-wrap">
            <table className="mdm-canon-table">
              <thead>
                <tr>
                  <th>Entity</th>
                  <th>Field</th>
                  <th>Type</th>
                  <th>Required</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {filtered.map((f) => (
                  <tr key={f.field_id} className={selected?.field_id === f.field_id ? 'active' : ''} onClick={() => setSelected(f)}>
                    <td><span className="mdm-canon-entity-chip">{f.entity_type}</span></td>
                    <td><span className="mdm-canon-source-field">{f.canonical_field_name}</span></td>
                    <td><span className="mdm-canon-type-chip">{f.data_type}</span></td>
                    <td>{f.is_required ? 'YES' : 'NO'}</td>
                    <td><span className={`mdm-canon-badge mdm-canon-badge--${f.status}`}>{f.status}</span></td>
                    <td>
                      <div className="mdm-canon-action-row" onClick={(e) => e.stopPropagation()}>
                        <button type="button" className="mdm-link-btn mdm-link-btn--edit" onClick={() => edit(f)}>Edit</button>
                        <button type="button" className="mdm-link-btn mdm-link-btn--archive" onClick={() => void archiveField(f)}>
                          {f.status === 'ARCHIVED' ? 'Unarchive' : 'Archive'}
                        </button>
                        <button type="button" className="mdm-link-btn mdm-link-btn--danger" onClick={() => void deleteField(f)}>Delete</button>
                        <button type="button" className="mdm-link-btn mdm-link-btn--view" onClick={() => { setSelected(f); setViewField(f); }}>View</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={6} className="mdm-canon-table-empty">
                      <span className="mdm-canon-empty-icon">◫</span>
                      <p>
                        {fields.length === 0
                          ? 'No canonical fields yet. Create your first canonical field to get started.'
                          : 'No canonical fields match the current filters.'}
                      </p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {viewField && (
        <div className="mdm-canon-drawer-overlay" onClick={() => setViewField(null)}>
          <aside className="mdm-canon-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="mdm-canon-drawer-header">
              <div>
                <h3 className="mdm-canon-drawer-title">Saved Configuration: {viewField.canonical_field_name}</h3>
                <p className="mdm-canon-drawer-sub">{viewField.entity_type} · {viewField.data_type}</p>
              </div>
              <button type="button" className="mdm-canon-drawer-close" onClick={() => setViewField(null)}>✕</button>
            </div>
            <div className="mdm-canon-drawer-body">
              <pre className="mdm-canon-pre">
{JSON.stringify({
  entity_type: viewField.entity_type,
  canonical_field_name: viewField.canonical_field_name,
  data_type: viewField.data_type,
  is_required: viewField.is_required,
  validation_type: viewField.validation_type,
  standardization_type: viewField.standardization_type,
  status: viewField.status,
  updated_at: viewField.updated_at,
}, null, 2)}
              </pre>
            </div>
          </aside>
        </div>
      )}

      {showEditor && (
        <div className="mdm-canon-overlay" onClick={() => setShowEditor(false)} role="presentation">
          <div className="mdm-canon-modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
            <div className="mdm-canon-modal-header">
              <div>
                <h3 className="mdm-canon-modal-title">{mode === 'create' ? 'Create Canonical Field' : 'Edit Canonical Field'}</h3>
                <p className="mdm-canon-modal-sub">Configure canonical field definition and validation rules.</p>
              </div>
              <button type="button" className="mdm-canon-modal-close" onClick={() => setShowEditor(false)}>✕</button>
            </div>
            <div className="mdm-canon-modal-body">
              <div className="mdm-canon-form">
                <input className="mdm-canon-input" placeholder="Entity type (e.g. CUSTOMER)" value={form.entity_type} onChange={(e) => setForm((p) => ({ ...p, entity_type: e.target.value.toUpperCase() }))} />
                <input className="mdm-canon-input" placeholder="Canonical field name (snake_case)" value={form.canonical_field_name} onChange={(e) => setForm((p) => ({ ...p, canonical_field_name: e.target.value }))} />
                <select className="mdm-canon-select" value={form.data_type} onChange={(e) => setForm((p) => ({ ...p, data_type: e.target.value }))}>
                  {DATA_TYPES.map((d) => <option key={d} value={d}>{d}</option>)}
                </select>
                <select className="mdm-canon-select" value={form.validation_type} onChange={(e) => setForm((p) => ({ ...p, validation_type: e.target.value }))}>
                  {VALIDATION_TYPES.map((d) => <option key={d} value={d}>{d}</option>)}
                </select>
                <select className="mdm-canon-select" value={form.standardization_type} onChange={(e) => setForm((p) => ({ ...p, standardization_type: e.target.value }))}>
                  {STANDARDIZATION_TYPES.map((d) => <option key={d} value={d}>{d}</option>)}
                </select>
                <select className="mdm-canon-select" value={form.status} onChange={(e) => setForm((p) => ({ ...p, status: e.target.value as FieldStatus }))}>
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="INACTIVE">INACTIVE</option>
                  <option value="ARCHIVED">ARCHIVED</option>
                </select>
                <label className="mdm-canon-checkbox">
                  <input type="checkbox" checked={form.is_required} onChange={(e) => setForm((p) => ({ ...p, is_required: e.target.checked }))} />
                  Required field
                </label>
              </div>
            </div>
            <div className="mdm-canon-modal-footer">
              <button type="button" className="mdm-canon-btn mdm-canon-btn-secondary" onClick={() => setShowEditor(false)}>Cancel</button>
              <button type="button" className="mdm-canon-btn" onClick={save} disabled={saving}>
                {saving ? 'Saving...' : mode === 'create' ? 'Create Field' : 'Update Field'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CanonicalModelsPage;
