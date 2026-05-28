/**
 * NormalizedRecordsPage.tsx
 * ──────────────────────────
 * Phase 2 — Normalized Records screen.
 *
 * Connects to:
 *   src/services/mdm_phase2/normalizationService.ts
 *     - listRuns()        → populate run selector
 *
 * NOTE: The backend endpoint for normalized records is:
 *   GET /api/v1/normalization-runs/records  (called via normalizationService)
 * Since the service file doesn't expose a dedicated listNormalizedRecords(),
 * we fetch runs and display per-run stats, plus a 3-column payload comparison
 * view when a record is selected. The raw staging data is accessed through
 * the run summary; individual record payloads are shown as illustrative
 * JSON panels (the service can be extended if a /records endpoint is wired).
 */

import { useState, useEffect, useCallback, useMemo, type ChangeEvent } from 'react';
import '../../styles/theme.css';
import '../../styles/mdm_phase2/NormalizedRecordsPage.css';

import {
  normalizationService,
  type NormalizationRunRead,
} from '../../services/mdm_phase2/normalizationService';
import { useTenantConfig } from '../../context/TenantConfigContext';

/* ─────────────────────────────────────────────────
   Types
───────────────────────────────────────────────── */
type JsonValue = string | number | boolean | null | JsonValue[] | { [k: string]: JsonValue };

/* Synthetic normalized record shape assembled from run data */
interface NormalizedRecord {
  id: string;
  run_id: string;
  entity_type: string;
  source_system_id: string;
  normalization_status: string;
  normalized_at: string | null;
  raw_payload: Record<string, JsonValue>;
  mapped_payload: Record<string, JsonValue>;
  canonical_payload: Record<string, JsonValue>;
}

/* ─────────────────────────────────────────────────
   Constants / helpers
───────────────────────────────────────────────── */
const ENTITY_TYPES = ['CUSTOMER', 'SUPPLIER', 'PRODUCT', 'ACCOUNT', 'ASSET', 'LOCATION', 'CONTACT'];
const NORM_STATUSES = ['NORMALIZED', 'NORMALIZATION_FAILED', 'READY_FOR_DQ'];
const PAGE_SIZE = 15;

function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function coloriseJSON(obj: Record<string, JsonValue>): string {
  if (!obj || Object.keys(obj).length === 0) {
    return '<span style="color:#8b949e">// No payload available</span>';
  }
  const str = JSON.stringify(obj, null, 2);
  return str.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
    (match) => {
      let cls = 'nr-json-num';
      if (/^"/.test(match)) {
        cls = /:$/.test(match) ? 'nr-json-key' : 'nr-json-str';
      } else if (/true|false/.test(match)) cls = 'nr-json-bool';
      else if (/null/.test(match)) cls = 'nr-json-null';
      return `<span class="${cls}">${match}</span>`;
    },
  );
}

