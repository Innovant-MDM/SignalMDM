/**
 * MappingErrorsPage.tsx
 * ──────────────────────
 * Phase 2 — Mapping & Validation Errors screen.
 *
 * Connects to:
 *   src/services/mdm_phase2/normalizationService.ts
 *     - listErrors()      → fetch errors
 *     - retryError()      → trigger a retry for a specific error
 */

import { useState, useEffect, useCallback, useMemo, type ChangeEvent } from 'react';
import '../../styles/theme.css';
import '../../styles/mdm_phase2/MappingErrorsPage.css'; // Uses NormalizationRunsPage tokens

import {
  normalizationService,
  type MappingErrorRead,
} from '../../services/mdm_phase2/normalizationService';
import { useTenantConfig } from '../../context/TenantConfigContext';
import { useSnackbar } from '../../context/SnackbarContext';

/* ─────────────────────────────────────────────────
   Constants / helpers
───────────────────────────────────────────────── */
const ERROR_TYPES = ['MISSING_MAPPING', 'TRANSFORMATION_FAILED', 'STANDARDIZATION_FAILED', 'PAYLOAD_ERROR'];
const ERROR_STATUSES = ['OPEN', 'RETRIED', 'RESOLVED', 'IGNORED'];
const PAGE_SIZE = 15;

function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function getErrorTypeLabel(type: string): string {
  return type.replace(/_/g, ' ');
}

/* ─────────────────────────────────────────────────
   Error Detail Drawer
───────────────────────────────────────────────── */
interface ErrorDrawerProps {
  errorObj: MappingErrorRead;
  onClose: () => void;
  onRetry: (errorId: string) => Promise<void>;
  retryingId: string | null;
}

