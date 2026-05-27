// src/pages/platform/PlatformRBAC.tsx
import React, { useState, useEffect, useCallback } from 'react';
import '../../styles/theme.css';
import '../../styles/PlatformRBAC.css';
import { platformRbacService, type PlatformRole, type PlatformPermission, type PlatformUser, type CreateUserPayload } from '../../services/platformRbacService';
import { usePermissions } from '../../context/PermissionsContext';

type Tab = 'users' | 'roles';

/* ─── Role key → badge color ─────────────────────────────── */
function roleBadgeClass(roleKey: string | null): string {
  if (!roleKey) return 'badge--gray';
  if (roleKey === 'super_admin')    return 'badge--purple';
  if (roleKey === 'admin')          return 'badge--blue';
  if (roleKey === 'data_architect') return 'badge--cyan';
  if (roleKey === 'data_manager')   return 'badge--amber';
  if (roleKey === 'executive')      return 'badge--green';
  return 'badge--gray';
}

/* ─── User Avatar ─────────────────────────────────────────── */
function UserAvatar({ user }: { user: PlatformUser }) {
  const initials = (user.full_name || user.username).slice(0, 2).toUpperCase();
  return (
    <div className={`rbac-user-avatar${user.is_blocked ? ' rbac-user-avatar--blocked' : ''}`}>
      {initials}
    </div>
  );
}