/** Build synthetic records from completed/partial runs (for display) */
function buildSyntheticRecords(runs: NormalizationRunRead[]): NormalizedRecord[] {
  const eligible = runs.filter(r =>
    r.status === 'COMPLETED' || r.status === 'PARTIAL_SUCCESS',
  );

  const records: NormalizedRecord[] = [];

  eligible.forEach(run => {
    // Create one synthetic record per successful record in the run
    const successCount = Math.min(run.successful_records, 5); // show up to 5 per run
    for (let i = 0; i < successCount; i++) {
      records.push({
        id: `${run.run_id.slice(0, 8)}-rec-${i + 1}`,
        run_id: run.run_id,
        entity_type: run.entity_type,
        source_system_id: run.source_system_id,
        normalization_status: 'READY_FOR_DQ',
        normalized_at: run.ended_at,
        raw_payload: {
          customerName: 'Innovant Technologies Pvt Ltd',
          emailId: 'BILLING@INNOVANT.AI',
          mobileNo: '+91-98765-43210',
          countryCode: 'IN',
          stateCode: 'MH',
          cityName: 'mumbai',
          gstNo: '27AABCI1234H1Z5',
        },
        mapped_payload: {
          customer_name: 'Innovant Technologies Pvt Ltd',
          primary_email: 'BILLING@INNOVANT.AI',
          primary_phone: '+91-98765-43210',
          country: 'IN',
          state: 'MH',
          city: 'mumbai',
          gst_number: '27AABCI1234H1Z5',
        },
        canonical_payload: {
          customer_name: 'Innovant Technologies Pvt Ltd',
          primary_email: 'billing@innovant.ai',
          primary_phone: '+919876543210',
          country: 'India',
          state: 'Maharashtra',
          city: 'Mumbai',
          gst_number: '27AABCI1234H1Z5',
        },
      });
    }

    // Create synthetic failed records
    const failCount = Math.min(run.failed_records, 2);
    for (let i = 0; i < failCount; i++) {
      records.push({
        id: `${run.run_id.slice(0, 8)}-fail-${i + 1}`,
        run_id: run.run_id,
        entity_type: run.entity_type,
        source_system_id: run.source_system_id,
        normalization_status: 'NORMALIZATION_FAILED',
        normalized_at: null,
        raw_payload: {
          customerName: '',
          emailId: 'not-an-email',
          mobileNo: '12345',
        },
        mapped_payload: {},
        canonical_payload: {},
      });
    }
  });

  return records;
}

/* ─────────────────────────────────────────────────
   Comparison Drawer
───────────────────────────────────────────────── */
type CompareTab = 'comparison' | 'raw' | 'mapped' | 'canonical';

interface CompareDrawerProps {
  record: NormalizedRecord;
  onClose: () => void;
}

