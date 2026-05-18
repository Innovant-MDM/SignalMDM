/**
 * src/context/PermissionsContext.tsx
 * ------------------------------------
 * Fetches the current admin's role permissions from the backend and
 * provides a `canAccess(screenKey, featureKey?)` helper to the entire app.
 *
 * Permission map shape (from GET /api/v1/platform/my-permissions):
 *   { permissions: { dashboard: ['view'], sources: ['view','register'], ... } }
 *
 * Refresh mechanism:
 *   Call `refreshPermissions()` after any RBAC save to re-sync the sidebar.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { api } from '../services/api';
import { useAuth } from './AuthContext';

// ─── Types ────────────────────────────────────────────────────

type PermMap = Record<string, string[]>;   // { screen_key: [feature_key, ...] }

interface PermissionsValue {
  /** Returns true if the current admin can access the screen (and optionally a feature). */
  canAccess: (screen: string, feature?: string) => boolean;
  /** The raw permission map — useful for advanced checks. */
  permMap: PermMap;
  /** True while the initial load is in progress. */
  isLoading: boolean;
  /** Call this after saving RBAC changes to re-sync the sidebar. */
  refreshPermissions: () => Promise<void>;
}

const PermissionsContext = createContext<PermissionsValue | null>(null);

const CACHE_KEY = 'perms_v1';

function cacheRead(): PermMap | null {
  try { return JSON.parse(sessionStorage.getItem(CACHE_KEY) ?? 'null'); }
  catch { return null; }
}
function cacheWrite(m: PermMap) {
  try { sessionStorage.setItem(CACHE_KEY, JSON.stringify(m)); } catch { /* quota */ }
}
function cacheEvict() {
  try { sessionStorage.removeItem(CACHE_KEY); } catch { /* ignore */ }
}

// ─── Provider ─────────────────────────────────────────────────

export function PermissionsProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated, admin } = useAuth();
  const isPlatform = admin?.tenant_id === 'platform';

  const [permMap, setPermMap]     = useState<PermMap>({});
  const [isLoading, setIsLoading] = useState(true);

  const fetchPerms = useCallback(async (force = false) => {
    if (!isAuthenticated || !isPlatform) {
      setPermMap({});
      setIsLoading(false);
      return;
    }
    // Use cache on first load
    if (!force) {
      const cached = cacheRead();
      if (cached) { setPermMap(cached); setIsLoading(false); return; }
    }
    setIsLoading(true);
    try {
      const res = await api.get<{ permissions: PermMap }>('/platform/my-permissions');
      const map = res.data?.permissions ?? {};
      setPermMap(map);
      cacheWrite(map);
    } catch {
      setPermMap({});
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, isPlatform]);

  useEffect(() => { fetchPerms(); }, [fetchPerms]);

  const refreshPermissions = useCallback(async () => {
    cacheEvict();
    await fetchPerms(true);
  }, [fetchPerms]);

  const canAccess = useCallback((screen: string, feature?: string): boolean => {
    // Super-admin check: if they have ALL screens and features, short-circuit
    // Platform admin without any permissions map → deny
    const screenPerms = permMap[screen];
    if (!screenPerms) return false;
    if (!feature) return screenPerms.length > 0;
    return screenPerms.includes(feature);
  }, [permMap]);

  return (
    <PermissionsContext.Provider value={{ canAccess, permMap, isLoading, refreshPermissions }}>
      {children}
    </PermissionsContext.Provider>
  );
}

export function usePermissions(): PermissionsValue {
  const ctx = useContext(PermissionsContext);
  if (!ctx) throw new Error('usePermissions must be used inside <PermissionsProvider>.');
  return ctx;
}

/** Expose cache eviction for logout cleanup */
export const evictPermissionsCache = cacheEvict;