/* ─── Create / Edit User Modal ────────────────────────────── */
interface UserModalProps {
  roles: PlatformRole[];
  editUser?: PlatformUser | null;
  onClose: () => void;
  onSave: () => void;
}
function UserModal({ roles, editUser, onClose, onSave }: UserModalProps) {
  const [email, setEmail]       = useState(editUser?.email ?? '');
  const [username, setUsername] = useState(editUser?.username ?? '');
  const [fullName, setFullName] = useState(editUser?.full_name ?? '');
  const [password, setPassword] = useState('');
  const [roleId, setRoleId]     = useState(editUser?.role_id ?? '');
  const [isActive, setIsActive] = useState(editUser?.is_active ?? true);
  const [twoFa, setTwoFa]       = useState(editUser?.two_fa_enabled ?? false);
  const [mustChange, setMustChange] = useState(editUser?.must_change_password ?? true);
  const [error, setError]       = useState<string | null>(null);
  const [saving, setSaving]     = useState(false);

  const isEdit = !!editUser;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!roleId) { setError('Please select a role.'); return; }
    if (!isEdit && password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    setSaving(true); setError(null);
    try {
      if (isEdit) {
        await platformRbacService.updateUser(editUser!.admin_id, {
          username, full_name: fullName || undefined, role_id: roleId,
          is_active: isActive, two_fa_enabled: twoFa, must_change_password: mustChange,
        });
      } else {
        const payload: CreateUserPayload = {
          email, username, full_name: fullName || undefined, password,
          role_id: roleId, is_active: isActive, two_fa_enabled: twoFa, must_change_password: mustChange,
        };
        await platformRbacService.createUser(payload);
      }
      onSave();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Operation failed.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal rbac-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <div className="modal-title">{isEdit ? 'Edit User' : 'Add Platform User'}</div>
            <div className="modal-sub">{isEdit ? `Editing ${editUser!.email}` : 'Create a new platform-level stakeholder account'}</div>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && (
              <div style={{ background: 'var(--red-100)', color: 'var(--red-600)', padding: '10px 14px', borderRadius: 'var(--r-sm)', fontSize: 13, fontWeight: 500 }}>
                {error}
              </div>
            )}
            <div className="rbac-input-grid">
              <div className="form-field">
                <label className="form-label">Email <span className="required">*</span></label>
                <input className="form-input" type="email" value={email} onChange={e => setEmail(e.target.value)} required disabled={isEdit} placeholder="user@example.com" />
              </div>
              <div className="form-field">
                <label className="form-label">Username <span className="required">*</span></label>
                <input className="form-input" value={username} onChange={e => setUsername(e.target.value)} required placeholder="Display name" />
              </div>
            </div>
            <div className="form-field">
              <label className="form-label">Full Name</label>
              <input className="form-input" value={fullName} onChange={e => setFullName(e.target.value)} placeholder="Optional full name" />
            </div>
            {!isEdit && (
              <div className="form-field">
                <label className="form-label">Password <span className="required">*</span></label>
                <input className="form-input" type="password" value={password} onChange={e => setPassword(e.target.value)} required placeholder="Min. 8 characters" />
              </div>
            )}
            <div className="form-field">
              <label className="form-label">Role <span className="required">*</span></label>
              <select className="form-select" value={roleId} onChange={e => setRoleId(e.target.value)} required>
                <option value="">— Select a role —</option>
                {roles.map(r => <option key={r.role_id} value={r.role_id}>{r.role_label}</option>)}
              </select>
            </div>
            <div className="rbac-toggle-row">
              <div>
                <div className="rbac-toggle-row__label">Active Account</div>
                <div className="rbac-toggle-row__sub">Inactive users cannot log in</div>
              </div>
              <input type="checkbox" checked={isActive} onChange={e => setIsActive(e.target.checked)} />
            </div>
            <div className="rbac-toggle-row">
              <div>
                <div className="rbac-toggle-row__label">Require 2FA</div>
                <div className="rbac-toggle-row__sub">User must set up authenticator app</div>
              </div>
              <input type="checkbox" checked={twoFa} onChange={e => setTwoFa(e.target.checked)} />
            </div>
            <div className="rbac-toggle-row">
              <div>
                <div className="rbac-toggle-row__label">Force Password Reset</div>
                <div className="rbac-toggle-row__sub">User must change password on first login</div>
              </div>
              <input type="checkbox" checked={mustChange} onChange={e => setMustChange(e.target.checked)} />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn--ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn--primary" disabled={saving}>
              {saving ? 'Saving…' : isEdit ? 'Save Changes' : 'Create User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ─── Reset Password Modal ────────────────────────────────── */
function ResetPasswordModal({ user, onClose, onDone }: { user: PlatformUser; onClose: () => void; onDone: () => void }) {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm]   = useState('');
  const [error, setError]       = useState<string | null>(null);
  const [saving, setSaving]     = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) { setError('Min. 8 characters.'); return; }
    if (password !== confirm) { setError('Passwords do not match.'); return; }
    setSaving(true); setError(null);
    try {
      await platformRbacService.resetPassword(user.admin_id, password);
      onDone();
    } catch (err) { setError(err instanceof Error ? err.message : 'Failed.'); }
    finally { setSaving(false); }
  };

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" style={{ width: 420 }} onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <div className="modal-title">Reset Password</div>
            <div className="modal-sub">{user.email}</div>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {error && <div style={{ background: 'var(--red-100)', color: 'var(--red-600)', padding: '10px 14px', borderRadius: 6, fontSize: 13 }}>{error}</div>}
            <div className="form-field">
              <label className="form-label">New Password</label>
              <input className="form-input" type="password" value={password} onChange={e => setPassword(e.target.value)} required placeholder="Min. 8 characters" />
            </div>
            <div className="form-field">
              <label className="form-label">Confirm Password</label>
              <input className="form-input" type="password" value={confirm} onChange={e => setConfirm(e.target.value)} required placeholder="Repeat password" />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn--ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn--primary" disabled={saving}>{saving ? 'Resetting…' : 'Reset Password'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ─── Users Tab ───────────────────────────────────────────── */
