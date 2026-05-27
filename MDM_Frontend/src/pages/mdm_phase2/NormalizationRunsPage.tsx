/**
 * NormalizationRunsPage.tsx
 * ──────────────────────────
 * Phase 2 — Normalization Runs screen.
 *
 * Connects to:
 *   src/services/mdm_phase2/normalizationService.ts
 *     - listRuns()       → show all runs in a table
 *     - triggerRun()     → trigger a new normalization run
 *     - getRunStatus()   → refresh a single run's status
 */

import { useState, useEffect, useCallback, useMemo, type ChangeEvent } from 'react';
import '../../styles/theme.css';
import '../../styles/mdm_phase2/NormalizationRunsPage.css';

import {
  normalizationService,
  type NormalizationRunRead,
  type NormalizationRunCreate,
} from '../../services/mdm_phase2/normalizationService';
import { sourceService, type SourceRecord } from '../../services/sourceService';
import { useTenantConfig } from '../../context/TenantConfigContext';
import { useSnackbar } from '../../context/SnackbarContext';

/* ─────────────────────────────────────────────────
   Constants / helpers
───────────────────────────────────────────────── */
const ENTITY_TYPES = ['CUSTOMER', 'SUPPLIER', 'PRODUCT', 'ACCOUNT', 'ASSET', 'LOCATION', 'CONTACT'];
const RUN_STATUSES = ['CREATED', 'RUNNING', 'COMPLETED', 'FAILED', 'PARTIAL_SUCCESS', 'CANCELLED'];
const PAGE_SIZE = 15;

function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function fmtDuration(start: string | null, end: string | null): string {
  if (!start) return '—';
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  const sec = Math.floor((e - s) / 1000);
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  return `${min}m ${sec % 60}s`;
}

function getProgressClass(run: NormalizationRunRead): string {
  if (run.failed_records > 0 && run.successful_records > 0) return 'mixed';
  if (run.failed_records > 0) return 'fail';
  return 'ok';
}

function getProgressPct(run: NormalizationRunRead): number {
  if (run.total_records === 0) return 0;
  return Math.round((run.processed_records / run.total_records) * 100);
}

/* ─────────────────────────────────────────────────
   Run Detail Drawer
───────────────────────────────────────────────── */
type DrawerTab = 'overview' | 'errors';

interface RunDrawerProps {
  run: NormalizationRunRead;
  onClose: () => void;
  onRefresh: (runId: string) => Promise<NormalizationRunRead>;
}

