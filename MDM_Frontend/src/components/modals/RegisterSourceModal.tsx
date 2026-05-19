import { useState, useEffect } from 'react';
import {
  sourceService,
  type SourceRecord,
  type SourceType,
  type ConnectionType,
  type EntityType,
  SOURCE_TYPES,
  CONNECTION_TYPES,
  ENTITY_TYPES,
} from '../../services/sourceService';
import { tenantService, type TenantRecord } from '../../services/tenantService';
import { useAuth } from '../../context/AuthContext';

/* Import Styles */
import '../../styles/theme.css';
import '../../styles/RegisterSourceModal.css';

/* ─── Types & constants ──────────────────────────────────────── */
interface PriorityRow { attribute: string; priority: number }
interface FormErrors { 
  tenantId?: string;
  sourceName?: string; 
  sourceCode?: string; 
  sourceType?: string; 
  connectionType?: string; 
  supportedEntities?: string 
}

const DEFAULT_PRIORITY: Partial<Record<EntityType, PriorityRow[]>> = {
  CUSTOMER: [
    { attribute: 'customer_name', priority: 1 }, { attribute: 'email', priority: 1 }, { attribute: 'phone', priority: 2 }, { attribute: 'billing_address', priority: 3 },
    { attribute: 'shipping_address', priority: 3 }, { attribute: 'date_of_birth', priority: 4 }, { attribute: 'loyalty_tier', priority: 4 }, { attribute: 'status', priority: 2 }, { attribute: 'created_at', priority: 5 }
  ],
  SUPPLIER: [
    { attribute: 'supplier_name', priority: 1 }, { attribute: 'tax_id', priority: 1 }, { attribute: 'contact_email', priority: 2 }, { attribute: 'contact_phone', priority: 2 },
    { attribute: 'payment_terms', priority: 3 }, { attribute: 'rating', priority: 4 }, { attribute: 'website_url', priority: 5 }, { attribute: 'supplier_status', priority: 2 }
  ],
  PRODUCT: [
    { attribute: 'product_name', priority: 1 }, { attribute: 'sku', priority: 1 }, { attribute: 'category', priority: 2 }, { attribute: 'price', priority: 2 },
    { attribute: 'stock_quantity', priority: 3 }, { attribute: 'manufacturer', priority: 3 }, { attribute: 'weight', priority: 4 }, { attribute: 'dimensions', priority: 4 }, { attribute: 'is_active', priority: 2 }
  ],
  ACCOUNT: [
    { attribute: 'account_name', priority: 1 }, { attribute: 'account_number', priority: 1 }, { attribute: 'currency', priority: 2 }, { attribute: 'account_type', priority: 2 },
    { attribute: 'balance', priority: 3 }, { attribute: 'branch_code', priority: 3 }, { attribute: 'swift_code', priority: 4 }, { attribute: 'opened_date', priority: 4 }
  ],
  ASSET: [
    { attribute: 'asset_name', priority: 1 }, { attribute: 'asset_id', priority: 1 }, { attribute: 'location', priority: 2 }, { attribute: 'purchase_date', priority: 3 },
    { attribute: 'value', priority: 3 }, { attribute: 'depreciation_rate', priority: 4 }, { attribute: 'status', priority: 2 }, { attribute: 'assigned_to', priority: 3 }
  ],
  LOCATION: [
    { attribute: 'location_name', priority: 1 }, { attribute: 'address', priority: 1 }, { attribute: 'region', priority: 2 }, { attribute: 'country', priority: 2 },
    { attribute: 'postal_code', priority: 3 }, { attribute: 'latitude', priority: 4 }, { attribute: 'longitude', priority: 4 }, { attribute: 'capacity', priority: 5 }
  ],
  EMPLOYEE: [
    { attribute: 'name', priority: 1 }, { attribute: 'employee_id', priority: 1 }, { attribute: 'department', priority: 2 }, { attribute: 'role', priority: 2 },
    { attribute: 'email', priority: 2 }, { attribute: 'phone', priority: 3 }, { attribute: 'hire_date', priority: 3 }, { attribute: 'manager_id', priority: 4 }, { attribute: 'salary_band', priority: 5 }
  ],
  OTHER: [
    { attribute: 'name', priority: 1 }, { attribute: 'description', priority: 2 }, { attribute: 'type', priority: 2 }, { attribute: 'status', priority: 3 },
    { attribute: 'metadata_json', priority: 4 }, { attribute: 'created_by', priority: 5 }
  ],
};

