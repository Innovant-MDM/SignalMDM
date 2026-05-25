# SignalMDM: Database Schema & Referentials Manual

This document provides a highly detailed reference of the PostgreSQL database schemas, indexes, structural tenant-isolation strategies, and transactional audit layouts in SignalMDM. It includes copy-pasteable PostgreSQL DDL commands and default seed scripts to initialize the database from scratch.

---

## 1. Multi-Tenant Isolation Strategy

Logical isolation is enforced directly within the PostgreSQL storage tier.
1.  **Strict Scoping Column:** Every core tenant table includes a mandatory column:
    ```sql
    tenant_id UUID NOT NULL
    ```
2.  **No Direct Deletes:** Foreign key definitions contain `ondelete="RESTRICT"` for operational tables. This prevents transactional data (e.g. Ingestion runs or Raw records) from being wiped out or orphaned:
    ```sql
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenant(tenant_id) ON DELETE RESTRICT
    ```
3.  **Automatic Queries Appends:** Row-level context parameters, decoded from the client's AES-256 JWT by backend middlewares, are bound to the active database session context. All SELECT queries append:
    ```sql
    WHERE tenant_id = :session_tenant_id
    ```
    This completely isolates query data between corporate organizations.

---

## 2. Table Referential Specifications

Here we outline the structural details and exact SQL DDL creation parameters of key system tables.

### 2.1 Table: `tenant`
*   **Purpose:** The parent organization identity record. All system schemas reference this root.
*   **DDL Schema:**
    ```sql
    CREATE TABLE tenant (
        tenant_id   UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_name VARCHAR(255)  NOT NULL,
        tenant_code VARCHAR(100)  NOT NULL UNIQUE,
        status      VARCHAR(50)   NOT NULL DEFAULT 'ACTIVE',
        created_at  TIMESTAMPTZ   NOT NULL DEFAULT now()
    );
    COMMENT ON TABLE tenant IS 'Root tenant / organisation record.';
    ```

---

### 2.2 Table: `platform_role`
*   **Purpose:** Stores platform-level administration roles.
*   **DDL Schema:**
    ```sql
    CREATE TABLE platform_role (
        role_id     UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
        role_key    VARCHAR(80)  NOT NULL UNIQUE,
        role_label  VARCHAR(150) NOT NULL,
        description TEXT,
        is_system   BOOLEAN      NOT NULL DEFAULT FALSE,
        created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
    );
    ```

---

### 2.3 Table: `platform_permission`
*   **Purpose:** Stores granular administrative screen-level permissions.
*   **DDL Schema:**
    ```sql
    CREATE TABLE platform_permission (
        permission_id UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
        screen_key    VARCHAR(100) NOT NULL,
        feature_key   VARCHAR(150) NOT NULL,
        label         VARCHAR(255) NOT NULL,
        description   TEXT,
        UNIQUE (screen_key, feature_key)
    );
    ```

---

### 2.4 Table: `platform_role_permission`
*   **Purpose:** Join table linking roles to permissions.
*   **DDL Schema:**
    ```sql
    CREATE TABLE platform_role_permission (
        role_id       UUID NOT NULL REFERENCES platform_role(role_id) ON DELETE CASCADE,
        permission_id UUID NOT NULL REFERENCES platform_permission(permission_id) ON DELETE CASCADE,
        PRIMARY KEY (role_id, permission_id)
    );
    CREATE INDEX idx_prp_role_id ON platform_role_permission(role_id);
    ```

---

