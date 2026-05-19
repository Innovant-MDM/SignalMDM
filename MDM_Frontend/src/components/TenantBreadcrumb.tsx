/**
 * src/components/TenantBreadcrumb.tsx
 * ------------------------------------
 * Compact breadcrumb shown at the top of data-pipeline screens:
 *   Platform > <Tenant Name | All Tenants> > <Screen Label>
 *
 * Goal: make tenant context unambiguous on every screen, especially for
 * platform admins who switch scope between tenants.
 *
 * Source of truth is `useTenantConfig()`:
 *   - mode 'SPECIFIC' → shows tenant name
 *   - mode 'ALL'      → shows "All Tenants"
 *   - non-platform users → tenant pill is not rendered (they're implicitly
 *     scoped) but the screen crumb is still shown.
 */

import React from 'react';
import { useTenantConfig } from '../context/TenantConfigContext';
import { authService } from '../services/authService';
import '../styles/TenantBreadcrumb.css';

interface TenantBreadcrumbProps {
  /** Final crumb shown to the user (e.g. "Ingestion Runs"). */
  screen: string;
  /** Optional sub-screen (e.g. selected Run ID). */
  detail?: string;
}

export default function TenantBreadcrumb({ screen, detail }: TenantBreadcrumbProps): React.ReactElement {
  const { mode, activeTenantName, isLoading } = useTenantConfig();
  const info = authService.getAdminInfoFromCookie();
  const isPlatform = info?.tenant_id === 'platform';

  const tenantLabel = isLoading
    ? '…'
    : mode === 'SPECIFIC' && activeTenantName
      ? activeTenantName
      : 'All Tenants';

  return (
    <nav className="tb-crumb" aria-label="Tenant data hierarchy">
      {isPlatform && (
        <>
          <span className="tb-crumb__root">
            <span className="tb-crumb__icon" aria-hidden>🛰️</span>
            Platform
          </span>
          <span className="tb-crumb__sep" aria-hidden>›</span>
        </>
      )}
      <span
        className={`tb-crumb__tenant tb-crumb__tenant--${mode === 'SPECIFIC' ? 'specific' : 'all'}`}
        title={mode === 'SPECIFIC' ? 'Scoped to a specific tenant' : 'Showing data across all tenants'}
      >
        <span className="tb-crumb__icon" aria-hidden>🏢</span>
        {tenantLabel}
      </span>
      <span className="tb-crumb__sep" aria-hidden>›</span>
      <span className="tb-crumb__screen">{screen}</span>
      {detail && (
        <>
          <span className="tb-crumb__sep" aria-hidden>›</span>
          <span className="tb-crumb__detail" title={detail}>{detail}</span>
        </>
      )}
    </nav>
  );
}