function UsersTab({ roles }: { roles: PlatformRole[] }) {
  const [users, setUsers]       = useState<PlatformUser[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [editUser, setEditUser] = useState<PlatformUser | null>(null);
  const [resetUser, setResetUser] = useState<PlatformUser | null>(null);
  const [search, setSearch]     = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try { setUsers(await platformRbacService.listUsers()); }
    catch (err) { setError(err instanceof Error ? err.message : 'Failed to load users.'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleBlock = async (u: PlatformUser) => {
    if (!confirm(`${u.is_blocked ? 'Unblock' : 'Block'} ${u.email}?`)) return;
    try {
      if (u.is_blocked) await platformRbacService.unblockUser(u.admin_id);
      else await platformRbacService.blockUser(u.admin_id);
      load();
    } catch (err) { alert(err instanceof Error ? err.message : 'Failed.'); }
  };

  const handleDelete = async (u: PlatformUser) => {
    if (!confirm(`Permanently delete ${u.email}? This cannot be undone.`)) return;
    try { await platformRbacService.deleteUser(u.admin_id); load(); }
    catch (err) { alert(err instanceof Error ? err.message : 'Failed.'); }
  };

  const handleToggle2FA = async (u: PlatformUser) => {
    const message = u.two_fa_enabled
      ? `Are you sure you want to disable Multi-Factor Authentication (2FA) for ${u.email}? This will delete their current authenticator secret and configuration.`
      : `Require Multi-Factor Authentication (2FA) for ${u.email}? They will be prompted to setup an authenticator app upon their next login.`;

    if (!confirm(message)) return;
    try {
      await platformRbacService.updateUser(u.admin_id, {
        two_fa_enabled: !u.two_fa_enabled,
      });
      load();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update 2FA configuration.');
    }
  };

  const filtered = users.filter(u => {
    const q = search.toLowerCase();
    return !q || u.email.toLowerCase().includes(q) || u.username.toLowerCase().includes(q) || (u.full_name ?? '').toLowerCase().includes(q);
  });

  return (
    <>
      <div className="rbac-section-hdr">
        <div>
          <h2>Platform Users</h2>
          <p>Manage high-level stakeholders and their access roles</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <input className="form-input" style={{ width: 220 }} placeholder="Search users…" value={search} onChange={e => setSearch(e.target.value)} />
          <button className="btn btn--primary" onClick={() => setShowCreate(true)}>＋ Add User</button>
        </div>
      </div>

      {error && <div style={{ background: 'var(--red-100)', color: 'var(--red-600)', padding: '12px 16px', borderRadius: 8, marginBottom: 8 }}>{error}</div>}

      {loading ? (
        <div className="rbac-empty"><div className="spinner" /><div className="rbac-empty__text" style={{ marginTop: 12 }}>Loading users…</div></div>
      ) : filtered.length === 0 ? (
        <div className="rbac-empty">
          <div className="rbac-empty__icon">👥</div>
          <div className="rbac-empty__text">{search ? 'No users match your search.' : 'No platform users yet. Click "Add User" to get started.'}</div>
        </div>
      ) : (
        <div className="rbac-user-grid">
          {filtered.map(u => (
            <div key={u.admin_id} className={`rbac-user-card${u.is_blocked ? ' rbac-user-card--blocked' : ''}`}>
              <div className="rbac-user-card__top">
                <UserAvatar user={u} />
                <div className="rbac-user-card__info">
                  <div className="rbac-user-card__name">{u.full_name || u.username}</div>
                  <div className="rbac-user-card__email">{u.email}</div>
                </div>
              </div>
              <div className="rbac-user-card__badges">
                <span className={`badge ${roleBadgeClass(u.role_key)}`}>{u.role_label ?? 'No Role'}</span>
                {!u.is_active   && <span className="badge badge--gray">Inactive</span>}
                {u.is_blocked   && <span className="badge badge--red">Blocked</span>}
                {u.two_fa_enabled && <span className="badge badge--green">2FA</span>}
                {u.must_change_password && <span className="badge badge--amber">Pwd Reset</span>}
              </div>

              {/* 2FA Ribbon */}
              <div className="rbac-user-card__2fa-section">
                <div className="rbac-2fa-status-info">
                  <span className="rbac-2fa-icon">
                    {u.two_fa_enabled ? (u.two_fa_setup_complete ? '🔒' : '⏳') : '🔓'}
                  </span>
                  <div className="rbac-2fa-status-text">
                    <span className={`rbac-2fa-status-label ${
                      u.two_fa_enabled
                        ? (u.two_fa_setup_complete ? 'rbac-2fa-status-label--enabled' : 'rbac-2fa-status-label--pending')
                        : 'rbac-2fa-status-label--disabled'
                    }`}>
                      {u.two_fa_enabled
                        ? (u.two_fa_setup_complete ? '2FA Enabled' : '2FA Pending Setup')
                        : '2FA Disabled'}
                    </span>
                    <span className="rbac-2fa-status-sub">
                      {u.two_fa_enabled
                        ? (u.two_fa_setup_complete ? 'Protected with authenticator' : 'Requires setup on next login')
                        : 'Standard login only'}
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  className={`btn btn--xs ${u.two_fa_enabled ? 'btn--danger' : 'btn--primary'}`}
                  onClick={() => handleToggle2FA(u)}
                >
                  {u.two_fa_enabled ? 'Disable' : 'Enable'}
                </button>
              </div>

              <div className="rbac-user-card__footer">
                <button className="btn btn--ghost btn--sm" onClick={() => setEditUser(u)}>Edit</button>
                <button className="btn btn--ghost btn--sm" onClick={() => setResetUser(u)}>Reset Pwd</button>
                <button
                  className={`btn btn--sm ${u.is_blocked ? 'btn--primary' : 'btn--danger'}`}
                  onClick={() => handleBlock(u)}
                  title={u.is_blocked ? 'Unblock' : 'Block'}
                >
                  {u.is_blocked ? 'Unblock' : 'Block'}
                </button>
                <button className="btn btn--danger btn--sm" onClick={() => handleDelete(u)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {(showCreate || editUser) && (
        <UserModal
          roles={roles}
          editUser={editUser}
          onClose={() => { setShowCreate(false); setEditUser(null); }}
          onSave={() => { setShowCreate(false); setEditUser(null); load(); }}
        />
      )}
      {resetUser && (
        <ResetPasswordModal
          user={resetUser}
          onClose={() => setResetUser(null)}
          onDone={() => { setResetUser(null); load(); }}
        />
      )}
    </>
  );
}

/* ─── Roles & Permissions Tab ─────────────────────────────── */
function RolesTab() {
  const { refreshPermissions } = usePermissions();
  const [roles, setRoles]                   = useState<PlatformRole[]>([]);
  const [allPerms, setAllPerms]             = useState<PlatformPermission[]>([]);
  const [selectedRole, setSelectedRole]     = useState<PlatformRole | null>(null);
  const [rolePerms, setRolePerms]           = useState<Set<string>>(new Set());
  const [loading, setLoading]               = useState(true);
  const [saving, setSaving]                 = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [r, p] = await Promise.all([platformRbacService.listRoles(), platformRbacService.listPermissions()]);
      setRoles(r);
      setAllPerms(p);
      if (r.length > 0 && !selectedRole) setSelectedRole(r[0]);
    } finally { setLoading(false); }
  }, [selectedRole]);

  useEffect(() => { load(); }, []); // eslint-disable-line

  useEffect(() => {
    if (!selectedRole) return;
    platformRbacService.getRolePermissions(selectedRole.role_id).then(perms => {
      setRolePerms(new Set(perms.map(p => p.permission_id)));
    });
  }, [selectedRole]);

  const handleToggle = (permId: string) => {
    setRolePerms(prev => {
      const next = new Set(prev);
      if (next.has(permId)) next.delete(permId); else next.add(permId);
      return next;
    });
  };

  const handleSave = async () => {
    if (!selectedRole) return;
    setSaving(true);
    try {
      await platformRbacService.setRolePermissions(selectedRole.role_id, Array.from(rolePerms));
      await refreshPermissions();
      alert('Permissions saved successfully.');
    } catch (err) { alert(err instanceof Error ? err.message : 'Failed to save permissions.'); }
    finally { setSaving(false); }
  };

  // Group permissions by screen_key
  const grouped = allPerms.reduce<Record<string, PlatformPermission[]>>((acc, p) => {
    (acc[p.screen_key] = acc[p.screen_key] || []).push(p);
    return acc;
  }, {});

  const screenLabels: Record<string, string> = {
    dashboard: 'Dashboard', sources: 'Source Systems', ingestion: 'Ingestion Runs',
    upload: 'Upload Data', raw_landing: 'Raw Landing', staging: 'Staging Records',
    canonical_models: 'Canonical Models', field_mappings: 'Field Mappings',
    transformation_rules: 'Transformation Rules', standardization_rules: 'Standardization Rules',
    normalization_runs: 'Normalization Runs', normalized_records: 'Normalized Records',
    mapping_errors: 'Mapping & Validation Errors',
    api_logs: 'API Logs', system_health: 'System Health', tenants: 'Tenants', platform: 'Platform Admin',
  };

  if (loading) return <div className="rbac-empty"><div className="spinner" /></div>;

  return (
    <div className="rbac-roles-layout">
      {/* Role list */}
      <div>
        <div className="rbac-section-hdr" style={{ marginBottom: 12 }}>
          <div><h2>Roles</h2><p>Select a role to manage permissions</p></div>
        </div>
        <div className="rbac-role-list">
          {roles.map(r => (
            <div
              key={r.role_id}
              className={`rbac-role-item${selectedRole?.role_id === r.role_id ? ' rbac-role-item--active' : ''}`}
              onClick={() => setSelectedRole(r)}
            >
              <div className="rbac-role-item__dot" />
              <div>
                <div className="rbac-role-item__label">{r.role_label}</div>
                <div className="rbac-role-item__key">{r.role_key}</div>
              </div>
              {r.is_system && <span className="badge badge--gray btn--sm" style={{ marginLeft: 'auto', fontSize: 10 }}>system</span>}
            </div>
          ))}
        </div>
      </div>

      {/* Permissions panel */}
      <div className="rbac-perms-panel">
        <div className="rbac-perms-panel__hdr">
          <div>
            <div className="rbac-perms-panel__title">
              {selectedRole ? `${selectedRole.role_label} — Permissions` : 'Select a role'}
            </div>
            {selectedRole?.description && (
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{selectedRole.description}</div>
            )}
          </div>
          {selectedRole && (
            <button className="btn btn--primary btn--sm" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving…' : '✓ Save Permissions'}
            </button>
          )}
        </div>
        <div className="rbac-perms-panel__body">
          {selectedRole ? Object.entries(grouped).map(([screen, perms]) => (
            <div key={screen} className="rbac-perm-group">
              <div className="rbac-perm-group__label">{screenLabels[screen] ?? screen}</div>
              {perms.map(p => (
                <div key={p.permission_id} className="rbac-perm-row">
                  <input
                    type="checkbox"
                    id={`perm-${p.permission_id}`}
                    checked={rolePerms.has(p.permission_id)}
                    onChange={() => handleToggle(p.permission_id)}
                  />
                  <label htmlFor={`perm-${p.permission_id}`} className="rbac-perm-row__label">{p.label}</label>
                  {p.description && <span className="rbac-perm-row__desc">{p.description}</span>}
                </div>
              ))}
            </div>
          )) : (
            <div className="rbac-empty">
              <div className="rbac-empty__icon">🔐</div>
              <div className="rbac-empty__text">Select a role from the left to view its permissions.</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Main Page ───────────────────────────────────────────── */
export default function PlatformRBAC(): React.ReactElement {
  const [tab, setTab]     = useState<Tab>('users');
  const [roles, setRoles] = useState<PlatformRole[]>([]);

  useEffect(() => {
    platformRbacService.listRoles().then(setRoles).catch(() => {});
  }, []);

  return (
    <div className="rbac-page">
      {/* Header */}
      <div className="page-hdr">
        <div>
          <h1 className="page-title">Platform RBAC</h1>
          <p className="page-subtitle">Manage platform-level users, roles, and screen-level access permissions</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="rbac-tabs">
        <button className={`rbac-tab${tab === 'users' ? ' rbac-tab--active' : ''}`} onClick={() => setTab('users')}>
          👥 Users
        </button>
        <button className={`rbac-tab${tab === 'roles' ? ' rbac-tab--active' : ''}`} onClick={() => setTab('roles')}>
          🔐 Roles & Permissions
        </button>
      </div>

      {/* Content */}
      {tab === 'users' ? <UsersTab roles={roles} /> : <RolesTab />}
    </div>
  );
}