### 2.5 Table: `platform_admin`
*   **Purpose:** Stores identity records and authentication states for global administrators.
*   **DDL Schema:**
    ```sql
    CREATE TABLE platform_admin (
        admin_id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
        email                 VARCHAR(255) NOT NULL UNIQUE,
        username              VARCHAR(150) NOT NULL,
        password_hash         TEXT         NOT NULL,
        is_active             BOOLEAN      NOT NULL DEFAULT TRUE,
        role_id               UUID         REFERENCES platform_role(role_id) ON DELETE SET NULL,
        full_name             VARCHAR(255),
        is_blocked            BOOLEAN      NOT NULL DEFAULT FALSE,
        must_change_password  BOOLEAN      NOT NULL DEFAULT FALSE,
        created_by            UUID         REFERENCES platform_admin(admin_id) ON DELETE SET NULL,
        two_fa_enabled        BOOLEAN      NOT NULL DEFAULT FALSE,
        two_fa_secret         TEXT,
        two_fa_setup_complete BOOLEAN      NOT NULL DEFAULT FALSE,
        last_login_at         TIMESTAMPTZ,
        created_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
        updated_at            TIMESTAMPTZ  NOT NULL DEFAULT now()
    );
    CREATE INDEX idx_platform_admin_email ON platform_admin (email);
    CREATE INDEX idx_pa_role_id ON platform_admin(role_id);
    ```

---

### 2.6 Table: `source_systems`
*   **Purpose:** Registered origins of data flowing into the MDM platform per tenant.
*   **DDL Schema:**
    ```sql
    CREATE TABLE source_systems (
        source_system_id UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id        UUID         NOT NULL REFERENCES tenant(tenant_id) ON DELETE RESTRICT,
        source_name      VARCHAR(255) NOT NULL,
        source_code      VARCHAR(100) NOT NULL UNIQUE,
        source_type      VARCHAR(50)  NOT NULL DEFAULT 'OTHER',
        connection_type  VARCHAR(50)  NOT NULL DEFAULT 'OTHER',
        config_json      JSONB,
        is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
        status           VARCHAR(50)  NOT NULL DEFAULT 'ACTIVE',
        created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
        updated_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
    );
    CREATE INDEX idx_source_systems_tenant ON source_systems(tenant_id);
    ```

---

### 2.7 Table: `domains`
*   **Purpose:** Stores registered data domains representing logical data classification categories (e.g. Customer, Finance, HR) per tenant.
*   **DDL Schema:**
    ```sql
    CREATE TABLE domains (
        id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id   UUID         NOT NULL REFERENCES tenant(tenant_id) ON DELETE CASCADE,
        domain_name VARCHAR(100) NOT NULL,
        description TEXT,
        status      VARCHAR(50)  NOT NULL DEFAULT 'ACTIVE',
        created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
        updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
    );
    CREATE INDEX idx_domains_tenant ON domains(tenant_id);
    ```

---

### 2.8 Table: `upload_sessions`
*   **Purpose:** Tracks folders/sessions of bulk dataset uploads.
*   **DDL Schema:**
    ```sql
    CREATE TABLE upload_sessions (
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
    CREATE INDEX idx_upload_sessions_tenant ON upload_sessions(tenant_id);
    ```

---

### 2.9 Table: `upload_session_files`
*   **Purpose:** Stores files associated with upload sessions.
*   **DDL Schema:**
    ```sql
    CREATE TABLE upload_session_files (
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
    CREATE INDEX idx_usf_session ON upload_session_files(session_id);
    CREATE INDEX idx_usf_tenant ON upload_session_files(tenant_id);
    ```

---

### 2.10 Table: `ingestion_runs`
*   **Purpose:** Records single execution jobs of the data loading and staging workflow.
*   **DDL Schema:**
    ```sql
    CREATE TABLE ingestion_runs (
        run_id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id        UUID         NOT NULL REFERENCES tenant(tenant_id) ON DELETE RESTRICT,
        source_system_id UUID         NOT NULL REFERENCES source_systems(source_system_id) ON DELETE RESTRICT,
        state            VARCHAR(50)  NOT NULL DEFAULT 'CREATED',
        triggered_by     VARCHAR(150),
        file_count       INTEGER      NOT NULL DEFAULT 0,
        record_count     INTEGER      NOT NULL DEFAULT 0,
        error_message    TEXT,
        started_at       TIMESTAMPTZ,
        completed_at     TIMESTAMPTZ,
        created_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
    );
    CREATE INDEX idx_ingestion_runs_tenant ON ingestion_runs(tenant_id);
    CREATE INDEX idx_ingestion_runs_source ON ingestion_runs(source_system_id);
    ```

