/**
 * src/services/api.ts
 * -------------------
 * Base HTTP client for the SignalMDM FastAPI backend.
 *
 * Auth strategy (cookie-based):
 *   - `accessToken`  — httpOnly cookie set by backend on login (AES-encrypted JWT).
 *     Browser sends it automatically on every same-origin / credentialed request.
 *   - `X-Device-ID`  — non-sensitive stable device fingerprint, kept in sessionStorage.
 *
 * All responses are wrapped in StandardResponse:
 *   { success: bool, message: string, data: T | null, errors: string[] }
 */

export const API_BASE_URL =
  (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000/api/v1';

const BASE_URL = API_BASE_URL;

// ─── Standard response envelope ───────────────────────────────────────────
export interface StandardResponse<T = unknown> {
  success: boolean;
  message: string;
  data: T | null;
  errors: string[];
}

// ─── Typed API error ───────────────────────────────────────────────────────
export class ApiError extends Error {
  public readonly status: number;
  public readonly errors: string[];

  constructor(
    message: string,
    status: number,
    errors: string[] = [],
  ) {
    super(message);
    this.status = status;
    this.errors = errors;
    this.name = 'ApiError';
  }
}

// ─── Device ID helper (non-sensitive — not a secret) ──────────────────────
export function getDeviceId(): string {
  let id = sessionStorage.getItem('mdm_device_id');
  if (!id) {
    // FingerprintJS will overwrite this with a stable ID after init.
    // Fallback: random ID for the session.
    id = `web-${Math.random().toString(36).slice(2)}`;
    sessionStorage.setItem('mdm_device_id', id);
  }
  return id;
}

export function setDeviceId(id: string): void {
  sessionStorage.setItem('mdm_device_id', id);
}

// ─── Build request headers ─────────────────────────────────────────────────
// Note: accessToken is in an httpOnly cookie — browser attaches it automatically.
// We only need to send X-Device-ID explicitly.
function getHeaders(extra?: Record<string, string>): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    'X-Device-ID': getDeviceId(),
    ...extra,
  };
}

// ─── Core request ─────────────────────────────────────────────────────────
// ─── Core request with automatic token refresh ─────────────────────────────
async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  extraHeaders?: Record<string, string>,
  _isRetry = false,
): Promise<StandardResponse<T>> {
  const headers = getHeaders(extraHeaders);
  console.debug(`[api] ${method} ${path}`, { headers, body });
  
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    credentials: "include", // ← sends httpOnly cookies
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  // Handle 401 Unauthorized
  if (response.status === 401) {
    // If we're already on an auth path, just throw (don't refresh loop)
    if (path.startsWith("/auth/")) {
      const json = (await response.json()) as StandardResponse<T>;
      throw new ApiError(json.message || "Auth failed", 401);
    }

    // Try token refresh once
    if (!_isRetry) {
      try {
        console.warn(`[api] 401 on ${path} — attempting token refresh...`);
        const refreshRes = await fetch(`${BASE_URL}/auth/refresh`, {
          method: "POST",
          headers: getHeaders(),
          credentials: "include",
        });

        if (refreshRes.ok) {
          console.info("[api] Refresh successful — retrying original request.");
          return request<T>(method, path, body, extraHeaders, true);
        }
      } catch (err) {
        console.error("[api] Refresh call failed:", err);
      }
    }

    // If refresh failed or was already a retry, redirect to login
    console.error("[api] Session expired. Redirecting to login.");
    window.location.href = "/login";
    return { success: false, message: "Session expired.", data: null, errors: [] };
  }

  let json: StandardResponse<T>;
  try {
    json = (await response.json()) as StandardResponse<T>;
  } catch {
    throw new ApiError(
      `Server returned a non-JSON response (HTTP ${response.status})`,
      response.status
    );
  }

  if (!response.ok) {
    throw new ApiError(
      json?.message ?? `Request failed with status ${response.status}`,
      response.status,
      json?.errors ?? []
    );
  }

  return json;
}

// ─── Multipart (e.g. file upload) — do not set Content-Type (browser sets boundary) ──
async function postFormData<T>(
  path: string,
  formData: FormData,
  extraHeaders?: Record<string, string>,
  _isRetry = false,
): Promise<StandardResponse<T>> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      'X-Device-ID': getDeviceId(),
      ...extraHeaders,
    },
    credentials: 'include',
    body: formData,
  });

  if (response.status === 401) {
    if (path.startsWith('/auth/')) {
      const json = (await response.json()) as StandardResponse<T>;
      throw new ApiError(json.message || 'Auth failed', 401);
    }
    if (!_isRetry) {
      try {
        const refreshRes = await fetch(`${BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: getHeaders(),
          credentials: 'include',
        });
        if (refreshRes.ok) {
          return postFormData<T>(path, formData, extraHeaders, true);
        }
      } catch (err) {
        console.error('[api] Refresh call failed:', err);
      }
    }
    console.error('[api] Session expired. Redirecting to login.');
    window.location.href = '/login';
    return { success: false, message: 'Session expired.', data: null, errors: [] };
  }

  let json: StandardResponse<T>;
  try {
    json = (await response.json()) as StandardResponse<T>;
  } catch {
    throw new ApiError(
      `Server returned a non-JSON response (HTTP ${response.status})`,
      response.status,
    );
  }

  if (!response.ok) {
    throw new ApiError(
      json?.message ?? `Request failed with status ${response.status}`,
      response.status,
      json?.errors ?? [],
    );
  }

  return json;
}

// ─── Convenience methods ───────────────────────────────────────────────────
export const api = {
  get:    <T>(path: string, headers?: Record<string, string>) =>
            request<T>('GET', path, undefined, headers),
  post:   <T>(path: string, body: unknown, headers?: Record<string, string>) =>
            request<T>('POST', path, body, headers),
  put:    <T>(path: string, body: unknown, headers?: Record<string, string>) =>
            request<T>('PUT', path, body, headers),
  patch:  <T>(path: string, body: unknown, headers?: Record<string, string>) =>
            request<T>('PATCH', path, body, headers),
  delete: <T>(path: string, headers?: Record<string, string>) =>
            request<T>('DELETE', path, undefined, headers),
  postForm: <T>(path: string, formData: FormData, headers?: Record<string, string>) =>
            postFormData<T>(path, formData, headers),
};
