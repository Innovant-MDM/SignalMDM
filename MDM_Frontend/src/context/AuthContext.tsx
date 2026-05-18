/**
 * src/context/AuthContext.tsx
 * ----------------------------
 * React context for authentication state throughout the application.
 *
 * On mount, calls GET /auth/me via the httpOnly cookie.
 * Provides admin profile, loading state, login helpers, and logout.
 *
 * Usage:
 *   const { admin, isAuthenticated, logout } = useAuth();
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { useNavigate } from 'react-router-dom';
import { authService, type AdminProfile } from '../services/authService';
import { evictPermissionsCache } from './PermissionsContext';
import { tenantConfigService } from '../services/tenantConfigService';

// ─── Context shape ────────────────────────────────────────────────────────

interface AuthContextValue {
  admin:           AdminProfile | null;
  isAuthenticated: boolean;
  isLoading:       boolean;
  /** Refresh profile from backend (call after login succeeds). */
  refreshProfile:  () => Promise<void>;
  logout:          () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// ─── Provider ─────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const [admin,     setAdmin]     = useState<AdminProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  const loadProfile = useCallback(async () => {
    try {
      const profile = await authService.getMe();
      setAdmin(profile);
    } catch {
      setAdmin(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // On app mount — probe the backend to see if already authenticated
  useEffect(() => {
    authService.init().then(() => loadProfile());
  }, [loadProfile]);

  const refreshProfile = useCallback(async () => {
    await loadProfile();
  }, [loadProfile]);

  const logout = useCallback(async () => {
    await authService.logout();
    evictPermissionsCache();
    tenantConfigService.clearCache();
    setAdmin(null);
    navigate('/login', { replace: true });
  }, [navigate]);

  return (
    <AuthContext.Provider
      value={{
        admin,
        isAuthenticated: admin !== null,
        isLoading,
        refreshProfile,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ─── Hook ─────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>.');
  return ctx;
}

// ─── ProtectedRoute ───────────────────────────────────────────────────────

import { Navigate } from 'react-router-dom';

interface ProtectedRouteProps {
  children: ReactNode;
  allowedRoles?: string[];
}

export function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const { admin, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        background: 'var(--bg-base)',
        color: 'var(--text-muted)',
        fontFamily: 'var(--font-sans)',
        fontSize: 14,
        gap: 10,
      }}>
        <span style={{
          width: 18, height: 18, border: '2px solid var(--accent)',
          borderTopColor: 'transparent', borderRadius: '50%',
          display: 'inline-block', animation: 'spin 0.7s linear infinite',
        }} />
        Verifying session…
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && admin && !allowedRoles.includes(admin.role)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
