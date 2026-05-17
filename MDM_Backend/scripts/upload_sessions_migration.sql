-- ============================================================
-- SignalMDM — Upload Sessions Schema Migration
-- Run this ONCE against your PostgreSQL database.
-- ============================================================

-- Upload Sessions (folders)
CREATE TABLE IF NOT EXISTS upload_sessions (
    session_id   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID         NOT NULL REFERENCES tenant(tenant_id) ON DELETE RESTRICT,
    session_name VARCHAR(200) NOT NULL,
    domain       VARCHAR(200) NOT NULL,
    status       VARCHAR(20)  NOT NULL DEFAULT 'OPEN',
    created_by   VARCHAR(150),
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, session_name)
);

CREATE INDEX IF NOT EXISTS idx_upload_sessions_tenant ON upload_sessions(tenant_id);

-- Upload Session Files (one physical file per row)
CREATE TABLE IF NOT EXISTS upload_session_files (
    file_id           UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id        UUID          NOT NULL REFERENCES upload_sessions(session_id) ON DELETE CASCADE,
    tenant_id         UUID          NOT NULL REFERENCES tenant(tenant_id) ON DELETE RESTRICT,
    file_label        VARCHAR(300)  NOT NULL,
    original_filename VARCHAR(500)  NOT NULL,
    stored_path       VARCHAR(1000) NOT NULL,
    file_size_bytes   BIGINT,
    content_type      VARCHAR(100),
    record_count      INTEGER,
    checksum_md5      VARCHAR(32),
    uploaded_by       VARCHAR(150),
    uploaded_at       TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_usf_session ON upload_session_files(session_id);
CREATE INDEX IF NOT EXISTS idx_usf_tenant  ON upload_session_files(tenant_id);
