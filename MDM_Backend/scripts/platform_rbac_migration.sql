-- ============================================================
-- SignalMDM — Platform RBAC Schema Migration
-- Run this ONCE against your PostgreSQL database.
-- ============================================================

-- 1. Platform Roles
CREATE TABLE IF NOT EXISTS platform_role (
    role_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    role_key         VARCHAR(80) NOT NULL UNIQUE,
    role_label       VARCHAR(150) NOT NULL,
    description      TEXT,
    is_system        BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed system roles
INSERT INTO platform_role (role_key, role_label, description, is_system) VALUES
  ('super_admin',    'Super Admin',    'Full platform control — all screens, all features, user & role management.', TRUE),
  ('admin',          'Admin',          'Tenant management, platform user management, audit review. No RBAC editing.', TRUE),
  ('data_architect', 'Data Architect', 'Upload data, manage source systems, review ingestion runs, delete sources.', TRUE),
  ('data_manager',   'Data Manager',   'Review staging records and approve data for target loading.', TRUE),
  ('executive',      'Executive',      'Read-only dashboard and reports. Verify data quality and completeness.', TRUE)
ON CONFLICT (role_key) DO NOTHING;

-- 2. Platform Permissions (screen + feature granularity)
CREATE TABLE IF NOT EXISTS platform_permission (
    permission_id    UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    screen_key       VARCHAR(100) NOT NULL,
    feature_key      VARCHAR(150) NOT NULL,
    label            VARCHAR(255) NOT NULL,
    description      TEXT,
    UNIQUE (screen_key, feature_key)
);

-- Screen-level permissions (view access)
INSERT INTO platform_permission (screen_key, feature_key, label, description) VALUES
  ('dashboard',     'view',           'View Dashboard',            'Access the main dashboard'),
  ('sources',       'view',           'View Source Systems',       'See list of registered source systems'),
  ('sources',       'register',       'Register Source',           'Register a new source system'),
  ('sources',       'delete',         'Delete Source',             'Delete a source system'),
  ('ingestion',     'view',           'View Ingestion Runs',       'See ingestion run list and details'),
  ('ingestion',     'start',          'Start Ingestion',           'Launch a new ingestion run'),
  ('ingestion',     'cancel',         'Cancel Ingestion',          'Stop a running ingestion job'),
  ('upload',        'view',           'View Upload Data',          'Access the upload data screen'),
  ('upload',        'upload_file',    'Upload Files',              'Upload CSV/JSON files for ingestion'),
  ('raw_landing',   'view',           'View Raw Landing',          'Browse raw loaded records'),
  ('staging',       'view',           'View Staging Records',      'Browse staging entity records'),
  ('staging',       'approve',        'Approve Staging',           'Approve staging records for target load'),
  ('api_logs',      'view',           'View API Logs',             'Access API request/response logs'),
  ('system_health', 'view',           'View System Health',        'Access system health monitoring'),
  ('platform',      'view_tenants',   'View Tenants',              'See the tenant list'),
  ('platform',      'manage_tenants', 'Manage Tenants',            'Create and update tenants'),
  ('platform',      'view_users',     'View Platform Users',       'See platform admin user list'),
  ('platform',      'manage_users',   'Manage Platform Users',     'Create, edit, block platform users'),
  ('platform',      'view_roles',     'View Roles & Permissions',  'See RBAC roles and assignments'),
  ('platform',      'manage_roles',   'Manage Roles & Permissions','Edit role permissions and screen access'),
  ('domains',       'view',           'View Domains',              'Access the domains management screen'),
  ('domains',       'manage',         'Manage Domains',            'Create, update and deactivate domains')
ON CONFLICT (screen_key, feature_key) DO NOTHING;

-- 3. Role-Permission join table
CREATE TABLE IF NOT EXISTS platform_role_permission (
    role_id       UUID NOT NULL REFERENCES platform_role(role_id)       ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES platform_permission(permission_id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- Seed default role-permission assignments
DO $$
DECLARE
    r_super       UUID;
    r_admin       UUID;
    r_architect   UUID;
    r_manager     UUID;
    r_executive   UUID;
BEGIN
    SELECT role_id INTO r_super     FROM platform_role WHERE role_key = 'super_admin';
    SELECT role_id INTO r_admin     FROM platform_role WHERE role_key = 'admin';
    SELECT role_id INTO r_architect FROM platform_role WHERE role_key = 'data_architect';
    SELECT role_id INTO r_manager   FROM platform_role WHERE role_key = 'data_manager';
    SELECT role_id INTO r_executive FROM platform_role WHERE role_key = 'executive';

    -- Super Admin: all permissions
    INSERT INTO platform_role_permission (role_id, permission_id)
        SELECT r_super, permission_id FROM platform_permission
        ON CONFLICT DO NOTHING;

    -- Admin: all except manage_roles
    INSERT INTO platform_role_permission (role_id, permission_id)
        SELECT r_admin, permission_id FROM platform_permission
        WHERE (screen_key, feature_key) NOT IN (('platform', 'manage_roles'))
        ON CONFLICT DO NOTHING;

    -- Data Architect
    INSERT INTO platform_role_permission (role_id, permission_id)
        SELECT r_architect, permission_id FROM platform_permission
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
        SELECT r_manager, permission_id FROM platform_permission
        WHERE (screen_key, feature_key) IN (
            ('dashboard','view'),
            ('ingestion','view'),
            ('raw_landing','view'),
            ('staging','view'), ('staging','approve')
        )
        ON CONFLICT DO NOTHING;

    -- Executive
    INSERT INTO platform_role_permission (role_id, permission_id)
        SELECT r_executive, permission_id FROM platform_permission
        WHERE (screen_key, feature_key) IN (('dashboard','view'))
        ON CONFLICT DO NOTHING;
END $$;

-- 4. Alter platform_admin — add new columns
ALTER TABLE platform_admin
    ADD COLUMN IF NOT EXISTS role_id              UUID REFERENCES platform_role(role_id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS full_name            VARCHAR(255),
    ADD COLUMN IF NOT EXISTS is_blocked           BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS created_by           UUID REFERENCES platform_admin(admin_id) ON DELETE SET NULL;

-- Backfill: existing admins become super_admin
UPDATE platform_admin
SET role_id = (SELECT role_id FROM platform_role WHERE role_key = 'super_admin')
WHERE role_id IS NULL;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_prp_role_id ON platform_role_permission(role_id);
CREATE INDEX IF NOT EXISTS idx_pa_role_id  ON platform_admin(role_id);

-- Verify:
-- SELECT pa.email, pr.role_label FROM platform_admin pa
-- LEFT JOIN platform_role pr ON pr.role_id = pa.role_id;
