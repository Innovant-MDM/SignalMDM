// MDM_Frontend/src/pages/staging/StagingRecords.tsx
import {
    useState,
    useEffect,
    useCallback,
    useMemo,
    type ChangeEvent,
    type MouseEvent,
} from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useSnackbar } from '../../context/SnackbarContext';

import IngestionRunLineagePicker from '../../components/ingestion/IngestionRunLineagePicker';
import TenantBreadcrumb from '../../components/TenantBreadcrumb';
import { formatRunOptionLabel, resolveInitialRunId } from '../../utils/ingestionRunScope';
import '../../styles/theme.css';
import '../../styles/StagingRecords.css';


import { sourceService, type SourceRecord } from '../../services/sourceService';
import {
    ingestionRunService,
    type IngestionLineageRunSummary,
} from '../../services/ingestionRunService';
import { useTenantConfig } from '../../context/TenantConfigContext';
import {
    stagingService,
    toStagingUiRecord,
    type StagingUiRecord,
    type StagingStateApi,
} from '../../services/stagingService';
import { ApiError } from '../../services/api';

type DrawerTab = 'overview' | 'raw' | 'canonical' | 'validation';
type JsonPrimitive = string | number | boolean | null;
type JsonValue = JsonPrimitive | JsonObject | JsonValue[];
interface JsonObject {
    [key: string]: JsonValue;
}

type DQClass = 'high' | 'mid' | 'low';

const STG_STATE_LABELS: Record<string, string> = {
    READY_FOR_MAPPING: 'Ready for mapping',
    MAPPED: 'Mapped',
    REJECTED: 'Rejected',
};

const STG_FILTER_STATES: StagingStateApi[] = ['READY_FOR_MAPPING', 'MAPPED', 'REJECTED'];

const VAL_STATUSES = ['PASSED', 'FAILED', 'PARTIAL', 'PENDING'] as const;

const PAGE_SIZE = 25;

function stagingStateDisplay(state: string): string {
    return STG_STATE_LABELS[state] ?? state;
}

function payloadToJsonObject(data: Record<string, unknown>): JsonObject {
    return JSON.parse(JSON.stringify(data ?? {})) as JsonObject;
}

function getDQClass(score: number): DQClass {
    if (score >= 90) return 'high';
    if (score >= 65) return 'mid';
    return 'low';
}

function coloriseJSON(obj: JsonObject): string {
    if (!obj || Object.keys(obj).length === 0) {
        return '<span style="color:#8b949e">// No data available</span>';
    }
    const str = JSON.stringify(obj, null, 2);
    return str.replace(
        /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
        (match: string) => {
            let cls = 'sr-json-num';
            if (/^"/.test(match)) {
                if (/:$/.test(match)) cls = 'sr-json-key';
                else cls = 'sr-json-str';
            } else if (/true|false/.test(match)) cls = 'sr-json-bool';
            else if (/null/.test(match)) cls = 'sr-json-null';
            return `<span class="${cls}">${match}</span>`;
        },
    );
}

interface RecordDrawerProps {
    record: StagingUiRecord;
    onClose: () => void;
}

