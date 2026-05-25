// MDM_Frontend/src/pages/domains/Domains.tsx
import { useState, useEffect, useCallback } from 'react';
import {
  domainService,
  type DomainRecord,
  type DomainCreatePayload,
  type DomainUpdatePayload,
  ApiError,
} from '../../services/domainService';
import { useTenantConfig } from '../../context/TenantConfigContext';
import { useSnackbar } from '../../context/SnackbarContext';
import '../../styles/theme.css';
import '../../styles/Domains.css';

/* ─── Status Badge ──────────────────────────────────────────────────────── */

function StatusBadge({ status }: { status: DomainRecord['status'] }) {
  const map: Record<DomainRecord['status'], { cls: string; label: string }> = {
    ACTIVE:      { cls: 'dm-badge--green', label: 'Active' },
    DEACTIVATED: { cls: 'dm-badge--red',   label: 'Deactivated' },
    SUSPENDED:   { cls: 'dm-badge--amber', label: 'Suspended' },
    ARCHIVED:    { cls: 'dm-badge--amber', label: 'Archived' },
  };
  const { cls, label } = map[status] ?? map.DEACTIVATED;
  return <span className={`dm-badge ${cls}`}>{label}</span>;
}

/* ─── Create Modal ──────────────────────────────────────────────────────── */