function ErrorDrawer({ errorObj, onClose, onRetry, retryingId }: ErrorDrawerProps) {
  const isRetrying = retryingId === errorObj.error_id;

  return (
    <div className="nr-drawer-overlay" onClick={onClose} role="presentation">
      <div
        className="nr-drawer"
        style={{ width: 560 }}
        onClick={e => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="nr-drawer-header">
          <div>
            <h2 className="nr-drawer-title">Error Details</h2>
            <div className="nr-drawer-sub">{errorObj.error_id}</div>
          </div>
          <button type="button" className="nr-drawer-close" onClick={onClose}>✕</button>
        </div>

        <div className="nr-drawer-body">

          {/* Status & action banner */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--bg-elevated)', padding: '16px 20px', borderRadius: 'var(--r-md)', border: '1px solid var(--border-light)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span className={`nr-badge nr-badge--${errorObj.status}`}>
                {errorObj.status}
              </span>
              <span className="nr-error-type">{getErrorTypeLabel(errorObj.error_type)}</span>
            </div>
            {errorObj.status === 'OPEN' && (
              <button
                type="button"
                className="nr-retry-btn"
                onClick={() => void onRetry(errorObj.error_id)}
                disabled={isRetrying}
              >
                {isRetrying ? '⏳ Retrying…' : '↻ Retry Processing'}
              </button>
            )}
          </div>

          <div className="nr-drawer-section">
            <p className="nr-drawer-section-title">Context</p>
            <div className="nr-drawer-grid">
              <div className="nr-drawer-field">
                <span className="nr-drawer-field-label">Normalization Run ID</span>
                <span className="nr-drawer-field-value nr-drawer-field-value--mono">
                  {errorObj.normalization_run_id.slice(0, 16)}…
                </span>
              </div>
              <div className="nr-drawer-field">
                <span className="nr-drawer-field-label">Staging Record ID</span>
                <span className="nr-drawer-field-value nr-drawer-field-value--mono">
                  {errorObj.staging_id.slice(0, 16)}…
                </span>
              </div>
              <div className="nr-drawer-field">
                <span className="nr-drawer-field-label">Created At</span>
                <span className="nr-drawer-field-value">{fmtDate(errorObj.created_at)}</span>
              </div>
              <div className="nr-drawer-field">
                <span className="nr-drawer-field-label">Updated At</span>
                <span className="nr-drawer-field-value">{fmtDate(errorObj.updated_at)}</span>
              </div>
              {(errorObj.resolved_at || errorObj.resolved_by) && (
                <>
                  <div className="nr-drawer-field">
                    <span className="nr-drawer-field-label">Resolved At</span>
                    <span className="nr-drawer-field-value">{fmtDate(errorObj.resolved_at)}</span>
                  </div>
                  <div className="nr-drawer-field">
                    <span className="nr-drawer-field-label">Resolved By</span>
                    <span className="nr-drawer-field-value">{errorObj.resolved_by ?? '—'}</span>
                  </div>
                </>
              )}
            </div>
          </div>

          <div className="nr-drawer-section">
            <p className="nr-drawer-section-title">Error Message</p>
            <div className="nr-alert nr-alert--error">
              <span>⚠</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>{errorObj.error_message}</span>
            </div>
          </div>

          {(errorObj.source_field || errorObj.source_value) && (
            <div className="nr-drawer-section">
              <p className="nr-drawer-section-title">Failing Field Details</p>
              <div className="nr-drawer-grid">
                {errorObj.source_field && (
                  <div className="nr-drawer-field">
                    <span className="nr-drawer-field-label">Source Field</span>
                    <span className="nr-error-field" style={{ alignSelf: 'flex-start' }}>
                      {errorObj.source_field}
                    </span>
                  </div>
                )}
                {errorObj.source_value && (
                  <div className="nr-drawer-field">
                    <span className="nr-drawer-field-label">Source Value</span>
                    <span className="nr-drawer-field-value" style={{ wordBreak: 'break-all' }}>
                      <code style={{ background: 'var(--surface-2)', padding: '2px 6px', borderRadius: 4 }}>
                        {errorObj.source_value}
                      </code>
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="nr-drawer-section">
            <p className="nr-drawer-section-title">Resolution Steps</p>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5, background: 'var(--bg-elevated)', padding: '16px', borderRadius: 'var(--r-md)' }}>
              {errorObj.error_type === 'MISSING_MAPPING' && (
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  <li>Go to <strong>Field Mappings</strong>.</li>
                  <li>Create a new mapping for the missing <strong>{errorObj.source_field}</strong> source field.</li>
                  <li>Return here and click <strong>Retry Processing</strong>.</li>
                </ul>
              )}
              {errorObj.error_type === 'TRANSFORMATION_FAILED' && (
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  <li>Check the applied transformation rules for <strong>{errorObj.source_field}</strong>.</li>
                  <li>Ensure the value <code>{errorObj.source_value}</code> is compatible with the rule logic (e.g. regex compilation).</li>
                  <li>Update the rule or mapping, then <strong>Retry</strong>.</li>
                </ul>
              )}
              {errorObj.error_type === 'STANDARDIZATION_FAILED' && (
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  <li>Check the standardization reference mappings for <strong>{errorObj.source_field}</strong>.</li>
                  <li>Add a missing reference key-value pair for <code>{errorObj.source_value}</code> if required.</li>
                  <li>Return and <strong>Retry</strong>.</li>
                </ul>
              )}
              {errorObj.error_type === 'PAYLOAD_ERROR' && (
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  <li>The overall staging payload could not be processed.</li>
                  <li>Check the JSON structure in Raw Landing or review the normalization run summary.</li>
                </ul>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────
   Main Page
───────────────────────────────────────────────── */
export const MappingErrorsPage: React.FC = () => {
  const { activeTenantId } = useTenantConfig();
  const snackbar = useSnackbar();

  const [errorsList, setErrorsList] = useState<MappingErrorRead[]>([]);
  const [loading, setLoading]       = useState(true);
  const [errorMsg, setErrorMsg]     = useState<string | null>(null);

  const [search, setSearch]             = useState('');
  const [filterType, setFilterType]     = useState('ALL');
  const [filterStatus, setFilterStatus] = useState('OPEN'); // default to OPEN
  const [page, setPage]                 = useState(1);

  const [viewError, setViewError]       = useState<MappingErrorRead | null>(null);
  const [retryingId, setRetryingId]     = useState<string | null>(null);

  /* ── Load errors ────────────────────────────── */
  const loadErrors = useCallback(async (statusVal: string) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      // In a real app we might pass "ALL" and filter client-side,
      // but the API wrapper currently takes a specific status.
      // We will fetch all and filter locally for a better UX.
      const statusesToFetch = statusVal === 'ALL' ? ERROR_STATUSES : [statusVal];
      const promises = statusesToFetch.map(s =>
        normalizationService.listErrors(s, activeTenantId ?? undefined).catch(() => [])
      );
      const results = await Promise.all(promises);
      const combined = results.flat();

      // Sort by created_at desc
      combined.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      setErrorsList(combined);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to load mapping errors.');
    } finally {
      setLoading(false);
    }
  }, [activeTenantId]);

  useEffect(() => { void loadErrors(filterStatus); }, [loadErrors, filterStatus]);

  /* ── Retry handler ──────────────────────────── */
  const handleRetry = async (errorId: string) => {
    setRetryingId(errorId);
    try {
      const res = await normalizationService.retryError(errorId);
      snackbar.showSuccess(res.message || 'Retry initiated successfully.');
      // Reload errors after retry
      await loadErrors(filterStatus);
      // Close drawer if it was the one retried
      if (viewError?.error_id === errorId) setViewError(null);
    } catch (err) {
      snackbar.showError(err instanceof Error ? err.message : 'Retry failed.');
    } finally {
      setRetryingId(null);
    }
  };

  /* ── Filtering ──────────────────────────────── */
  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return errorsList.filter(e => {
      const matchText = !q ||
        e.error_id.toLowerCase().includes(q) ||
        e.error_message.toLowerCase().includes(q) ||
        (e.source_field && e.source_field.toLowerCase().includes(q)) ||
        e.staging_id.toLowerCase().includes(q);
      const matchType = filterType === 'ALL' || e.error_type === filterType;
      // Note: filterStatus is handled at the API call level mostly, but we keep it here just in case.
      const matchStatus = filterStatus === 'ALL' || e.status === filterStatus;
      return matchText && matchType && matchStatus;
    });
  }, [errorsList, search, filterType, filterStatus]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated  = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  useEffect(() => { setPage(p => Math.min(p, totalPages)); }, [totalPages]);

  /* ── Render ─────────────────────────────────── */
  return (
    <div className="nr-page">

      {/* Header */}
      <div className="nr-header">
        <div>
          <h1 className="nr-title">⚠ Mapping & Validation Errors</h1>
          <p className="nr-subtitle">
            Review normalization failures, correct mapping rules, and retry processing.
          </p>
        </div>
        <div className="nr-header-actions">
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => void loadErrors(filterStatus)}
            disabled={loading}
          >
            {loading ? '…' : '↻'} Refresh
          </button>
        </div>
      </div>

      {errorMsg && <div className="nr-alert nr-alert--error">⚠ {errorMsg}</div>}

      {/* Filter bar */}
      <div className="nr-filter-bar">
        <div className="nr-search-wrap">
          <span className="nr-search-icon">🔍</span>
          <input
            className="nr-search-input"
            placeholder="Search error msg, source field, ID…"
            value={search}
            onChange={(e: ChangeEvent<HTMLInputElement>) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>

        <select
          className="nr-select"
          value={filterType}
          onChange={(e: ChangeEvent<HTMLSelectElement>) => { setFilterType(e.target.value); setPage(1); }}
        >
          <option value="ALL">All error types</option>
          {ERROR_TYPES.map(t => <option key={t} value={t}>{getErrorTypeLabel(t)}</option>)}
        </select>

        <select
          className="nr-select"
          value={filterStatus}
          onChange={(e: ChangeEvent<HTMLSelectElement>) => { setFilterStatus(e.target.value); setPage(1); }}
        >
          <option value="ALL">All statuses</option>
          {ERROR_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        <span className="nr-count-label">{filtered.length} error{filtered.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Table */}
      <div className="nr-table-card">
        <div className="nr-table-wrap">
          <table className="nr-table">
            <thead>
              <tr>
                <th>Error Type</th>
                <th>Status</th>
                <th>Source Field</th>
                <th>Error Message</th>
                <th>Staging ID</th>
                <th>Created At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && errorsList.length === 0 ? (
                <tr>
                  <td colSpan={7} className="nr-table-empty">
                    <span className="nr-empty-icon">⏳</span>
                    <p>Loading errors…</p>
                  </td>
                </tr>
              ) : paginated.length === 0 ? (
                <tr>
                  <td colSpan={7} className="nr-table-empty">
                    <span className="nr-empty-icon">✓</span>
                    <p>
                      {errorsList.length === 0
                        ? `No ${filterStatus === 'ALL' ? '' : filterStatus.toLowerCase()} mapping errors found.`
                        : 'No errors match the current filters.'}
                    </p>
                  </td>
                </tr>
              ) : (
                paginated.map(e => {
                  const isRetrying = retryingId === e.error_id;
                  return (
                    <tr key={e.error_id} onClick={() => setViewError(e)}>
                      <td>
                        <span className="nr-error-type">{getErrorTypeLabel(e.error_type)}</span>
                      </td>
                      <td>
                        <span className={`nr-badge nr-badge--${e.status}`}>{e.status}</span>
                      </td>
                      <td>
                        {e.source_field ? (
                          <span className="nr-error-field">{e.source_field}</span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>—</span>
                        )}
                      </td>
                      <td style={{ maxWidth: 300 }}>
                        <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={e.error_message}>
                          {e.error_message}
                        </span>
                      </td>
                      <td>
                        <span className="nr-id-chip">{e.staging_id.slice(0, 12)}…</span>
                      </td>
                      <td>
                        <span className="nr-ts">{fmtDate(e.created_at)}</span>
                      </td>
                      <td>
                        <div className="nr-action-row" onClick={ev => ev.stopPropagation()}>
                          <button
                            type="button"
                            className="btn btn--ghost btn--sm"
                            onClick={() => setViewError(e)}
                          >
                            Details
                          </button>
                          {e.status === 'OPEN' && (
                            <button
                              type="button"
                              className="nr-retry-btn"
                              onClick={() => void handleRetry(e.error_id)}
                              disabled={isRetrying}
                            >
                              {isRetrying ? '⏳' : '↻'} Retry
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="nr-pagination">
            <span className="nr-pag-info">Page {page} of {totalPages} · {filtered.length} errors</span>
            <div className="nr-pag-btns">
              <button type="button" className="btn btn--ghost btn--sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
              <button type="button" className="btn btn--ghost btn--sm" disabled={page === totalPages} onClick={() => setPage(p => p + 1)}>Next →</button>
            </div>
          </div>
        )}
      </div>

      {/* Error Detail Drawer */}
      {viewError && (
        <ErrorDrawer
          errorObj={viewError}
          onClose={() => setViewError(null)}
          onRetry={handleRetry}
          retryingId={retryingId}
        />
      )}
    </div>
  );
};

export default MappingErrorsPage;
