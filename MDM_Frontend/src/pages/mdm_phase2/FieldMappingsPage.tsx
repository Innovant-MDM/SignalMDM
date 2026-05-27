/**
 * FieldMappingsPage.tsx
 * ─────────────────────
 * Phase 2 — Field Mappings screen.
 *
 * Connects to:
 *   src/services/mdm_phase2/mappingService.ts   (list + create mappings)
 *   src/services/mdm_phase2/canonicalService.ts  (load canonical fields for selector)
 *   src/services/mdm_phase2/ruleService.ts       (load transformation rules for selector)
 */

import { useState, useEffect, useCallback, useMemo, type ChangeEvent } from 'react';
import '../../styles/theme.css';
import '../../styles/mdm_phase2/FieldMappingsPage.css';

import {
  mappingService,
  type FieldMappingRead,
  type FieldMappingCreate,
} from '../../services/mdm_phase2/mappingService';
import {
  canonicalService,
  type CanonicalFieldRead,
} from '../../services/mdm_phase2/canonicalService';
import {
  ruleService,
  type TransformationRuleRead,
} from '../../services/mdm_phase2/ruleService';
import { sourceService, type SourceRecord } from '../../services/sourceService';
import { useTenantConfig } from '../../context/TenantConfigContext';
import { useSnackbar } from '../../context/SnackbarContext';

/* ─────────────────────────────────────────────────
   Constants / helpers
───────────────────────────────────────────────── */
const ENTITY_TYPES = ['CUSTOMER', 'SUPPLIER', 'PRODUCT', 'ACCOUNT', 'ASSET', 'LOCATION', 'CONTACT'];
const MAPPING_STATUSES = ['ACTIVE', 'DRAFT', 'INACTIVE'];
const PAGE_SIZE = 20;

function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  });
}

function coloriseJSON(obj: unknown): string {
  if (!obj) return '<span style="color:#8b949e">// No data</span>';
  const str = JSON.stringify(obj, null, 2);
  return str.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
    (match) => {
      let cls = 'nr-json-num';
      if (/^"/.test(match)) {
        if (/:$/.test(match)) cls = 'nr-json-key';
        else cls = 'nr-json-str';
      } else if (/true|false/.test(match)) cls = 'nr-json-bool';
      else if (/null/.test(match)) cls = 'nr-json-null';
      return `<span class="${cls}">${match}</span>`;
    },
  );
}

/* ─────────────────────────────────────────────────
   Mapping Detail Drawer
───────────────────────────────────────────────── */
interface DrawerProps {
  mapping: FieldMappingRead;
  canonicals: CanonicalFieldRead[];
  rules: TransformationRuleRead[];
  sources: SourceRecord[];
  onClose: () => void;
}