function CreateDomainModal({
  onClose,
  onCreate,
  saving,
}: {
  onClose: () => void;
  onCreate: (payload: DomainCreatePayload) => void;
  saving: boolean;
}) {
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleSubmit = () => {
    const errs: Record<string, string> = {};
    if (!name.trim()) errs.name = 'Domain name is required.';
    else if (name.trim().length > 100) errs.name = 'Max 100 characters.';
    setErrors(errs);
    if (Object.keys(errs).length) return;
    onCreate({ domain_name: name.trim(), description: desc.trim() || undefined });
  };

  return (
    <div className="dm-modal-overlay" onClick={onClose}>
      <div className="dm-modal" onClick={e => e.stopPropagation()}>
        <div className="dm-modal__header">
          <h2 className="dm-modal__title">Register New Domain</h2>
          <button className="dm-modal__close" onClick={onClose}>✕</button>
        </div>
        <div className="dm-modal__body">
          <div className={`dm-field${errors.name ? ' dm-field--error' : ''}`}>
            <label className="dm-label">Domain Name <span className="dm-required">*</span></label>
            <input
              id="dm-create-name"
              className="dm-input"
              placeholder="e.g. Customer, Finance, HR"
              value={name}
              onChange={e => setName(e.target.value)}
              autoFocus
            />
            {errors.name && <span className="dm-error-msg">{errors.name}</span>}
          </div>
          <div className="dm-field">
            <label className="dm-label">Description</label>
            <textarea
              id="dm-create-desc"
              className="dm-textarea"
              placeholder="Brief description of the data domain (optional)"
              value={desc}
              onChange={e => setDesc(e.target.value)}
              rows={3}
            />
          </div>
        </div>
        <div className="dm-modal__footer">
          <button className="dm-btn dm-btn--ghost" onClick={onClose} disabled={saving}>Cancel</button>
          <button className="dm-btn dm-btn--primary" onClick={handleSubmit} disabled={saving}>
            {saving ? '⏳ Creating…' : '✓ Create Domain'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Edit Drawer ───────────────────────────────────────────────────────── */

function EditDomainDrawer({
  domain,
  onClose,
  onSave,
  saving,
}: {
  domain: DomainRecord;
  onClose: () => void;
  onSave: (id: string, payload: DomainUpdatePayload) => void;
  saving: boolean;
}) {
  const [name, setName] = useState(domain.domainName);
  const [desc, setDesc] = useState(domain.description);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleSubmit = () => {
    const errs: Record<string, string> = {};
    if (!name.trim()) errs.name = 'Domain name is required.';
    setErrors(errs);
    if (Object.keys(errs).length) return;

    const payload: DomainUpdatePayload = {};
    if (name.trim() !== domain.domainName) payload.domain_name = name.trim();
    if (desc.trim() !== domain.description) payload.description = desc.trim();

    if (Object.keys(payload).length === 0) {
      onClose();
      return;
    }
    onSave(domain.id, payload);
  };

  return (
    <div className="dm-drawer-overlay" onClick={onClose}>
      <div className="dm-drawer" onClick={e => e.stopPropagation()}>
        <div className="dm-drawer__header">
          <div>
            <h2 className="dm-drawer__title">Edit Domain</h2>
            <div className="dm-drawer__subtitle">{domain.domainName}</div>
          </div>
          <button className="dm-drawer__close" onClick={onClose}>✕</button>
        </div>
        <div className="dm-drawer__body">
          <div className="dm-drawer__grid">
            <div className="dm-drawer__field">
              <span className="dm-drawer__field-label">Status</span>
              <StatusBadge status={domain.status} />
            </div>
            <div className="dm-drawer__field">
              <span className="dm-drawer__field-label">Created</span>
              <span className="dm-drawer__field-value">{domain.createdDate}</span>
            </div>
          </div>

          <div className={`dm-field${errors.name ? ' dm-field--error' : ''}`}>
            <label className="dm-label">Domain Name <span className="dm-required">*</span></label>
            <input
              id="dm-edit-name"
              className="dm-input"
              value={name}
              onChange={e => setName(e.target.value)}
            />
            {errors.name && <span className="dm-error-msg">{errors.name}</span>}
          </div>
          <div className="dm-field">
            <label className="dm-label">Description</label>
            <textarea
              id="dm-edit-desc"
              className="dm-textarea"
              value={desc}
              onChange={e => setDesc(e.target.value)}
              rows={3}
            />
          </div>
        </div>
        <div className="dm-drawer__footer">
          <button className="dm-btn dm-btn--ghost" onClick={onClose} disabled={saving}>Cancel</button>
          <button className="dm-btn dm-btn--primary" onClick={handleSubmit} disabled={saving}>
            {saving ? '⏳ Saving…' : '✓ Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Main Page ─────────────────────────────────────────────────────────── */

export default function Domains() {
  const { activeTenantId } = useTenantConfig();
  const snackbar = useSnackbar();

  const [domains, setDomains]   = useState<DomainRecord[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [search, setSearch]     = useState('');
  const [filterStatus, setFilterStatus] = useState('ALL');

  // Modals/drawers
  const [showCreate, setShowCreate]     = useState(false);
  const [editDomain, setEditDomain]     = useState<DomainRecord | null>(null);
  const [saving, setSaving]             = useState(false);
  const [deactivating, setDeactivating] = useState<string | null>(null);

  /* ── Load domains ──────────────────────────────────────────────────── */
  const loadDomains = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const tId = activeTenantId ?? undefined;
      const data = await domainService.listDomains(0, 200, tId);
      setDomains(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load domains.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [activeTenantId]);

  useEffect(() => { loadDomains(); }, [loadDomains]);

  /* ── Create ────────────────────────────────────────────────────────── */
  const handleCreate = async (payload: DomainCreatePayload) => {
    setSaving(true);
    try {
      const newDomain = await domainService.createDomain(payload, activeTenantId ?? undefined);
      setDomains(prev => [newDomain, ...prev]);
      setShowCreate(false);
      snackbar.showSuccess(`Domain "${newDomain.domainName}" created successfully.`);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Create failed';
      snackbar.showError(`Failed to create domain: ${msg}`);
    } finally {
      setSaving(false);
    }
  };

  /* ── Update ────────────────────────────────────────────────────────── */
  const handleUpdate = async (id: string, payload: DomainUpdatePayload) => {
    setSaving(true);
    try {
      const updated = await domainService.updateDomain(id, payload);
      setDomains(prev => prev.map(d => d.id === updated.id ? updated : d));
      setEditDomain(null);
      snackbar.showSuccess(`Domain "${updated.domainName}" updated successfully.`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Update failed';
      snackbar.showError(`Failed to update domain: ${msg}`);
    } finally {
      setSaving(false);
    }
  };

  /* ── Deactivate ────────────────────────────────────────────────────── */
  const handleDeactivate = async (domain: DomainRecord) => {
    if (!window.confirm(`Deactivate domain "${domain.domainName}"? It will no longer be available for new upload sessions.`)) return;
    setDeactivating(domain.id);
    try {
      const updated = await domainService.deleteDomain(domain.id);
      setDomains(prev => prev.map(d => d.id === updated.id ? updated : d));
      snackbar.showSuccess(`Domain "${domain.domainName}" deactivated.`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Deactivation failed';
      snackbar.showError(`Failed to deactivate domain: ${msg}`);
    } finally {
      setDeactivating(null);
    }
  };

  /* ── Filtering ─────────────────────────────────────────────────────── */
  const filtered = domains.filter(d => {
    const q = search.toLowerCase();
    return (
      (d.domainName.toLowerCase().includes(q) || d.description.toLowerCase().includes(q)) &&
      (filterStatus === 'ALL' || d.status === filterStatus)
    );
  });

  const totalActive  = domains.filter(d => d.status === 'ACTIVE').length;
  const totalInactive = domains.filter(d => d.status === 'DEACTIVATED').length;
  const totalOther    = domains.filter(d => d.status === 'SUSPENDED' || d.status === 'ARCHIVED').length;

  return (
    <div className="dm-page">
      {/* Header */}
      <div className="dm-page-header">
        <div>
          <h1 className="dm-page-title">Domains</h1>
          <p className="dm-page-subtitle">Register and manage data classification domains for your tenant</p>
        </div>
        <div className="dm-page-header__actions">
          <button className="dm-btn dm-btn--ghost" onClick={loadDomains} disabled={loading}>
            {loading ? '…' : '↻'} Refresh
          </button>
          <button className="dm-btn dm-btn--primary" onClick={() => setShowCreate(true)}>
            + Register Domain
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="dm-error-banner">
          <span className="dm-error-banner__icon">⚠</span>
          <span>{error}</span>
        </div>
      )}

      {/* Summary Cards */}
      <div className="dm-summary-row">
        <div className="dm-summary-card dm-summary-card--purple">
          <span className="dm-summary-card__value">{domains.length}</span>
          <span className="dm-summary-card__label">Total Domains</span>
        </div>
        <div className="dm-summary-card dm-summary-card--green">
          <span className="dm-summary-card__value">{totalActive}</span>
          <span className="dm-summary-card__label">Active</span>
        </div>
        <div className="dm-summary-card dm-summary-card--red">
          <span className="dm-summary-card__value">{totalInactive}</span>
          <span className="dm-summary-card__label">Deactivated</span>
        </div>
        <div className="dm-summary-card dm-summary-card--amber">
          <span className="dm-summary-card__value">{totalOther}</span>
          <span className="dm-summary-card__label">Suspended/Archived</span>
        </div>
      </div>

      {/* Table Card */}
      <div className="dm-table-card">
        <div className="dm-table-toolbar">
          <div className="dm-search-wrap">
            <span className="dm-search-icon">🔍</span>
            <input
              id="dm-search"
              className="dm-search-input"
              placeholder="Search by name or description…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div className="dm-filter-row">
            <select
              id="dm-filter-status"
              className="dm-select"
              value={filterStatus}
              onChange={e => setFilterStatus(e.target.value)}
            >
              <option value="ALL">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="DEACTIVATED">Deactivated</option>
              <option value="SUSPENDED">Suspended</option>
              <option value="ARCHIVED">Archived</option>
            </select>
            <span className="dm-count-label">
              {filtered.length} record{filtered.length !== 1 ? 's' : ''}
            </span>
          </div>
        </div>

        <div className="dm-table-wrap">
          {loading ? (
            <div className="dm-loading">
              <div className="dm-spinner" />
              Loading domains…
            </div>
          ) : (
            <table className="dm-table">
              <thead>
                <tr>
                  <th>Domain Name</th>
                  <th>Description</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Updated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="dm-table-empty">
                      <span>🏷️</span>
                      <p>No domains found</p>
                    </td>
                  </tr>
                ) : filtered.map(domain => (
                  <tr key={domain.id} className="dm-table-row">
                    <td>
                      <div className="dm-domain-name">
                        <div className="dm-domain-avatar">
                          {domain.domainName.slice(0, 2).toUpperCase()}
                        </div>
                        <span className="dm-domain-name__text">{domain.domainName}</span>
                      </div>
                    </td>
                    <td>
                      <span className="dm-desc" title={domain.description}>
                        {domain.description || '—'}
                      </span>
                    </td>
                    <td><StatusBadge status={domain.status} /></td>
                    <td className="dm-date">{domain.createdDate}</td>
                    <td className="dm-date">{domain.updatedDate}</td>
                    <td>
                      <div className="dm-action-row">
                        <button
                          className="dm-action-btn"
                          onClick={() => setEditDomain(domain)}
                        >
                          Edit
                        </button>
                        {domain.status === 'ACTIVE' && (
                          <button
                            className="dm-action-btn dm-action-btn--danger"
                            onClick={() => handleDeactivate(domain)}
                            disabled={deactivating === domain.id}
                          >
                            {deactivating === domain.id ? '…' : 'Deactivate'}
                          </button>
                        )}
                        {domain.status === 'DEACTIVATED' && (
                          <button
                            className="dm-action-btn dm-action-btn--primary"
                            onClick={async () => {
                              try {
                                const updated = await domainService.updateDomain(domain.id, { status: 'ACTIVE' });
                                setDomains(prev => prev.map(d => d.id === updated.id ? updated : d));
                                snackbar.showSuccess(`Domain "${domain.domainName}" reactivated.`);
                              } catch (err) {
                                snackbar.showError(err instanceof Error ? err.message : 'Failed to reactivate.');
                              }
                            }}
                          >
                            Activate
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <CreateDomainModal
          onClose={() => setShowCreate(false)}
          onCreate={handleCreate}
          saving={saving}
        />
      )}

      {/* Edit Drawer */}
      {editDomain && (
        <EditDomainDrawer
          domain={editDomain}
          onClose={() => setEditDomain(null)}
          onSave={handleUpdate}
          saving={saving}
        />
      )}
    </div>
  );
}