const CONN_FIELDS: Record<ConnectionType, { field: string; label: string; type?: string; placeholder?: string }[]> = {
  REST_API: [{ field: 'baseUrl', label: 'Base URL', type: 'url', placeholder: 'https://api.example.com' }, { field: 'authType', label: 'Auth Type', placeholder: 'Bearer / OAuth2 / Basic' }, { field: 'apiKey', label: 'API Key', type: 'password', placeholder: '••••••••••••••••' }, { field: 'timeout', label: 'Timeout (ms)', type: 'number', placeholder: '30000' }],
  CSV: [{ field: 'fileFormat', label: 'File Format', placeholder: 'CSV' }, { field: 'delimiter', label: 'Delimiter', placeholder: ',' }, { field: 'encoding', label: 'Encoding', placeholder: 'UTF-8' }, { field: 'path', label: 'File Path / URL', placeholder: '/data/import.csv' }],
  JSON: [{ field: 'fileFormat', label: 'File Format', placeholder: 'JSON' }, { field: 'encoding', label: 'Encoding', placeholder: 'UTF-8' }, { field: 'path', label: 'File Path / URL', placeholder: '/data/import.json' }],
  JDBC: [{ field: 'host', label: 'Host', placeholder: 'db.example.com' }, { field: 'port', label: 'Port', type: 'number', placeholder: '5432' }, { field: 'database', label: 'Database', placeholder: 'mdm_source' }, { field: 'username', label: 'Username', placeholder: 'db_user' }, { field: 'password', label: 'Password', type: 'password', placeholder: '••••••••' }],
  SFTP: [{ field: 'host', label: 'Host', placeholder: 'sftp.example.com' }, { field: 'port', label: 'Port', type: 'number', placeholder: '22' }, { field: 'remotePath', label: 'Remote Path', placeholder: '/data/incoming' }, { field: 'username', label: 'Username', placeholder: 'sftp_user' }, { field: 'privateKey', label: 'Private Key (path)', placeholder: '/keys/id_rsa' }],
  S3: [{ field: 'bucket', label: 'Bucket Name', placeholder: 'my-mdm-bucket' }, { field: 'region', label: 'Region', placeholder: 'us-east-1' }, { field: 'prefix', label: 'Key Prefix', placeholder: 'data/imports/' }, { field: 'accessKey', label: 'Access Key ID', placeholder: 'AKIA…' }, { field: 'secretKey', label: 'Secret Access Key', type: 'password', placeholder: '••••••••' }],
  OTHER: [{ field: 'notes', label: 'Notes / Description', placeholder: 'Describe the connection…' }],
};

const ALL_ENTITIES = ENTITY_TYPES;
const ENTITY_ICONS: Record<EntityType, string> = {
  CUSTOMER: '👤',
  SUPPLIER: '🏭',
  PRODUCT: '📦',
  ACCOUNT: '💼',
  ASSET: '🖥',
  LOCATION: '📍',
  EMPLOYEE: '👥',
  OTHER: '⚙️'
};
const STEP_LABELS_DEFAULT = ['Basic Info', 'Entities', 'Priority', 'Connection'];
const STEP_LABELS_SUPER   = ['Select Tenant', 'Basic Info', 'Entities', 'Priority', 'Connection'];

/* ─── Props ──────────────────────────────────────────────────── */
interface Props {
  onClose: () => void;
  onRegister: (record: SourceRecord) => void;
}