function MappingDrawer({ mapping, canonicals, rules, sources, onClose }: DrawerProps) {
  const canonicalField = canonicals.find(c => c.field_id === mapping.canonical_field_id);
  const appliedRules = (mapping.transformation_rule_ids ?? [])
    .map(id => rules.find(r => r.rule_id === id))
    .filter(Boolean) as TransformationRuleRead[];

  const previewConfig = appliedRules[0]?.config_json ?? null;

  return (
    <div className="fm-drawer-overlay" onClick={onClose} role="presentation">
      <div
        className="fm-drawer"
        onClick={e => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="fm-drawer-header">
          <div>
            <h2 className="fm-drawer-title">
              {mapping.source_field_name} → {mapping.canonical_field_id}
            </h2>
            <div className="fm-drawer-sub">{mapping.mapping_id}</div>
          </div>
          <button type="button" className="fm-drawer-close" onClick={onClose}>✕</button>
        </div>

        <div className="fm-drawer-body">

          {/* Mapping detail */}
          <div>
            <p className="fm-drawer-section-title">Mapping Details</p>
            <div className="fm-drawer-grid">
              <div className="fm-drawer-field">
                <span className="fm-drawer-field-label">Entity Type</span>
                <span className="fm-drawer-field-value">
                  <span className="fm-entity-chip">{mapping.entity_type}</span>
                </span>
              </div>
              <div className="fm-drawer-field">
                <span className="fm-drawer-field-label">Status</span>
                <span className="fm-drawer-field-value">
                  <span className={`fm-badge fm-badge--${mapping.status}`}>{mapping.status}</span>
                </span>
              </div>
              <div className="fm-drawer-field">
                <span className="fm-drawer-field-label">Source System</span>
                <span className="fm-drawer-field-value">{sources.find(s => s.id === mapping.source_system_id)?.sourceName ?? mapping.source_system_id.slice(0, 8) + '…'}</span>
              </div>
              <div className="fm-drawer-field">
                <span className="fm-drawer-field-label">Source Field</span>
                <span className="fm-source-field">{mapping.source_field_name}</span>
              </div>
              <div className="fm-drawer-field">
                <span className="fm-drawer-field-label">Canonical Field</span>
                <span className="fm-canonical-field">
                  {canonicalField?.canonical_field_name ?? mapping.canonical_field_id.slice(0, 8) + '…'}
                </span>
              </div>
              {canonicalField && (
                <>
                  <div className="fm-drawer-field">
                    <span className="fm-drawer-field-label">Data Type</span>
                    <span className="fm-drawer-field-value">{canonicalField.data_type}</span>
                  </div>
                  <div className="fm-drawer-field">
                    <span className="fm-drawer-field-label">Required</span>
                    <span className="fm-drawer-field-value">{canonicalField.is_required ? 'Yes' : 'No'}</span>
                  </div>
                  {canonicalField.validation_type && (
                    <div className="fm-drawer-field">
                      <span className="fm-drawer-field-label">Validation</span>
                      <span className="fm-drawer-field-value">{canonicalField.validation_type}</span>
                    </div>
                  )}
                </>
              )}
              <div className="fm-drawer-field">
                <span className="fm-drawer-field-label">Created At</span>
                <span className="fm-drawer-field-value">{fmtDate(mapping.created_at)}</span>
              </div>
              <div className="fm-drawer-field">
                <span className="fm-drawer-field-label">Updated At</span>
                <span className="fm-drawer-field-value">{fmtDate(mapping.updated_at)}</span>
              </div>
            </div>
          </div>

          {/* Transformation Rules */}
          <div>
            <p className="fm-drawer-section-title">Transformation Rules ({appliedRules.length})</p>
            {appliedRules.length === 0 ? (
              <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No transformation rules applied.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {appliedRules.map((r, i) => (
                  <div
                    key={r.rule_id}
                    style={{
                      background: 'var(--bg-elevated)',
                      border: '1px solid var(--border-light)',
                      borderRadius: 'var(--r-sm)',
                      padding: '10px 14px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 4,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{
                        fontSize: 10, fontWeight: 700, background: 'var(--amber-100)',
                        color: '#b45309', padding: '1px 6px', borderRadius: 99,
                      }}>Step {i + 1}</span>
                      <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                        {r.rule_name}
                      </span>
                      <span className="fm-rule-chip">{r.transformation_type}</span>
                    </div>
                    <span style={{ fontSize: 11.5, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      {JSON.stringify(r.config_json)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Preview */}
          <div>
            <p className="fm-drawer-section-title">Mapping Preview</p>
            <div className="fm-preview-panel">
              <p className="fm-preview-title">Source → Transformation → Canonical</p>
              <div className="fm-preview-flow">
                <div className="fm-preview-box">
                  <div className="fm-preview-box-label">Source Field</div>
                  <div className="fm-preview-box-value">{mapping.source_field_name}</div>
                </div>
                <span className="fm-preview-arrow">→</span>
                <div className="fm-preview-box">
                  <div className="fm-preview-box-label">Rules Applied</div>
                  <div className="fm-preview-box-value" style={{ color: appliedRules.length ? '#b45309' : 'var(--text-muted)' }}>
                    {appliedRules.length ? appliedRules.map(r => r.transformation_type).join(' → ') : 'None'}
                  </div>
                </div>
                <span className="fm-preview-arrow">→</span>
                <div className="fm-preview-box">
                  <div className="fm-preview-box-label">Canonical Field</div>
                  <div className="fm-preview-box-value" style={{ color: 'var(--purple-500)' }}>
                    {canonicalField?.canonical_field_name ?? '—'}
                  </div>
                </div>
              </div>
              {previewConfig && (
                <div>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, fontWeight: 600 }}>RULE CONFIG</p>
                  <div
                    className="nr-json-viewer"
                    style={{ fontSize: 11.5, maxHeight: 120 }}
                    dangerouslySetInnerHTML={{ __html: coloriseJSON(previewConfig) }}
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────
   Create Mapping Modal
───────────────────────────────────────────────── */
interface CreateModalProps {
  canonicals: CanonicalFieldRead[];
  rules: TransformationRuleRead[];
  sources: SourceRecord[];
  onSave: (payload: FieldMappingCreate) => Promise<void>;
  onClose: () => void;
}

function CreateMappingModal({ canonicals, rules, sources, onSave, onClose }: CreateModalProps) {
  const [form, setForm] = useState<FieldMappingCreate>({
    source_system_id: '',
    entity_type: 'CUSTOMER',
    source_field_name: '',
    canonical_field_id: '',
    transformation_rule_ids: [],
    standardization_rule_id: null,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filteredCanonicals = canonicals.filter(
    c => c.entity_type === form.entity_type && c.status === 'ACTIVE',
  );

  const handleChange = (field: keyof FieldMappingCreate, value: unknown) => {
    setForm(prev => ({ ...prev, [field]: value }));
    setError(null);
  };

  const toggleRule = (ruleId: string) => {
    const current = form.transformation_rule_ids ?? [];
    const next = current.includes(ruleId)
      ? current.filter(id => id !== ruleId)
      : [...current, ruleId];
    handleChange('transformation_rule_ids', next);
  };

  const handleSubmit = async () => {
    if (!form.source_system_id.trim()) { setError('Source system ID is required.'); return; }
    if (!form.source_field_name.trim()) { setError('Source field name is required.'); return; }
    if (!form.canonical_field_id) { setError('Please select a canonical field.'); return; }
    setSaving(true);
    try {
      await onSave(form);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fm-overlay" onClick={onClose} role="presentation">
      <div
        className="fm-modal"
        onClick={e => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="fm-modal-header">
          <div>
            <h2 className="fm-modal-title">Create Field Mapping</h2>
            <p className="fm-modal-sub">Map a source field to a canonical field with optional transformations</p>
          </div>
          <button type="button" className="fm-modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="fm-modal-body">
          {error && <div className="fm-form-error">⚠ {error}</div>}

          <div className="fm-form-grid">

            <div className="fm-form-field">
              <label className="fm-form-label">
                Source System <span className="req">*</span>
              </label>
              <select
                className="form-select"
                value={form.source_system_id}
                onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                  handleChange('source_system_id', e.target.value)
                }
              >
                <option value="">— Select source system —</option>
                {sources.map(src => (
                  <option key={src.id} value={src.id}>
                    {src.sourceName} ({src.id.slice(0, 8)}…)
                  </option>
                ))}
              </select>
            </div>

            <div className="fm-form-field">
              <label className="fm-form-label">
                Entity Type <span className="req">*</span>
              </label>
              <select
                className="form-select"
                value={form.entity_type}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                  handleChange('entity_type', e.target.value);
                  handleChange('canonical_field_id', '');
                }}
              >
                {ENTITY_TYPES.map(et => (
                  <option key={et} value={et}>{et}</option>
                ))}
              </select>
            </div>

            <div className="fm-form-field">
              <label className="fm-form-label">
                Source Field Name <span className="req">*</span>
              </label>
              <input
                className="form-input"
                placeholder="e.g. customerName, emailId"
                value={form.source_field_name}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  handleChange('source_field_name', e.target.value)
                }
              />
            </div>

            <div className="fm-form-field">
              <label className="fm-form-label">
                Canonical Field <span className="req">*</span>
              </label>
              <select
                className="form-select"
                value={form.canonical_field_id}
                onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                  handleChange('canonical_field_id', e.target.value)
                }
              >
                <option value="">— Select canonical field —</option>
                {filteredCanonicals.map(cf => (
                  <option key={cf.field_id} value={cf.field_id}>
                    {cf.canonical_field_name} ({cf.data_type})
                  </option>
                ))}
              </select>
            </div>

            <div className="fm-form-field fm-form-field--full">
              <label className="fm-form-label">Transformation Rules (ordered)</label>
              {rules.length === 0 ? (
                <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No transformation rules available.</p>
              ) : (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {rules.filter(r => r.status === 'ACTIVE').map(r => {
                    const selected = (form.transformation_rule_ids ?? []).includes(r.rule_id);
                    return (
                      <button
                        key={r.rule_id}
                        type="button"
                        onClick={() => toggleRule(r.rule_id)}
                        style={{
                          padding: '5px 12px',
                          borderRadius: 99,
                          fontSize: 12,
                          fontWeight: 600,
                          fontFamily: 'inherit',
                          cursor: 'pointer',
                          border: '1px solid',
                          transition: 'all .13s',
                          background: selected ? 'var(--amber-100)' : 'var(--bg-elevated)',
                          color: selected ? '#b45309' : 'var(--text-secondary)',
                          borderColor: selected ? 'rgba(245,158,11,.35)' : 'var(--border-light)',
                        }}
                      >
                        {selected ? '✓ ' : ''}{r.rule_name}
                        <span style={{ opacity: .6, marginLeft: 5, fontSize: 10.5 }}>
                          {r.transformation_type}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
              {(form.transformation_rule_ids?.length ?? 0) > 0 && (
                <p style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 4 }}>
                  Order: {(form.transformation_rule_ids ?? [])
                    .map(id => rules.find(r => r.rule_id === id)?.rule_name ?? id)
                    .join(' → ')}
                </p>
              )}
            </div>

          </div>
        </div>

        <div className="fm-modal-footer">
          <button type="button" className="btn btn--ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => void handleSubmit()}
            disabled={saving}
          >
            {saving ? <><span className="spinner" /> Saving…</> : '+ Create Mapping'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────
   Main Page
───────────────────────────────────────────────── */
export const FieldMappingsPage: React.FC = () => {
  const { activeTenantId } = useTenantConfig();
  const snackbar = useSnackbar();

  const [mappings, setMappings]     = useState<FieldMappingRead[]>([]);
  const [canonicals, setCanonicals] = useState<CanonicalFieldRead[]>([]);
  const [rules, setRules]           = useState<TransformationRuleRead[]>([]);
  const [sources, setSources]       = useState<SourceRecord[]>([]);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState<string | null>(null);

  const [search, setSearch]               = useState('');
  const [filterSource, setFilterSource]   = useState('ALL');
  const [filterEntity, setFilterEntity]   = useState('ALL');
  const [filterStatus, setFilterStatus]   = useState('ALL');
  const [page, setPage]                   = useState(1);

  const [viewMapping, setViewMapping]     = useState<FieldMappingRead | null>(null);
  const [showCreate, setShowCreate]       = useState(false);

  /* ── Load data ─────────────────────────────── */
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const tId = activeTenantId ?? undefined;
      const [mapsData, canoData, rulesData, sourcesData] = await Promise.all([
        mappingService.listMappings(tId),
        canonicalService.listFields(tId),
        ruleService.listTransformationRules(tId),
        sourceService.listSources(0, 1000, tId),
      ]);
      setMappings(mapsData);
      setCanonicals(canoData);
      setRules(rulesData);
      setSources(sourcesData);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load field mappings.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [activeTenantId]);

  useEffect(() => { void loadData(); }, [loadData]);

  /* ── Filtering / pagination ────────────────── */
  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return mappings.filter(m => {
      const matchText = !q ||
        m.source_field_name.toLowerCase().includes(q) ||
        m.canonical_field_id.toLowerCase().includes(q) ||
        m.entity_type.toLowerCase().includes(q);
      const matchEntity = filterEntity === 'ALL' || m.entity_type === filterEntity;
      const matchStatus = filterStatus === 'ALL' || m.status === filterStatus;
      const matchSource = filterSource === 'ALL' || m.source_system_id === filterSource;
      return matchText && matchEntity && matchStatus && matchSource;
    });
  }, [mappings, search, filterEntity, filterStatus, filterSource]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated  = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  useEffect(() => { setPage(p => Math.min(p, totalPages)); }, [totalPages]);

  /* ── Stats ─────────────────────────────────── */
  const activeCount   = mappings.filter(m => m.status === 'ACTIVE').length;
  const draftCount    = mappings.filter(m => m.status === 'DRAFT').length;
  const inactiveCount = mappings.filter(m => m.status === 'INACTIVE').length;
  const entitySet     = new Set(mappings.map(m => m.entity_type));

  /* ── Create handler ─────────────────────────── */
  const handleCreate = async (payload: FieldMappingCreate) => {
    await mappingService.createMapping(payload, activeTenantId ?? undefined);
    snackbar.showSuccess('Field mapping created successfully.');
    setShowCreate(false);
    await loadData();
  };

  /* ── Canonical name resolver ─────────────────── */
  const resolveCanonicalName = (fieldId: string) => {
    const cf = canonicals.find(c => c.field_id === fieldId);
    return cf ? cf.canonical_field_name : fieldId.slice(0, 12) + '…';
  };

  /* ── Source system name resolver ──────────────── */
  const resolveSourceName = (sourceId: string) => {
    const src = sources.find(s => s.id === sourceId);
    return src ? src.sourceName : sourceId.slice(0, 8) + '…';
  };

  /* ── Render ─────────────────────────────────── */
  return (
    <div className="fm-page">

      {/* Header */}
      <div className="fm-header">
        <div>
          <h1 className="fm-title">⇌ Field Mappings</h1>
          <p className="fm-subtitle">
            Map source system fields to canonical model fields with optional transformation rules.
          </p>
        </div>
        <div className="fm-header-actions">
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => void loadData()}
            disabled={loading}
          >
            {loading ? '…' : '↻'} Refresh
          </button>
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => setShowCreate(true)}
          >
            + New Mapping
          </button>
        </div>
      </div>

      {/* Error */}
      {error && <div className="fm-alert fm-alert--error">⚠ {error}</div>}

      {/* Stats */}
      <div className="fm-stats-row">
        <div className="fm-stat-card">
          <span className="fm-stat-value">{mappings.length}</span>
          <span className="fm-stat-label">Total Mappings</span>
        </div>
        <div className="fm-stat-card fm-stat-card--green">
          <span className="fm-stat-value">{activeCount}</span>
          <span className="fm-stat-label">Active</span>
        </div>
        <div className="fm-stat-card fm-stat-card--amber">
          <span className="fm-stat-value">{draftCount}</span>
          <span className="fm-stat-label">Draft</span>
        </div>
        <div className="fm-stat-card fm-stat-card--red">
          <span className="fm-stat-value">{inactiveCount}</span>
          <span className="fm-stat-label">Inactive</span>
        </div>
        <div className="fm-stat-card fm-stat-card--purple">
          <span className="fm-stat-value">{entitySet.size}</span>
          <span className="fm-stat-label">Entity Types</span>
        </div>
      </div>

      {/* Filter bar */}
      <div className="fm-filter-bar">
        <div className="fm-search-wrap">
          <span className="fm-search-icon">🔍</span>
          <input
            className="fm-search-input"
            placeholder="Search source or canonical field…"
            value={search}
            onChange={(e: ChangeEvent<HTMLInputElement>) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>

        <select
          className="fm-select"
          value={filterSource}
          onChange={(e: ChangeEvent<HTMLSelectElement>) => { setFilterSource(e.target.value); setPage(1); }}
        >
          <option value="ALL">All source systems</option>
          {sources.map(src => <option key={src.id} value={src.id}>{src.sourceName}</option>)}
        </select>

        <select
          className="fm-select"
          value={filterEntity}
          onChange={(e: ChangeEvent<HTMLSelectElement>) => { setFilterEntity(e.target.value); setPage(1); }}
        >
          <option value="ALL">All entities</option>
          {ENTITY_TYPES.map(et => <option key={et} value={et}>{et}</option>)}
        </select>

        <select
          className="fm-select"
          value={filterStatus}
          onChange={(e: ChangeEvent<HTMLSelectElement>) => { setFilterStatus(e.target.value); setPage(1); }}
        >
          <option value="ALL">All statuses</option>
          {MAPPING_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        <span className="fm-count-label">{filtered.length} mapping{filtered.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Table */}
      <div className="fm-table-card">
        <div className="fm-table-wrap">
          <table className="fm-table">
            <thead>
              <tr>
                <th>Source System</th>
                <th>Source Field</th>
                <th></th>
                <th>Canonical Field</th>
                <th>Entity</th>
                <th>Transformations</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && mappings.length === 0 ? (
                <tr>
                  <td colSpan={8} className="fm-table-empty">
                    <span className="fm-empty-icon">⏳</span>
                    <p>Loading field mappings…</p>
                  </td>
                </tr>
              ) : paginated.length === 0 ? (
                <tr>
                  <td colSpan={8} className="fm-table-empty">
                    <span className="fm-empty-icon">⇌</span>
                    <p>
                      {mappings.length === 0
                        ? 'No field mappings yet. Create your first mapping to get started.'
                        : 'No mappings match the current filters.'}
                    </p>
                  </td>
                </tr>
              ) : (
                paginated.map(m => {
                  const ruleIds = m.transformation_rule_ids ?? [];
                  const appliedRules = ruleIds
                    .map(id => rules.find(r => r.rule_id === id))
                    .filter(Boolean) as TransformationRuleRead[];

                  return (
                    <tr key={m.mapping_id} onClick={() => setViewMapping(m)}>
                      <td>
                        <span className="fm-entity-chip" style={{ background: 'var(--bg-elevated)', color: 'var(--text-primary)', border: '1px solid var(--border-light)' }}>
                          {resolveSourceName(m.source_system_id)}
                        </span>
                      </td>
                      <td>
                        <span className="fm-source-field">{m.source_field_name}</span>
                      </td>
                      <td>
                        <span className="fm-arrow">→</span>
                      </td>
                      <td>
                        <span className="fm-canonical-field">
                          {resolveCanonicalName(m.canonical_field_id)}
                        </span>
                      </td>
                      <td>
                        <span className="fm-entity-chip">{m.entity_type}</span>
                      </td>
                      <td>
                        {appliedRules.length === 0 ? (
                          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>None</span>
                        ) : (
                          <div className="fm-rules-wrap">
                            {appliedRules.map(r => (
                              <span key={r.rule_id} className="fm-rule-chip">
                                {r.transformation_type}
                              </span>
                            ))}
                          </div>
                        )}
                      </td>
                      <td>
                        <span className={`fm-badge fm-badge--${m.status}`}>{m.status}</span>
                      </td>
                      <td>
                        <span className="fm-ts">{fmtDate(m.created_at)}</span>
                      </td>
                      <td>
                        <div className="fm-action-row" onClick={e => e.stopPropagation()}>
                          <button
                            type="button"
                            className="btn btn--ghost btn--sm"
                            onClick={() => setViewMapping(m)}
                          >
                            View
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="fm-pagination">
            <span className="fm-pag-info">
              Page {page} of {totalPages} · {filtered.length} results
            </span>
            <div className="fm-pag-btns">
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                disabled={page === 1}
                onClick={() => setPage(p => p - 1)}
              >
                ← Prev
              </button>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                disabled={page === totalPages}
                onClick={() => setPage(p => p + 1)}
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Detail Drawer */}
      {viewMapping && (
        <MappingDrawer
          mapping={viewMapping}
          canonicals={canonicals}
          rules={rules}
          sources={sources}
          onClose={() => setViewMapping(null)}
        />
      )}

      {/* Create Modal */}
      {showCreate && (
        <CreateMappingModal
          canonicals={canonicals}
          rules={rules}
          sources={sources}
          onSave={handleCreate}
          onClose={() => setShowCreate(false)}
        />
      )}
    </div>
  );
};

export default FieldMappingsPage;
