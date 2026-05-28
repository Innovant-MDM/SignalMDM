import { useState, useRef, useCallback, useEffect, type ChangeEvent, type DragEvent } from 'react';
import '../../styles/theme.css';
import '../../styles/UploadData.css';
import { authService } from '../../services/authService';
import { useTenantConfig } from '../../context/TenantConfigContext';
import {
  uploadSessionService,
  type UploadSession,
  type UploadSessionFile,
} from '../../services/uploadSessionService';
import { ApiError } from '../../services/api';
import { useSnackbar } from '../../context/SnackbarContext';
import { domainService, type DomainRecord } from '../../services/domainService';

// ── helpers ────────────────────────────────────────────────────────────────

function fmtBytes(b: number): string {
  if (b < 1024) return `${b} B`;
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1048576).toFixed(2)} MB`;
}
function fmtDate(s: string): string {
  return new Date(s).toLocaleString();
}
function fmtFriendlyDate(s: string): string {
  const d = new Date(s);
  const hour = d.getHours();
  const min = d.getMinutes().toString().padStart(2, '0');
  const sec = d.getSeconds().toString().padStart(2, '0');
  const ampm = hour >= 12 ? 'PM' : 'AM';
  const hour12 = hour % 12 || 12;
  const day = d.getDate().toString().padStart(2, '0');
  const month = (d.getMonth() + 1).toString().padStart(2, '0');
  const year = d.getFullYear();
  return `${hour12}:${min}:${sec} ${ampm} ${day}/${month}/${year}`;
}

// ── pending file row (before upload) ──────────────────────────────────────

interface SchemaValidationError {
  type: 'error' | 'warning';
  message: string;
}

interface PendingEntry {
  id: string;          // local key
  file: File;
  label: string;       // user-assigned label
  previewCount: number | null; // CSV rows counted client-side
  validationStatus: 'PASSED' | 'WARNING' | 'FAILED' | 'SKIPPED';
  validationErrors: SchemaValidationError[];
}

const EXPECTED_ATTRIBUTES: Record<string, { columns: string[]; mandatory: string[] }> = {
  CUSTOMER: {
    columns: ['customer_name', 'email', 'phone', 'billing_address', 'shipping_address', 'date_of_birth', 'loyalty_tier', 'status', 'created_at'],
    mandatory: ['customer_name', 'email']
  },
  SUPPLIER: {
    columns: ['supplier_name', 'tax_id', 'contact_email', 'contact_phone', 'payment_terms', 'rating', 'website_url', 'supplier_status'],
    mandatory: ['supplier_name', 'tax_id']
  },
  PRODUCT: {
    columns: ['product_name', 'sku', 'category', 'price', 'stock_quantity', 'manufacturer', 'weight', 'dimensions', 'is_active'],
    mandatory: ['product_name', 'sku']
  },
  ACCOUNT: {
    columns: ['account_name', 'account_number', 'currency', 'account_type', 'balance', 'branch_code', 'swift_code', 'opened_date'],
    mandatory: ['account_name', 'account_number']
  },
  ASSET: {
    columns: ['asset_name', 'asset_id', 'location', 'purchase_date', 'value', 'depreciation_rate', 'status', 'assigned_to'],
    mandatory: ['asset_name', 'asset_id']
  },
  LOCATION: {
    columns: ['location_name', 'address', 'region', 'country', 'postal_code', 'latitude', 'longitude', 'capacity'],
    mandatory: ['location_name', 'address']
  },
  EMPLOYEE: {
    columns: ['name', 'employee_id', 'department', 'role', 'email', 'phone', 'hire_date', 'manager_id', 'salary_band'],
    mandatory: ['name', 'employee_id']
  },
  OTHER: {
    columns: ['name', 'description', 'type', 'status', 'metadata_json', 'created_by'],
    mandatory: ['name']
  }
};

function getExpectedSchemaForDomain(domain: string) {
  const norm = domain.trim().toUpperCase();
  if (EXPECTED_ATTRIBUTES[norm]) return EXPECTED_ATTRIBUTES[norm];
  for (const key of Object.keys(EXPECTED_ATTRIBUTES)) {
    if (norm.includes(key) || key.includes(norm)) {
      return EXPECTED_ATTRIBUTES[key];
    }
  }
  return EXPECTED_ATTRIBUTES.OTHER;
}

function parseCsvHeaders(text: string): string[] {
  const firstLine = text.split(/\r?\n/)[0] || '';
  return firstLine.split(',').map(h => h.trim().replace(/^["']|["']$/g, ''));
}

function parseJsonHeaders(text: string): string[] {
  try {
    const parsed = JSON.parse(text);
    const obj = Array.isArray(parsed) ? parsed[0] : parsed;
    return obj ? Object.keys(obj) : [];
  } catch {
    return [];
  }
}

function countCsvRows(text: string): number {
  const lines = text.split(/\r?\n/).filter(l => l.trim().length > 0);
  return Math.max(0, lines.length - 1);
}

// ── view modes ─────────────────────────────────────────────────────────────

type View = 'list' | 'newSession' | 'detail';

// ===========================================================================
export default function UploadData() {
  const snackbar = useSnackbar();
  // ── tenant from global context (same as IngestionRuns) ──
  const { activeTenantId, activeTenantName } = useTenantConfig();
  const [isSuperAdmin, setIsSuperAdmin] = useState(false);

  // ── sessions ──
  const [sessions, setSessions] = useState<UploadSession[]>([]);
  const [activeSession, setActiveSession] = useState<UploadSession | null>(null);
  const [sessionSearch, setSessionSearch] = useState('');

  // ── view ──
  const [view, setView] = useState<View>('list');
  const [pageLoading, setPageLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);

  // ── new-session form ──
  const [newDomain, setNewDomain] = useState('');
  const [newSessionName, setNewSessionName] = useState('');
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [creating, setCreating] = useState(false);
  const [availableDomains, setAvailableDomains] = useState<DomainRecord[]>([]);

  // ── file upload form (within a session) ──
  const [pendingEntries, setPendingEntries] = useState<PendingEntry[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // ── load ──────────────────────────────────────────────────────────────────

  const loadSessions = useCallback(async (tid?: string | null) => {
    try {
      const data = await uploadSessionService.listSessions(tid ?? undefined);
      setSessions(data);
    } catch (e) {
      setPageError(e instanceof Error ? e.message : 'Failed to load sessions');
    }
  }, []);

  const loadDomains = useCallback(async (tid?: string | null) => {
    try {
      const data = await domainService.listDomains(0, 100, tid ?? undefined);
      setAvailableDomains(data);
    } catch (e) {
      console.error('Failed to load domains', e);
    }
  }, []);

  // Detect platform admin from cookie
  useEffect(() => {
    const info = authService.getAdminInfoFromCookie();
    const superAdmin = info?.tenant_id === 'platform' || info?.role === 'admin';
    setIsSuperAdmin(superAdmin);
  }, []);

  // Reload sessions whenever the global active tenant changes
  useEffect(() => {
    setPageLoading(true);
    Promise.all([
      loadSessions(activeTenantId),
      loadDomains(activeTenantId)
    ]).finally(() => setPageLoading(false));
  }, [activeTenantId, loadSessions, loadDomains]);

  // ── tenant filter ─────────────────────────────────────────────────────────
  // NOTE: Tenant selection is now handled globally by TenantScopeBar in MainLayout.
  //       activeTenantId from useTenantConfig() is the single source of truth.

  // ── session select ────────────────────────────────────────────────────────

  const openSession = async (s: UploadSession) => {
    try {
      const full = await uploadSessionService.getSession(s.session_id, activeTenantId ?? undefined);
      setActiveSession(full);
      setView('detail');
      setPendingEntries([]);
      setUploadError(null);
      setUploadSuccess(false);
    } catch (e) {
      setPageError(e instanceof Error ? e.message : 'Failed to open session');
    }
  };

  const handleDeleteSession = async (session: UploadSession) => {
    if (!window.confirm(`Delete session "${session.session_name}" and all its files?`)) return;
    try {
      await uploadSessionService.deleteSession(session.session_id, activeTenantId ?? undefined);
      if (activeSession?.session_id === session.session_id) {
        setActiveSession(null);
        setView('list');
      }
      await loadSessions(activeTenantId);
      snackbar.showSuccess(`Session "${session.session_name}" deleted.`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Delete failed';
      setPageError(msg);
      snackbar.showError(`Failed to delete session: ${msg}`);
    }
  };

  // ── new session ───────────────────────────────────────────────────────────

  const validateSessionForm = () => {
    const errs: Record<string, string> = {};
    if (!newDomain.trim()) errs.domain = 'Domain is required';
    if (!newSessionName.trim()) errs.sessionName = 'Session name is required';
    else if (sessions.some(s => s.session_name.toLowerCase() === newSessionName.trim().toLowerCase()))
      errs.sessionName = 'Session name already exists';
    setFormErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleCreateSession = async () => {
    if (isSuperAdmin && !activeTenantId) {
      setFormErrors({ general: 'Please select a tenant from the top dropdown first.' });
      return;
    }
    if (!validateSessionForm()) return;
    setCreating(true);
    try {
      const s = await uploadSessionService.createSession(
        { 
          session_name: newSessionName.trim(), 
          domain: newDomain.trim(),
          tenant_id: activeTenantId ?? undefined,
        },
        activeTenantId ?? undefined,
      );
      await loadSessions(activeTenantId);
      setNewDomain('');
      setNewSessionName('');
      setFormErrors({});
      setView('detail');
      setActiveSession(s);
      setPendingEntries([]);
      snackbar.showSuccess(`Upload session "${s.session_name}" created successfully.`);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Create failed';
      setFormErrors(prev => ({ ...prev, general: msg }));
      snackbar.showError(`Failed to create session: ${msg}`);
    } finally {
      setCreating(false);
    }
  };

  // ── file picking ──────────────────────────────────────────────────────────

  const addFiles = useCallback(async (files: FileList | File[]) => {
    const arr = Array.from(files);
    const newEntries: PendingEntry[] = [];
    const tooLarge: string[] = [];
    const unsupported: string[] = [];

    const domain = activeSession?.domain || 'OTHER';
    const schema = getExpectedSchemaForDomain(domain);

    for (const f of arr) {
      if (f.size > 100 * 1024 * 1024) {
        tooLarge.push(f.name);
        continue;
      }
      
      const ext = f.name.split('.').pop()?.toLowerCase();
      if (!ext || !['csv', 'json', 'xlsx'].includes(ext)) {
        unsupported.push(f.name);
        continue;
      }

      let previewCount: number | null = null;
      if (f.name.toLowerCase().endsWith('.csv')) {
        try { previewCount = countCsvRows(await f.text()); } catch { /* ok */ }
      }

      let validationStatus: 'PASSED' | 'WARNING' | 'FAILED' | 'SKIPPED' = 'PASSED';
      const validationErrors: SchemaValidationError[] = [];
      let headers: string[] = [];

      if (ext === 'csv') {
        try {
          const text = await f.text();
          headers = parseCsvHeaders(text);
        } catch {
          validationStatus = 'FAILED';
          validationErrors.push({ type: 'error', message: 'Failed to read CSV file text.' });
        }
      } else if (ext === 'json') {
        try {
          const text = await f.text();
          headers = parseJsonHeaders(text);
        } catch {
          validationStatus = 'FAILED';
          validationErrors.push({ type: 'error', message: 'Failed to parse JSON file.' });
        }
      } else {
        validationStatus = 'SKIPPED';
      }

      if (validationStatus !== 'FAILED' && validationStatus !== 'SKIPPED') {
        const lowerHeaders = headers.map(h => h.toLowerCase());
        const missingMandatory = schema.mandatory.filter(col => !lowerHeaders.includes(col.toLowerCase()));
        const missingOptional = schema.columns.filter(col => !schema.mandatory.includes(col) && !lowerHeaders.includes(col.toLowerCase()));
        const extraColumns = headers.filter(h => !schema.columns.map(c => c.toLowerCase()).includes(h.toLowerCase()));
        const hasOverlap = headers.some(h => schema.columns.map(c => c.toLowerCase()).includes(h.toLowerCase()));

        if (missingMandatory.length > 0) {
          validationStatus = 'WARNING';
          validationErrors.push({
            type: 'warning',
            message: `Missing expected column(s) for ${domain}: ${missingMandatory.join(', ')} — file will be uploaded as raw data.`
          });
        } else if (!hasOverlap && headers.length > 0) {
          validationStatus = 'WARNING';
          validationErrors.push({
            type: 'warning',
            message: `Schema mismatch: None of the expected columns for ${domain} found — file will be uploaded as raw data.`
          });
        } else {
          if (missingOptional.length > 0) {
            validationStatus = 'WARNING';
            validationErrors.push({
              type: 'warning',
              message: `Missing optional column(s): ${missingOptional.join(', ')}`
            });
          }
          if (extraColumns.length > 0) {
            if (validationStatus === 'PASSED') validationStatus = 'WARNING';
            validationErrors.push({
              type: 'warning',
              message: `Detected unrecognized column(s): ${extraColumns.join(', ')}`
            });
          }
        }
      }

      newEntries.push({
        id: crypto.randomUUID(),
        file: f,
        label: f.name.replace(/\.[^.]+$/, ''),
        previewCount,
        validationStatus,
        validationErrors,
      });
    }

    if (tooLarge.length > 0 || unsupported.length > 0) {
      const errMsgs = [];
      if (tooLarge.length > 0) {
        errMsgs.push(`Skipped ${tooLarge.length} file(s) exceeding 100MB: ${tooLarge.join(', ')}`);
        snackbar.showError(`Files exceeding 100MB limit: ${tooLarge.join(', ')}`);
      }
      if (unsupported.length > 0) {
        errMsgs.push(`Skipped ${unsupported.length} unsupported file(s): ${unsupported.join(', ')}. Only CSV, JSON, and XLSX are allowed.`);
        snackbar.showWarning(`Unsupported formats: ${unsupported.join(', ')}`);
      }
      setUploadError(errMsgs.join(' | '));
    } else {
      setUploadError(null);
    }
    
    setPendingEntries(prev => [...prev, ...newEntries]);
  }, [activeSession, snackbar]);

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length) void addFiles(e.dataTransfer.files);
  }, [addFiles]);

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) void addFiles(e.target.files);
    e.target.value = '';
  };

  const removeEntry = (id: string) => setPendingEntries(prev => prev.filter(p => p.id !== id));
  const updateLabel = (id: string, label: string) =>
    setPendingEntries(prev => prev.map(p => p.id === id ? { ...p, label } : p));

  // ── upload ────────────────────────────────────────────────────────────────

  const handleUpload = async () => {
    if (!activeSession || pendingEntries.length === 0) return;
    const emptyLabel = pendingEntries.find(p => !p.label.trim());
    if (emptyLabel) {
      snackbar.showWarning('All file labels are required.');
      setUploadError('All file labels are required.');
      return;
    }

    setUploading(true);
    setUploadError(null);
    setUploadSuccess(false);
    setUploadProgress(10);

    const timer = window.setInterval(() => {
      setUploadProgress(p => (p == null || p >= 85 ? 85 : p + 10));
    }, 300);

    try {
      await uploadSessionService.uploadFiles(
        activeSession.session_id,
        pendingEntries.map(p => ({ file: p.file, label: p.label })),
        activeTenantId ?? undefined,
      );
      setUploadProgress(100);
      setUploadSuccess(true);
      setPendingEntries([]);
      // refresh session detail
      const full = await uploadSessionService.getSession(activeSession.session_id, activeTenantId ?? undefined);
      setActiveSession(full);
      await loadSessions(activeTenantId);

      const hasDuplicate = full.files?.some(f => f.is_duplicate);
      if (hasDuplicate) {
        snackbar.showWarning('File upload completed. Note: One or more uploaded files are duplicate checksums.');
      } else {
        snackbar.showSuccess('Files uploaded successfully.');
      }
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Upload failed';
      setUploadError(msg);
      snackbar.showError(`Upload failed: ${msg}`);
    } finally {
      clearInterval(timer);
      setUploading(false);
      setTimeout(() => setUploadProgress(null), 800);
    }
  };

  const handleDeleteFile = async (file: UploadSessionFile) => {
    if (!activeSession) return;
    if (!window.confirm(`Remove "${file.file_label}"?`)) return;
    try {
      await uploadSessionService.deleteFile(activeSession.session_id, file.file_id, activeTenantId ?? undefined);
      const full = await uploadSessionService.getSession(activeSession.session_id, activeTenantId ?? undefined);
      setActiveSession(full);
      await loadSessions(activeTenantId);
      snackbar.showSuccess(`File "${file.file_label}" has been removed.`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Delete failed';
      setUploadError(msg);
      snackbar.showError(`Failed to delete file: ${msg}`);
    }
  };

  // ── filtered sessions ─────────────────────────────────────────────────────

  const filteredSessions = sessions.filter(s =>
    sessionSearch === '' ||
    s.session_name.toLowerCase().includes(sessionSearch.toLowerCase()) ||
    s.domain.toLowerCase().includes(sessionSearch.toLowerCase())
  );

  // ── render ────────────────────────────────────────────────────────────────

  if (pageLoading) {
    return (
      <div className="up-page">
        <div className="up-spinner">⏳ Loading upload sessions…</div>
      </div>
    );
  }

  return (
    <div className="up-page">
      {/* Header */}
      <div className="up-header">
        <div>
          <h1 className="up-title">Upload Data</h1>
          <p className="up-subtitle">
            Organise files into named sessions (folders) before ingestion. Upload multiple files per session.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          {isSuperAdmin && activeTenantName && (
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--blue-600)', background: 'var(--blue-100)', padding: '4px 10px', borderRadius: 99, border: '1px solid var(--blue-200)' }}>
              🏢 {activeTenantName}
            </span>
          )}
          <button
            className="up-btn up-btn--primary"
            onClick={() => { setView('newSession'); setFormErrors({}); setNewDomain(''); setNewSessionName(''); }}
            type="button"
          >
            + New Session
          </button>
        </div>
      </div>

      {pageError && (
        <div className="up-alert up-alert--error">
          <span>✕</span><span>{pageError}</span>
        </div>
      )}

      {/* Main layout */}
      <div className="up-layout">
        {/* LEFT — session browser */}
        <div className="up-card">
          <div className="up-browser__toolbar up-card__head">
            <span className="up-browser__title">📁 Sessions ({filteredSessions.length})</span>
            <input
              className="up-browser__search"
              placeholder="Search…"
              value={sessionSearch}
              onChange={e => setSessionSearch(e.target.value)}
            />
          </div>
          {filteredSessions.length === 0 ? (
            <div className="up-empty" style={{ padding: 40 }}>
              <span className="up-empty__icon">📂</span>
              <span className="up-empty__title">No sessions yet</span>
              <span className="up-empty__sub">Click "New Session" to create a named upload folder.</span>
            </div>
          ) : (
            <div className="up-session-list">
              {filteredSessions.map(s => (
                <div
                  key={s.session_id}
                  className={`up-session-row${activeSession?.session_id === s.session_id && view === 'detail' ? ' up-session-row--active' : ''}`}
                  onClick={() => void openSession(s)}
                >
                  <div className="up-session-row__left">
                    <span className="up-session-icon">📁</span>
                    <div>
                      <div className="up-session-name">{s.session_name}</div>
                      <div className="up-session-domain">{s.domain}</div>
                    </div>
                  </div>
                  <div className="up-session-row__right">
                    <span className="up-session-count">{s.file_count} file{s.file_count !== 1 ? 's' : ''}</span>
                    <span className={`up-session-status up-session-status--${s.status.toLowerCase()}`}>
                      {s.status}
                    </span>
                    <button
                      className="up-btn up-btn--danger up-btn--sm"
                      type="button"
                      title="Delete session"
                      onClick={(e) => {
                        e.stopPropagation();
                        void handleDeleteSession(s);
                      }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* RIGHT — new session form or session detail */}
        <div className="up-card">
          {view === 'newSession' && (
            <>
              <div className="up-card__head">
                <div className="up-card__title">Create New Session</div>
                <div className="up-card__sub">A session is a named folder that groups related uploads.</div>
              </div>
              <div className="up-card__body">
                {formErrors.general && (
                  <div className="up-alert up-alert--error"><span>✕</span><span>{formErrors.general}</span></div>
                )}
                <div className={`up-field${formErrors.domain ? ' up-field--error' : ''}`}>
                  <label className="up-label">Domain <span className="up-required">*</span></label>
                  <select
                    className="up-input"
                    value={newDomain}
                    onChange={e => setNewDomain(e.target.value)}
                  >
                    <option value="">-- Select a Domain --</option>
                    {availableDomains.map(d => (
                      <option key={d.id} value={d.domainName}>{d.domainName}</option>
                    ))}
                  </select>
                  {formErrors.domain && <span className="up-error-msg">{formErrors.domain}</span>}
                </div>
                <div className={`up-field${formErrors.sessionName ? ' up-field--error' : ''}`}>
                  <label className="up-label">Session Name <span className="up-required">*</span></label>
                  <input
                    className="up-input"
                    placeholder="e.g. StudentDataUploadSession1"
                    value={newSessionName}
                    onChange={e => setNewSessionName(e.target.value)}
                  />
                  {formErrors.sessionName && <span className="up-error-msg">{formErrors.sessionName}</span>}
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    Must be unique within your tenant.
                  </span>
                </div>
                <div className="up-alert up-alert--info">
                  <span>ℹ</span>
                  <span>
                    <strong>Example:</strong> Domain = Student, Session = StudentDataUploadSession1. You can then upload multiple files (Student Data Set1, Student Data Set2 Master, Courses Master) inside it.
                  </span>
                </div>
              </div>
              <div className="up-card__foot">
                <button className="up-btn up-btn--ghost" onClick={() => setView('list')} type="button">Cancel</button>
                <button className="up-btn up-btn--primary" onClick={() => void handleCreateSession()} disabled={creating} type="button">
                  {creating ? '⏳ Creating…' : '✓ Create Session'}
                </button>
              </div>
            </>
          )}

          {view === 'list' && (
            <div className="up-empty">
              <span className="up-empty__icon">👈</span>
              <span className="up-empty__title">Select a session</span>
              <span className="up-empty__sub">Choose a session from the left panel, or create a new one.</span>
            </div>
          )}

          {view === 'detail' && activeSession && (
            <>
              <div className="up-card__head">
                <div className="up-detail__header">
                  <span className="up-detail__folder">📁</span>
                  <div>
                    <div className="up-detail__name">{activeSession.session_name}</div>
                    <div className="up-detail__domain">{activeSession.domain}</div>
                    <div className="up-detail__meta">
                      <span className="up-detail__chip">
                        {activeSession.file_count} file{activeSession.file_count !== 1 ? 's' : ''}
                      </span>
                      <span className={`up-session-status up-session-status--${activeSession.status.toLowerCase()}`}>
                        {activeSession.status}
                      </span>
                      <span className="up-detail__chip">Created {fmtDate(activeSession.created_at)}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="up-card__body">
                {/* Existing files table */}
                {(activeSession.files?.length ?? 0) > 0 && (
                  <div className="up-files-table-wrap">
                    <table className="up-files-table">
                      <thead>
                        <tr>
                          <th>File Label</th>
                          <th>Original Filename</th>
                          <th>Records</th>
                          <th>Size</th>
                          <th>Who Uploaded</th>
                          <th>When was it</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        {activeSession.files!.map(f => (
                          <tr key={f.file_id}>
                            <td>
                              <strong>{f.file_label}</strong>
                              {f.is_duplicate && (
                                <div className="up-dup-warning" style={{ marginTop: 4 }}>
                                  <div className="up-dup-title">⚠ Duplicate File</div>
                                  <div className="up-dup-meta">
                                    First uploaded by <strong>{f.first_uploaded_by || 'Unknown'}</strong> on {f.first_uploaded_at ? fmtFriendlyDate(f.first_uploaded_at) : ''}
                                  </div>
                                </div>
                              )}
                            </td>
                            <td style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono,monospace)', fontSize: 11 }}>
                              {f.original_filename}
                            </td>
                            <td>
                              {f.record_count != null
                                ? <span className="up-rec-badge">{f.record_count.toLocaleString()} rows</span>
                                : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                            </td>
                            <td>{f.file_size_bytes != null ? fmtBytes(f.file_size_bytes) : '—'}</td>
                            <td>
                              <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>
                                {f.uploaded_by || 'Unknown'}
                              </span>
                            </td>
                            <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                              {fmtFriendlyDate(f.uploaded_at)}
                            </td>
                            <td>
                              <button
                                className="up-btn up-btn--danger up-btn--sm"
                                onClick={() => void handleDeleteFile(f)}
                                type="button"
                              >✕</button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Upload new files */}
                {activeSession.status === 'OPEN' && (
                  <>
                    <div style={{ borderTop: '1px solid var(--border)', paddingTop: 14 }}>
                      <div className="up-card__title" style={{ marginBottom: 10 }}>Add Files to Session</div>

                      {/* Dropzone */}
                      {pendingEntries.length === 0 && (
                        <div
                          className={`up-dropzone${isDragging ? ' up-dropzone--active' : ''}`}
                          onDrop={handleDrop}
                          onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
                          onDragLeave={() => setIsDragging(false)}
                          onClick={() => fileInputRef.current?.click()}
                          role="button" tabIndex={0}
                          onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click(); }}
                        >
                          <span className="up-dropzone__icon">☁️</span>
                          <span className="up-dropzone__label">Drag &amp; drop CSV/JSON/XLSX files here</span>
                          <span className="up-dropzone__sub">or click to browse — multiple files supported (100MB maximum per file)</span>
                          <input
                            ref={fileInputRef}
                            type="file"
                            accept=".csv,.json,.xlsx"
                            multiple
                            style={{ display: 'none' }}
                            onChange={handleInputChange}
                          />
                        </div>
                      )}

                      {/* Pending entries */}
                      {pendingEntries.length > 0 && (
                        <>
                          <div className="up-file-entries">
                            {pendingEntries.map(entry => (
                              <div key={entry.id} className="up-file-entry">
                                <div className="up-field">
                                  <label className="up-label">File Name (Label) <span className="up-required">*</span></label>
                                  <input
                                    className="up-input"
                                    value={entry.label}
                                    onChange={e => updateLabel(entry.id, e.target.value)}
                                    placeholder="e.g. Student Data Set1"
                                  />
                                </div>
                                <div className="up-field">
                                  <label className="up-label">Original File</label>
                                  <input className="up-input" value={entry.file.name} readOnly style={{ opacity: .7 }} />
                                </div>
                                <button className="up-file-entry__remove" onClick={() => removeEntry(entry.id)} type="button">✕</button>
                                <div className="up-file-entry__meta" style={{ flexDirection: 'column', gap: 6, alignItems: 'flex-start' }}>
                                  <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                                    <span>📄 {fmtBytes(entry.file.size)}</span>
                                    {entry.previewCount != null && (
                                      <span className="up-file-entry__badge">~{entry.previewCount.toLocaleString()} rows</span>
                                    )}
                                  </div>
                                  <div>
                                    <div className={`up-validation-badge up-validation-badge--${entry.validationStatus.toLowerCase()}`}>
                                      {entry.validationStatus === 'PASSED' && '✓ Schema Verified'}
                                      {entry.validationStatus === 'WARNING' && '⚠ Schema Warning'}
                                      {entry.validationStatus === 'FAILED' && '✕ Schema Failed'}
                                      {entry.validationStatus === 'SKIPPED' && 'ℹ Verification Skipped (.xlsx)'}
                                    </div>
                                    {entry.validationErrors.length > 0 && (
                                      <ul className="up-validation-errors">
                                        {entry.validationErrors.map((err, index) => (
                                          <li key={index} className={`up-validation-error--${err.type}`}>
                                            {err.message}
                                          </li>
                                        ))}
                                      </ul>
                                    )}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>

                          <div className="up-add-row" style={{ marginTop: 8 }}>
                            <button
                              className="up-btn up-btn--ghost up-btn--sm"
                              onClick={() => fileInputRef.current?.click()}
                              type="button"
                            >+ Add more files</button>
                            <input
                              ref={fileInputRef}
                              type="file" accept=".csv,.json,.xlsx" multiple
                              style={{ display: 'none' }}
                              onChange={handleInputChange}
                            />
                          </div>
                        </>
                      )}
                    </div>

                    {uploadError && (
                      <div className="up-alert up-alert--error"><span>✕</span><span>{uploadError}</span></div>
                    )}
                    {pendingEntries.some(e => e.validationStatus === 'FAILED') && (
                      <div className="up-alert up-alert--error" style={{ marginTop: 12 }}>
                        <span>✕</span>
                        <span>Please remove files with failed schema validations before uploading.</span>
                      </div>
                    )}
                    {uploadSuccess && (
                      <div className="up-alert up-alert--success"><span>✓</span><span>Files uploaded successfully.</span></div>
                    )}
                    {uploadProgress != null && (
                      <div className="up-progress">
                        <div className="up-progress__label"><span>Uploading…</span><span>{uploadProgress}%</span></div>
                        <div className="up-progress__track">
                          <div className="up-progress__fill" style={{ width: `${uploadProgress}%` }} />
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>

              {activeSession.status === 'OPEN' && pendingEntries.length > 0 && (
                <div className="up-card__foot">
                  <button className="up-btn up-btn--ghost" onClick={() => setPendingEntries([])} disabled={uploading} type="button">Clear</button>
                  <button
                    className="up-btn up-btn--primary"
                    onClick={() => void handleUpload()}
                    disabled={uploading || pendingEntries.length === 0 || pendingEntries.some(e => e.validationStatus === 'FAILED')}
                    type="button"
                  >
                    {uploading ? '⏳ Uploading…' : `⬆ Upload ${pendingEntries.length} File${pendingEntries.length !== 1 ? 's' : ''}`}
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
