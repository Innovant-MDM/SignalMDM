// MDM_Frontend/src/pages/rawlanding/RawLanding.tsx
import {
    useState,
    useEffect,
    useCallback,
    useMemo,
    type ChangeEvent,
    type MouseEvent,
} from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import IngestionRunLineagePicker from '../../components/ingestion/IngestionRunLineagePicker';
import TenantBreadcrumb from '../../components/TenantBreadcrumb';
import { formatRunOptionLabel, resolveInitialRunId } from '../../utils/ingestionRunScope';
import '../../styles/theme.css';
import '../../styles/RawLanding.css';


import { sourceService, ENTITY_TYPES, type SourceRecord } from '../../services/sourceService';
import {
    ingestionRunService,
    type IngestionLineageRunSummary,
} from '../../services/ingestionRunService';
import { useTenantConfig } from '../../context/TenantConfigContext';
import {
    rawLandingService,
    toRawLandingRecord,
    type RawLandingRecord,
    type RawProcessingStatus,
} from '../../services/rawLandingService';
import { ApiError } from '../../services/api';

type ModalTab = 'payload' | 'metadata';
type PayloadValue = string | number | boolean | null;

const PROC_STATUSES: RawProcessingStatus[] = [
    'PENDING',
    'PROCESSING',
    'COMPLETED',
    'FAILED',
    'DUPLICATE',
];

const PROC_LABELS: Record<RawProcessingStatus, string> = {
    PENDING: 'Pending',
    PROCESSING: 'Processing',
    COMPLETED: 'Completed',
    FAILED: 'Failed',
    DUPLICATE: 'Duplicate',
};

const PAGE_SIZE = 25;

interface PayloadModalProps {
    record: RawLandingRecord;
    onClose: () => void;
    initialTab?: ModalTab;
}

function coloriseJSON(obj: Record<string, PayloadValue>): string {
    const str = JSON.stringify(obj, null, 2);
    return str.replace(
        /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
        (match) => {
            let cls = 'rl-json-num';
            if (/^"/.test(match)) {
                if (/:$/.test(match)) cls = 'rl-json-key';
                else cls = 'rl-json-str';
            } else if (/true|false/.test(match)) cls = 'rl-json-bool';
            else if (/null/.test(match)) cls = 'rl-json-null';
            return `<span class="${cls}">${match}</span>`;
        },
    );
}