/* ─── Component ──────────────────────────────────────────────── */
export default function RegisterSourceModal({ onClose, onRegister }: Props) {
  const { admin } = useAuth();
  const isSuperAdmin = admin?.tenant_id === 'platform';

  const [step, setStep] = useState(1);
  const [tenants, setTenants] = useState<TenantRecord[]>([]);
  const [targetTenantId, setTargetTenantId] = useState('');
  const [loadingTenants, setLoadingTenants] = useState(false);

  const [sourceName, setSourceName] = useState('');
  const [sourceCode, setSourceCode] = useState('');
  const [sourceType, setSourceType] = useState<SourceType | ''>('');
  const [connectionType, setConnectionType] = useState<ConnectionType | ''>('');
  const [entities, setEntities] = useState<EntityType[]>([]);
  const [priorityConfig, setPriorityConfig] = useState<Record<string, PriorityRow[]>>({});
  const [connConfig, setConnConfig] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<FormErrors>({});
  const [codeEdited, setCodeEdited] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const stepLabels = isSuperAdmin ? STEP_LABELS_SUPER : STEP_LABELS_DEFAULT;
  const totalSteps = stepLabels.length;

  // Fetch tenants for SuperAdmin
  useEffect(() => {
    if (isSuperAdmin) {
      setLoadingTenants(true);
      tenantService.listTenants()
        .then(res => setTenants(res))
        .catch(() => setSubmitError('Failed to load tenants list.'))
        .finally(() => setLoadingTenants(false));
    }
  }, [isSuperAdmin]);

  // Auto-generate lowercase slug
  useEffect(() => {
    if (sourceName && !codeEdited) {
      setSourceCode(
        sourceName.toLowerCase().replace(/[^a-z0-9\s]/g, '').trim().replace(/\s+/g, '_'),
      );
    }
  }, [sourceName, codeEdited]);

  useEffect(() => {
    setPriorityConfig(prev => {
      const next: Record<string, PriorityRow[]> = {};
      entities.forEach(e => { 
        next[e] = prev[e] || DEFAULT_PRIORITY[e] || []; 
      });
      return next;
    });
  }, [entities]);

  const toggleEntity = (e: EntityType) =>
    setEntities(prev => prev.includes(e) ? prev.filter(x => x !== e) : [...prev, e]);

  const handleNext = () => {
    // SuperAdmin Tenant Step
    if (isSuperAdmin && step === 1) {
      if (!targetTenantId) {
        setErrors({ tenantId: 'Please select a tenant first' });
        return;
      }
    }

    // Basic Info Step (Step 1 for standard, Step 2 for SuperAdmin)
    const basicInfoStep = isSuperAdmin ? 2 : 1;
    if (step === basicInfoStep) {
      const errs: FormErrors = {};
      if (!sourceName.trim()) errs.sourceName = 'Source name is required';
      if (!sourceCode.trim()) errs.sourceCode = 'Source code is required';
      else if (!/^[a-z0-9_\-]+$/.test(sourceCode)) errs.sourceCode = 'Lowercase letters, digits, underscores or hyphens only';
      if (!sourceType) errs.sourceType = 'Source type is required';
      if (!connectionType) errs.connectionType = 'Connection type is required';
      if (Object.keys(errs).length) { setErrors(errs); return; }
    }

    const entitiesStep = isSuperAdmin ? 3 : 2;
    if (step === entitiesStep && entities.length === 0) { 
      setErrors({ supportedEntities: 'Select at least one entity' }); 
      return; 
    }

    setErrors({});
    setStep(s => Math.min(s + 1, totalSteps));
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const record = await sourceService.registerSource({
        source_name: sourceName,
        source_code: sourceCode,
        source_type: sourceType as SourceType,
        connection_type: connectionType as ConnectionType,
        config_json: {
          supported_entities: entities,
          priority_config: priorityConfig,
          connection_config: connConfig,
        },
      }, isSuperAdmin ? targetTenantId : undefined);
      onRegister(record);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Registration failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="rsm-overlay" onClick={onClose}>
      <div className="rsm-modal" onClick={e => e.stopPropagation()} role="dialog" aria-modal="true">

        {/* Header */}
        <div className="rsm-header">
          <div>
            <h2 className="rsm-header__title">Register Source System</h2>
            <p className="rsm-header__sub">Step {step} of {totalSteps} — {stepLabels[step - 1]}</p>
          </div>
          <button className="rsm-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        {/* Stepper */}
        <div className="rsm-stepper">
          {stepLabels.map((label, i) => (
            <div key={label} className={`rsm-step${i + 1 === step ? ' rsm-step--active' : ''}${i + 1 < step ? ' rsm-step--done' : ''}`}>
              <div className="rsm-step__dot">{i + 1 < step ? '✓' : i + 1}</div>
              <span className="rsm-step__label">{label}</span>
              {i < totalSteps - 1 && <div className="rsm-step__line" />}
            </div>
          ))}
        </div>

        {/* Body */}
        <div className="rsm-body">

          {/* Step 1 (SuperAdmin Only) — Tenant Selection */}
          {isSuperAdmin && step === 1 && (
            <div className="rsm-section">
              <p className="rsm-section-desc">You are logged in as SuperAdmin. Please select the tenant for which you want to register this source system.</p>
              <div className={`rsm-field${errors.tenantId ? ' rsm-field--error' : ''}`}>
                <label htmlFor="rsm-tenant-id" className="rsm-label">Target Tenant <span className="rsm-required">*</span></label>
                {loadingTenants ? (
                  <div className="rsm-loading-inline">Loading tenants...</div>
                ) : (
                  <select 
                    id="rsm-tenant-id" 
                    className="rsm-select" 
                    value={targetTenantId} 
                    onChange={e => { setTargetTenantId(e.target.value); setErrors({}); }}
                  >
                    <option value="">— Select tenant —</option>
                    {tenants.map(t => (
                      <option key={t.id} value={t.id}>{t.tenantName} ({t.tenantCode})</option>
                    ))}
                  </select>
                )}
                {errors.tenantId && <span className="rsm-error-msg">{errors.tenantId}</span>}
              </div>
              <div className="rsm-alert rsm-alert--info" style={{ marginTop: '20px' }}>
                ℹ This source system will be isolated and exclusively available to the selected tenant.
              </div>
            </div>
          )}

          {/* Step Basic Info (Step 1 or 2) */}
          {step === (isSuperAdmin ? 2 : 1) && (
            <div className="rsm-section">
              <div className="rsm-field-grid">
                <div className={`rsm-field${errors.sourceName ? ' rsm-field--error' : ''}`}>
                  <label htmlFor="rsm-source-name" className="rsm-label">📝 Source Name <span className="rsm-required">*</span></label>
                  <input id="rsm-source-name" className="rsm-input" placeholder="e.g. Salesforce CRM" value={sourceName} onChange={e => setSourceName(e.target.value)} />
                  {errors.sourceName && <span className="rsm-error-msg">{errors.sourceName}</span>}
                </div>
                <div className={`rsm-field${errors.sourceCode ? ' rsm-field--error' : ''}`}>
                  <label htmlFor="rsm-source-code" className="rsm-label">🔑 Source Code <span className="rsm-required">*</span><span className="rsm-hint">AUTO-GENERATED</span></label>
                  <input id="rsm-source-code" className="rsm-input rsm-input--mono" placeholder="salesforce_crm" value={sourceCode}
                    onChange={e => { setCodeEdited(true); setSourceCode(e.target.value.toLowerCase().replace(/[^a-z0-9_\-]/g, '')); }} />
                  {errors.sourceCode && <span className="rsm-error-msg">{errors.sourceCode}</span>}
                </div>
                <div className={`rsm-field${errors.sourceType ? ' rsm-field--error' : ''}`}>
                  <label htmlFor="rsm-source-type" className="rsm-label">🗂️ Source Type <span className="rsm-required">*</span></label>
                  <select id="rsm-source-type" className="rsm-select" value={sourceType} onChange={e => setSourceType(e.target.value as SourceType)}>
                    <option value="">— Select type —</option>
                    {SOURCE_TYPES.map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                  {errors.sourceType && <span className="rsm-error-msg">{errors.sourceType}</span>}
                </div>
                <div className={`rsm-field${errors.connectionType ? ' rsm-field--error' : ''}`}>
                  <label htmlFor="rsm-conn-type" className="rsm-label">🔌 Connection Type <span className="rsm-required">*</span></label>
                  <select id="rsm-conn-type" className="rsm-select" value={connectionType} onChange={e => setConnectionType(e.target.value as ConnectionType)}>
                    <option value="">— Select connection —</option>
                    {CONNECTION_TYPES.map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                  {errors.connectionType && <span className="rsm-error-msg">{errors.connectionType}</span>}
                </div>
              </div>
            </div>
          )}

          {/* Step Entities (Step 2 or 3) */}
          {step === (isSuperAdmin ? 3 : 2) && (
            <div className="rsm-section">
              <p className="rsm-section-desc">Select all entity types this source system provides data for.</p>
              {errors.supportedEntities && <div className="rsm-alert rsm-alert--error">{errors.supportedEntities}</div>}
              <div className="rsm-entity-grid">
                {ALL_ENTITIES.map(e => (
                  <button
                    key={e}
                    type="button"
                    className={`rsm-entity-card${entities.includes(e) ? ' rsm-entity-card--selected' : ''}`}
                    onClick={() => toggleEntity(e)}
                  >
                    <span className="rsm-entity-icon">{ENTITY_ICONS[e]}</span>
                    <span className="rsm-entity-name">{e}</span>
                    {entities.includes(e) && <span className="rsm-entity-check">✓</span>}
                  </button>
                ))}
              </div>
              <p className="rsm-entity-count">{entities.length} selected</p>
            </div>
          )}

          {/* Step Priority (Step 3 or 4) */}
          {step === (isSuperAdmin ? 4 : 3) && (
            <div className="rsm-section">
              <p className="rsm-section-desc">Configure attribute priority per entity. Lower number = higher priority.</p>
              {entities.length === 0 && (
                <div className="rsm-alert rsm-alert--info">No entities selected. Go back to Step 2.</div>
              )}
              {entities.map(entity => (
                <div key={entity} className="rsm-priority-block">
                  <div className="rsm-priority-block__header">
                    <span className="rsm-priority-block__entity">{entity}</span>
                  </div>
                  <table className="rsm-priority-table">
                    <thead>
                      <tr><th>Attribute</th><th style={{ width: '120px' }}>Priority</th></tr>
                    </thead>
                    <tbody>
                      {(priorityConfig[entity] || []).map((row, idx) => (
                        <tr key={row.attribute}>
                          <td><code className="rsm-attr-code">{row.attribute}</code></td>
                          <td>
                            <input
                              type="number" min={1} max={10}
                              className="rsm-priority-input"
                              value={row.priority}
                              onChange={e => setPriorityConfig(prev => ({
                                ...prev,
                                [entity]: prev[entity].map((r, i) => i === idx ? { ...r, priority: Number(e.target.value) } : r),
                              }))}
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          )}

          {/* Step Connection (Step 4 or 5) */}
          {step === (isSuperAdmin ? 5 : 4) && (
            <div className="rsm-section">
              {!connectionType ? (
                <div className="rsm-alert rsm-alert--info">No connection type selected. Go back to Step 1.</div>
              ) : (
                <>
                  <div className="rsm-conn-type-badge">
                    <span>Connection: </span><strong>{connectionType}</strong>
                  </div>
                  <div className="rsm-field-grid">
                    {CONN_FIELDS[connectionType as ConnectionType]?.map(f => (
                      <div key={f.field} className="rsm-field">
                        <label htmlFor={`rsm-conn-${f.field}`} className="rsm-label">{f.label}</label>
                        {f.field === 'notes' ? (
                          <textarea
                            id={`rsm-conn-${f.field}`}
                            className="rsm-textarea"
                            placeholder={f.placeholder}
                            rows={4}
                            value={connConfig[f.field] || ''}
                            onChange={e => setConnConfig(c => ({ ...c, [f.field]: e.target.value }))}
                          />
                        ) : (
                          <input
                            id={`rsm-conn-${f.field}`}
                            className="rsm-input"
                            type={f.type || 'text'}
                            placeholder={f.placeholder}
                            value={connConfig[f.field] || ''}
                            onChange={e => setConnConfig(c => ({ ...c, [f.field]: e.target.value }))}
                          />
                        )}
                      </div>
                    ))}
                  </div>
                  <p className="rsm-note">⚠ Connection credentials are stored encrypted. Never share your API keys.</p>
                </>
              )}
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="rsm-footer">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', flex: 1 }}>
            {submitError && (
              <div className="rsm-alert rsm-alert--error" style={{ padding: '8px 12px', fontSize: '12px' }}>
                ⚠ {submitError}
              </div>
            )}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
              <button className="rsm-btn rsm-btn--ghost" onClick={onClose} disabled={submitting}>Cancel</button>
              <div className="rsm-footer__right">
                {step > 1 && (
                  <button className="rsm-btn rsm-btn--outline" onClick={() => setStep(s => s - 1)} disabled={submitting}>← Back</button>
                )}
                {step < totalSteps ? (
                  <button id="rsm-next-btn" className="rsm-btn rsm-btn--primary" onClick={handleNext}>Next →</button>
                ) : (
                  <button
                    id="rsm-register-btn"
                    className="rsm-btn rsm-btn--primary rsm-btn--submit"
                    onClick={handleSubmit}
                    disabled={submitting}
                  >
                    {submitting ? '⏳ Registering…' : '✓ Register Source'}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}