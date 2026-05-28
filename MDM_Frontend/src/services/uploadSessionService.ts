/**
 * src/services/uploadSessionService.ts
 * ---------------------------------------
 * Client for the Upload Session endpoints.
 *
 * Backend endpoints:
 *   POST   /api/v1/uploads/sessions
 *   GET    /api/v1/uploads/sessions
 *   GET    /api/v1/uploads/sessions/{id}
 *   POST   /api/v1/uploads/sessions/{id}/files   (multipart, multi-file)
 *   DELETE /api/v1/uploads/sessions/{id}/files/{fileId}
 */

import { api, ApiError } from './api';

// ---------------------------------------------------------------------------
// Shapes
// ---------------------------------------------------------------------------

export interface UploadSessionFile {
  file_id: string;
  session_id: string;
  tenant_id: string;
  file_label: string;
  original_filename: string;
  file_size_bytes: number | null;
  content_type: string | null;
  record_count: number | null;
  uploaded_by: string | null;
  uploaded_at: string;
  is_duplicate?: boolean;
  first_uploaded_by?: string | null;
  first_uploaded_at?: string | null;
}

export interface UploadSession {
  session_id: string;
  tenant_id: string;
  session_name: string;
  domain: string;
  status: 'OPEN' | 'CLOSED';
  created_by: string | null;
  created_at: string;
  updated_at: string;
  file_count: number;
  files?: UploadSessionFile[];
}

export interface CreateSessionPayload {
  session_name: string;
  domain: string;
  tenant_id?: string;
}

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

export const uploadSessionService = {
  /** Create a new upload session (folder). */
  async createSession(
    payload: CreateSessionPayload,
    tenantId?: string,
  ): Promise<UploadSession> {
    // Use query param as the primary transport — most reliable, never stripped
    const qs = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : '';
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.post<UploadSession>(`/uploads/sessions${qs}`, payload, headers);
    if (!res.success || !res.data) {
      throw new ApiError(res.message || 'Failed to create session', 400, res.errors ?? []);
    }
    return res.data;
  },

  /** List sessions for the current tenant. */
  async listSessions(tenantId?: string): Promise<UploadSession[]> {
    const qs = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : '';
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.get<UploadSession[]>(`/uploads/sessions${qs}`, headers);
    if (!res.success || !res.data) {
      throw new ApiError(res.message || 'Failed to list sessions', 400, res.errors ?? []);
    }
    return res.data;
  },

  /** Get a single session with all its files. */
  async getSession(sessionId: string, tenantId?: string): Promise<UploadSession> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.get<UploadSession>(`/uploads/sessions/${sessionId}`, headers);
    if (!res.success || !res.data) {
      throw new ApiError(res.message || 'Session not found', 404, res.errors ?? []);
    }
    return res.data;
  },

  /** Delete a session and all files within it. */
  async deleteSession(sessionId: string, tenantId?: string): Promise<void> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.delete<null>(`/uploads/sessions/${sessionId}`, headers);
    if (!res.success) {
      throw new ApiError(res.message || 'Failed to delete session', 400, res.errors ?? []);
    }
  },

  /**
   * Upload multiple files into a session.
   * `entries` — array of { file: File, label: string } pairs.
   */
  async uploadFiles(
    sessionId: string,
    entries: { file: File; label: string }[],
    tenantId?: string,
  ): Promise<{ session_id: string; uploaded: UploadSessionFile[] }> {
    const formData = new FormData();
    entries.forEach(({ file, label }) => {
      formData.append('files', file);
      formData.append('file_labels', label);
    });

    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.postForm<{ session_id: string; uploaded: UploadSessionFile[] }>(
      `/uploads/sessions/${sessionId}/files`,
      formData,
      headers,
    );
    if (!res.success || !res.data) {
      throw new ApiError(res.message || 'Upload failed', 400, res.errors ?? []);
    }
    return res.data;
  },

  /** Delete a single file from a session. */
  async deleteFile(sessionId: string, fileId: string, tenantId?: string): Promise<void> {
    const headers = tenantId ? { 'X-Tenant-ID': tenantId } : undefined;
    const res = await api.delete<null>(
      `/uploads/sessions/${sessionId}/files/${fileId}`,
      headers,
    );
    if (!res.success) {
      throw new ApiError(res.message || 'Delete failed', 400, res.errors ?? []);
    }
  },
};

export { ApiError };