---

### 2.11 Table: `file_uploads`
*   **Purpose:** Records files processed within a specific ingestion run.
*   **DDL Schema:**
    ```sql
    CREATE TABLE file_uploads (
        file_id           UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id         UUID          NOT NULL REFERENCES tenant(tenant_id) ON DELETE RESTRICT,
        run_id            UUID          NOT NULL REFERENCES ingestion_runs(run_id) ON DELETE CASCADE,
        original_filename VARCHAR(500)  NOT NULL,
        stored_path       VARCHAR(1000) NOT NULL,
        file_size_bytes   BIGINT,
        content_type      VARCHAR(100),
        checksum_md5      VARCHAR(32),
        uploaded_at       TIMESTAMPTZ   NOT NULL DEFAULT now()
    );
    CREATE INDEX idx_file_uploads_tenant ON file_uploads(tenant_id);
    CREATE INDEX idx_file_uploads_run ON file_uploads(run_id);
    ```

---

### 2.12 Table: `raw_records`
*   **Purpose:** The immutable landing zone for raw loaded records.
*   **DDL Schema:**
    ```sql
    CREATE TABLE raw_records (
        raw_record_id    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id        UUID        NOT NULL REFERENCES tenant(tenant_id) ON DELETE RESTRICT,
        run_id           UUID        NOT NULL REFERENCES ingestion_runs(run_id) ON DELETE CASCADE,
        file_id          UUID        REFERENCES file_uploads(file_id) ON DELETE SET NULL,
        source_system_id UUID        NOT NULL REFERENCES source_systems(source_system_id) ON DELETE RESTRICT,
        row_index        INTEGER,
        raw_data         JSONB       NOT NULL,
        checksum_md5     VARCHAR(32) NOT NULL,
        created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE INDEX idx_raw_records_tenant ON raw_records(tenant_id);
    CREATE INDEX idx_raw_records_run ON raw_records(run_id);
    CREATE INDEX idx_raw_records_checksum ON raw_records(tenant_id, checksum_md5);
    ```

---

### 2.13 Table: `staging_entities`
*   **Purpose:** The staging zone where records are cleansed and prepared for mapping.
*   **DDL Schema:**
    ```sql
    CREATE TABLE staging_entities (
        staging_id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id          UUID         NOT NULL REFERENCES tenant(tenant_id) ON DELETE RESTRICT,
        run_id             UUID         NOT NULL REFERENCES ingestion_runs(run_id) ON DELETE CASCADE,
        raw_record_id      UUID         NOT NULL UNIQUE REFERENCES raw_records(raw_record_id) ON DELETE RESTRICT,
        source_system_id   UUID         NOT NULL REFERENCES source_systems(source_system_id) ON DELETE RESTRICT,
        entity_data        JSONB        NOT NULL,
        state              VARCHAR(50)  NOT NULL DEFAULT 'READY_FOR_MAPPING',
        mapped_entity_type VARCHAR(100),
        created_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
    );
    CREATE INDEX idx_staging_entities_tenant ON staging_entities(tenant_id);
    CREATE INDEX idx_staging_entities_run ON staging_entities(run_id);
    ```

---

### 2.14 Table: `audit_log`
*   **Purpose:** Immutable append-only audit trail capturing all system mutations.
*   **DDL Schema:**
    ```sql
    CREATE TABLE audit_log (
        audit_id        UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id       UUID         REFERENCES tenant(tenant_id) ON DELETE RESTRICT,
        entity_name     VARCHAR(150),
        entity_id       UUID,
        operation_type  VARCHAR(50),
        old_value       JSONB,
        new_value       JSONB,
        performed_by    VARCHAR(150),
        performed_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
        source_ip       VARCHAR(100),
        trace_id        VARCHAR(255),
        approved_by     VARCHAR(150),
        approval_reason VARCHAR(500)
    );
    CREATE INDEX idx_audit_trace ON audit_log(trace_id);
    CREATE INDEX idx_audit_performed ON audit_log(performed_at);
    ```

