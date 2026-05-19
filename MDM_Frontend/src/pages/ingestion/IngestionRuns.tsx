// MDM_Frontend/src/pages/ingestion/IngestionRuns.tsx
import React, { useState, useEffect, useRef, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import '../../styles/theme.css';
import '../../styles/IngestionRuns.css';
import {
    ingestionRunService,
    describeResolvedConfig,
    type IngestionResolvedConfig,
    type IngestionRunFileRead,
    type IngestionRunRecord,
    type RunStatus,
} from '../../services/ingestionRunService';
import { uploadSessionService, type UploadSession } from '../../services/uploadSessionService';
import { sourceService, type SourceRecord } from '../../services/sourceService';
import { authService } from '../../services/authService';
import { useTenantConfig } from '../../context/TenantConfigContext';
import TenantBreadcrumb from '../../components/TenantBreadcrumb';

/* ═══════════════════════════════════════════════════════════════
   TYPES
═══════════════════════════════════════════════════════════════ */
interface TimelineItem {
    label: string;
    ts: string;
    done?: boolean;
    active?: boolean;
    fail?: boolean;
}

interface RunError {
    code: string;
    msg: string;
}

interface StartIngestionData {
    tenantId: string;
    sourceId: string;
    sessionId: string;
}

interface ModalErrors {
    tenant?: string;
    source?: string;
    session?: string;
    resolve?: string;
}

/* ═══════════════════════════════════════════════════════════════
   CONSTANTS
═══════════════════════════════════════════════════════════════ */
const STATUSES: RunStatus[] = ["CREATED", "RUNNING", "RAW_LOADED", "STAGING_CREATED", "FAILED", "COMPLETED"];

const STATUS_LABEL: Record<RunStatus, string> = {
    CREATED: "Created", RUNNING: "Running", RAW_LOADED: "Raw Loaded",
    STAGING_CREATED: "Staging Created", FAILED: "Failed", COMPLETED: "Completed",
};

const RUN_TIMELINES: Record<RunStatus, TimelineItem[]> = {
    COMPLETED: [
        { label: "Run Created", ts: "Done", done: true },
        { label: "Files Ingested", ts: "Done", done: true },
        { label: "Raw Landing", ts: "Done", done: true },
        { label: "Staging Created", ts: "Done", done: true },
        { label: "Completed", ts: "Done", done: true },
    ],
    RUNNING: [
        { label: "Run Created", ts: "Done", done: true },
        { label: "Parsing upload session files…", ts: "In progress", active: true },
    ],
    FAILED: [{ label: "Run Created", ts: "Done", done: true }, { label: "Pipeline Failed", ts: "Failed", fail: true }],
    CREATED: [{ label: "Run Queued", ts: "Pending", done: false }],
    RAW_LOADED: [
        { label: "Run Created", ts: "Done", done: true },
        { label: "Raw Records Loaded", ts: "Done", done: true },
        { label: "Building staging…", ts: "Next", active: true },
    ],
    STAGING_CREATED: [
        { label: "Run Created", ts: "Done", done: true },
        { label: "Raw Loaded", ts: "Done", done: true },
        { label: "Staging Created", ts: "Done", done: true },
        { label: "Finalizing…", ts: "In progress", active: true },
    ],
};

const RUN_ERRORS: Partial<Record<RunStatus, RunError[]>> = {};

/* ─── Sub-components ────────────────────────────────────────── */
function StatusBadge({ status }: { status: RunStatus }): React.ReactElement {
    return (
        <span className={`ir-status ir-status--${status}`}>
            {STATUS_LABEL[status] || status}
        </span>
    );
}

/* ═══════════════════════════════════════════════════════════════
   START INGESTION MODAL
═══════════════════════════════════════════════════════════════ */
interface StartIngestionModalProps {
    onClose: () => void;
    onStart: (data: StartIngestionData) => void;
    sources: SourceRecord[];
    tenants: { id: string; tenantName: string }[];
    isSuperAdmin: boolean;
    activeTenantId: string | null;
    initialSessionId?: string | null;
    submitting: boolean;
}

function StartIngestionModal({
    onClose,
    onStart,
    sources,
    tenants,
    isSuperAdmin,
    activeTenantId,
    initialSessionId,
    submitting,
}: StartIngestionModalProps): React.ReactElement {
    const [tenantId, setTenantId] = useState<string>(activeTenantId || "");
    const [sourceId, setSourceId] = useState<string>("");
    const [sessionId, setSessionId] = useState<string>(initialSessionId || "");
    const [resolved, setResolved] = useState<IngestionResolvedConfig | null>(null);
    const [resolveLoading, setResolveLoading] = useState(false);
    const [sessions, setSessions] = useState<UploadSession[]>([]);
    const [sessionsLoading, setSessionsLoading] = useState(false);
    const [errors, setErrors] = useState<ModalErrors>({});

    useEffect(() => {
        if (activeTenantId) setTenantId(activeTenantId);
    }, [activeTenantId]);

    const effectiveTenantId = isSuperAdmin ? tenantId : (activeTenantId || tenantId);
    const showTenantSelector = isSuperAdmin;

    const filteredSources = effectiveTenantId
        ? sources.filter(s => s.tenantId === effectiveTenantId)
        : (isSuperAdmin ? [] : sources);

    const readySessions = sessions.filter(s => s.file_count > 0);
    const selectedSession = readySessions.find(s => s.session_id === sessionId);

    useEffect(() => {
        if (!effectiveTenantId) {
            setSessions([]);
            return;
        }
        let cancelled = false;
        setSessionsLoading(true);
        uploadSessionService.listSessions(effectiveTenantId)
            .then((list) => { if (!cancelled) setSessions(list); })
            .catch(() => { if (!cancelled) setSessions([]); })
            .finally(() => { if (!cancelled) setSessionsLoading(false); });
        return () => { cancelled = true; };
    }, [effectiveTenantId]);

    useEffect(() => {
        if (!sessionId || !sourceId || !effectiveTenantId) {
            setResolved(null);
            return;
        }
        let cancelled = false;
        setResolveLoading(true);
        setErrors((e) => ({ ...e, resolve: undefined }));
        ingestionRunService
            .resolveConfig(sessionId, sourceId, effectiveTenantId)
            .then((cfg) => { if (!cancelled) setResolved(cfg); })
            .catch((err) => {
                if (!cancelled) {
                    setResolved(null);
                    setErrors((e) => ({
                        ...e,
                        resolve: err instanceof Error ? err.message : "Could not resolve ingestion settings",
                    }));
                }
            })
            .finally(() => { if (!cancelled) setResolveLoading(false); });
        return () => { cancelled = true; };
    }, [sessionId, sourceId, effectiveTenantId]);

    const resolveHints = resolved ? describeResolvedConfig(resolved) : null;

    const handleSubmit = (): void => {
        const errs: ModalErrors = {};
        if (showTenantSelector && !tenantId) errs.tenant = "Target tenant is required";
        if (!sourceId) errs.source = "Source system is required";
        if (!sessionId) errs.session = "Select an upload session with files";
        if (!resolved) errs.resolve = errors.resolve || "Select session and source to load resolved settings";

        if (Object.keys(errs).length) { setErrors(errs); return; }
        onStart({
            tenantId: showTenantSelector ? tenantId : "",
            sourceId,
            sessionId,
        });
    };

    return (
        <div className="sim-overlay" onClick={onClose}>
            <div className="sim-modal" onClick={(e: React.MouseEvent) => e.stopPropagation()} role="dialog" aria-modal="true">
                <div className="sim-header">
                    <div>
                        <h2 className="sim-header__title">Start Ingestion Run</h2>
                        <p className="sim-header__sub">
                            Pick upload session + source — entity, run type, and trigger are resolved automatically
                        </p>
                    </div>
                    <button className="sim-close" onClick={onClose}>✕</button>
                </div>

                <div className="sim-body">
                    <div className="sim-section">
                        <div className="sim-field-grid">
                            {showTenantSelector && (
                                <div className={`sim-field sim-field--full${errors.tenant ? " sim-field--error" : ""}`}>
                                    <label className="sim-label">Target Tenant <span className="sim-required">*</span></label>
                                    <select 
                                        className="sim-select" 
                                        value={tenantId} 
                                        onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
                                            setTenantId(e.target.value);
                                            setSourceId(""); // Reset source when tenant changes
                                        }}
                                    >
                                        <option value="">— Select tenant —</option>
                                        {tenants.map(t => <option key={t.id} value={t.id}>{t.tenantName}</option>)}
                                    </select>
                                    {errors.tenant && <span className="sim-error-msg">{errors.tenant}</span>}
                                </div>
                            )}

                            <div className={`sim-field sim-field--full${errors.source ? " sim-field--error" : ""}`}>
                                <label className="sim-label">Source System <span className="sim-required">*</span></label>
                                <select 
                                    className="sim-select" 
                                    value={sourceId} 
                                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSourceId(e.target.value)}
                                    disabled={showTenantSelector && !tenantId}
                                >
                                    <option value="">{showTenantSelector && !tenantId ? "— Select tenant first —" : "— Select source —"}</option>
                                    {filteredSources.map(s => <option key={s.id} value={s.id}>{s.sourceName}</option>)}
                                </select>
                                {errors.source && <span className="sim-error-msg">{errors.source}</span>}
                            </div>

                            <div className={`sim-field sim-field--full${errors.session ? " sim-field--error" : ""}`}>
                                <label className="sim-label">Upload Session <span className="sim-required">*</span></label>
                                <select
                                    className="sim-select"
                                    value={sessionId}
                                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
                                        setSessionId(e.target.value);
                                        setResolved(null);
                                    }}
                                    disabled={!effectiveTenantId || sessionsLoading}
                                >
                                    <option value="">
                                        {!effectiveTenantId
                                            ? "— Select tenant first —"
                                            : sessionsLoading
                                                ? "— Loading sessions… —"
                                                : readySessions.length === 0
                                                    ? "— No sessions with files (upload first) —"
                                                    : "— Select session —"}
                                    </option>
                                    {readySessions.map(s => (
                                        <option key={s.session_id} value={s.session_id}>
                                            {s.session_name} · {s.domain} · {s.file_count} file{s.file_count !== 1 ? "s" : ""}
                                        </option>
                                    ))}
                                </select>
                                {errors.session && <span className="sim-error-msg">{errors.session}</span>}
                                {selectedSession && (
                                    <div className="ir-session-preview">
                                        <span>Domain: <strong>{selectedSession.domain}</strong></span>
                                        <span>{selectedSession.file_count} file(s) ready for ingestion</span>
                                    </div>
                                )}
                            </div>

                            <div className={`sim-field sim-field--full${errors.resolve ? " sim-field--error" : ""}`}>
                                <label className="sim-label">Resolved configuration</label>
                                {resolveLoading && (
                                    <p className="ir-resolve-hint">Resolving entity, run type, and trigger…</p>
                                )}
                                {!resolveLoading && resolved && resolveHints && (
                                    <div className="ir-resolve-panel">
                                        <div className="ir-resolve-row">
                                            <span className="ir-resolve-label">Entity</span>
                                            <span className="ir-entity-chip">{resolved.entity_type}</span>
                                            <span className="ir-resolve-note">{resolveHints.entityHint}</span>
                                        </div>
                                        <div className="ir-resolve-row">
                                            <span className="ir-resolve-label">Run type</span>
                                            <span className="ir-run-type">{resolved.run_type}</span>
                                            <span className="ir-resolve-note">{resolveHints.runTypeHint}</span>
                                        </div>
                                        <div className="ir-resolve-row">
                                            <span className="ir-resolve-label">Trigger</span>
                                            <span className="ir-run-type">{resolved.trigger_type}</span>
                                            <span className="ir-resolve-note">{resolveHints.triggerHint}</span>
                                        </div>
                                        {resolved.supported_entities.length > 0 && (
                                            <p className="ir-resolve-hint">
                                                Source allows: {resolved.supported_entities.join(", ")}
                                            </p>
                                        )}
                                    </div>
                                )}
                                {!resolveLoading && sessionId && sourceId && !resolved && (
                                    <p className="ir-resolve-hint ir-resolve-hint--warn">
                                        {errors.resolve || "Could not resolve settings — check session domain matches the source."}
                                    </p>
                                )}
                                {(!sessionId || !sourceId) && (
                                    <p className="ir-resolve-hint">Select both session and source to preview auto-resolved settings.</p>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                <div className="sim-footer">
                    <button className="sim-btn sim-btn--ghost" onClick={onClose}>Cancel</button>
                    <div className="sim-footer__right">
                        <button
                            className="sim-btn sim-btn--primary"
                            onClick={handleSubmit}
                            disabled={submitting || resolveLoading || !resolved}
                        >
                            {submitting ? "Starting pipeline…" : "▶ Start Ingestion"}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

/* ═══════════════════════════════════════════════════════════════
   RUN DETAILS DRAWER
═══════════════════════════════════════════════════════════════ */
type DrawerTab = "overview" | "files" | "timeline" | "errors";

interface RunDetailsDrawerProps {
    run: IngestionRunRecord;
    tenantIdForApi: string | undefined;
    isSuperAdmin: boolean;
    onClose: () => void;
    onViewRawLanding: (runId: string) => void;
}

function formatFriendlyDate(iso: string | null): string {
    if (!iso) return '—';
    const d = new Date(iso.replace(' ', 'T'));
    if (Number.isNaN(d.getTime())) return iso;
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

function formatBytes(n: number | null | undefined): string {
    if (n == null) return '—';
    if (n < 1024) return `${n} B`;
    if (n < 1048576) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / 1048576).toFixed(2)} MB`;
}

function RunDetailsDrawer({ run, tenantIdForApi, isSuperAdmin, onClose, onViewRawLanding }: RunDetailsDrawerProps): React.ReactElement {
    const [tab, setTab] = useState<DrawerTab>("overview");
    const [isCancelling, setIsCancelling] = useState(false);
    const [files, setFiles] = useState<IngestionRunFileRead[] | null>(null);
    const [filesLoading, setFilesLoading] = useState(false);
    const [filesError, setFilesError] = useState<string | null>(null);
    const timeline: TimelineItem[] = RUN_TIMELINES[run.state] || RUN_TIMELINES["CREATED"];
    const errors: RunError[] = RUN_ERRORS[run.state] || [];

    useEffect(() => {
        if (tab !== 'files' || files != null) return;
        let cancelled = false;
        setFilesLoading(true);
        setFilesError(null);
        ingestionRunService
            .listRunFiles(run.id, tenantIdForApi)
            .then((rows) => { if (!cancelled) setFiles(rows); })
            .catch((err) => {
                if (!cancelled) setFilesError(err instanceof Error ? err.message : 'Failed to load files');
            })
            .finally(() => { if (!cancelled) setFilesLoading(false); });
        return () => { cancelled = true; };
    }, [tab, files, run.id, tenantIdForApi]);

    const duplicateFileCount = files ? files.filter((f) => f.is_duplicate).length : 0;
    const deletedFileCount = files ? files.filter((f) => f.deleted_at).length : 0;

    const handleCancel = async () => {
        if (!window.confirm("Are you sure you want to stop this ingestion run?")) return;
        setIsCancelling(true);
        try {
            await ingestionRunService.cancelRun(run.id, tenantIdForApi);
            onClose();
        } catch (err) {
            alert(err instanceof Error ? err.message : "Failed to cancel run");
        } finally {
            setIsCancelling(false);
        }
    };

    return (
        <div className="ir-drawer-overlay" onClick={onClose}>
            <div className="ir-drawer" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
                <div className="ir-drawer__header">
                    <div>
                        <h2 className="ir-drawer__title">{run.sourceName}</h2>
                        <div className="ir-drawer__sub">{run.id}</div>
                    </div>
                    <button className="ir-drawer__close" onClick={onClose}>✕</button>
                </div>

                <div className="ir-drawer-tabs">
                    {([
                        ["overview", "Overview"],
                        ["files", "Files"],
                        ["timeline", "Timeline"],
                        ["errors", "Errors"],
                    ] as [DrawerTab, string][]).map(([key, label]) => (
                        <button key={key} className={`ir-drawer-tab${tab === key ? " ir-drawer-tab--active" : ""}`} onClick={() => setTab(key)}>
                            {label}
                            {key === "errors" && errors.length > 0 && <span style={{ marginLeft: 4, background: "var(--red-500)", color: "#fff", borderRadius: 99, fontSize: 10, padding: "1px 5px", fontWeight: 700 }}>{errors.length}</span>}
                            {key === "files" && (duplicateFileCount > 0 || deletedFileCount > 0) && (
                                <span
                                    style={{
                                        marginLeft: 4,
                                        background: duplicateFileCount > 0 ? "var(--amber-500)" : "var(--red-500)",
                                        color: "#fff",
                                        borderRadius: 99,
                                        fontSize: 10,
                                        padding: "1px 5px",
                                        fontWeight: 700,
                                    }}
                                    title={`${duplicateFileCount} duplicate · ${deletedFileCount} deleted`}
                                >
                                    {duplicateFileCount + deletedFileCount}
                                </span>
                            )}
                        </button>
                    ))}
                </div>

                <div className="ir-drawer__body">
                    {/* Overview tab */}
                    {tab === "overview" && (
                        <div className="ir-drawer__content">
                            <div className="ir-drawer__grid">
                                <div className="ir-drawer__field">
                                    <span className="ir-drawer__field-label">Tenant</span>
                                    <span className="ir-drawer__field-value">
                                        {run.tenantName || run.tenantId.slice(0, 8) + "…"}
                                    </span>
                                </div>
                                <div className="ir-drawer__field">
                                    <span className="ir-drawer__field-label">Status</span>
                                    <StatusBadge status={run.state} />
                                </div>
                                <div className="ir-drawer__field">
                                    <span className="ir-drawer__field-label">Entity / Run</span>
                                    <span className="ir-drawer__field-value">
                                        {run.entityType || "—"} · {run.runType || "—"}
                                    </span>
                                </div>
                                <div className="ir-drawer__field">
                                    <span className="ir-drawer__field-label">Trigger</span>
                                    <span className="ir-drawer__field-value">{run.triggerType || "—"}</span>
                                </div>
                                <div className="ir-drawer__field">
                                    <span className="ir-drawer__field-label">Initiated By</span>
                                    <span className="ir-drawer__field-value">{run.initiatedBy || run.triggeredBy || "—"}</span>
                                </div>
                                <div className="ir-drawer__field">
                                    <span className="ir-drawer__field-label">Started At</span>
                                    <span className="ir-drawer__field-value" style={{ fontSize: 12.5 }}>{run.startedAt || "—"}</span>
                                </div>
                                <div className="ir-drawer__field">
                                    <span className="ir-drawer__field-label">Completed At</span>
                                    <span className="ir-drawer__field-value" style={{ fontSize: 12.5 }}>{run.completedAt || "—"}</span>
                                </div>
                            </div>

                             <div>
                                <span className="ir-drawer__field-label" style={{ display: "block", marginBottom: 10 }}>Record Counts</span>
                                <div className="ir-drawer__counts">
                                    <div className="ir-drawer__count-card">
                                        <span className="ir-drawer__count-val">{run.recordCount.toLocaleString()}</span>
                                        <span className="ir-drawer__count-lbl">Total Raw Records</span>
                                    </div>
                                    <div className="ir-drawer__count-card">
                                        <span className="ir-drawer__count-val ir-drawer__count-val--loaded">{run.fileCount}</span>
                                        <span className="ir-drawer__count-lbl">Files Uploaded</span>
                                    </div>
                                </div>
                            </div>

                            {run.errorMessage && (
                                <div style={{ marginTop: 20, padding: 12, background: "var(--red-500-10)", borderRadius: 8, border: "1px solid var(--red-500-20)" }}>
                                    <span className="ir-drawer__field-label" style={{ color: "var(--red-500)", display: "block", marginBottom: 4 }}>Error Message</span>
                                    <p style={{ margin: 0, fontSize: 13, color: "var(--text-primary)" }}>{run.errorMessage}</p>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Files tab */}
                    {tab === "files" && (
                        <div className="ir-drawer__content">
                            {filesLoading && (
                                <div className="ir-files-empty">⏳ Loading files…</div>
                            )}
                            {filesError && !filesLoading && (
                                <div className="ir-files-empty" style={{ color: "var(--red-500)" }}>{filesError}</div>
                            )}
                            {!filesLoading && !filesError && files != null && files.length === 0 && (
                                <div className="ir-files-empty">No files attached to this run.</div>
                            )}
                            {!filesLoading && !filesError && files != null && files.length > 0 && (
                                <>
                                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
                                        <span className="ir-file-badge ir-file-badge--ok">{files.length} file{files.length !== 1 ? "s" : ""}</span>
                                        {duplicateFileCount > 0 && (
                                            <span className="ir-file-badge ir-file-badge--dup">⚠ {duplicateFileCount} duplicate{duplicateFileCount !== 1 ? "s" : ""}</span>
                                        )}
                                        {deletedFileCount > 0 && (
                                            <span className="ir-file-badge ir-file-badge--deleted">🗑 {deletedFileCount} deleted</span>
                                        )}
                                    </div>
                                    <div className="ir-files-table-wrap">
                                        <table className="ir-files-table">
                                            <thead>
                                                <tr>
                                                    <th>File</th>
                                                    <th>Size</th>
                                                    <th>Uploaded by</th>
                                                    <th>Uploaded at</th>
                                                    <th>Status</th>
                                                    <th>Deletion</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {files.map((f) => {
                                                    const isDeleted = !!f.deleted_at;
                                                    return (
                                                        <tr
                                                            key={f.file_id}
                                                            className={isDeleted ? "ir-files-table__row--deleted" : undefined}
                                                        >
                                                            <td>
                                                                <div className="ir-files-table__filename">{f.original_filename}</div>
                                                                <div className="ir-files-table__meta">
                                                                    {f.content_type || "file"} · {f.checksum_md5 ? f.checksum_md5.slice(0, 10) + "…" : "no checksum"}
                                                                </div>
                                                                {f.is_duplicate && (
                                                                    <div className="ir-dup-note">
                                                                        <span className="ir-dup-note__strong">⚠ Duplicate upload.</span>{" "}
                                                                        First uploaded by{" "}
                                                                        <span className="ir-dup-note__strong">{f.first_uploaded_by || "unknown"}</span>
                                                                        {f.first_uploaded_at ? <> on <span className="ir-dup-note__strong">{formatFriendlyDate(f.first_uploaded_at)}</span></> : null}
                                                                        {f.first_uploaded_run_id ? <> (run <code>{f.first_uploaded_run_id.slice(0, 8)}…</code>)</> : null}.
                                                                    </div>
                                                                )}
                                                            </td>
                                                            <td>{formatBytes(f.file_size_bytes)}</td>
                                                            <td>
                                                                <span className="ir-files-table__user">{f.uploaded_by || "—"}</span>
                                                            </td>
                                                            <td>
                                                                <span className="ir-files-table__meta">{formatFriendlyDate(f.uploaded_at)}</span>
                                                            </td>
                                                            <td>
                                                                {isDeleted ? (
                                                                    <span className="ir-file-badge ir-file-badge--deleted">DELETED</span>
                                                                ) : f.is_duplicate ? (
                                                                    <span className="ir-file-badge ir-file-badge--dup">DUPLICATE</span>
                                                                ) : (
                                                                    <span className="ir-file-badge ir-file-badge--ok">ACTIVE</span>
                                                                )}
                                                            </td>
                                                            <td>
                                                                {isDeleted ? (
                                                                    <>
                                                                        <div className="ir-files-table__user">{f.deleted_by || "unknown"}</div>
                                                                        <div className="ir-files-table__meta">{formatFriendlyDate(f.deleted_at)}</div>
                                                                    </>
                                                                ) : (
                                                                    <span className="ir-files-table__meta">—</span>
                                                                )}
                                                            </td>
                                                        </tr>
                                                    );
                                                })}
                                            </tbody>
                                        </table>
                                    </div>
                                    <p className="ir-files-table__meta" style={{ marginTop: 10 }}>
                                        Upload and deletion history comes from the audit log. Duplicate detection compares MD5 checksum across all files within {isSuperAdmin && run.tenantName ? <strong>{run.tenantName}</strong> : "this tenant"}.
                                    </p>
                                </>
                            )}
                        </div>
                    )}

                    {/* Timeline tab */}
                    {tab === "timeline" && (
                        <div className="ir-drawer__content">
                            <div className="ir-timeline">
                                {timeline.map((item, i) => (
                                    <div key={i} className="ir-timeline__item">
                                        <div className={`ir-timeline__dot${item.done ? " ir-timeline__dot--done" : ""}${item.active ? " ir-timeline__dot--active" : ""}${item.fail ? " ir-timeline__dot--fail" : ""}`}>
                                            {item.done ? "✓" : item.fail ? "✕" : i + 1}
                                        </div>
                                        <div className="ir-timeline__body">
                                            <div className="ir-timeline__label">{item.label}</div>
                                            <div className="ir-timeline__ts">{item.ts}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Errors tab */}
                    {tab === "errors" && (
                        <div className="ir-drawer__content">
                            {errors.length === 0
                                ? <div className="ir-no-errors">✓ No errors recorded for this run</div>
                                : <div className="ir-error-list">
                                    {errors.map((err, i) => (
                                        <div key={i} className="ir-error-item">
                                            <div className="ir-error-item__code">{err.code}</div>
                                            {err.msg}
                                        </div>
                                    ))}
                                </div>
                            }
                        </div>
                    )}
                </div>
                <div className="ir-drawer-footer" style={{ padding: "16px 24px", borderTop: "1px solid var(--border-color)", display: "flex", justifyContent: "flex-end", gap: 12, background: "var(--bg-primary)" }}>
                    {(run.state === "RUNNING" || run.state === "CREATED" || run.state === "RAW_LOADED") && (
                        <button 
                            className="ird-action-btn ird-action-btn--danger" 
                            onClick={handleCancel}
                            disabled={isCancelling}
                            style={{ marginRight: "auto", background: "var(--red-500-10)", color: "var(--red-500)", border: "1px solid var(--red-500-20)", padding: "8px 16px", borderRadius: 6, fontWeight: 600, cursor: "pointer" }}
                        >
                            {isCancelling ? "Stopping…" : "Stop Ingestion"}
                        </button>
                    )}
                    {(run.state === "RAW_LOADED" || run.state === "STAGING_CREATED" || run.state === "COMPLETED") && run.recordCount > 0 && (
                        <button
                            type="button"
                            className="ird-action-btn"
                            onClick={() => onViewRawLanding(run.id)}
                            style={{ marginRight: "auto", padding: "8px 16px", borderRadius: 6, border: "1px solid var(--blue-500-30)", background: "var(--blue-500-10)", color: "var(--blue-600)", fontWeight: 600, cursor: "pointer" }}
                        >
                            View Raw Landing →
                        </button>
                    )}
                    <button className="ird-action-btn" onClick={onClose} style={{ padding: "8px 16px", borderRadius: 6, border: "1px solid var(--border-color)", background: "var(--bg-secondary)", color: "var(--text-primary)", fontWeight: 600, cursor: "pointer" }}>Close</button>
                </div>
            </div>
        </div>
    );
}

/* ═══════════════════════════════════════════════════════════════
   INGESTION RUNS PAGE
═══════════════════════════════════════════════════════════════ */
function IngestionRuns(): React.ReactElement {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const { activeTenantId, activeTenantName, mode: tenantMode } = useTenantConfig();
    const [runs, setRuns] = useState<IngestionRunRecord[]>([]);
    const [sources, setSources] = useState<SourceRecord[]>([]);
    const [isSuperAdmin, setIsSuperAdmin] = useState<boolean>(false);
    const [loading, setLoading] = useState<boolean>(true);
    const [starting, setStarting] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [showModal, setShowModal] = useState<boolean>(false);
    const [viewRun, setViewRun] = useState<IngestionRunRecord | null>(null);
    const [search, setSearch] = useState<string>("");
    const [filterStatus, setFilterStatus] = useState<string>("ALL");
    const [filterSource, setFilterSource] = useState<string>("ALL");
    const [deletingRunId, setDeletingRunId] = useState<string | null>(null);
    const refreshRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const sessionIdFromUrl = searchParams.get("sessionId");

    useEffect(() => {
        if (sessionIdFromUrl) {
            setShowModal(true);
        }
    }, [sessionIdFromUrl]);

    const loadData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const adminInfo = authService.getAdminInfoFromCookie();
            const superAdmin = adminInfo?.tenant_id === 'platform';
            setIsSuperAdmin(superAdmin);

            const tId = activeTenantId ?? undefined;

            const srcData = await sourceService.listSources(0, 100, tId);
            setSources(srcData);

            const nameMap: Record<string, string> = {};
            srcData.forEach(s => { nameMap[s.id] = s.sourceName; });

            const runData = await ingestionRunService.listRuns(0, 50, nameMap, tId);
            setRuns(runData);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load ingestion data");
        } finally {
            setLoading(false);
        }
    }, [activeTenantId]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    /* Auto-refresh every 5s for active pipeline jobs */
    useEffect(() => {
        refreshRef.current = setInterval(() => {
            const hasActive = runs.some(r =>
                r.state === "RUNNING" || r.state === "CREATED" || r.state === "RAW_LOADED" || r.state === "STAGING_CREATED"
            );
            if (hasActive) {
                loadData();
            }
        }, 5000);
        return () => {
            if (refreshRef.current) clearInterval(refreshRef.current);
        };
    }, [runs, loadData]);

    const filtered = runs.filter(r => {
        const q = search.toLowerCase();
        return (
            (r.id.toLowerCase().includes(q) || r.sourceName.toLowerCase().includes(q)) &&
            (filterStatus === "ALL" || r.state === filterStatus) &&
            (filterSource === "ALL" || r.sourceId === filterSource)
        );
    });

    const handleStart = async (data: StartIngestionData): Promise<void> => {
        setStarting(true);
        const tId = isSuperAdmin ? data.tenantId : (activeTenantId ?? undefined);
        try {
            const newRun = await ingestionRunService.startRunFromSession(
                {
                    source_system_id: data.sourceId,
                    upload_session_id: data.sessionId,
                    triggered_by: "user",
                },
                tId,
            );

            setShowModal(false);
            await loadData();
            setViewRun(newRun);

            await ingestionRunService.waitForRun(newRun.id, tId, {
                intervalMs: 3000,
                timeoutMs: 240_000,
                onTick: (updated) => setViewRun(updated),
            });
            await loadData();
        } catch (err) {
            const msg = err instanceof Error ? err.message : String(err);
            if (msg.includes("SuperAdmin must provide")) {
                setIsSuperAdmin(true);
                alert("Platform Admin: select a target tenant, then try again.");
                return;
            }
            if (msg.includes("no files") || msg.includes("Upload session has no files")) {
                alert("That session has no files. Upload data on the Upload Data screen first.");
                return;
            }
            alert(msg);
        } finally {
            setStarting(false);
        }
    };

    const goToRawLanding = (runId: string) => {
        navigate(`/raw-landing?runId=${encodeURIComponent(runId)}`);
    };

    const handleDeleteRun = async (run: IngestionRunRecord) => {
        if (run.state === "RUNNING") {
            alert("This run is still processing. Wait for it to finish or cancel it first.");
            return;
        }
        if (!window.confirm("Delete this ingestion run and all of its raw and staging records? This cannot be undone.")) {
            return;
        }
        const tId = isSuperAdmin ? activeTenantId ?? undefined : (activeTenantId ?? undefined);
        setDeletingRunId(run.id);
        try {
            await ingestionRunService.deleteRun(run.id, tId);
            if (viewRun?.id === run.id) setViewRun(null);
            await loadData();
        } catch (err) {
            alert(err instanceof Error ? err.message : "Failed to delete run");
        } finally {
            setDeletingRunId(null);
        }
    };

    /* Summary counts */
    const total = runs.length;
    const running = runs.filter(r => r.state === "RUNNING").length;
    const completed = runs.filter(r => r.state === "COMPLETED").length;
    const failed = runs.filter(r => r.state === "FAILED").length;
    const stagingCreated = runs.filter(r => r.state === "STAGING_CREATED").length;
    const rawLoaded = runs.filter(r => r.state === "RAW_LOADED").length;

    return (
        <div className="ir-page">
            {/* Tenant hierarchy breadcrumb */}
            <TenantBreadcrumb screen="Ingestion Runs" />

            {/* Header */}
            <div className="ir-page-header">
                <div>
                    <h1 className="ir-page-title">
                        Ingestion Runs 
                        {isSuperAdmin && <span style={{ marginLeft: 12, fontSize: 11, background: "var(--blue-500)", color: "#fff", padding: "2px 8px", borderRadius: 4, verticalAlign: "middle", letterSpacing: 0.5 }}>PLATFORM VIEW</span>}
                    </h1>
                    <p className="ir-page-subtitle">Start runs from Upload Data sessions, then track raw load and staging</p>
                </div>
                <div className="ir-page-header__actions">
                    <div className="ir-refresh-badge">
                        <span className="ir-refresh-dot" />
                        Auto-refresh: 10s
                    </div>
                    <button className="ir-btn ir-btn--ghost" onClick={loadData} disabled={loading}>
                        {loading ? "…" : "↻"} Refresh
                    </button>
                    <button className="ir-btn ir-btn--primary" onClick={() => setShowModal(true)}>▶ Start Ingestion</button>
                </div>
            </div>

            {/* Error Banner */}
            {error && (
                <div style={{ background: "var(--red-500-10)", color: "var(--red-500)", padding: "12px 16px", borderRadius: 8, marginBottom: 20, border: "1px solid var(--red-500-20)", display: "flex", alignItems: "center", gap: 10 }}>
                    <span>⚠</span>
                    <span>{error}</span>
                </div>
            )}

            {/* Summary Cards */}
            <div className="ir-summary-row">
                <div className="ir-summary-card"><span className="ir-summary-card__value">{total}</span><span className="ir-summary-card__label">Total Runs</span></div>
                <div className="ir-summary-card ir-summary-card--blue"><span className="ir-summary-card__value">{running}</span><span className="ir-summary-card__label">Running</span></div>
                <div className="ir-summary-card ir-summary-card--green"><span className="ir-summary-card__value">{completed}</span><span className="ir-summary-card__label">Completed</span></div>
                <div className="ir-summary-card ir-summary-card--red"><span className="ir-summary-card__value">{failed}</span><span className="ir-summary-card__label">Failed</span></div>
                <div className="ir-summary-card ir-summary-card--cyan"><span className="ir-summary-card__value">{rawLoaded}</span><span className="ir-summary-card__label">Raw Loaded</span></div>
                <div className="ir-summary-card ir-summary-card--purple"><span className="ir-summary-card__value">{stagingCreated}</span><span className="ir-summary-card__label">Staging Created</span></div>
            </div>

            {/* Table */}
            <div className="ir-table-card">
                <div className="ir-table-toolbar">
                    <div className="ir-search-wrap">
                        <span className="ir-search-icon">🔍</span>
                        <input className="ir-search-input" placeholder="Search by run ID, source, entity…" value={search} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearch(e.target.value)} />
                    </div>
                    <div className="ir-filter-row">
                        {isSuperAdmin && tenantMode === 'SPECIFIC' && activeTenantName && (
                            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--blue-600)', background: 'var(--blue-100)', padding: '4px 10px', borderRadius: 99, border: '1px solid var(--blue-200)' }}>
                                🏢 {activeTenantName}
                            </span>
                        )}
                        <select className="ir-select" value={filterSource} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFilterSource(e.target.value)}>
                            <option value="ALL">All Sources</option>
                            {sources.map(s => <option key={s.id} value={s.id}>{s.sourceName}</option>)}
                        </select>
                        <select className="ir-select" value={filterStatus} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFilterStatus(e.target.value)}>
                            <option value="ALL">All Statuses</option>
                            {STATUSES.map(s => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
                        </select>
                        <span className="ir-count-label">{filtered.length} record{filtered.length !== 1 ? "s" : ""}</span>
                    </div>
                </div>

                <div className="ir-table-wrap">
                    <table className="ir-table">
                        <thead>
                            <tr>
                                <th>Run ID</th>
                                {isSuperAdmin && <th>Tenant</th>}
                                <th>Source System</th>
                                <th>Entity</th>
                                <th>Run Type</th>
                                <th>Status</th>
                                <th>Files</th>
                                <th>Records</th>
                                <th>Started At</th>
                                <th>Completed At</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.length === 0 ? (
                                <tr><td colSpan={isSuperAdmin ? 11 : 10} className="ir-table-empty"><span>📋</span><p>No ingestion runs found</p></td></tr>
                            ) : filtered.map(run => (
                                <tr key={run.id} className="ir-table-row" onClick={() => setViewRun(run)}>
                                    <td><code className="ir-run-id">{run.id.slice(0, 8)}…</code></td>
                                    {isSuperAdmin && (
                                        <td>
                                            <span
                                                className={`ir-tenant-chip${run.tenantName ? "" : " ir-tenant-chip--muted"}`}
                                                title={run.tenantId}
                                            >
                                                🏢 {run.tenantName || run.tenantId.slice(0, 8) + "…"}
                                            </span>
                                        </td>
                                    )}
                                    <td>
                                        <div className="ir-source-cell">
                                            <div className="ir-source-avatar">{run.sourceName.slice(0, 2).toUpperCase()}</div>
                                            <span className="ir-source-name">{run.sourceName}</span>
                                        </div>
                                    </td>
                                    <td><span className="ir-entity-chip">{run.entityType || "—"}</span></td>
                                    <td><span className="ir-run-type">{run.runType || "—"}</span></td>
                                    <td><StatusBadge status={run.state} /></td>
                                    <td><span className="ir-count-cell">{run.fileCount}</span></td>
                                    <td><span className="ir-count-cell">{run.recordCount > 0 ? run.recordCount.toLocaleString() : <span className="ir-count-cell--muted">—</span>}</span></td>
                                    <td><span className="ir-ts">{run.startedAt || "—"}</span></td>
                                    <td><span className={run.completedAt ? "ir-ts" : "ir-ts-na"}>{run.completedAt || "—"}</span></td>
                                    <td onClick={(e: React.MouseEvent) => e.stopPropagation()}>
                                        <div className="ir-action-row">
                                            <button type="button" className="ir-action-btn ir-action-btn--primary" onClick={() => setViewRun(run)}>Details</button>
                                            <button
                                                type="button"
                                                className="ir-action-btn ir-action-btn--danger"
                                                disabled={deletingRunId === run.id || run.state === "RUNNING"}
                                                title={run.state === "RUNNING" ? "Cannot delete while pipeline is running" : "Delete run and all raw/staging data"}
                                                onClick={() => void handleDeleteRun(run)}
                                            >
                                                {deletingRunId === run.id ? "…" : "Delete"}
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Run Details Drawer */}
            {viewRun && (
                <RunDetailsDrawer
                    run={viewRun}
                    tenantIdForApi={isSuperAdmin ? (activeTenantId ?? viewRun.tenantId) : (activeTenantId ?? undefined)}
                    isSuperAdmin={isSuperAdmin}
                    onClose={() => setViewRun(null)}
                    onViewRawLanding={goToRawLanding}
                />
            )}

            {/* Start Ingestion Modal */}
            {showModal && (
                <StartIngestionModal
                    onClose={() => setShowModal(false)}
                    onStart={handleStart}
                    sources={sources}
                    tenants={[]}
                    isSuperAdmin={isSuperAdmin}
                    activeTenantId={activeTenantId}
                    initialSessionId={sessionIdFromUrl}
                    submitting={starting}
                />
            )}
        </div>
    );
}

export default IngestionRuns;