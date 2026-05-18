import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { IngestionLineageRunSummary, RunStatus } from '../../services/ingestionRunService';
import { formatLineageTimestamp } from '../../utils/ingestionRunScope';
import '../../styles/IngestionRuns.css';
import './IngestionLineage.css';

export type LineageScreen = 'raw' | 'staging';

const STATUS_LABEL: Record<string, string> = {
    CREATED: 'Created',
    RUNNING: 'Running',
    RAW_LOADED: 'Raw loaded',
    STAGING_CREATED: 'Staging created',
    FAILED: 'Failed',
    COMPLETED: 'Completed',
};

interface IngestionRunLineagePickerProps {
    lineage: IngestionLineageRunSummary[];
    activeRunId: string;
    onSelectRun: (runId: string) => void;
    onDeleteRun?: (runId: string) => Promise<void>;
    screen: LineageScreen;
    loading?: boolean;
}

function RunStatusBadge({ status }: { status: string }) {
    return (
        <span className={`ir-status ir-status--${status}`}>
            {STATUS_LABEL[status] || status}
        </span>
    );
}

export default function IngestionRunLineagePicker({
    lineage,
    activeRunId,
    onSelectRun,
    onDeleteRun,
    screen,
    loading,
}: IngestionRunLineagePickerProps) {
    const screenLabel = screen === 'raw' ? 'raw landing' : 'staging';
    const countCol = screen === 'raw' ? 'raw_record_count' : 'staging_record_count';
    const [deletingId, setDeletingId] = useState<string | null>(null);

    const handleDelete = async (runId: string, state: string) => {
        if (!onDeleteRun) return;
        if (state === 'RUNNING') {
            window.alert('This run is still processing. Wait for it to finish or cancel it from Ingestion Runs first.');
            return;
        }
        const ok = window.confirm(
            'Delete this ingestion run and all of its raw and staging records? This cannot be undone.',
        );
        if (!ok) return;
        setDeletingId(runId);
        try {
            await onDeleteRun(runId);
        } finally {
            setDeletingId(null);
        }
    };

    return (
        <div className="il-lineage-card ir-table-card">
            <div className="il-lineage-toolbar">
                <h2 className="il-lineage-toolbar__title">Ingestion runs</h2>
                <p className="il-lineage-toolbar__sub">
                    Each run is a separate batch. Select a run to view its {screenLabel} records.
                </p>
            </div>
            <div className="ir-table-wrap">
                <table className="ir-table">
                    <thead>
                        <tr>
                            <th>Run ID</th>
                            <th>Source</th>
                            <th>Entity</th>
                            <th>Run type</th>
                            <th>Status</th>
                            <th>Raw</th>
                            <th>Staging</th>
                            <th>Lineage</th>
                            <th>Started</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading && lineage.length === 0 ? (
                            <tr className="il-lineage-empty">
                                <td colSpan={10}>Loading runs…</td>
                            </tr>
                        ) : lineage.length === 0 ? (
                            <tr className="il-lineage-empty">
                                <td colSpan={10}>No ingestion runs yet. Start one from Ingestion Runs.</td>
                            </tr>
                        ) : (
                            lineage.map((row) => {
                                const isActive = activeRunId === row.run_id;
                                const isRunning = row.state === 'RUNNING';
                                return (
                                    <tr
                                        key={row.run_id}
                                        className={`ir-table-row il-table-row--scoped${isActive ? ' il-table-row--active' : ''}`}
                                        onClick={() => onSelectRun(row.run_id)}
                                    >
                                        <td>
                                            <code className="ir-run-id">{row.run_id.slice(0, 8)}…</code>
                                        </td>
                                        <td>
                                            <div className="ir-source-cell">
                                                <div className="ir-source-avatar">
                                                    {row.source_name.slice(0, 2).toUpperCase()}
                                                </div>
                                                <span className="ir-source-name">{row.source_name}</span>
                                            </div>
                                        </td>
                                        <td>
                                            {row.entity_type ? (
                                                <span className="ir-entity-chip">{row.entity_type}</span>
                                            ) : (
                                                '—'
                                            )}
                                        </td>
                                        <td>
                                            <span className="ir-run-type">{row.run_type || '—'}</span>
                                        </td>
                                        <td>
                                            <RunStatusBadge status={row.state as RunStatus} />
                                        </td>
                                        <td>
                                            <span className="ir-count-cell">{row.raw_record_count}</span>
                                        </td>
                                        <td>
                                            <span className="ir-count-cell">{row.staging_record_count}</span>
                                        </td>
                                        <td>
                                            {row[countCol] === 0 ? (
                                                <span className="ir-count-cell--muted">—</span>
                                            ) : row.counts_aligned ? (
                                                <span className="ir-count-cell">1:1</span>
                                            ) : (
                                                <span className="il-lineage-warn" title={row.pipeline_note}>
                                                    mismatch
                                                </span>
                                            )}
                                        </td>
                                        <td>
                                            <span className="ir-ts">{formatLineageTimestamp(row.created_at)}</span>
                                        </td>
                                        <td onClick={(e) => e.stopPropagation()}>
                                            <div className="ir-action-row">
                                                <Link
                                                    to={`/raw-landing?runId=${encodeURIComponent(row.run_id)}`}
                                                    className="ir-action-btn ir-action-btn--primary"
                                                    onClick={() => onSelectRun(row.run_id)}
                                                >
                                                    Raw
                                                </Link>
                                                <Link
                                                    to={`/staging?runId=${encodeURIComponent(row.run_id)}`}
                                                    className="ir-action-btn"
                                                    onClick={() => onSelectRun(row.run_id)}
                                                >
                                                    Staging
                                                </Link>
                                                {onDeleteRun && (
                                                    <button
                                                        type="button"
                                                        className="ir-action-btn ir-action-btn--danger"
                                                        disabled={deletingId === row.run_id || isRunning}
                                                        title={
                                                            isRunning
                                                                ? 'Cannot delete while pipeline is running'
                                                                : 'Delete run and all raw/staging data'
                                                        }
                                                        onClick={() => void handleDelete(row.run_id, row.state)}
                                                    >
                                                        {deletingId === row.run_id ? '…' : 'Delete'}
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
        </div>
    );
}