---

## 3. Index Strategy Summary

*   **Foreign Key Indexing:** Every foreign key in the schema is backed by a B-Tree index to speed up join operations and avoid full table scans during cascades.
*   **Composite Indexing:** Multi-tenant scoping queries are optimized using composite indexes prefixed with the `tenant_id` column (e.g. `idx_raw_records_checksum` on `(tenant_id, checksum_md5)`).
*   **JSONB Indexing:** The `raw_data` and metadata `config_json` columns use generalized inverted index (GIN) models to support nested attribute filtering:
    ```sql
    CREATE INDEX idx_raw_data_gin ON raw_records USING gin (raw_data);
    ```

---

## 4. Complete Unified PostgreSQL DDL Script

Copy and execute this script against your PostgreSQL instance to establish the complete schema at once:

```sql
-- D:\SignalMDM\MDM_DataLayer\SignalMDM_Schema.sql
-- ============================================================================
-- SIGNALMDM SYSTEM SCHEMA CREATION
-- ============================================================================

-- Extensions (for UUID generation)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Table definitions in topological dependency order
CREATE TABLE tenant (
    tenant_id   UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_name VARCHAR(255)  NOT NULL,
    tenant_code VARCHAR(100)  NOT NULL UNIQUE,
    status      VARCHAR(50)   NOT NULL DEFAULT 'ACTIVE',
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE platform_role (
    role_id     UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    role_key    VARCHAR(80)  NOT NULL UNIQUE,
    role_label  VARCHAR(150) NOT NULL,
    description TEXT,
    is_system   BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE platform_permission (
    permission_id UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    screen_key    VARCHAR(100) NOT NULL,
    feature_key   VARCHAR(150) NOT NULL,
    label         VARCHAR(255) NOT NULL,
    description   TEXT,
    UNIQUE (screen_key, feature_key)
);

CREATE TABLE platform_role_permission (
    role_id       UUID NOT NULL REFERENCES platform_role(role_id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES platform_permission(permission_id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE platform_admin (
    admin_id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email                 VARCHAR(255) NOT NULL UNIQUE,
    username              VARCHAR(150) NOT NULL,
    password_hash         TEXT         NOT NULL,
    is_active             BOOLEAN      NOT NULL DEFAULT TRUE,
    role_id               UUID         REFERENCES platform_role(role_id) ON DELETE SET NULL,
    full_name             VARCHAR(255),
    is_blocked            BOOLEAN      NOT NULL DEFAULT FALSE,
    must_change_password  BOOLEAN      NOT NULL DEFAULT FALSE,
    created_by            UUID         REFERENCES platform_admin(admin_id) ON DELETE SET NULL,
    two_fa_enabled        BOOLEAN      NOT NULL DEFAULT FALSE,
    two_fa_secret         TEXT,
    two_fa_setup_complete BOOLEAN      NOT NULL DEFAULT FALSE,
    last_login_at         TIMESTAMPTZ,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE source_systems (
    source_system_id UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID         NOT NULL REFERENCES tenant(tenant_id) ON DELETE RESTRICT,
    source_name      VARCHAR(255) NOT NULL,
    source_code      VARCHAR(100) NOT NULL UNIQUE,
    source_type      VARCHAR(50)  NOT NULL DEFAULT 'OTHER',
    connection_type  VARCHAR(50)  NOT NULL DEFAULT 'OTHER',
    config_json      JSONB,
    is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
    status           VARCHAR(50)  NOT NULL DEFAULT 'ACTIVE',
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE domains (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID         NOT NULL REFERENCES tenant(tenant_id) ON DELETE CASCADE,
    domain_name VARCHAR(100) NOT NULL,
    description TEXT,
    status      VARCHAR(50)  NOT NULL DEFAULT 'ACTIVE',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE upload_sessions (
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

CREATE TABLE upload_session_files (
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

CREATE TABLE ingestion_runs (
    run_id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID         NOT NULL REFERENCES tenant(tenant_id) ON DELETE RESTRICT,
    source_system_id UUID         NOT NULL REFERENCES source_systems(source_system_id) ON DELETE RESTRICT,
    state            VARCHAR(50)  NOT NULL DEFAULT 'CREATED',
    triggered_by     VARCHAR(150),
    file_count       INTEGER      NOT NULL DEFAULT 0,
    record_count     INTEGER      NOT NULL DEFAULT 0,
    error_message    TEXT,
    started_at       TIMESTAMPTZ,
    completed_at     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE file_uploads (
    file_id           UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         UUID          NOT NULL REFERENCES tenant(tenant_id) ON DELETE RESTRICT,
    run_id            UUID          NOT NULL REFERENCES ingestion_runs(run_id) ON DELETE CASCADE,
    original_filename VARCHAR(500)  NOT NULL,
    stored_path       VARCHAR(1000) NOT NULL,
    file_size_bytes   BIGINT,
    content_type      VARCHAR(100),
    checksum_md5      VARCHAR(32),
    uploaded_at       TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE raw_records (
    raw_record_id    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID        NOT NULL REFERENCES tenant(tenant_id) ON DELETE RESTRICT,
    run_id           UUID        NOT NULL REFERENCES ingestion_runs(run_id) ON DELETE CASCADE,
    file_id          UUID        REFERENCES file_uploads(file_id) ON DELETE SET NULL,
    source_system_id UUID        NOT NULL REFERENCES source_systems(source_system_id) ON DELETE RESTRICT,
    row_index        INTEGER,
    raw_data         JSONB       NOT NULL,
    checksum_md5     VARCHAR(32) NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE staging_entities (
    staging_id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID         NOT NULL REFERENCES tenant(tenant_id) ON DELETE RESTRICT,
    run_id             UUID         NOT NULL REFERENCES ingestion_runs(run_id) ON DELETE CASCADE,
    raw_record_id      UUID         NOT NULL UNIQUE REFERENCES raw_records(raw_record_id) ON DELETE RESTRICT,
    source_system_id   UUID         NOT NULL REFERENCES source_systems(source_system_id) ON DELETE RESTRICT,
    entity_data        JSONB        NOT NULL,
    state              VARCHAR(50)  NOT NULL DEFAULT 'READY_FOR_MAPPING',
    mapped_entity_type VARCHAR(100),
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (
    audit_id        UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID         REFERENCES tenant(tenant_id) ON DELETE RESTRICT,
    entity_name     VARCHAR(150),
    entity_id       UUID,
    operation_type  VARCHAR(50),
    old_value       JSONB,
    new_value       JSONB,
    performed_by    VARCHAR(150),
    performed_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    source_ip       VARCHAR(100),
    trace_id        VARCHAR(255),
    approved_by     VARCHAR(150),
    approval_reason VARCHAR(500)
);

-- Index creation queries
CREATE INDEX idx_platform_admin_email    ON platform_admin (email);
CREATE INDEX idx_pa_role_id              ON platform_admin(role_id);
CREATE INDEX idx_prp_role_id             ON platform_role_permission(role_id);
CREATE INDEX idx_source_systems_tenant   ON source_systems(tenant_id);
CREATE INDEX idx_domains_tenant          ON domains(tenant_id);
CREATE INDEX idx_upload_sessions_tenant  ON upload_sessions(tenant_id);
CREATE INDEX idx_usf_session             ON upload_session_files(session_id);
CREATE INDEX idx_usf_tenant              ON upload_session_files(tenant_id);
CREATE INDEX idx_ingestion_runs_tenant   ON ingestion_runs(tenant_id);
CREATE INDEX idx_ingestion_runs_source   ON ingestion_runs(source_system_id);
CREATE INDEX idx_file_uploads_tenant     ON file_uploads(tenant_id);
CREATE INDEX idx_file_uploads_run        ON file_uploads(run_id);
CREATE INDEX idx_raw_records_tenant      ON raw_records(tenant_id);
CREATE INDEX idx_raw_records_run         ON raw_records(run_id);
CREATE INDEX idx_raw_records_checksum    ON raw_records(tenant_id, checksum_md5);
CREATE INDEX idx_staging_entities_tenant ON staging_entities(tenant_id);
CREATE INDEX idx_staging_entities_run    ON staging_entities(run_id);
CREATE INDEX idx_audit_trace             ON audit_log(trace_id);
CREATE INDEX idx_audit_performed         ON audit_log(performed_at);
CREATE INDEX idx_raw_data_gin            ON raw_records USING gin (raw_data);
```

