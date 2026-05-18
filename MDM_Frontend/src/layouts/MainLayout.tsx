import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { usePermissions } from '../context/PermissionsContext';
import TenantScopeBar from '../components/TenantScopeBar';
import './MainLayout.css';

interface NavItem  { label: string; path: string; icon: string; screen: string; superAdminOnly?: boolean; }
interface NavGroup { group: string; items: NavItem[]; platformOnly?: boolean; }

const NAV: NavGroup[] = [
  {
    group: 'Main',
    items: [
      { label: 'Dashboard',       path: '/',            icon: '⊞', screen: 'dashboard' },
    ],
  },
  {
    group: 'Foundation',
    items: [
      { label: 'Source Systems',  path: '/sources',     icon: '⬡', screen: 'sources' },
      { label: 'Upload Data',     path: '/upload',      icon: '⬆', screen: 'upload' },
      { label: 'Ingestion Runs',  path: '/ingestion',   icon: '↻', screen: 'ingestion' },
      { label: 'Raw Landing',     path: '/raw-landing', icon: '⬇', screen: 'raw_landing' },
      { label: 'Staging Records', path: '/staging',     icon: '◫', screen: 'staging' },
    ],
  },
  {
    group: 'Admin',
    items: [
      { label: 'API Logs',        path: '/api-logs',      icon: '≡', screen: 'api_logs' },
      { label: 'System Health',   path: '/system-health', icon: '♥', screen: 'system_health' },
    ],
  },
  {
    group: 'Platform',
    platformOnly: true,
    items: [
      { label: 'Tenants',        path: '/tenants',       icon: '🏢', screen: 'tenants' },
      { label: 'Platform Users', path: '/platform-rbac', icon: '👥', screen: 'platform', superAdminOnly: true },
    ],
  },
];

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const { admin, isLoading, logout } = useAuth();
  const { canAccess } = usePermissions();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  const initials = admin
    ? (admin.username ?? admin.email).slice(0, 2).toUpperCase()
    : '??';

  const isPlatform  = admin?.tenant_id === 'platform';
  const isSuperAdmin = admin?.role === 'super_admin';

  const visibleNav = NAV.map(group => {
    // Platform group: platform admins only
    if (group.platformOnly && !isPlatform) return { ...group, items: [] };
    return {
      ...group,
      items: group.items.filter(item => {
        if (item.superAdminOnly) return isSuperAdmin;
        return canAccess(item.screen, 'view');
      }),
    };
  }).filter(group => group.items.length > 0);

  return (
    <div className={`mdm-shell${collapsed ? ' mdm-shell--collapsed' : ''}`}>
      {/* ── Sidebar ── */}
      <aside className="mdm-sidebar">
        <div className="mdm-sidebar__brand">
          <span className="mdm-sidebar__logo">
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              <rect width="22" height="22" rx="5" fill="#1557ff" />
              <path d="M5 11h12M11 5v12" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" />
            </svg>
          </span>
          {!collapsed && (
            <span className="mdm-sidebar__brand-text">
              Signal<strong>MDM</strong>
            </span>
          )}
          <button
            className="mdm-sidebar__collapse-btn"
            onClick={() => setCollapsed(c => !c)}
            title={collapsed ? 'Expand' : 'Collapse'}
          >
            {collapsed ? '›' : '‹'}
          </button>
        </div>

        <nav className="mdm-sidebar__nav">
          {visibleNav.map(group => (
            <div key={group.group} className="mdm-sidebar__group">
              {!collapsed && (
                <span className="mdm-sidebar__group-label">{group.group}</span>
              )}
              {group.items.map(item => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === '/'}
                  className={({ isActive }) =>
                    `mdm-sidebar__link${isActive ? ' mdm-sidebar__link--active' : ''}`
                  }
                  title={collapsed ? item.label : undefined}
                >
                  <span className="mdm-sidebar__link-icon">{item.icon}</span>
                  {!collapsed && (
                    <span className="mdm-sidebar__link-label">{item.label}</span>
                  )}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="mdm-sidebar__footer">
          {!collapsed && (
            <div className="mdm-sidebar__user">
              <div className="mdm-sidebar__avatar">{initials}</div>
              <div className="mdm-sidebar__user-info">
                <span className="mdm-sidebar__user-name">
                  {isLoading ? '…' : (admin?.username ?? 'Admin')}
                </span>
                <span className="mdm-sidebar__user-role">
                  {admin?.role?.toUpperCase() ?? 'ADMIN'}
                </span>
              </div>
            </div>
          )}
          <button
            className="mdm-sidebar__logout-btn"
            onClick={handleLogout}
            title="Logout"
          >
            <span style={{ fontSize: collapsed ? 16 : 14 }}>⏻</span>
            {!collapsed && <span>Logout</span>}
          </button>
        </div>
      </aside>

      {/* ── Main ── */}
      <div className="mdm-main">
        <header className="mdm-topbar">
          <div className="mdm-topbar__left">
            <span className="mdm-topbar__env-badge">PHASE 1 — FOUNDATION</span>
          </div>
          <div className="mdm-topbar__right">
            {isPlatform && <TenantScopeBar />}
            {admin && (
              <span style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                {admin.email}
              </span>
            )}
          </div>
        </header>
        <main className="mdm-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