function PayloadModal({ record, onClose, initialTab = 'payload' }: PayloadModalProps) {
    const [tab, setTab] = useState<ModalTab>(initialTab);
    const [copied, setCopied] = useState(false);

    const handleCopy = () => {
        void navigator.clipboard.writeText(JSON.stringify(record.payload, null, 2)).catch(() => { });
        setCopied(true);
        setTimeout(() => setCopied(false), 1800);
    };

    const modalTabs: Array<[ModalTab, string]> = [
        ['payload', 'Payload'],
        ['metadata', 'Metadata'],
    ];

    return (
        <div className="rl-modal-overlay" onClick={onClose}>
            <div
                className="rl-modal"
                onClick={(e: MouseEvent<HTMLDivElement>) => e.stopPropagation()}
                role="dialog"
                aria-modal="true"
            >
                <div className="rl-modal__header">
                    <div>
                        <h2 className="rl-modal__title">
                            {record.srcId} — {record.entity}
                        </h2>
                        <div className="rl-modal__sub">
                            {record.id} · {record.source}
                        </div>
                    </div>
                    <button type="button" className="rl-modal__close" onClick={onClose}>
                        ✕
                    </button>
                </div>

                <div className="rl-modal-tabs">
                    {modalTabs.map(([key, label]) => (
                        <button
                            key={key}
                            type="button"
                            className={`rl-modal-tab${tab === key ? ' rl-modal-tab--active' : ''}`}
                            onClick={() => setTab(key)}
                        >
                            {label}
                        </button>
                    ))}
                </div>

                <div className="rl-modal__body">
                    {tab === 'payload' && (
                        <>
                            <div className="rl-json-toolbar">
                                <button
                                    type="button"
                                    className={`rl-copy-btn${copied ? ' rl-copy-btn--copied' : ''}`}
                                    onClick={handleCopy}
                                >
                                    {copied ? '✓ Copied!' : '⎘ Copy JSON'}
                                </button>
                            </div>
                            <div
                                className="rl-json-viewer"
                                dangerouslySetInnerHTML={{ __html: coloriseJSON(record.payload) }}
                            />
                        </>
                    )}

                    {tab === 'metadata' && (
                        <div className="rl-meta-grid">
                            {record.isDuplicate && (
                                <div className="rl-meta-callout">
                                    <div className="rl-meta-callout__title">
                                        ⚠ Duplicate record ({record.duplicateScope === 'CROSS_RUN' ? 'cross-run' : 'within run'})
                                    </div>
                                    This payload has the same MD5 checksum as an earlier raw record in this tenant.
                                    {' '}First added by <strong>{record.firstSeenBy || 'unknown'}</strong>
                                    {record.firstSeenAt ? <> on <strong>{record.firstSeenAt}</strong></> : null}
                                    {record.duplicateOfRawId ? <> (raw id <code>{record.duplicateOfRawId.slice(0, 8)}…</code></> : null}
                                    {record.duplicateOfRawId && record.duplicateOfRunId ? <> · run <code>{record.duplicateOfRunId.slice(0, 8)}…</code>)</> : record.duplicateOfRawId ? <>)</> : null}.
                                </div>
                            )}
                            <div className="rl-meta-field">
                                <span className="rl-meta-label">Raw Record ID</span>
                                <span className="rl-meta-value rl-meta-value--mono">{record.id}</span>
                            </div>
                            <div className="rl-meta-field">
                                <span className="rl-meta-label">Source Record ID</span>
                                <span className="rl-meta-value rl-meta-value--mono">{record.srcId}</span>
                            </div>
                            <div className="rl-meta-field">
                                <span className="rl-meta-label">Entity (hint)</span>
                                <span className="rl-meta-value">{record.entity}</span>
                            </div>
                            <div className="rl-meta-field">
                                <span className="rl-meta-label">Source System</span>
                                <span className="rl-meta-value">{record.source}</span>
                            </div>
                            <div className="rl-meta-field">
                                <span className="rl-meta-label">Tenant</span>
                                <span className="rl-meta-value">{record.tenantName || record.tenantId.slice(0, 8) + '…'}</span>
                            </div>
                            <div className="rl-meta-field">
                                <span className="rl-meta-label">Ingestion Run</span>
                                <span className="rl-meta-value rl-meta-value--mono">{record.runId}</span>
                            </div>
                            <div className="rl-meta-field">
                                <span className="rl-meta-label">Run pipeline state</span>
                                <span className="rl-meta-value">{record.ingestionRunState}</span>
                            </div>
                            <div className="rl-meta-field">
                                <span className="rl-meta-label">Processing status</span>
                                <span className="rl-meta-value">{PROC_LABELS[record.status]}</span>
                            </div>
                            <div className="rl-meta-field">
                                <span className="rl-meta-label">Received At</span>
                                <span className="rl-meta-value">{record.receivedAt}</span>
                            </div>
                            <div className="rl-meta-field">
                                <span className="rl-meta-label">Field Count</span>
                                <span className="rl-meta-value">{Object.keys(record.payload).length} fields</span>
                            </div>
                            <div className="rl-meta-field" style={{ gridColumn: '1/-1' }}>
                                <span className="rl-meta-label">Checksum (MD5)</span>
                                <span className="rl-meta-value rl-meta-value--mono">{record.checksum}</span>
                            </div>
                            {record.isDuplicate && (
                                <>
                                    <div className="rl-meta-field">
                                        <span className="rl-meta-label">First added by</span>
                                        <span className="rl-meta-value">{record.firstSeenBy || 'unknown'}</span>
                                    </div>
                                    <div className="rl-meta-field">
                                        <span className="rl-meta-label">First added at</span>
                                        <span className="rl-meta-value">{record.firstSeenAt || '—'}</span>
                                    </div>
                                </>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default function RawLanding() {
    const [searchParams, setSearchParams] = useSearchParams();
    const runIdFromUrl = searchParams.get('runId');
    const { activeTenantId } = useTenantConfig();
    const [records, setRecords] = useState<RawLandingRecord[]>([]);
    const [totalApi, setTotalApi] = useState(0);
    const [sources, setSources] = useState<SourceRecord[]>([]);
    const [lineage, setLineage] = useState<IngestionLineageRunSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [searchInput, setSearchInput] = useState('');
    const [debouncedSearch, setDebouncedSearch] = useState('');
    const [filterSource, setFilterSource] = useState<string>('ALL');
    const [filterEntity, setFilterEntity] = useState<string>('ALL');
    const [filterStatus, setFilterStatus] = useState<string>('ALL');
    const [filterRun, setFilterRun] = useState<string>(runIdFromUrl || 'ALL');
    const [viewRecord, setViewRecord] = useState<RawLandingRecord | null>(null);
    const [viewTab, setViewTab] = useState<ModalTab>('payload');
    const [page, setPage] = useState(1);

    useEffect(() => {
        const t = window.setTimeout(() => setDebouncedSearch(searchInput), 400);
        return () => window.clearTimeout(t);
    }, [searchInput]);

    useEffect(() => {
        if (runIdFromUrl) {
            setFilterRun(runIdFromUrl);
            return;
        }
        if (lineage.length === 0) return;
        const def = resolveInitialRunId(null, lineage, 'raw');
        if (def !== 'ALL') {
            setFilterRun(def);
            setSearchParams({ runId: def }, { replace: true });
        }
    }, [runIdFromUrl, lineage, setSearchParams]);

    const selectRun = useCallback(
        (runId: string) => {
            setFilterRun(runId);
            setPage(1);
            if (runId === 'ALL') setSearchParams({});
            else setSearchParams({ runId });
        },
        [setSearchParams],
    );

    const activeLineage = useMemo(
        () => (filterRun !== 'ALL' ? lineage.find((l) => l.run_id === filterRun) : null),
        [filterRun, lineage],
    );

    const loadData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const tId = activeTenantId ?? undefined;

            const srcData = await sourceService.listSources(0, 100, tId);
            setSources(srcData);
            const lineageData = await ingestionRunService.fetchLineageSummary(tId, 50).catch(() => []);
            setLineage(lineageData);

            if (filterRun === 'ALL') {
                setRecords([]);
                setTotalApi(0);
                return;
            }

            const res = await rawLandingService.listRecords({
                skip: 0,
                limit: 500,
                tenantId: tId,
                runId: filterRun,
                sourceSystemId: filterSource === 'ALL' ? undefined : filterSource,
                entityType: filterEntity === 'ALL' ? undefined : filterEntity,
                search: debouncedSearch.trim() || undefined,
            });
            setRecords(res.items.map(toRawLandingRecord));
            setTotalApi(res.total);
        } catch (err) {
            const msg =
                err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Load failed';
            setError(msg);
            setRecords([]);
        } finally {
            setLoading(false);
        }
    }, [activeTenantId, filterRun, filterSource, filterEntity, debouncedSearch]);

    useEffect(() => {
        void loadData();
    }, [loadData]);

    const handleDeleteRun = useCallback(
        async (runId: string) => {
            try {
                const tId = activeTenantId ?? undefined;
                await ingestionRunService.deleteRun(runId, tId);
                if (filterRun === runId) {
                    selectRun('ALL');
                }
                await loadData();
            } catch (err) {
                const msg =
                    err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Delete failed';
                setError(msg);
                throw err;
            }
        },
        [activeTenantId, filterRun, selectRun, loadData],
    );

    const filtered = useMemo(() => {
        return records.filter((r) => {
            const q = searchInput.toLowerCase();
            const textMatch =
                !q ||
                r.id.toLowerCase().includes(q) ||
                r.srcId.toLowerCase().includes(q) ||
                r.entity.toLowerCase().includes(q) ||
                r.source.toLowerCase().includes(q);
            return (
                textMatch &&
                (filterEntity === 'ALL' || r.entity === filterEntity) &&
                (filterStatus === 'ALL' || r.status === filterStatus)
            );
        });
    }, [records, searchInput, filterEntity, filterStatus]);

    const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
    const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

    useEffect(() => {
        setPage((p) => Math.min(p, totalPages));
    }, [totalPages]);

    const openModal = (rec: RawLandingRecord, tab: ModalTab = 'payload') => {
        setViewRecord(rec);
        setViewTab(tab);
    };

    const completed = records.filter((r) => r.status === 'COMPLETED').length;
    const processing = records.filter((r) => r.status === 'PROCESSING').length;
    const failed = records.filter((r) => r.status === 'FAILED').length;
    const duplicates = records.filter((r) => r.status === 'DUPLICATE').length;

    return (
        <div className="rl-page">
            <TenantBreadcrumb
                screen="Raw Landing"
                detail={filterRun !== 'ALL' ? `Run ${filterRun.slice(0, 8)}…` : undefined}
            />

            <div className="rl-page-header">
                <div>
                    <h1 className="rl-page-title">Raw Landing</h1>
                    <p className="rl-page-subtitle">
                        Raw records are scoped per ingestion run — pick a run below (two runs = two separate batches)
                    </p>
                </div>
                <div className="rl-page-header__actions">
                    <button type="button" className="rl-btn rl-btn--ghost" disabled title="Export not wired yet">
                        ⬇ Export
                    </button>
                    <button
                        type="button"
                        className="rl-btn rl-btn--ghost"
                        onClick={() => void loadData()}
                        disabled={loading}
                    >
                        {loading ? '…' : '↻'} Refresh
                    </button>
                </div>
            </div>

            <IngestionRunLineagePicker
                lineage={lineage}
                activeRunId={filterRun}
                onSelectRun={selectRun}
                onDeleteRun={handleDeleteRun}
                screen="raw"
                loading={loading}
            />

            {filterRun !== 'ALL' && activeLineage && (
                <div className="rl-run-banner">
                    <div>
                        <strong>Run {filterRun.slice(0, 8)}…</strong>
                        <span className="rl-run-banner__meta">
                            Entity {activeLineage.entity_type || '—'} · Raw {activeLineage.raw_record_count} → Staging{' '}
                            {activeLineage.staging_record_count}
                            {activeLineage.counts_aligned ? ' (1:1 when complete)' : ` — ${activeLineage.pipeline_note}`}
                        </span>
                    </div>
                    <Link to={`/staging?runId=${encodeURIComponent(filterRun)}`} className="rl-btn rl-btn--ghost">
                        View staging →
                    </Link>
                </div>
            )}

            {error && (
                <div
                    style={{
                        background: 'var(--red-500-10)',
                        color: 'var(--red-500)',
                        padding: '12px 16px',
                        borderRadius: 8,
                        marginBottom: 16,
                    }}
                >
                    ✕ {error}
                </div>
            )}

            {filterRun === 'ALL' ? (
                <div className="rl-table-card rl-lineage-empty-card">
                    <p className="rl-lineage-empty-card__text">
                        Select an ingestion run in the table above. Raw Landing does not mix rows from different runs —
                        each run is one batch with its own entity and counts.
                    </p>
                </div>
            ) : (
            <>
                        <div className="rl-summary-row">
                <div className="rl-summary-card">
                    <span className="rl-summary-card__value">{totalApi}</span>
                    <span className="rl-summary-card__label">Total (this run)</span>
                </div>
                <div className="rl-summary-card">
                    <span className="rl-summary-card__value">{records.length}</span>
                    <span className="rl-summary-card__label">Loaded</span>
                </div>
                <div className="rl-summary-card rl-summary-card--green">
                    <span className="rl-summary-card__value">{completed}</span>
                    <span className="rl-summary-card__label">Completed</span>
                </div>
                <div className="rl-summary-card" style={{ borderTopColor: 'var(--blue-500)' }}>
                    <span className="rl-summary-card__value">{processing}</span>
                    <span className="rl-summary-card__label">Processing</span>
                </div>
                <div className="rl-summary-card rl-summary-card--red">
                    <span className="rl-summary-card__value">{failed}</span>
                    <span className="rl-summary-card__label">Failed</span>
                </div>
                <div className="rl-summary-card rl-summary-card--amber">
                    <span className="rl-summary-card__value">{duplicates}</span>
                    <span className="rl-summary-card__label">Duplicates</span>
                </div>
            </div>

            <div className="rl-table-card">
                <div className="rl-table-toolbar">
                    <div className="rl-search-wrap">
                        <span className="rl-search-icon">🔍</span>
                        <input
                            className="rl-search-input"
                            placeholder="Search (also sent to API after typing pauses)…"
                            value={searchInput}
                            onChange={(e: ChangeEvent<HTMLInputElement>) => {
                                setSearchInput(e.target.value);
                                setPage(1);
                            }}
                        />
                    </div>
                    <div className="rl-filter-row">
                        <select
                            className="rl-select"
                            value={filterSource}
                            onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                                setFilterSource(e.target.value);
                                setPage(1);
                            }}
                        >
                            <option value="ALL">All Sources</option>
                            {sources.map((s) => (
                                <option key={s.id} value={s.id}>
                                    {s.sourceName}
                                </option>
                            ))}
                        </select>
                        <select
                            className="rl-select"
                            value={filterEntity}
                            onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                                setFilterEntity(e.target.value);
                                setPage(1);
                            }}
                        >
                            <option value="ALL">All Entities</option>
                            {ENTITY_TYPES.map((e) => (
                                <option key={e} value={e}>
                                    {e}
                                </option>
                            ))}
                        </select>
                        <select
                            className="rl-select"
                            value={filterStatus}
                            onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                                setFilterStatus(e.target.value);
                                setPage(1);
                            }}
                        >
                            <option value="ALL">All Statuses</option>
                            {PROC_STATUSES.map((s) => (
                                <option key={s} value={s}>
                                    {PROC_LABELS[s]}
                                </option>
                            ))}
                        </select>
                        <select
                            className="rl-select"
                            value={filterRun}
                            onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                                selectRun(e.target.value);
                            }}
                        >
                            <option value="ALL">Overview (no records)</option>
                            {lineage.map((row) => (
                                <option key={row.run_id} value={row.run_id}>
                                    {formatRunOptionLabel(row)}
                                </option>
                            ))}
                        </select>
                        <span className="rl-count-label">
                            {filtered.length} shown (client filters) · {paginated.length} on page
                        </span>
                    </div>
                </div>

                <div className="rl-table-wrap">
                    <table className="rl-table">
                        <thead>
                            <tr>
                                <th>Raw Record ID</th>
                                <th>Source Record ID</th>
                                <th>Entity Type</th>
                                <th>Source System</th>
                                <th>Processing Status</th>
                                <th>Received At</th>
                                <th>Checksum</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading && records.length === 0 ? (
                                <tr>
                                    <td colSpan={8} className="rl-table-empty">
                                        <span>⏳</span>
                                        <p>Loading raw records…</p>
                                    </td>
                                </tr>
                            ) : paginated.length === 0 ? (
                                <tr>
                                    <td colSpan={8} className="rl-table-empty">
                                        <span>🗄</span>
                                        <p>No raw records found</p>
                                    </td>
                                </tr>
                            ) : (
                                paginated.map((rec) => (
                                    <tr
                                        key={rec.id}
                                        className={`rl-table-row${rec.isDuplicate ? ' rl-row--dup' : ''}`}
                                    >
                                        <td>
                                            <code className="rl-raw-id">{rec.id.slice(0, 13)}…</code>
                                        </td>
                                        <td>
                                            <span className="rl-src-id">{rec.srcId}</span>
                                        </td>
                                        <td>
                                            <span className="rl-entity-chip">{rec.entity}</span>
                                        </td>
                                        <td
                                            style={{
                                                fontSize: 13,
                                                color: 'var(--text-secondary)',
                                                fontWeight: 500,
                                            }}
                                        >
                                            {rec.source}
                                        </td>
                                        <td>
                                            <div className="rl-dup-cell">
                                                <span className={`rl-proc-status rl-proc-status--${rec.status}`}>
                                                    {PROC_LABELS[rec.status]}
                                                </span>
                                                {rec.isDuplicate && (
                                                    <>
                                                        <span className={`rl-dup-scope rl-dup-scope--${rec.duplicateScope || 'WITHIN_RUN'}`}>
                                                            {rec.duplicateScope === 'CROSS_RUN' ? 'Cross-run dup' : 'Within-run dup'}
                                                        </span>
                                                        <span className="rl-dup-meta">
                                                            First by <span className="rl-dup-meta__strong">{rec.firstSeenBy || 'unknown'}</span>
                                                            {rec.firstSeenAt ? <> on <span className="rl-dup-meta__strong">{rec.firstSeenAt}</span></> : null}
                                                        </span>
                                                    </>
                                                )}
                                            </div>
                                        </td>
                                        <td>
                                            <span className="rl-ts">{rec.receivedAt}</span>
                                        </td>
                                        <td>
                                            <span className="rl-checksum" title={rec.checksum}>
                                                {rec.checksum.slice(0, 12)}…
                                            </span>
                                        </td>
                                        <td>
                                            <div className="rl-action-row">
                                                <button
                                                    type="button"
                                                    className="rl-action-btn rl-action-btn--primary"
                                                    onClick={() => openModal(rec, 'payload')}
                                                >
                                                    View Payload
                                                </button>
                                                <button
                                                    type="button"
                                                    className="rl-action-btn"
                                                    onClick={() => openModal(rec, 'metadata')}
                                                >
                                                    Metadata
                                                </button>
                                                <button
                                                    type="button"
                                                    className="rl-action-btn"
                                                    onClick={() => {
                                                        const blob = new Blob([JSON.stringify(rec.payload, null, 2)], {
                                                            type: 'application/json',
                                                        });
                                                        const url = URL.createObjectURL(blob);
                                                        const a = document.createElement('a');
                                                        a.href = url;
                                                        a.download = `${rec.id}.json`;
                                                        a.click();
                                                        URL.revokeObjectURL(url);
                                                    }}
                                                >
                                                    ⬇ JSON
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                <div className="rl-pagination">
                    <span className="rl-pagination__info">
                        Showing{' '}
                        {filtered.length === 0
                            ? 0
                            : Math.min((page - 1) * PAGE_SIZE + 1, filtered.length)}
                        –
                        {Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length}
                    </span>
                    <div className="rl-pagination__btns">
                        <button
                            type="button"
                            className="rl-page-btn"
                            onClick={() => setPage((p) => p - 1)}
                            disabled={page === 1}
                        >
                            ←
                        </button>
                        {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                            <button
                                key={p}
                                type="button"
                                className={`rl-page-btn${p === page ? ' rl-page-btn--active' : ''}`}
                                onClick={() => setPage(p)}
                            >
                                {p}
                            </button>
                        ))}
                        <button
                            type="button"
                            className="rl-page-btn"
                            onClick={() => setPage((p) => p + 1)}
                            disabled={page === totalPages}
                        >
                            →
                        </button>
                    </div>
                </div>
            </div>

            </>
            )}

            {viewRecord && (
                <PayloadModal record={viewRecord} onClose={() => setViewRecord(null)} initialTab={viewTab} />
            )}
        </div>
    );
}
