// API Logs — integrated with GET /api/v1/api-logs/ (audit_log; same patterns as Raw Landing)
import {
    useState,
    useEffect,
    useCallback,
    useMemo,
    type ChangeEvent,
    type MouseEvent,
} from 'react';

import '../../styles/theme.css';
import '../../styles/ApiLogs.css';

import { authService } from '../../services/authService';
import { tenantService, type TenantRecord } from '../../services/tenantService';
import {
    apiLogsService,
    toApiLogUiRecord,
    type ApiLogUiRecord,
    type OperationType,
} from '../../services/apiLogsService';
import { ApiError } from '../../services/api';

type DrawerTab = 'overview' | 'before' | 'after';
type JsonPrimitive = string | number | boolean | null;
type JsonValue = JsonPrimitive | JsonObject | JsonValue[];
interface JsonObject {
    [key: string]: JsonValue;
}

const OPERATIONS: OperationType[] = ['INSERT', 'UPDATE', 'DELETE', 'MERGE'];
const ENTITY_PRESETS = ['tenant', 'source_systems', 'ingestion_runs'];
const PAGE_SIZE = 25;

function opBadgeClass(op: string): string {
    if (OPERATIONS.includes(op as OperationType)) return op;
    return 'default';
}

function payloadToJsonObject(data: Record<string, unknown> | null): JsonObject {
    if (!data) return {};
    return JSON.parse(JSON.stringify(data)) as JsonObject;
}

function coloriseJSON(obj: JsonObject): string {
    if (!obj || Object.keys(obj).length === 0) {
        return '<span style="color:#8b949e">// No data</span>';
    }
    const str = JSON.stringify(obj, null, 2);
    return str.replace(
        /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
        (match: string) => {
            let cls = 'al-json-num';
            if (/^"/.test(match)) {
                if (/:$/.test(match)) cls = 'al-json-key';
                else cls = 'al-json-str';
            } else if (/true|false/.test(match)) cls = 'al-json-bool';
            else if (/null/.test(match)) cls = 'al-json-null';
            return `<span class="${cls}">${match}</span>`;
        },
    );
}

function DrawerField({
    label,
    value,
    mono,
    wide,
}: {
    label: string;
    value: string;
    mono?: boolean;
    wide?: boolean;
}) {
    return (
        <div className="al-drawer__field" style={wide ? { gridColumn: '1 / -1' } : undefined}>
            <span className="al-drawer__field-label">{label}</span>
            <span className={`al-drawer__field-value${mono ? ' al-drawer__field-value--mono' : ''}`}>
                {value}
            </span>
        </div>
    );
}

interface LogDrawerProps {
    record: ApiLogUiRecord;
    onClose: () => void;
    initialTab?: DrawerTab;
}