function RecordDrawer({ record, onClose }: RecordDrawerProps) {
    const [tab, setTab] = useState<DrawerTab>('overview');
    const [rawCopied, setRawCopied] = useState(false);
    const [canCopied, setCanCopied] = useState(false);

    const dqClass = getDQClass(record.dqScore);
    const rawJson = payloadToJsonObject(record.rawPayload);
    const canJson = payloadToJsonObject(record.canonicalPayload);

    const copyJSON = (obj: JsonObject, setCopied: (value: boolean) => void) => {
        void navigator.clipboard.writeText(JSON.stringify(obj, null, 2)).catch(() => { });
        setCopied(true);
        setTimeout(() => setCopied(false), 1800);
    };

    const tabs: Array<[DrawerTab, string]> = [
        ['overview', 'Overview'],
        ['raw', 'Raw Payload'],
        ['canonical', 'Canonical / Staged'],
        ['validation', 'Validation'],
    ];

    return (
        <div className="sr-drawer-overlay" onClick={onClose} role="presentation">
            <div
                className="sr-drawer"
                onClick={(e: MouseEvent<HTMLDivElement>) => e.stopPropagation()}
                role="dialog"
                aria-modal="true"
            >
                <div className="sr-drawer__header">
                    <div>
                        <h2 className="sr-drawer__title">
                            {record.srcId} — {record.entity}
                        </h2>
                        <div className="sr-drawer__sub">
                            {record.id} · {record.source}
                        </div>
                    </div>
                    <button type="button" className="sr-drawer__close" onClick={onClose}>
                        ✕
                    </button>
                </div>

                <div className="sr-drawer-tabs">
                    {tabs.map(([key, label]) => (
                        <button
                            key={key}
                            type="button"
                            className={`sr-drawer-tab${tab === key ? ' sr-drawer-tab--active' : ''}`}
                            onClick={() => setTab(key)}
                        >
                            {label}
                        </button>
                    ))}
                </div>

                <div className="sr-drawer__body">
                    {tab === 'overview' && (
                        <div className="sr-drawer__content">
                            {record.isDuplicate && (
                                <div className="sr-dup-callout">
                                    <div className="sr-dup-callout__title">
                                        ⚠ Duplicate record ({record.duplicateScope === 'CROSS_RUN' ? 'cross-run' : 'within run'})
                                    </div>
                                    This staging row was built from a raw payload whose checksum already existed in this tenant.
                                    {' '}First added by <strong>{record.firstSeenBy || 'unknown'}</strong>
                                    {record.firstSeenAt ? <> on <strong>{record.firstSeenAt}</strong></> : null}
                                    {record.duplicateOfRawId ? <> (raw id <code>{record.duplicateOfRawId.slice(0, 8)}…</code></> : null}
                                    {record.duplicateOfRawId && record.duplicateOfRunId ? <> · run <code>{record.duplicateOfRunId.slice(0, 8)}…</code>)</> : record.duplicateOfRawId ? <>)</> : null}.
                                </div>
                            )}
                            <div className="sr-drawer__grid">
                                <div className="sr-drawer__field">
                                    <span className="sr-drawer__field-label">Staging ID</span>
                                    <span className="sr-stg-id" style={{ alignSelf: 'flex-start' }}>
                                        {record.id}
                                    </span>
                                </div>
                                <div className="sr-drawer__field">
                                    <span className="sr-drawer__field-label">Raw Record ID</span>
                                    <span className="sr-raw-id" style={{ alignSelf: 'flex-start' }}>
                                        {record.rawId}
                                    </span>
                                </div>
                                <div className="sr-drawer__field">
                                    <span className="sr-drawer__field-label">Tenant</span>
                                    <span className="sr-drawer__field-value">
                                        {record.tenantName || record.tenantId.slice(0, 8) + '…'}
                                    </span>
                                </div>
                                <div className="sr-drawer__field">
                                    <span className="sr-drawer__field-label">Staging state</span>
                                    <span className={`sr-stg-badge sr-stg-badge--${record.stgBadgeClass}`}>
                                        {stagingStateDisplay(record.stgState)}
                                    </span>
                                </div>
                                <div className="sr-drawer__field">
                                    <span className="sr-drawer__field-label">Validation status</span>
                                    <span className={`sr-val-badge sr-val-badge--${record.valStatus}`}>
                                        {record.valStatus}
                                    </span>
                                </div>
                                <div className="sr-drawer__field">
                                    <span className="sr-drawer__field-label">Source system</span>
                                    <span className="sr-drawer__field-value">{record.source}</span>
                                </div>
                                <div className="sr-drawer__field">
                                    <span className="sr-drawer__field-label">Created at</span>
                                    <span className="sr-drawer__field-value" style={{ fontSize: 12.5 }}>
                                        {record.createdAt}
                                    </span>
                                </div>
                                <div className="sr-drawer__field">
                                    <span className="sr-drawer__field-label">Ingestion run</span>
                                    <span className="sr-drawer__field-value sr-drawer__field-value--mono">
                                        {record.runId}
                                    </span>
                                </div>
                                <div className="sr-drawer__field">
                                    <span className="sr-drawer__field-label">Run pipeline state</span>
                                    <span className="sr-drawer__field-value">{record.ingestionRunState}</span>
                                </div>
                                <div className="sr-drawer__field">
                                    <span className="sr-drawer__field-label">Entity (hint)</span>
                                    <span className="sr-entity-chip" style={{ alignSelf: 'flex-start' }}>
                                        {record.entity}
                                    </span>
                                </div>
                                {record.isDuplicate && (
                                    <>
                                        <div className="sr-drawer__field">
                                            <span className="sr-drawer__field-label">First added by</span>
                                            <span className="sr-drawer__field-value">{record.firstSeenBy || 'unknown'}</span>
                                        </div>
                                        <div className="sr-drawer__field">
                                            <span className="sr-drawer__field-label">First added at</span>
                                            <span className="sr-drawer__field-value" style={{ fontSize: 12.5 }}>
                                                {record.firstSeenAt || '—'}
                                            </span>
                                        </div>
                                        {record.duplicateOfStagingId && (
                                            <div className="sr-drawer__field">
                                                <span className="sr-drawer__field-label">Original staging ID</span>
                                                <span className="sr-drawer__field-value sr-drawer__field-value--mono">
                                                    {record.duplicateOfStagingId}
                                                </span>
                                            </div>
                                        )}
                                    </>
                                )}
                            </div>

                            <div>
                                <span className="sr-drawer__field-label" style={{ display: 'block', marginBottom: 10 }}>
                                    Data quality score (Phase 1 placeholder)
                                </span>
                                <div className="sr-dq-card">
                                    <div className="sr-dq-card__score-row">
                                        <span className={`sr-dq-card__score-val sr-dq-card__score-val--${dqClass}`}>
                                            {record.dqScore}
                                        </span>
                                        <span className="sr-dq-card__score-lbl">/ 100</span>
                                    </div>
                                    <div className="sr-dq-card__bar">
                                        <div
                                            className={`sr-dq-card__fill sr-dq-card__fill--${dqClass}`}
                                            style={{ width: `${record.dqScore}%` }}
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {tab === 'raw' && (
                        <div className="sr-drawer__content">
                            <div className="sr-json-toolbar">
                                <button
                                    type="button"
                                    className={`sr-copy-btn${rawCopied ? ' sr-copy-btn--copied' : ''}`}
                                    onClick={() => copyJSON(rawJson, setRawCopied)}
                                >
                                    {rawCopied ? '✓ Copied!' : '⎘ Copy JSON'}
                                </button>
                            </div>
                            <div
                                className="sr-json-viewer"
                                dangerouslySetInnerHTML={{ __html: coloriseJSON(rawJson) }}
                            />
                            <div className="sr-drawer__field">
                                <span className="sr-drawer__field-label">Field count</span>
                                <span className="sr-drawer__field-value">{Object.keys(rawJson).length} fields</span>
                            </div>
                        </div>
                    )}

                    {tab === 'canonical' && (
                        <div className="sr-drawer__content">
                            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>
                                Phase 1: staged payload is a verbatim copy of raw. Mapping transforms arrive in later
                                phases.
                            </p>
                            <div className="sr-diff-header">
                                <span className="sr-diff-label">Raw input</span>
                                <span
                                    className="sr-diff-label"
                                    style={{ background: 'var(--purple-100)', color: 'var(--purple-500)' }}
                                >
                                    Staged entity_data
                                </span>
                            </div>
                            <div className="sr-diff-panels">
                                <div
                                    className="sr-json-viewer"
                                    style={{ fontSize: 11 }}
                                    dangerouslySetInnerHTML={{ __html: coloriseJSON(rawJson) }}
                                />
                                <div
                                    className="sr-json-viewer"
                                    style={{ fontSize: 11, borderColor: 'rgba(139,92,246,.25)' }}
                                    dangerouslySetInnerHTML={{ __html: coloriseJSON(canJson) }}
                                />
                            </div>
                            <div className="sr-json-toolbar">
                                <button
                                    type="button"
                                    className={`sr-copy-btn${canCopied ? ' sr-copy-btn--copied' : ''}`}
                                    onClick={() => copyJSON(canJson, setCanCopied)}
                                >
                                    {canCopied ? '✓ Copied!' : '⎘ Copy staged JSON'}
                                </button>
                            </div>
                        </div>
                    )}

                    {tab === 'validation' && (
                        <div className="sr-drawer__content">
                            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>
                                Phase 1: rule rows are illustrative until DQ engine is wired.
                            </p>
                            <div>
                                <span className="sr-drawer__field-label" style={{ display: 'block', marginBottom: 10 }}>
                                    DQ rules
                                </span>
                                <div className="sr-dq-rules">
                                    {record.validationRules.map((r, i) => (
                                        <div key={i} className="sr-dq-rule">
                                            <span className="sr-dq-rule__name">{r.rule}</span>
                                            <span
                                                className={`sr-dq-rule__result sr-dq-rule__result--${r.result === 'PASS'
                                                        ? 'pass'
                                                        : r.result === 'FAIL'
                                                            ? 'fail'
                                                            : 'warn'
                                                    }`}
                                            >
                                                {r.result === 'PASS'
                                                    ? '✓ PASS'
                                                    : r.result === 'FAIL'
                                                        ? '✕ FAIL'
                                                        : r.result === 'WARN'
                                                            ? '⚠ WARN'
                                                            : '⏳ PENDING'}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div>
                                <span className="sr-drawer__field-label" style={{ display: 'block', marginBottom: 10 }}>
                                    DQ score
                                </span>
                                <div className="sr-dq-card">
                                    <div className="sr-dq-card__score-row">
                                        <span
                                            className={`sr-dq-card__score-val sr-dq-card__score-val--${getDQClass(record.dqScore)}`}
                                        >
                                            {record.dqScore}
                                        </span>
                                        <span className="sr-dq-card__score-lbl">/ 100</span>
                                    </div>
                                    <div className="sr-dq-card__bar">
                                        <div
                                            className={`sr-dq-card__fill sr-dq-card__fill--${getDQClass(record.dqScore)}`}
                                            style={{ width: `${record.dqScore}%` }}
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default function StagingRecords() {
    const snackbar = useSnackbar();
    const [searchParams, setSearchParams] = useSearchParams();
    const runIdFromUrl = searchParams.get('runId');
    const { activeTenantId } = useTenantConfig();
    const [records, setRecords] = useState<StagingUiRecord[]>([]);
    const [totalApi, setTotalApi] = useState(0);
    const [sources, setSources] = useState<SourceRecord[]>([]);
    const [lineage, setLineage] = useState<IngestionLineageRunSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [searchInput, setSearchInput] = useState('');
    const [debouncedSearch, setDebouncedSearch] = useState('');
    const [filterSource, setFilterSource] = useState<string>('ALL');
    const [filterEntity, setFilterEntity] = useState<string>('ALL');
    const [filterStgStatus, setFilterStgStatus] = useState<string>('ALL');
    const [filterValStatus, setFilterValStatus] = useState<string>('ALL');
    const [filterRun, setFilterRun] = useState<string>(runIdFromUrl || 'ALL');
    const [viewRecord, setViewRecord] = useState<StagingUiRecord | null>(null);
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
        const def = resolveInitialRunId(null, lineage, 'staging');
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

    const entityOptions = useMemo(() => {
        const set = new Set<string>();
        lineage.forEach((l) => { if (l.entity_type) set.add(l.entity_type); });
        records.forEach((r) => { if (r.ingestionEntity) set.add(r.ingestionEntity); });
        return Array.from(set).sort();
    }, [lineage, records]);

    const loadData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const tId = activeTenantId ?? undefined;

            const srcData = await sourceService.listSources(0, 100, tId);
            setSources(srcData);
            const lineageData = await ingestionRunService.fetchLineageSummary(tId, 50);
            setLineage(lineageData);

            if (filterRun === 'ALL') {
                setRecords([]);
                setTotalApi(0);
                return;
            }

            const res = await stagingService.listRecords({
                skip: 0,
                limit: 500,
                tenantId: tId,
                runId: filterRun,
                sourceSystemId: filterSource === 'ALL' ? undefined : filterSource,
                entityType: filterEntity === 'ALL' ? undefined : filterEntity,
                search: debouncedSearch.trim() || undefined,
            });
            setRecords(res.items.map(toStagingUiRecord));
            setTotalApi(res.total);
        } catch (err) {
            const msg =
                err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Load failed';
            setError(msg);
            setRecords([]);
            setTotalApi(0);
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
                snackbar.showSuccess('Ingestion run deleted successfully.');
            } catch (err) {
                const msg =
                    err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Delete failed';
                setError(msg);
                snackbar.showError(`Failed to delete run: ${msg}`);
                throw err;
            }
        },
        [activeTenantId, filterRun, selectRun, loadData, snackbar],
    );

    const filtered = useMemo(() => {
        return records.filter((r) => {
            const q = searchInput.toLowerCase();
            const textMatch =
                !q ||
                r.id.toLowerCase().includes(q) ||
                r.srcId.toLowerCase().includes(q) ||
                r.rawId.toLowerCase().includes(q) ||
                r.entity.toLowerCase().includes(q) ||
                r.source.toLowerCase().includes(q);
            return (
                textMatch &&
                (filterEntity === 'ALL' || r.entity === filterEntity) &&
                (filterStgStatus === 'ALL' || r.stgState === filterStgStatus) &&
                (filterValStatus === 'ALL' || r.valStatus === filterValStatus)
            );
        });
    }, [records, searchInput, filterEntity, filterStgStatus, filterValStatus]);

    const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
    const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

    useEffect(() => {
        setPage((p) => Math.min(p, totalPages));
    }, [totalPages]);

    const readyCount = records.filter((r) => r.stgState === 'READY_FOR_MAPPING').length;
    const mappedCount = records.filter((r) => r.stgState === 'MAPPED').length;
    const rejectedCount = records.filter((r) => r.stgState === 'REJECTED').length;
    const avgDQ =
        records.length === 0 ? 0 : Math.round(records.reduce((s, r) => s + r.dqScore, 0) / records.length);

    return (
        <div className="sr-page">
            <TenantBreadcrumb
                screen="Staging Records"
                detail={filterRun !== 'ALL' ? `Run ${filterRun.slice(0, 8)}…` : undefined}
            />

            <div className="sr-page-header">
                <div>
                    <h1 className="sr-page-title">Staging Records</h1>
                    <p className="sr-page-subtitle">
                        Staging rows are scoped per ingestion run — pick a run below (1:1 with Raw Landing for that batch)
                    </p>
                </div>
                <div className="sr-page-header__actions">
                    <button type="button" className="sr-btn sr-btn--ghost" disabled title="Export not wired yet">
                        ⬇ Export
                    </button>
                    <button type="button" className="sr-btn sr-btn--ghost" onClick={() => void loadData()} disabled={loading}>
                        {loading ? '…' : '↻'} Refresh
                    </button>
                </div>
            </div>

            <IngestionRunLineagePicker
                lineage={lineage}
                activeRunId={filterRun}
                onSelectRun={selectRun}
                onDeleteRun={handleDeleteRun}
                screen="staging"
                loading={loading}
            />

            {filterRun !== 'ALL' && activeLineage && (
                <div className="sr-lineage-banner">
                    <div>
                        <strong>Run {filterRun.slice(0, 8)}…</strong>
                        <span className="sr-lineage-banner__meta">
                            Entity {activeLineage.entity_type || '—'} · Raw {activeLineage.raw_record_count} → Staging{' '}
                            {activeLineage.staging_record_count}
                            {activeLineage.counts_aligned
                                ? ' (1:1 with Raw Landing for this run)'
                                : ` — ${activeLineage.pipeline_note}`}
                        </span>
                    </div>
                    <Link to={`/raw-landing?runId=${encodeURIComponent(filterRun)}`} className="sr-btn sr-btn--ghost">
                        View raw records →
                    </Link>
                </div>
            )}

            {filterRun === 'ALL' && lineage.some((l) => !l.counts_aligned && l.raw_record_count > 0) && (
                <p className="sr-lineage-hint">
                    Overview mode: pick a run in the table above. Mixed "all runs" record lists are hidden because counts are per batch.
                </p>
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
                <div className="sr-table-card sr-lineage-empty-card">
                    <p className="sr-lineage-empty-card__text">
                        Select an ingestion run in the table above. Staging does not mix rows from different runs —
                        each completed run should match Raw Landing 1:1 for that batch.
                    </p>
                </div>
            ) : (
            <>
                        <div className="sr-summary-row">
                <div className="sr-summary-card">
                    <span className="sr-summary-card__value">{totalApi}</span>
                    <span className="sr-summary-card__label">Total (this run)</span>
                </div>
                <div className="sr-summary-card">
                    <span className="sr-summary-card__value">{records.length}</span>
                    <span className="sr-summary-card__label">Loaded</span>
                </div>
                <div className="sr-summary-card sr-summary-card--green">
                    <span className="sr-summary-card__value">{readyCount}</span>
                    <span className="sr-summary-card__label">Ready for mapping</span>
                </div>
                <div className="sr-summary-card sr-summary-card--purple">
                    <span className="sr-summary-card__value">{mappedCount}</span>
                    <span className="sr-summary-card__label">Mapped</span>
                </div>
                <div className="sr-summary-card sr-summary-card--red">
                    <span className="sr-summary-card__value">{rejectedCount}</span>
                    <span className="sr-summary-card__label">Rejected</span>
                </div>
                <div className="sr-summary-card sr-summary-card--amber">
                    <span
                        className="sr-summary-card__value"
                        style={{
                            color:
                                getDQClass(avgDQ) === 'high'
                                    ? '#16a34a'
                                    : getDQClass(avgDQ) === 'mid'
                                        ? '#d97706'
                                        : '#dc2626',
                        }}
                    >
                        {avgDQ}
                    </span>
                    <span className="sr-summary-card__label">Avg DQ (placeholder)</span>
                </div>
            </div>

            <div className="sr-table-card">
                <div className="sr-table-toolbar">
                    <div className="sr-search-wrap">
                        <span className="sr-search-icon">🔍</span>
                        <input
                            className="sr-search-input"
                            placeholder="Search (also sent to API after typing pauses)…"
                            value={searchInput}
                            onChange={(e: ChangeEvent<HTMLInputElement>) => {
                                setSearchInput(e.target.value);
                                setPage(1);
                            }}
                        />
                    </div>
                    <div className="sr-filter-row">
                        <select
                            className="sr-select"
                            value={filterSource}
                            onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                                setFilterSource(e.target.value);
                                setPage(1);
                            }}
                        >
                            <option value="ALL">All sources</option>
                            {sources.map((s) => (
                                <option key={s.id} value={s.id}>
                                    {s.sourceName}
                                </option>
                            ))}
                        </select>
                        <select
                            className="sr-select"
                            value={filterEntity}
                            onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                                setFilterEntity(e.target.value);
                                setPage(1);
                            }}
                        >
                            <option value="ALL">All entities (from runs)</option>
                            {entityOptions.map((e) => (
                                <option key={e} value={e}>
                                    {e}
                                </option>
                            ))}
                        </select>
                        <select
                            className="sr-select"
                            value={filterStgStatus}
                            onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                                setFilterStgStatus(e.target.value);
                                setPage(1);
                            }}
                        >
                            <option value="ALL">All staging states</option>
                            {STG_FILTER_STATES.map((s) => (
                                <option key={s} value={s}>
                                    {STG_STATE_LABELS[s]}
                                </option>
                            ))}
                        </select>
                        <select
                            className="sr-select"
                            value={filterValStatus}
                            onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                                setFilterValStatus(e.target.value);
                                setPage(1);
                            }}
                        >
                            <option value="ALL">All validation</option>
                            {VAL_STATUSES.map((s) => (
                                <option key={s} value={s}>
                                    {s}
                                </option>
                            ))}
                        </select>
                        <select
                            className="sr-select"
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
                        <span className="sr-count-label">
                            {filtered.length} shown (client filters) · {paginated.length} on page
                        </span>
                    </div>
                </div>

                <div className="sr-table-wrap">
                    <table className="sr-table">
                        <thead>
                            <tr>
                                <th>Staging ID</th>
                                <th>Source record ID</th>
                                <th>Entity type</th>
                                <th>Staging state</th>
                                <th>Validation</th>
                                <th>DQ score</th>
                                <th>Created at</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading && records.length === 0 ? (
                                <tr>
                                    <td colSpan={8} className="sr-table-empty">
                                        <span>⏳</span>
                                        <p>Loading staging records…</p>
                                    </td>
                                </tr>
                            ) : paginated.length === 0 ? (
                                <tr>
                                    <td colSpan={8} className="sr-table-empty">
                                        <span>📋</span>
                                        <p>No staging records found</p>
                                    </td>
                                </tr>
                            ) : (
                                paginated.map((rec) => {
                                    const dqCls = getDQClass(rec.dqScore);
                                    return (
                                        <tr
                                            key={rec.id}
                                            className={`sr-table-row${rec.isDuplicate ? ' sr-row--dup' : ''}`}
                                            onClick={() => setViewRecord(rec)}
                                        >
                                            <td>
                                                <code className="sr-stg-id">{rec.id.slice(0, 13)}…</code>
                                            </td>
                                            <td>
                                                <span
                                                    style={{
                                                        fontFamily: "'Courier New',monospace",
                                                        fontSize: 12,
                                                        color: 'var(--text-secondary)',
                                                    }}
                                                >
                                                    {rec.srcId}
                                                </span>
                                            </td>
                                            <td>
                                                <span className="sr-entity-chip">{rec.entity}</span>
                                            </td>
                                            <td>
                                                <div className="sr-dup-cell">
                                                    <span className={`sr-stg-badge sr-stg-badge--${rec.stgBadgeClass}`}>
                                                        {stagingStateDisplay(rec.stgState)}
                                                    </span>
                                                    {rec.isDuplicate && (
                                                        <>
                                                            <span className={`sr-dup-scope sr-dup-scope--${rec.duplicateScope || 'WITHIN_RUN'}`}>
                                                                {rec.duplicateScope === 'CROSS_RUN' ? 'Cross-run dup' : 'Within-run dup'}
                                                            </span>
                                                            <span className="sr-dup-meta">
                                                                First by <span className="sr-dup-meta__strong">{rec.firstSeenBy || 'unknown'}</span>
                                                                {rec.firstSeenAt ? <> on <span className="sr-dup-meta__strong">{rec.firstSeenAt}</span></> : null}
                                                            </span>
                                                        </>
                                                    )}
                                                </div>
                                            </td>
                                            <td>
                                                <span className={`sr-val-badge sr-val-badge--${rec.valStatus}`}>
                                                    {rec.valStatus}
                                                </span>
                                            </td>
                                            <td>
                                                <div className="sr-dq-wrap">
                                                    <span className={`sr-dq-score sr-dq-score--${dqCls}`}>{rec.dqScore}</span>
                                                    <div className="sr-dq-bar">
                                                        <div
                                                            className={`sr-dq-fill sr-dq-fill--${dqCls}`}
                                                            style={{ width: `${rec.dqScore}%` }}
                                                        />
                                                    </div>
                                                </div>
                                            </td>
                                            <td>
                                                <span className="sr-ts">{rec.createdAt}</span>
                                            </td>
                                            <td onClick={(e: MouseEvent<HTMLTableCellElement>) => e.stopPropagation()}>
                                                <div className="sr-action-row">
                                                    <button
                                                        type="button"
                                                        className="sr-action-btn sr-action-btn--primary"
                                                        onClick={() => setViewRecord(rec)}
                                                    >
                                                        Details
                                                    </button>
                                                    <button type="button" className="sr-action-btn" onClick={() => setViewRecord(rec)}>
                                                        Staged JSON
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

                <div className="sr-pagination">
                    <span className="sr-pagination__info">
                        Showing{' '}
                        {filtered.length === 0
                            ? 0
                            : Math.min((page - 1) * PAGE_SIZE + 1, filtered.length)}
                        –
                        {Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length}
                    </span>
                    <div className="sr-pagination__btns">
                        <button
                            type="button"
                            className="sr-page-btn"
                            onClick={() => setPage((p) => p - 1)}
                            disabled={page === 1}
                        >
                            ←
                        </button>
                        {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                            <button
                                key={p}
                                type="button"
                                className={`sr-page-btn${p === page ? ' sr-page-btn--active' : ''}`}
                                onClick={() => setPage(p)}
                            >
                                {p}
                            </button>
                        ))}
                        <button
                            type="button"
                            className="sr-page-btn"
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

            {viewRecord && <RecordDrawer record={viewRecord} onClose={() => setViewRecord(null)} />}
        </div>
    );
}