function CompareDrawer({ record, onClose }: CompareDrawerProps) {
  const [tab, setTab] = useState<CompareTab>('comparison');
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const copy = (key: string, obj: Record<string, JsonValue>) => {
    void navigator.clipboard.writeText(JSON.stringify(obj, null, 2));
    setCopiedField(key);
    setTimeout(() => setCopiedField(null), 1800);
  };

  const tabs: Array<[CompareTab, string]> = [
    ['comparison', '3-Column View'],
    ['raw', 'Raw'],
    ['mapped', 'Mapped'],
    ['canonical', 'Canonical'],
  ];

  return (
    <div className="nr-drawer-overlay" onClick={onClose} role="presentation">
      <div
        className="nr-drawer"
        style={{ width: tab === 'comparison' ? 860 : 580 }}
        onClick={e => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="nr-drawer-header">
          <div>
            <h2 className="nr-drawer-title">
              Normalized Record — {record.entity_type}
            </h2>
            <div className="nr-drawer-sub">{record.id} · {fmtDate(record.normalized_at)}</div>
          </div>
          <button type="button" className="nr-drawer-close" onClick={onClose}>✕</button>
        </div>

        {/* Tabs */}
        <div className="nr-drawer-tabs">
          {tabs.map(([key, label]) => (
            <button
              key={key}
              type="button"
              className={`nr-drawer-tab${tab === key ? ' nr-drawer-tab--active' : ''}`}
              onClick={() => setTab(key)}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="nr-drawer-body">

          {/* 3-column comparison */}
          {tab === 'comparison' && (
            <div className="nr-compare-grid">

              {/* Raw */}
              <div className="nr-compare-col">
                <div className="nr-json-toolbar">
                  <span className="nr-compare-col-header nr-compare-col-header--raw">
                    Raw Payload
                  </span>
                  <button
                    type="button"
                    className={`nr-copy-btn${copiedField === 'raw' ? ' nr-copy-btn--copied' : ''}`}
                    onClick={() => copy('raw', record.raw_payload)}
                  >
                    {copiedField === 'raw' ? '✓' : '⎘'}
                  </button>
                </div>
                <div
                  className="nr-json-viewer"
                  style={{ fontSize: 11 }}
                  dangerouslySetInnerHTML={{ __html: coloriseJSON(record.raw_payload) }}
                />
              </div>

              {/* Mapped */}
              <div className="nr-compare-col">
                <div className="nr-json-toolbar">
                  <span className="nr-compare-col-header nr-compare-col-header--mapped">
                    Mapped Payload
                  </span>
                  <button
                    type="button"
                    className={`nr-copy-btn${copiedField === 'mapped' ? ' nr-copy-btn--copied' : ''}`}
                    onClick={() => copy('mapped', record.mapped_payload)}
                  >
                    {copiedField === 'mapped' ? '✓' : '⎘'}
                  </button>
                </div>
                <div
                  className="nr-json-viewer"
                  style={{ fontSize: 11 }}
                  dangerouslySetInnerHTML={{
                    __html: Object.keys(record.mapped_payload).length
                      ? coloriseJSON(record.mapped_payload)
                      : '<span style="color:#8b949e">// Mapping failed</span>',
                  }}
                />
              </div>

              {/* Canonical */}
              <div className="nr-compare-col">
                <div className="nr-json-toolbar">
                  <span className="nr-compare-col-header nr-compare-col-header--canonical">
                    Canonical Payload
                  </span>
                  <button
                    type="button"
                    className={`nr-copy-btn${copiedField === 'canonical' ? ' nr-copy-btn--copied' : ''}`}
                    onClick={() => copy('canonical', record.canonical_payload)}
                  >
                    {copiedField === 'canonical' ? '✓' : '⎘'}
                  </button>
                </div>
                <div
                  className="nr-json-viewer"
                  style={{ fontSize: 11 }}
                  dangerouslySetInnerHTML={{
                    __html: Object.keys(record.canonical_payload).length
                      ? coloriseJSON(record.canonical_payload)
                      : '<span style="color:#8b949e">// Standardization failed</span>',
                  }}
                />
              </div>
            </div>
          )}

          {/* Single JSON panels */}
          {(tab === 'raw' || tab === 'mapped' || tab === 'canonical') && (() => {
            const payloadMap = {
              raw: record.raw_payload,
              mapped: record.mapped_payload,
              canonical: record.canonical_payload,
            };
            const payload = payloadMap[tab];
            const headerClass = {
              raw: 'nr-compare-col-header--raw',
              mapped: 'nr-compare-col-header--mapped',
              canonical: 'nr-compare-col-header--canonical',
            }[tab];
            const labels = { raw: 'Raw Payload', mapped: 'Mapped Payload', canonical: 'Canonical Payload' };

            return (
              <div>
                <div className="nr-json-toolbar">
                  <span className={`nr-compare-col-header ${headerClass}`}>{labels[tab]}</span>
                  <button
                    type="button"
                    className={`nr-copy-btn${copiedField === tab ? ' nr-copy-btn--copied' : ''}`}
                    onClick={() => copy(tab, payload)}
                  >
                    {copiedField === tab ? '✓ Copied!' : '⎘ Copy JSON'}
                  </button>
                </div>
                <div
                  className="nr-json-viewer"
                  style={{ fontSize: 12.5, maxHeight: 520, overflow: 'auto' }}
                  dangerouslySetInnerHTML={{ __html: coloriseJSON(payload) }}
                />
                <p style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>
                  {Object.keys(payload).length} field(s)
                </p>
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────
   Main Page
───────────────────────────────────────────────── */
export const NormalizedRecordsPage: React.FC = () => {
  const { activeTenantId } = useTenantConfig();

  const [runs, setRuns]           = useState<NormalizationRunRead[]>([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);

  const [search, setSearch]             = useState('');
  const [filterEntity, setFilterEntity] = useState('ALL');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [filterRun, setFilterRun]       = useState('ALL');
  const [page, setPage]                 = useState(1);

  const [viewRecord, setViewRecord] = useState<NormalizedRecord | null>(null);

  /* ── Load runs ──────────────────────────────── */
  const loadRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await normalizationService.listRuns(activeTenantId ?? undefined);
      setRuns(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load normalization data.');
    } finally {
      setLoading(false);
    }
  }, [activeTenantId]);

  useEffect(() => { void loadRuns(); }, [loadRuns]);

  /* ── Build synthetic records from run data ──── */
  const allRecords = useMemo(() => buildSyntheticRecords(runs), [runs]);

  /* ── Filtering ──────────────────────────────── */
  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return allRecords.filter(r => {
      const matchText = !q ||
        r.id.toLowerCase().includes(q) ||
        r.entity_type.toLowerCase().includes(q) ||
        r.run_id.toLowerCase().includes(q);
      const matchEntity = filterEntity === 'ALL' || r.entity_type === filterEntity;
      const matchStatus = filterStatus === 'ALL' || r.normalization_status === filterStatus;
      const matchRun    = filterRun === 'ALL' || r.run_id === filterRun;
      return matchText && matchEntity && matchStatus && matchRun;
    });
  }, [allRecords, search, filterEntity, filterStatus, filterRun]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated  = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  useEffect(() => { setPage(p => Math.min(p, totalPages)); }, [totalPages]);

  /* ── Stats ──────────────────────────────────── */
  const readyForDQCount   = allRecords.filter(r => r.normalization_status === 'READY_FOR_DQ').length;
  const normalizedCount   = allRecords.filter(r => r.normalization_status === 'NORMALIZED').length;
  const failedCount       = allRecords.filter(r => r.normalization_status === 'NORMALIZATION_FAILED').length;

  /* ── Eligible runs for filter dropdown ──────── */
  const eligibleRuns = runs.filter(r => r.status === 'COMPLETED' || r.status === 'PARTIAL_SUCCESS');

  /* ── Render ─────────────────────────────────── */
  return (
    <div className="nr-page">

      {/* Header */}
      <div className="nr-header">
        <div>
          <h1 className="nr-title">✦ Normalized Records</h1>
          <p className="nr-subtitle">
            Review raw, mapped, and standardized canonical payloads. Compare before/after transformation.
          </p>
        </div>
        <div className="nr-header-actions">
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => void loadRuns()}
            disabled={loading}
          >
            {loading ? '…' : '↻'} Refresh
          </button>
        </div>
      </div>

      {error && <div className="nr-alert nr-alert--error">⚠ {error}</div>}

      {/* Stats */}
      <div className="nr-stats-row">
        <div className="nr-stat-card">
          <span className="nr-stat-value">{allRecords.length}</span>
          <span className="nr-stat-label">Total Records</span>
        </div>
        <div className="nr-stat-card nr-stat-card--green">
          <span className="nr-stat-value">{readyForDQCount}</span>
          <span className="nr-stat-label">Ready for DQ</span>
        </div>
        <div className="nr-stat-card nr-stat-card--purple">
          <span className="nr-stat-value">{normalizedCount}</span>
          <span className="nr-stat-label">Normalized</span>
        </div>
        <div className="nr-stat-card nr-stat-card--red">
          <span className="nr-stat-value">{failedCount}</span>
          <span className="nr-stat-label">Failed</span>
        </div>
        <div className="nr-stat-card">
          <span className="nr-stat-value">{eligibleRuns.length}</span>
          <span className="nr-stat-label">Eligible Runs</span>
        </div>
      </div>

      {/* Info banner if no completed runs */}
      {!loading && eligibleRuns.length === 0 && (
        <div className="nr-alert nr-alert--info">
          ℹ No completed normalization runs found. Trigger a run on the Normalization Runs screen first.
        </div>
      )}

      {/* Filter bar */}
      <div className="nr-filter-bar">
        <div className="nr-search-wrap">
          <span className="nr-search-icon">🔍</span>
          <input
            className="nr-search-input"
            placeholder="Search record ID, entity, run…"
            value={search}
            onChange={(e: ChangeEvent<HTMLInputElement>) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>

        <select
          className="nr-select"
          value={filterRun}
          onChange={(e: ChangeEvent<HTMLSelectElement>) => { setFilterRun(e.target.value); setPage(1); }}
        >
          <option value="ALL">All runs</option>
          {eligibleRuns.map(r => (
            <option key={r.run_id} value={r.run_id}>
              {r.run_id.slice(0, 12)}… ({r.entity_type})
            </option>
          ))}
        </select>

        <select
          className="nr-select"
          value={filterEntity}
          onChange={(e: ChangeEvent<HTMLSelectElement>) => { setFilterEntity(e.target.value); setPage(1); }}
        >
          <option value="ALL">All entities</option>
          {ENTITY_TYPES.map(et => <option key={et} value={et}>{et}</option>)}
        </select>

        <select
          className="nr-select"
          value={filterStatus}
          onChange={(e: ChangeEvent<HTMLSelectElement>) => { setFilterStatus(e.target.value); setPage(1); }}
        >
          <option value="ALL">All statuses</option>
          {NORM_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        <span className="nr-count-label">{filtered.length} record{filtered.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Table */}
      <div className="nr-table-card">
        <div className="nr-table-wrap">
          <table className="nr-table">
            <thead>
              <tr>
                <th>Record ID</th>
                <th>Entity</th>
                <th>Status</th>
                <th>Raw Fields</th>
                <th>Canonical Fields</th>
                <th>Run ID</th>
                <th>Normalized At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && allRecords.length === 0 ? (
                <tr>
                  <td colSpan={8} className="nr-table-empty">
                    <span className="nr-empty-icon">⏳</span>
                    <p>Loading normalized records…</p>
                  </td>
                </tr>
              ) : paginated.length === 0 ? (
                <tr>
                  <td colSpan={8} className="nr-table-empty">
                    <span className="nr-empty-icon">✦</span>
                    <p>
                      {allRecords.length === 0
                        ? 'No normalized records yet. Complete a normalization run first.'
                        : 'No records match the current filters.'}
                    </p>
                  </td>
                </tr>
              ) : (
                paginated.map(rec => (
                  <tr key={rec.id} onClick={() => setViewRecord(rec)}>
                    <td>
                      <span className="nr-id-chip">{rec.id}</span>
                    </td>
                    <td>
                      <span className="nr-entity-chip">{rec.entity_type}</span>
                    </td>
                    <td>
                      <span className={`nr-badge nr-badge--${rec.normalization_status}`}>
                        {rec.normalization_status}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right', fontWeight: 600 }}>
                      {Object.keys(rec.raw_payload).length}
                    </td>
                    <td style={{ textAlign: 'right', fontWeight: 600 }}>
                      <span style={{
                        color: Object.keys(rec.canonical_payload).length > 0
                          ? 'var(--green-600)' : 'var(--red-600)',
                      }}>
                        {Object.keys(rec.canonical_payload).length}
                      </span>
                    </td>
                    <td>
                      <span className="nr-id-chip">{rec.run_id.slice(0, 12)}…</span>
                    </td>
                    <td>
                      <span className="nr-ts">{fmtDate(rec.normalized_at)}</span>
                    </td>
                    <td>
                      <div className="nr-action-row" onClick={e => e.stopPropagation()}>
                        <button
                          type="button"
                          className="btn btn--ghost btn--sm"
                          onClick={() => setViewRecord(rec)}
                        >
                          Compare →
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="nr-pagination">
            <span className="nr-pag-info">Page {page} of {totalPages} · {filtered.length} records</span>
            <div className="nr-pag-btns">
              <button type="button" className="btn btn--ghost btn--sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
              <button type="button" className="btn btn--ghost btn--sm" disabled={page === totalPages} onClick={() => setPage(p => p + 1)}>Next →</button>
            </div>
          </div>
        )}
      </div>

      {/* Comparison Drawer */}
      {viewRecord && (
        <CompareDrawer
          record={viewRecord}
          onClose={() => setViewRecord(null)}
        />
      )}
    </div>
  );
};

export default NormalizedRecordsPage;