function LogDrawer({ record, onClose, initialTab = 'overview' }: LogDrawerProps) {
    const [tab, setTab] = useState<DrawerTab>(initialTab);
    const [copied, setCopied] = useState(false);

    const oldJson = payloadToJsonObject(record.oldValue);
    const newJson = payloadToJsonObject(record.newValue);
    const activeJson = tab === 'before' ? oldJson : newJson;

    const copyPayload = (obj: JsonObject) => {
        void navigator.clipboard.writeText(JSON.stringify(obj, null, 2)).catch(() => { });
        setCopied(true);
        setTimeout(() => setCopied(false), 1800);
    };

    const tabs: Array<[DrawerTab, string]> = [
        ['overview', 'Overview'],
        ['before', 'Before'],
        ['after', 'After'],
    ];

    return (
        <div className="al-drawer-overlay" onClick={onClose} role="presentation">
            <div
                className="al-drawer"
                onClick={(e: MouseEvent<HTMLDivElement>) => e.stopPropagation()}
                role="dialog"
                aria-modal="true"
            >
                <div className="al-drawer__header">
                    <div>
                        <h2 className="al-drawer__title">
                            {record.operation} — {record.entityName}
                        </h2>
                        <div className="al-drawer__sub">{record.id}</div>
                    </div>
                    <button type="button" className="al-drawer__close" onClick={onClose}>
                        ✕
                    </button>
                </div>

                <div className="al-drawer-tabs">
                    {tabs.map(([key, label]) => (
                        <button
                            key={key}
                            type="button"
                            className={`al-drawer-tab${tab === key ? ' al-drawer-tab--active' : ''}`}
                            onClick={() => setTab(key)}
                        >
                            {label}
                        </button>
                    ))}
                </div>

                <div className="al-drawer__body">
                    {tab === 'overview' && (
                        <div className="al-drawer__grid">
                            <DrawerField label="Audit ID" value={record.id} mono />
                            <DrawerField label="Operation" value={record.operation} />
                            <DrawerField label="Entity" value={record.entityName} />
                            <DrawerField label="Entity ID" value={record.entityId ?? '—'} mono />
                            <DrawerField label="Performed by" value={record.performedBy} />
                            <DrawerField label="Performed at" value={record.performedAt} />
                            <DrawerField label="Tenant" value={record.tenantName} />
                            <DrawerField label="Source IP" value={record.sourceIp ?? '—'} />
                            <DrawerField label="Trace ID" value={record.traceId ?? '—'} mono wide />
                        </div>
                    )}
                    {(tab === 'before' || tab === 'after') && (
                        <>
                            <div className="al-json-toolbar">
                                <button
                                    type="button"
                                    className={`al-copy-btn${copied ? ' al-copy-btn--copied' : ''}`}
                                    onClick={() => copyPayload(activeJson)}
                                >
                                    {copied ? '✓ Copied!' : '⎘ Copy JSON'}
                                </button>
                            </div>
                            <div
                                className="al-json-viewer"
                                dangerouslySetInnerHTML={{ __html: coloriseJSON(activeJson) }}
                            />
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}

export default function ApiLogs() {
    const [logs, setLogs] = useState<ApiLogUiRecord[]>([]);
    const [totalApi, setTotalApi] = useState(0);
    const [tenants, setTenants] = useState<TenantRecord[]>([]);
    const [isSuperAdmin, setIsSuperAdmin] = useState(false);
    const [selectedTenantId, setSelectedTenantId] = useState<string>('ALL');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [searchInput, setSearchInput] = useState('');
    const [debouncedSearch, setDebouncedSearch] = useState('');
    const [filterOperation, setFilterOperation] = useState<string>('ALL');
    const [filterEntity, setFilterEntity] = useState<string>('ALL');
    const [filterActor, setFilterActor] = useState<string>('ALL');
    const [viewRecord, setViewRecord] = useState<ApiLogUiRecord | null>(null);
    const [viewTab, setViewTab] = useState<DrawerTab>('overview');
    const [page, setPage] = useState(1);

    useEffect(() => {
        const t = window.setTimeout(() => setDebouncedSearch(searchInput), 400);
        return () => window.clearTimeout(t);
    }, [searchInput]);

    const loadData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            await authService.init();
            const adminInfo = authService.getAdminInfoFromCookie();
            const superAdmin = adminInfo?.tenant_id === 'platform' || adminInfo?.role === 'admin';
            setIsSuperAdmin(superAdmin);
            try {
                const tenantData = await tenantService.listTenants();
                setTenants(tenantData);
                if (tenantData.length > 0) setIsSuperAdmin(true);
            } catch {
                /* ignore */
            }

            const tId = selectedTenantId === 'ALL' ? undefined : selectedTenantId;
            (window as unknown as { activeTenantId?: string }).activeTenantId = tId;

            const res = await apiLogsService.listLogs({
                skip: 0,
                limit: 500,
                tenantId: tId,
                operationType: filterOperation === 'ALL' ? undefined : filterOperation,
                entityName: filterEntity === 'ALL' ? undefined : filterEntity,
                search: debouncedSearch.trim() || undefined,
            });
            setLogs(res.items.map(toApiLogUiRecord));
            setTotalApi(res.total);
        } catch (err) {
            const msg =
                err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Load failed';
            setError(msg);
            setLogs([]);
            setTotalApi(0);
        } finally {
            setLoading(false);
        }
    }, [selectedTenantId, filterOperation, filterEntity, debouncedSearch]);

    useEffect(() => {
        void loadData();
    }, [loadData]);

    const entityOptions = useMemo(() => {
        const fromData = new Set(logs.map((l) => l.entityName).filter((e) => e && e !== '—'));
        ENTITY_PRESETS.forEach((e) => fromData.add(e));
        return Array.from(fromData).sort();
    }, [logs]);

    const actorOptions = useMemo(() => {
        const actors = new Set(logs.map((l) => l.performedBy));
        return Array.from(actors).sort();
    }, [logs]);

    const filtered = useMemo(() => {
        return logs.filter((l) => {
            const q = searchInput.toLowerCase();
            const textMatch =
                !q ||
                l.id.toLowerCase().includes(q) ||
                l.entityName.toLowerCase().includes(q) ||
                l.performedBy.toLowerCase().includes(q) ||
                l.tenantName.toLowerCase().includes(q) ||
                (l.traceId?.toLowerCase().includes(q) ?? false);
            return textMatch && (filterActor === 'ALL' || l.performedBy === filterActor);
        });
    }, [logs, searchInput, filterActor]);

    const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
    const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

    useEffect(() => {
        setPage((p) => Math.min(p, totalPages));
    }, [totalPages]);

    const insertCount = logs.filter((l) => l.operation === 'INSERT').length;
    const updateCount = logs.filter((l) => l.operation === 'UPDATE').length;
    const deleteCount = logs.filter((l) => l.operation === 'DELETE' || l.operation === 'MERGE').length;

    const openDrawer = (rec: ApiLogUiRecord, tab: DrawerTab = 'overview') => {
        setViewRecord(rec);
        setViewTab(tab);
    };

    return (
        <div className="al-page">
            <div className="al-page-header">
                <div>
                    <h1 className="al-page-title">API Logs</h1>
                    <p className="al-page-subtitle">
                        Immutable audit trail of platform actions (up to 500 loaded; filters refine this set)
                    </p>
                </div>
                <div className="al-page-header__actions">
                    <button type="button" className="al-btn al-btn--ghost" disabled title="Export not wired yet">
                        ⬇ Export
                    </button>
                    <button type="button" className="al-btn al-btn--ghost" onClick={() => void loadData()} disabled={loading}>
                        {loading ? '…' : '↻'} Refresh
                    </button>
                </div>
            </div>

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

            <div className="al-summary-row">
                <div className="al-summary-card">
                    <span className="al-summary-card__value">{totalApi}</span>
                    <span className="al-summary-card__label">Total (server match)</span>
                </div>
                <div className="al-summary-card">
                    <span className="al-summary-card__value">{logs.length}</span>
                    <span className="al-summary-card__label">Loaded</span>
                </div>
                <div className="al-summary-card al-summary-card--green">
                    <span className="al-summary-card__value">{insertCount}</span>
                    <span className="al-summary-card__label">Inserts</span>
                </div>
                <div className="al-summary-card" style={{ borderTopColor: 'var(--blue-500)' }}>
                    <span className="al-summary-card__value">{updateCount}</span>
                    <span className="al-summary-card__label">Updates</span>
                </div>
                <div className="al-summary-card al-summary-card--red">
                    <span className="al-summary-card__value">{deleteCount}</span>
                    <span className="al-summary-card__label">Delete / merge</span>
                </div>
            </div>

            <div className="al-table-card">
                <div className="al-table-toolbar">
                    <div className="al-search-wrap">
                        <span className="al-search-icon">🔍</span>
                        <input
                            className="al-search-input"
                            placeholder="Search (also sent to API after typing pauses)…"
                            value={searchInput}
                            onChange={(e: ChangeEvent<HTMLInputElement>) => {
                                setSearchInput(e.target.value);
                                setPage(1);
                            }}
                        />
                    </div>
                    <div className="al-filter-row">
                        {isSuperAdmin && tenants.length > 0 && (
                            <select
                                className="al-select"
                                value={selectedTenantId}
                                onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                                    setSelectedTenantId(e.target.value);
                                    setPage(1);
                                }}
                                style={{ borderColor: 'var(--blue-500)', background: 'var(--blue-500-10)' }}
                            >
                                <option value="ALL">All tenants</option>
                                {tenants.map((t) => (
                                    <option key={t.id} value={t.id}>
                                        {t.tenantName}
                                    </option>
                                ))}
                            </select>
                        )}
                        <select
                            className="al-select"
                            value={filterOperation}
                            onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                                setFilterOperation(e.target.value);
                                setPage(1);
                            }}
                        >
                            <option value="ALL">All operations</option>
                            {OPERATIONS.map((op) => (
                                <option key={op} value={op}>
                                    {op}
                                </option>
                            ))}
                        </select>
                        <select
                            className="al-select"
                            value={filterEntity}
                            onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                                setFilterEntity(e.target.value);
                                setPage(1);
                            }}
                        >
                            <option value="ALL">All entities</option>
                            {entityOptions.map((e) => (
                                <option key={e} value={e}>
                                    {e}
                                </option>
                            ))}
                        </select>
                        <select
                            className="al-select"
                            value={filterActor}
                            onChange={(e: ChangeEvent<HTMLSelectElement>) => {
                                setFilterActor(e.target.value);
                                setPage(1);
                            }}
                        >
                            <option value="ALL">All actors</option>
                            {actorOptions.map((a) => (
                                <option key={a} value={a}>
                                    {a}
                                </option>
                            ))}
                        </select>
                        <span className="al-count-label">
                            {filtered.length} shown (client filters) · {paginated.length} on page
                        </span>
                    </div>
                </div>

                <div className="al-table-wrap">
                    <table className="al-table">
                        <thead>
                            <tr>
                                <th>Performed at</th>
                                <th>Operation</th>
                                <th>Entity</th>
                                <th>Performed by</th>
                                <th>Tenant</th>
                                <th>Source IP</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading && logs.length === 0 ? (
                                <tr>
                                    <td colSpan={7} className="al-table-empty">
                                        <span>⏳</span>
                                        <p>Loading API logs…</p>
                                    </td>
                                </tr>
                            ) : paginated.length === 0 ? (
                                <tr>
                                    <td colSpan={7} className="al-table-empty">
                                        <span>≡</span>
                                        <p>No log entries found</p>
                                    </td>
                                </tr>
                            ) : (
                                paginated.map((rec) => (
                                    <tr
                                        key={rec.id}
                                        className="al-table-row"
                                        onClick={() => openDrawer(rec)}
                                    >
                                        <td>
                                            <span className="al-ts">{rec.performedAt}</span>
                                        </td>
                                        <td>
                                            <span className={`al-op-badge al-op-badge--${opBadgeClass(rec.operation)}`}>
                                                {rec.operation}
                                            </span>
                                        </td>
                                        <td>
                                            <span className="al-entity-chip">{rec.entityName}</span>
                                        </td>
                                        <td style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                                            {rec.performedBy}
                                        </td>
                                        <td style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                                            {rec.tenantName}
                                        </td>
                                        <td>
                                            <span className="al-ts">{rec.sourceIp ?? '—'}</span>
                                        </td>
                                        <td onClick={(e: MouseEvent<HTMLTableCellElement>) => e.stopPropagation()}>
                                            <div className="al-action-row">
                                                <button
                                                    type="button"
                                                    className="al-action-btn al-action-btn--primary"
                                                    onClick={() => openDrawer(rec, 'overview')}
                                                >
                                                    Details
                                                </button>
                                                <button
                                                    type="button"
                                                    className="al-action-btn"
                                                    onClick={() => openDrawer(rec, 'after')}
                                                >
                                                    After
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                <div className="al-pagination">
                    <span className="al-pagination__info">
                        Showing{' '}
                        {filtered.length === 0
                            ? 0
                            : Math.min((page - 1) * PAGE_SIZE + 1, filtered.length)}
                        –
                        {Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length}
                    </span>
                    <div className="al-pagination__btns">
                        <button
                            type="button"
                            className="al-page-btn"
                            onClick={() => setPage((p) => p - 1)}
                            disabled={page === 1}
                        >
                            ←
                        </button>
                        {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                            <button
                                key={p}
                                type="button"
                                className={`al-page-btn${p === page ? ' al-page-btn--active' : ''}`}
                                onClick={() => setPage(p)}
                            >
                                {p}
                            </button>
                        ))}
                        <button
                            type="button"
                            className="al-page-btn"
                            onClick={() => setPage((p) => p + 1)}
                            disabled={page === totalPages}
                        >
                            →
                        </button>
                    </div>
                </div>
            </div>

            {viewRecord && (
                <LogDrawer
                    record={viewRecord}
                    onClose={() => setViewRecord(null)}
                    initialTab={viewTab}
                />
            )}
        </div>
    );
}
