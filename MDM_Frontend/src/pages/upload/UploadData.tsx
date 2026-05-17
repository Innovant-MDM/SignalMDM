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

interface PendingEntry {
  id: string;          // local key
  file: File;
  label: string;       // user-assigned label
  previewCount: number | null; // CSV rows counted client-side
}

function countCsvRows(text: string): number {
  const lines = text.split(/\r?\n/).filter(l => l.trim().length > 0);
  return Math.max(0, lines.length - 1);
}

// ── view modes ─────────────────────────────────────────────────────────────

type View = 'list' | 'newSession' | 'detail';

// ===========================================================================
export default function UploadData() {
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

  // Detect platform admin from cookie
  useEffect(() => {
    const info = authService.getAdminInfoFromCookie();
    const superAdmin = info?.tenant_id === 'platform' || info?.role === 'admin';
    setIsSuperAdmin(superAdmin);
  }, []);

  // Reload sessions whenever the global active tenant changes
  useEffect(() => {
    setPageLoading(true);
    loadSessions(activeTenantId).finally(() => setPageLoading(false));
  }, [activeTenantId, loadSessions]);

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
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Create failed';
      setFormErrors(prev => ({ ...prev, general: msg }));
    } finally {
      setCreating(false);
    }
  };

  // ── file picking ──────────────────────────────────────────────────────────

  const addFiles = useCallback(async (files: FileList | File[]) => {
    const arr = Array.from(files);
    const newEntries: PendingEntry[] = [];
    const tooLarge: string[] = [];

    for (const f of arr) {
      if (f.size > 100 * 1024 * 1024) {
        tooLarge.push(f.name);
        continue;
      }
      let previewCount: number | null = null;
      if (f.name.toLowerCase().endsWith('.csv')) {
        try { previewCount = countCsvRows(await f.text()); } catch { /* ok */ }
      }
      newEntries.push({ id: crypto.randomUUID(), file: f, label: f.name.replace(/\.[^.]+$/, ''), previewCount });
    }

    if (tooLarge.length > 0) {
      setUploadError(`Skipped ${tooLarge.length} file(s) exceeding 100MB: ${tooLarge.join(', ')}`);
    }
    setPendingEntries(prev => [...prev, ...newEntries]);
  }, []);

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
    if (emptyLabel) { setUploadError('All file labels are required.'); return; }

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
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Upload failed';
      setUploadError(msg);
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
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : 'Delete failed');
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
                  <input
                    className="up-input"
                    placeholder="e.g. Student, Finance, HR"
                    value={newDomain}
                    onChange={e => setNewDomain(e.target.value)}
                  />
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
                            <td><strong>{f.file_label}</strong></td>
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
                          <span className="up-dropzone__label">Drag &amp; drop CSV/JSON files here</span>
                          <span className="up-dropzone__sub">or click to browse — multiple files supported</span>
                          <input
                            ref={fileInputRef}
                            type="file"
                            accept=".csv,.json"
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
                                <div className="up-file-entry__meta">
                                  <span>📄 {fmtBytes(entry.file.size)}</span>
                                  {entry.previewCount != null && (
                                    <span className="up-file-entry__badge">~{entry.previewCount.toLocaleString()} rows</span>
                                  )}
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
                              type="file" accept=".csv,.json" multiple
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
                  <button className="up-btn up-btn--primary" onClick={() => void handleUpload()} disabled={uploading || pendingEntries.length === 0} type="button">
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
