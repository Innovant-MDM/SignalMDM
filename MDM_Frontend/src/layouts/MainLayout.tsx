import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import TenantScopeBar from '../components/TenantScopeBar';
import './MainLayout.css';


interface NavItem  { label: string; path: string; icon: string; roles: string[]; }
interface NavGroup { group: string; items: NavItem[]; }

const NAV: NavGroup[] = [
  {
    group: 'Main',
    items: [
      { label: 'Dashboard',       path: '/',            icon: '⊞', roles: ['super_admin','admin','data_architect','data_manager','executive'] },
    ],
  },
  {
    group: 'Foundation',
    items: [
      { label: 'Source Systems',  path: '/sources',     icon: '⬡', roles: ['super_admin','admin','data_architect'] },
      { label: 'Upload Data',     path: '/upload',      icon: '⬆', roles: ['super_admin','admin','data_architect'] },
      { label: 'Ingestion Runs',  path: '/ingestion',   icon: '↻', roles: ['super_admin','admin','data_architect','data_manager'] },
      { label: 'Raw Landing',     path: '/raw-landing', icon: '⬇', roles: ['super_admin','admin','data_architect','data_manager'] },
      { label: 'Staging Records', path: '/staging',     icon: '◫', roles: ['super_admin','admin','data_architect','data_manager'] },
    ],
  },
  {
    group: 'Admin',
    items: [
      { label: 'API Logs',        path: '/api-logs',      icon: '≡', roles: ['super_admin','admin'] },
      { label: 'System Health',   path: '/system-health', icon: '♥', roles: ['super_admin','admin'] },
    ],
  },
  {
    group: 'Platform',
    items: [
      { label: 'Tenants',         path: '/tenants',        icon: '🏢', roles: ['super_admin','admin'] },
      { label: 'Platform Users',  path: '/platform-rbac',  icon: '👥', roles: ['super_admin','admin'] },
    ],
  },
];

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const { admin, isLoading, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  // Derive initials from username or email
  const initials = admin
    ? (admin.username ?? admin.email).slice(0, 2).toUpperCase()
    : '??';

  // Determine role — platform admins get full nav based on their role_key
  const userRole    = admin?.role ?? 'executive';
  const isPlatform  = admin?.tenant_id === 'platform';

  const visibleNav = NAV.map(group => {
    // Platform group is only for platform tenant users
    if (group.group === 'Platform' && !isPlatform) {
      return { ...group, items: [] };
    }
    return {
      ...group,
      items: group.items.filter(item => item.roles.includes(userRole)),
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