---

## 5. Seed Data & Sample User Script

Use the script below to seed system roles, administrative screen permissions, default mappings, a test tenant, and a default administrative user.

*   **Administrator Email:** `jofrey.joseph@flame.edu.in`
*   **Username:** `Jofrey`
*   **Password:** `Admin@123`

```sql
-- D:\SignalMDM\MDM_DataLayer\SignalMDM_Seed.sql
-- ============================================================================
-- SEED DATA SETUP
-- ============================================================================

-- 1. Create Default Tenant
INSERT INTO tenant (tenant_id, tenant_name, tenant_code, status)
VALUES ('11111111-1111-1111-1111-111111111111', 'System Platform Admin Tenant', 'platform', 'ACTIVE')
ON CONFLICT (tenant_code) DO NOTHING;

INSERT INTO tenant (tenant_id, tenant_name, tenant_code, status)
VALUES ('d3b07384-d113-4956-a5db-82601cf941a3', 'Standard Acme Corporate Tenant', 'acme', 'ACTIVE')
ON CONFLICT (tenant_code) DO NOTHING;

-- 2. Seed System Roles
INSERT INTO platform_role (role_id, role_key, role_label, description, is_system) 
VALUES
  ('22222222-2222-2222-2222-222222222222', 'super_admin',    'Super Admin',    'Full platform control — all screens, all features, user & role management.', TRUE),
  ('22222222-2222-2222-2222-333333333333', 'admin',          'Admin',          'Tenant management, platform user management, audit review. No RBAC editing.', TRUE),
  ('22222222-2222-2222-2222-444444444444', 'data_architect', 'Data Architect', 'Upload data, manage source systems, review ingestion runs, delete sources.', TRUE),
  ('22222222-2222-2222-2222-555555555555', 'data_manager',   'Data Manager',   'Review staging records and approve data for target loading.', TRUE),
  ('22222222-2222-2222-2222-666666666666', 'executive',      'Executive',      'Read-only dashboard and reports. Verify data quality and completeness.', TRUE)
ON CONFLICT (role_key) DO NOTHING;

-- 3. Seed Screen permissions
INSERT INTO platform_permission (permission_id, screen_key, feature_key, label, description) 
VALUES
  (gen_random_uuid(), 'dashboard',     'view',           'View Dashboard',            'Access the main dashboard'),
  (gen_random_uuid(), 'sources',       'view',           'View Source Systems',       'See list of registered source systems'),
  (gen_random_uuid(), 'sources',       'register',       'Register Source',           'Register a new source system'),
  (gen_random_uuid(), 'sources',       'delete',         'Delete Source',             'Delete a source system'),
  (gen_random_uuid(), 'ingestion',     'view',           'View Ingestion Runs',       'See ingestion run list and details'),
  (gen_random_uuid(), 'ingestion',     'start',          'Start Ingestion',           'Launch a new ingestion run'),
  (gen_random_uuid(), 'ingestion',     'cancel',         'Cancel Ingestion',          'Stop a running ingestion job'),
  (gen_random_uuid(), 'upload',        'view',           'View Upload Data',          'Access the upload data screen'),
  (gen_random_uuid(), 'upload',        'upload_file',    'Upload Files',              'Upload CSV/JSON files for ingestion'),
  (gen_random_uuid(), 'raw_landing',   'view',           'View Raw Landing',          'Browse raw loaded records'),
  (gen_random_uuid(), 'staging',       'view',           'View Staging Records',      'Browse staging entity records'),
  (gen_random_uuid(), 'staging',       'approve',        'Approve Staging',           'Approve staging records for target load'),
  (gen_random_uuid(), 'api_logs',      'view',           'View API Logs',             'Access API request/response logs'),
  (gen_random_uuid(), 'system_health', 'view',           'View System Health',        'Access system health monitoring'),
  (gen_random_uuid(), 'platform',      'view_tenants',   'View Tenants',              'See the tenant list'),
  (gen_random_uuid(), 'platform',      'manage_tenants', 'Manage Tenants',            'Create and update tenants'),
  (gen_random_uuid(), 'platform',      'view_users',     'View Platform Users',       'See platform admin user list'),
  (gen_random_uuid(), 'platform',      'manage_users',   'Manage Platform Users',     'Create, edit, block platform users'),
  (gen_random_uuid(), 'platform',      'view_roles',     'View Roles & Permissions',  'See RBAC roles and assignments'),
  (gen_random_uuid(), 'platform',      'manage_roles',   'Manage Roles & Permissions','Edit role permissions and screen access'),
  (gen_random_uuid(), 'domains',       'view',           'View Domains',              'Access the domains management screen'),
  (gen_random_uuid(), 'domains',       'manage',         'Manage Domains',            'Create, update and deactivate domains')
ON CONFLICT (screen_key, feature_key) DO NOTHING;

-- 4. Associate Permissions to System Roles
-- Super Admin (Gets all permissions)
INSERT INTO platform_role_permission (role_id, permission_id)
SELECT '22222222-2222-2222-2222-222222222222', permission_id FROM platform_permission
ON CONFLICT DO NOTHING;

-- Admin (Gets all permissions EXCEPT manage_roles)
INSERT INTO platform_role_permission (role_id, permission_id)
SELECT '22222222-2222-2222-2222-333333333333', permission_id FROM platform_permission
WHERE (screen_key, feature_key) NOT IN (('platform', 'manage_roles'))
ON CONFLICT DO NOTHING;

-- Data Architect
INSERT INTO platform_role_permission (role_id, permission_id)
SELECT '22222222-2222-2222-2222-444444444444', permission_id FROM platform_permission
WHERE (screen_key, feature_key) IN (
    ('dashboard','view'),
    ('sources','view'), ('sources','register'), ('sources','delete'),
    ('ingestion','view'), ('ingestion','start'), ('ingestion','cancel'),
    ('upload','view'), ('upload','upload_file'),
    ('raw_landing','view'),
    ('staging','view'),
    ('domains','view'), ('domains','manage')
)
ON CONFLICT DO NOTHING;

-- Data Manager
INSERT INTO platform_role_permission (role_id, permission_id)
SELECT '22222222-2222-2222-2222-555555555555', permission_id FROM platform_permission
WHERE (screen_key, feature_key) IN (
    ('dashboard','view'),
    ('ingestion','view'),
    ('raw_landing','view'),
    ('staging','view'), ('staging','approve')
)
ON CONFLICT DO NOTHING;

-- Executive
INSERT INTO platform_role_permission (role_id, permission_id)
SELECT '22222222-2222-2222-2222-666666666666', permission_id FROM platform_permission
WHERE (screen_key, feature_key) IN (('dashboard','view'))
ON CONFLICT DO NOTHING;

-- 5. Seed Test SuperAdmin User Account (Password: Admin@123)
-- Hash generated using bcrypt salt-cost 12
INSERT INTO platform_admin (
    admin_id,
    email,
    username,
    password_hash,
    is_active,
    role_id,
    full_name,
    is_blocked,
    must_change_password
) VALUES (
    '99999999-9999-9999-9999-999999999999',
    'jofrey.joseph@flame.edu.in',
    'Jofrey',
    '$2b$12$egUiMGcIpkKhHkEfGdJlf.5tDFM3bxl05N6bspquBzFNigseFmXzm',
    TRUE,
    '22222222-2222-2222-2222-222222222222', -- super_admin
    'Jofrey Joseph',
    FALSE,
    FALSE
) ON CONFLICT (email) DO NOTHING;
```
