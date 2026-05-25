import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, ProtectedRoute } from './context/AuthContext';
import { TenantConfigProvider } from './context/TenantConfigContext';
import { PermissionsProvider } from './context/PermissionsContext';
import { SnackbarProvider } from './context/SnackbarContext';
import MainLayout from './layouts/MainLayout';
import Login from './pages/Login';
import SourceSystems from './pages/source/SourceSystems';
import Domains from './pages/domains/Domains';
import IngestionRuns from './pages/ingestion/IngestionRuns';
import RawLanding from './pages/rawlanding/RawLanding';
import UploadData from './pages/upload/UploadData';
import StagingRecords from './pages/staging/StagingRecords';
import Tenants from './pages/admin/Tenants';
import SystemHealth from './pages/admin/SystemHealth';
import ApiLogs from './pages/apilogs/ApiLogs';
import DevSetup from './pages/DevSetup';
import PlatformRBAC from './pages/platform/PlatformRBAC';
import './index.css';

function Placeholder({ title }: { title: string }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', height: '60vh', gap: '12px',
      color: 'var(--text-muted)',
    }}>
      <span style={{ fontSize: '40px' }}>🚧</span>
      <h2 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-secondary)', margin: 0 }}>
        {title}
      </h2>
      <p style={{ fontSize: '13px', margin: 0 }}>This screen will be built in a future phase.</p>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <SnackbarProvider>
          <Routes>
            {/* ── Public ── */}
            <Route path="/login" element={<Login />} />

            {/* ── Protected shell ── */}
            <Route
              path="/"
              element={
                <ProtectedRoute allowedRoles={['super_admin', 'admin', 'data_architect', 'data_manager', 'executive']}>
                  <TenantConfigProvider>
                    <PermissionsProvider>
                      <MainLayout />
                    </PermissionsProvider>
                  </TenantConfigProvider>
                </ProtectedRoute>
              }
            >
              <Route index element={<Placeholder title="Dashboard — Coming Soon" />} />
              <Route path="sources" element={<SourceSystems />} />
              <Route path="domains" element={<Domains />} />
              <Route path="ingestion" element={<IngestionRuns />} />
              <Route path="upload" element={<UploadData />} />
              <Route path="raw-landing" element={<RawLanding />} />
              <Route path="staging" element={<StagingRecords />} />
              <Route path="tenants" element={<Tenants />} />
              <Route path="api-logs" element={<ApiLogs />} />
              <Route path="system-health" element={<SystemHealth />} />
              <Route path="dev-setup" element={<DevSetup />} />
              <Route
                path="platform-rbac"
                element={
                  <ProtectedRoute allowedRoles={['super_admin']}>
                    <PlatformRBAC />
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>

            {/* ── Catch-all ── */}
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </SnackbarProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
