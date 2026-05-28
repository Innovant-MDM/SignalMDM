-- SignalMDM Phase 2 — Mapping & Standardization RBAC Permissions Seed
-- PostgreSQL DML Script

BEGIN;

-- 1. Insert Phase 2 permissions in platform_permission
INSERT INTO platform_permission (screen_key, feature_key, label, description)
VALUES 
    -- Canonical Models
    ('canonical_models', 'view', 'View Canonical Models', 'Access the canonical fields definition screen'),
    ('canonical_models', 'manage', 'Manage Canonical Models', 'Create, update, and delete canonical fields'),

    -- Field Mappings
    ('field_mappings', 'view', 'View Field Mappings', 'Access the schema source-to-target field mapping screen'),
    ('field_mappings', 'manage', 'Manage Field Mappings', 'Configure and update field mapping relationships'),

    -- Transformation Rules
    ('transformation_rules', 'view', 'View Transformation Rules', 'Access the transformation rules list'),
    ('transformation_rules', 'manage', 'Manage Transformation Rules', 'Create, edit, and delete transformation rules'),

    -- Standardization Rules
    ('standardization_rules', 'view', 'View Standardization Rules', 'Access the standardization lookup and rules list'),
    ('standardization_rules', 'manage', 'Manage Standardization Rules', 'Create, edit, and delete standardization rules'),

    -- Normalization Runs
    ('normalization_runs', 'view', 'View Normalization Runs', 'Access and monitor background normalization jobs'),
    ('normalization_runs', 'manage', 'Manage Normalization Runs', 'Trigger, cancel, and manage normalization execution batches'),

    -- Normalized Records
    ('normalized_records', 'view', 'View Normalized Records', 'View successful standardized canonical records'),

    -- Mapping Errors
    ('mapping_errors', 'view', 'View Mapping Errors', 'View and browse normalization and validation errors'),
    ('mapping_errors', 'manage', 'Manage Mapping Errors', 'Resolve, edit mapping configurations, and trigger retry runs')
ON CONFLICT (screen_key, feature_key) DO NOTHING;

-- 2. Associate new permissions to System Roles

-- Super Admin: gets ALL permissions automatically (including the new ones)
INSERT INTO platform_role_permission (role_id, permission_id)
SELECT '22222222-2222-2222-2222-222222222222', p.permission_id
FROM platform_permission p
ON CONFLICT DO NOTHING;

-- Admin: gets all permissions (view + manage for all Phase 2 screens)
INSERT INTO platform_role_permission (role_id, permission_id)
SELECT '22222222-2222-2222-2222-333333333333', p.permission_id
FROM platform_permission p
WHERE p.screen_key IN (
    'canonical_models', 'field_mappings', 'transformation_rules', 
    'standardization_rules', 'normalization_runs', 'normalized_records', 'mapping_errors'
)
ON CONFLICT DO NOTHING;

-- Data Architect: gets all view and manage permissions for Phase 2
INSERT INTO platform_role_permission (role_id, permission_id)
SELECT '22222222-2222-2222-2222-444444444444', p.permission_id
FROM platform_permission p
WHERE p.screen_key IN (
    'canonical_models', 'field_mappings', 'transformation_rules', 
    'standardization_rules', 'normalization_runs', 'normalized_records', 'mapping_errors'
)
ON CONFLICT DO NOTHING;

-- Data Manager: gets view permissions for all, and manage for normalization_runs and mapping_errors
INSERT INTO platform_role_permission (role_id, permission_id)
SELECT '22222222-2222-2222-2222-555555555555', p.permission_id
FROM platform_permission p
WHERE (p.screen_key IN ('canonical_models', 'field_mappings', 'transformation_rules', 'standardization_rules', 'normalized_records') AND p.feature_key = 'view')
   OR (p.screen_key IN ('normalization_runs', 'mapping_errors'))
ON CONFLICT DO NOTHING;

-- Executive: gets view-only permissions for all screens
INSERT INTO platform_role_permission (role_id, permission_id)
SELECT '22222222-2222-2222-2222-666666666666', p.permission_id
FROM platform_permission p
WHERE p.screen_key IN (
    'canonical_models', 'field_mappings', 'transformation_rules', 
    'standardization_rules', 'normalization_runs', 'normalized_records', 'mapping_errors'
) AND p.feature_key = 'view'
ON CONFLICT DO NOTHING;

COMMIT;