function RunDrawer({ run: initialRun, onClose, onRefresh }: RunDrawerProps) {
  const [run, setRun] = useState<NormalizationRunRead>(initialRun);
  const [tab, setTab] = useState<DrawerTab>('overview');
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const updated = await onRefresh(run.run_id);
      setRun(updated);
    } finally {
      setRefreshing(false);
    }
  };

  const pct = getProgressPct(run);
  const pgClass = getProgressClass(run);

  return (
    <div className="nr-drawer-overlay" onClick={onClose} role="presentation">
      <div
        className="nr-drawer"
        onClick={e => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="nr-drawer-header">
          <div>
            <h2 className="nr-drawer-title">Normalization Run Details</h2>
            <div className="nr-drawer-sub">{run.run_id}</div>
          </div>
          <button type="button" className="nr-drawer-close" onClick={onClose}>✕</button>
        </div>

        {/* Tabs */}
        <div className="nr-drawer-tabs">
          {(['overview', 'errors'] as DrawerTab[]).map(t => (
            <button
              key={t}
              type="button"
              className={`nr-drawer-tab${tab === t ? ' nr-drawer-tab--active' : ''}`}
              onClick={() => setTab(t)}
            >
              {t === 'overview' ? 'Overview' : 'Error Summary'}
            </button>
          ))}
          <button
            type="button"
            className="nr-drawer-tab"
            style={{ marginLeft: 'auto' }}
            onClick={() => void handleRefresh()}
            disabled={refreshing}
          >
            {refreshing ? '⏳' : '↻'} Refresh
          </button>
        </div>

        {/* Body */}
        <div className="nr-drawer-body">

          {tab === 'overview' && (
            <>
              {/* Status + entity */}
              <div className="nr-drawer-section">
                <p className="nr-drawer-section-title">Run Summary</p>
                <div className="nr-drawer-grid">
                  <div className="nr-drawer-field">
                    <span className="nr-drawer-field-label">Status</span>
                    <span className="nr-drawer-field-value">
                      <span className={`nr-badge nr-badge--${run.status}`}>{run.status}</span>
                    </span>
                  </div>
                  <div className="nr-drawer-field">
                    <span className="nr-drawer-field-label">Entity Type</span>
                    <span className="nr-entity-chip">{run.entity_type}</span>
                  </div>
                  <div className="nr-drawer-field">
                    <span className="nr-drawer-field-label">Source System ID</span>
                    <span className="nr-drawer-field-value nr-drawer-field-value--mono">
                      {run.source_system_id.slice(0, 16)}…
                    </span>
                  </div>
                  <div className="nr-drawer-field">
                    <span className="nr-drawer-field-label">Ingestion Run</span>
                    <span className="nr-drawer-field-value nr-drawer-field-value--mono">
                      {run.ingestion_run_id ? run.ingestion_run_id.slice(0, 16) + '…' : '—'}
                    </span>
                  </div>
                  <div className="nr-drawer-field">
                    <span className="nr-drawer-field-label">Started At</span>
                    <span className="nr-drawer-field-value">{fmtDate(run.started_at)}</span>
                  </div>
                  <div className="nr-drawer-field">
                    <span className="nr-drawer-field-label">Ended At</span>
                    <span className="nr-drawer-field-value">{fmtDate(run.ended_at)}</span>
                  </div>
                  <div className="nr-drawer-field">
                    <span className="nr-drawer-field-label">Duration</span>
                    <span className="nr-drawer-field-value">
                      {fmtDuration(run.started_at, run.ended_at)}
                    </span>
                  </div>
                  <div className="nr-drawer-field">
                    <span className="nr-drawer-field-label">Created At</span>
                    <span className="nr-drawer-field-value">{fmtDate(run.created_at)}</span>
                  </div>
                </div>
              </div>

              {/* Record Counts */}
              <div className="nr-drawer-section">
                <p className="nr-drawer-section-title">Record Counts</p>
                <div className="nr-counts-row">
                  <div className="nr-count-chip">
                    <span className="nr-count-chip-val">{run.total_records}</span>
                    <span className="nr-count-chip-lbl">Total</span>
                  </div>
                  <div className="nr-count-chip">
                    <span className="nr-count-chip-val">{run.processed_records}</span>
                    <span className="nr-count-chip-lbl">Processed</span>
                  </div>
                  <div className="nr-count-chip nr-count-chip--success">
                    <span className="nr-count-chip-val">{run.successful_records}</span>
                    <span className="nr-count-chip-lbl">Successful</span>
                  </div>
                  <div className="nr-count-chip nr-count-chip--fail">
                    <span className="nr-count-chip-val">{run.failed_records}</span>
                    <span className="nr-count-chip-lbl">Failed</span>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="nr-progress-wrap" style={{ marginTop: 12 }}>
                  <div className="nr-progress-bar" style={{ height: 10 }}>
                    <div
                      className={`nr-progress-fill nr-progress-fill--${pgClass}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="nr-progress-label">{pct}%</span>
                </div>
              </div>

              {/* Error message if any */}
              {run.error_message && (
                <div className="nr-alert nr-alert--error">
                  <span>⚠</span>
                  <span>{run.error_message}</span>
                </div>
              )}
            </>
          )}

          {tab === 'errors' && (
            <div className="nr-drawer-section">
              <p className="nr-drawer-section-title">Error Summary</p>
              {run.failed_records === 0 ? (
                <div className="nr-alert nr-alert--success">
                  <span>✓</span>
                  <span>No failures recorded for this run.</span>
                </div>
              ) : (
                <div className="nr-alert nr-alert--error">
                  <span>⚠</span>
                  <div>
                    <strong>{run.failed_records}</strong> record(s) failed normalization.
                    <br />
                    <span style={{ fontSize: 12, opacity: .8 }}>
                      Visit the <strong>Mapping Errors</strong> screen for full details and retry options.
                    </span>
                  </div>
                </div>
              )}
              {run.error_message && (
                <div style={{ marginTop: 12 }}>
                  <p className="nr-drawer-section-title">Run Error Message</p>
                  <pre style={{
                    fontSize: 12, background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-light)',
                    borderRadius: 'var(--r-sm)',
                    padding: '10px 14px',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    color: 'var(--red-600)',
                    fontFamily: 'var(--font-mono)',
                  }}>
                    {run.error_message}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────
   Main Page
───────────────────────────────────────────────── */
export const NormalizationRunsPage: React.FC = () => {
  const { activeTenantId } = useTenantConfig();
  const snackbar = useSnackbar();

  const [runs, setRuns]         = useState<NormalizationRunRead[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [sources, setSources]   = useState<SourceRecord[]>([]);

  const [search, setSearch]             = useState('');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [filterEntity, setFilterEntity] = useState('ALL');
  const [page, setPage]                 = useState(1);

  const [viewRun, setViewRun] = useState<NormalizationRunRead | null>(null);

  /* Trigger form state */
  const [triggerForm, setTriggerForm] = useState<NormalizationRunCreate>({
    source_system_id: '',
    entity_type: 'CUSTOMER',
    ingestion_run_id: '',
  });

  /* ── Load sources ───────────────────────────── */
  const loadSources = useCallback(async () => {
    try {
      const data = await sourceService.listSources(0, 1000, activeTenantId ?? undefined);
      setSources(data);
    } catch (err) {
      console.error('Failed to load sources:', err);
    }
  }, [activeTenantId]);

  useEffect(() => { void loadSources(); }, [loadSources]);

  /* ── Load runs ──────────────────────────────── */
  const loadRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await normalizationService.listRuns(activeTenantId ?? undefined);
      setRuns(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load normalization runs.');
    } finally {
      setLoading(false);
    }
  }, [activeTenantId]);

  useEffect(() => { void loadRuns(); }, [loadRuns]);

  /* ── Trigger run ────────────────────────────── */
  const handleTrigger = async () => {
    if (!triggerForm.source_system_id.trim()) {
      snackbar.showError('Source system ID is required.');
      return;
    }
    setTriggering(true);
    try {
      const newRun = await normalizationService.triggerRun(
        {
          ...triggerForm,
          ingestion_run_id: triggerForm.ingestion_run_id?.trim() || null,
        },
        activeTenantId ?? undefined,
      );
      snackbar.showSuccess(`Normalization run triggered — ID: ${newRun.run_id.slice(0, 12)}…`);
      setTriggerForm({ source_system_id: '', entity_type: 'CUSTOMER', ingestion_run_id: '' });
      await loadRuns();
    } catch (err) {
      snackbar.showError(err instanceof Error ? err.message : 'Failed to trigger normalization run.');
    } finally {
      setTriggering(false);
    }
  };

  /* ── Refresh single run ─────────────────────── */
  const refreshRun = async (runId: string): Promise<NormalizationRunRead> => {
    const updated = await normalizationService.getRunStatus(runId, activeTenantId ?? undefined);
    setRuns(prev => prev.map(r => r.run_id === runId ? updated : r));
    return updated;
  };

  /* ── Filtering ──────────────────────────────── */
  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return runs.filter(r => {
      const matchText = !q ||
        r.run_id.toLowerCase().includes(q) ||
        r.entity_type.toLowerCase().includes(q) ||
        r.source_system_id.toLowerCase().includes(q);
      const matchStatus = filterStatus === 'ALL' || r.status === filterStatus;
      const matchEntity = filterEntity === 'ALL' || r.entity_type === filterEntity;
      return matchText && matchStatus && matchEntity;
    });
  }, [runs, search, filterStatus, filterEntity]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated  = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  useEffect(() => { setPage(p => Math.min(p, totalPages)); }, [totalPages]);

  /* ── Stats ──────────────────────────────────── */
  const completedCount = runs.filter(r => r.status === 'COMPLETED').length;
  const runningCount   = runs.filter(r => r.status === 'RUNNING').length;
  const failedCount    = runs.filter(r => r.status === 'FAILED').length;
  const partialCount   = runs.filter(r => r.status === 'PARTIAL_SUCCESS').length;
  const totalNorm      = runs.reduce((s, r) => s + r.successful_records, 0);

  /* ── Render ─────────────────────────────────── */
  return (
    <div className="nr-page">

      {/* Header */}
      <div className="nr-header">
        <div>
          <h1 className="nr-title">⚙ Normalization Runs</h1>
          <p className="nr-subtitle">
            Trigger and monitor normalization batches — converts READY_FOR_MAPPING records into READY_FOR_DQ.
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

      {/* Trigger panel */}
      <div className="nr-trigger-panel">
        <div>
          <h2 className="nr-trigger-title">▶ Trigger New Normalization Run</h2>
          <p className="nr-trigger-desc">
            Select a source system and entity type, then launch normalization.
          </p>
        </div>
        <div className="nr-trigger-fields">
          <div className="nr-trigger-field">
            <label className="nr-trigger-label">Source System</label>
            <select
              className="nr-trigger-select"
              value={triggerForm.source_system_id}
              onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                setTriggerForm(prev => ({ ...prev, source_system_id: e.target.value }))
              }
            >
              <option value="">-- Select Source System --</option>
              {sources.map(src => (
                <option key={src.id} value={src.id}>
                  {src.sourceName} ({src.id.slice(0, 8)}…)
                </option>
              ))}
            </select>
          </div>
          <div className="nr-trigger-field">
            <label className="nr-trigger-label">Entity Type</label>
            <select
              className="nr-trigger-select"
              value={triggerForm.entity_type}
              onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                setTriggerForm(prev => ({ ...prev, entity_type: e.target.value }))
              }
            >
              {ENTITY_TYPES.map(et => <option key={et} value={et}>{et}</option>)}
            </select>
          </div>
          <div className="nr-trigger-field">
            <label className="nr-trigger-label">Ingestion Run ID (optional)</label>
            <input
              className="nr-trigger-input"
              placeholder="UUID or leave blank"
              value={triggerForm.ingestion_run_id ?? ''}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setTriggerForm(prev => ({ ...prev, ingestion_run_id: e.target.value }))
              }
            />
          </div>
          <button
            type="button"
            className="nr-trigger-btn"
            onClick={() => void handleTrigger()}
            disabled={triggering}
          >
            {triggering ? <><span className="spinner" style={{ borderColor: 'rgba(255,255,255,.4)', borderTopColor: 'transparent' }} /> Running…</> : '▶ Trigger Run'}
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="nr-stats-row">
        <div className="nr-stat-card">
          <span className="nr-stat-value">{runs.length}</span>
          <span className="nr-stat-label">Total Runs</span>
        </div>
        <div className="nr-stat-card nr-stat-card--running">
          <span className="nr-stat-value">{runningCount}</span>
          <span className="nr-stat-label">Running</span>
        </div>
        <div className="nr-stat-card nr-stat-card--green">
          <span className="nr-stat-value">{completedCount}</span>
          <span className="nr-stat-label">Completed</span>
        </div>
        <div className="nr-stat-card nr-stat-card--amber">
          <span className="nr-stat-value">{partialCount}</span>
          <span className="nr-stat-label">Partial</span>
        </div>
        <div className="nr-stat-card nr-stat-card--red">
          <span className="nr-stat-value">{failedCount}</span>
          <span className="nr-stat-label">Failed</span>
        </div>
        <div className="nr-stat-card nr-stat-card--green">
          <span className="nr-stat-value">{totalNorm.toLocaleString()}</span>
          <span className="nr-stat-label">Records Normalized</span>
        </div>
      </div>

      {/* Filter bar */}
      <div className="nr-filter-bar">
        <div className="nr-search-wrap">
          <span className="nr-search-icon">🔍</span>
          <input
            className="nr-search-input"
            placeholder="Search run ID, entity, source…"
            value={search}
            onChange={(e: ChangeEvent<HTMLInputElement>) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
        <select
          className="nr-select"
          value={filterStatus}
          onChange={(e: ChangeEvent<HTMLSelectElement>) => { setFilterStatus(e.target.value); setPage(1); }}
        >
          <option value="ALL">All statuses</option>
          {RUN_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select
          className="nr-select"
          value={filterEntity}
          onChange={(e: ChangeEvent<HTMLSelectElement>) => { setFilterEntity(e.target.value); setPage(1); }}
        >
          <option value="ALL">All entities</option>
          {ENTITY_TYPES.map(et => <option key={et} value={et}>{et}</option>)}
        </select>
        <span className="nr-count-label">{filtered.length} run{filtered.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Table */}
      <div className="nr-table-card">
        <div className="nr-table-wrap">
          <table className="nr-table">
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Entity</th>
                <th>Status</th>
                <th>Progress</th>
                <th>Total</th>
                <th>✓ OK</th>
                <th>✗ Failed</th>
                <th>Duration</th>
                <th>Triggered</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && runs.length === 0 ? (
                <tr>
                  <td colSpan={10} className="nr-table-empty">
                    <span className="nr-empty-icon">⏳</span>
                    <p>Loading normalization runs…</p>
                  </td>
                </tr>
              ) : paginated.length === 0 ? (
                <tr>
                  <td colSpan={10} className="nr-table-empty">
                    <span className="nr-empty-icon">⚙</span>
                    <p>
                      {runs.length === 0
                        ? 'No normalization runs yet. Use the panel above to trigger your first run.'
                        : 'No runs match the current filters.'}
                    </p>
                  </td>
                </tr>
              ) : (
                paginated.map(run => {
                  const pct = getProgressPct(run);
                  const pgClass = getProgressClass(run);
                  return (
                    <tr key={run.run_id} onClick={() => setViewRun(run)}>
                      <td>
                        <span className="nr-id-chip">{run.run_id.slice(0, 12)}…</span>
                      </td>
                      <td>
                        <span className="nr-entity-chip">{run.entity_type}</span>
                      </td>
                      <td>
                        <span className={`nr-badge nr-badge--${run.status}`}>{run.status}</span>
                      </td>
                      <td style={{ minWidth: 130 }}>
                        <div className="nr-progress-wrap">
                          <div className="nr-progress-bar">
                            <div
                              className={`nr-progress-fill nr-progress-fill--${pgClass}`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <span className="nr-progress-label">{pct}%</span>
                        </div>
                      </td>
                      <td style={{ textAlign: 'right', fontWeight: 600 }}>
                        {run.total_records}
                      </td>
                      <td style={{ textAlign: 'right', color: 'var(--green-600)', fontWeight: 600 }}>
                        {run.successful_records}
                      </td>
                      <td style={{ textAlign: 'right', color: run.failed_records > 0 ? 'var(--red-600)' : 'var(--text-muted)', fontWeight: 600 }}>
                        {run.failed_records}
                      </td>
                      <td>
                        <span className="nr-ts">{fmtDuration(run.started_at, run.ended_at)}</span>
                      </td>
                      <td>
                        <span className="nr-ts">{fmtDate(run.created_at)}</span>
                      </td>
                      <td>
                        <div className="nr-action-row" onClick={e => e.stopPropagation()}>
                          <button
                            type="button"
                            className="btn btn--ghost btn--sm"
                            onClick={() => setViewRun(run)}
                          >
                            Details
                          </button>
                          <button
                            type="button"
                            className="btn btn--ghost btn--sm"
                            onClick={() => void refreshRun(run.run_id)}
                          >
                            ↻
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
          <div className="nr-pagination">
            <span className="nr-pag-info">Page {page} of {totalPages} · {filtered.length} runs</span>
            <div className="nr-pag-btns">
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

      {/* Run Detail Drawer */}
      {viewRun && (
        <RunDrawer
          run={viewRun}
          onClose={() => setViewRun(null)}
          onRefresh={refreshRun}
        />
      )}
    </div>
  );
};

export default NormalizationRunsPage;
