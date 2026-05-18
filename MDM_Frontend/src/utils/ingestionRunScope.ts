import type { IngestionLineageRunSummary } from '../services/ingestionRunService';

/** Human-readable option label for run select elements. */
export function formatRunOptionLabel(row: IngestionLineageRunSummary): string {
    const date = row.created_at.includes('T')
        ? row.created_at.slice(0, 16).replace('T', ' ')
        : row.created_at.slice(0, 16);
    const entity = row.entity_type || '—';
    const runType = row.run_type || '—';
    return `${row.run_id.slice(0, 8)}… · ${row.source_name} · ${entity} · ${runType} · ${date}`;
}

/**
 * Pick the run to scope Raw/Staging tables.
 * URL wins; otherwise newest run (lineage is created_at desc) with rows for the screen.
 */
export function resolveInitialRunId(
    urlRunId: string | null,
    lineage: IngestionLineageRunSummary[],
    screen: 'raw' | 'staging',
): string {
    if (urlRunId) return urlRunId;
    const countKey = screen === 'raw' ? 'raw_record_count' : 'staging_record_count';
    const withRows = lineage.filter((l) => l[countKey] > 0);
    if (withRows.length > 0) return withRows[0].run_id;
    if (lineage.length > 0) return lineage[0].run_id;
    return 'ALL';
}

export function formatLineageTimestamp(iso: string): string {
    return iso.includes('T') ? iso.replace('T', ' ').slice(0, 19) : iso.slice(0, 19);
}
