-- SignalMDM Phase 2 — Mapping & Standardization Database Migration
-- PostgreSQL DDL Script

BEGIN;

-- =========================================================================
-- 1. CANONICAL FIELDS
-- =========================================================================
CREATE TABLE IF NOT EXISTS canonical_fields (
    field_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant(tenant_id) ON DELETE RESTRICT,
    entity_type VARCHAR(50) NOT NULL, -- CUSTOMER, SUPPLIER, PRODUCT, ACCOUNT, ASSET, LOCATION, CONTACT
    canonical_field_name VARCHAR(100) NOT NULL,
    data_type VARCHAR(50) NOT NULL, -- TEXT, EMAIL, PHONE, DATE, CODE, etc.
    is_required BOOLEAN NOT NULL DEFAULT FALSE,
    validation_type VARCHAR(50) NOT NULL DEFAULT 'TEXT',
    standardization_type VARCHAR(50) NOT NULL DEFAULT 'TEXT',
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE, ARCHIVED
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tenant_entity_field UNIQUE (tenant_id, entity_type, canonical_field_name)
);

CREATE INDEX IF NOT EXISTS idx_canonical_fields_tenant_entity ON canonical_fields(tenant_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_canonical_fields_status ON canonical_fields(status);


-- =========================================================================
-- 2. REUSABLE TRANSFORMATION RULES
-- =========================================================================
CREATE TABLE IF NOT EXISTS transformation_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant(tenant_id) ON DELETE RESTRICT,
    rule_name VARCHAR(100) NOT NULL,
    rule_code VARCHAR(50) NOT NULL, -- E.g. TRIM, LOWERCASE, REMOVE_SPECIAL_CHARS
    transformation_type VARCHAR(50) NOT NULL, -- TRIM, UPPERCASE, LOWERCASE, TITLE_CASE, etc.
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tenant_rule_code UNIQUE (tenant_id, rule_code)
);

CREATE INDEX IF NOT EXISTS idx_transformation_rules_tenant ON transformation_rules(tenant_id);


-- =========================================================================
-- 3. REUSABLE STANDARDIZATION RULES
-- =========================================================================
CREATE TABLE IF NOT EXISTS standardization_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant(tenant_id) ON DELETE RESTRICT,
    rule_name VARCHAR(100) NOT NULL,
    rule_code VARCHAR(50) NOT NULL, -- E.g. COUNTRY_CODE_STD, STATE_CODE_STD
    standardization_type VARCHAR(50) NOT NULL, -- NAME, EMAIL, PHONE, ADDRESS, COUNTRY, STATE, CITY, DATE, CODE, TEXT
    mappings_json JSONB NOT NULL DEFAULT '{}'::jsonb, -- Key-value map like {"USA": "United States", "US": "United States"}
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tenant_std_rule_code UNIQUE (tenant_id, rule_code)
);

CREATE INDEX IF NOT EXISTS idx_standardization_rules_tenant ON standardization_rules(tenant_id);


-- =========================================================================
-- 4. FIELD MAPPINGS
-- =========================================================================
CREATE TABLE IF NOT EXISTS field_mappings (
    mapping_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant(tenant_id) ON DELETE RESTRICT,
    source_system_id UUID NOT NULL REFERENCES source_systems(source_system_id) ON DELETE RESTRICT,
    entity_type VARCHAR(50) NOT NULL,
    source_field_name VARCHAR(100) NOT NULL,
    canonical_field_id UUID NOT NULL REFERENCES canonical_fields(field_id) ON DELETE RESTRICT,
    transformation_rule_ids UUID[] NOT NULL DEFAULT '{}',
    standardization_rule_id UUID REFERENCES standardization_rules(rule_id) ON DELETE SET NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE', -- DRAFT, ACTIVE, INACTIVE
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tenant_src_entity_field UNIQUE (tenant_id, source_system_id, entity_type, source_field_name)
);

CREATE INDEX IF NOT EXISTS idx_field_mappings_tenant_src ON field_mappings(tenant_id, source_system_id);
CREATE INDEX IF NOT EXISTS idx_field_mappings_canonical ON field_mappings(canonical_field_id);


-- =========================================================================
-- 5. NORMALIZATION RUNS
-- =========================================================================
CREATE TABLE IF NOT EXISTS normalization_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant(tenant_id) ON DELETE RESTRICT,
    ingestion_run_id UUID REFERENCES ingestion_runs(run_id) ON DELETE SET NULL,
    source_system_id UUID NOT NULL REFERENCES source_systems(source_system_id) ON DELETE RESTRICT,
    entity_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'CREATED', -- CREATED, RUNNING, COMPLETED, FAILED, PARTIAL_SUCCESS, CANCELLED
    total_records INT NOT NULL DEFAULT 0,
    processed_records INT NOT NULL DEFAULT 0,
    successful_records INT NOT NULL DEFAULT 0,
    failed_records INT NOT NULL DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_by VARCHAR(150),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_normalization_runs_tenant ON normalization_runs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_normalization_runs_status ON normalization_runs(status);


-- =========================================================================
-- 6. MAPPING ERRORS
-- =========================================================================
CREATE TABLE IF NOT EXISTS mapping_errors (
    error_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant(tenant_id) ON DELETE RESTRICT,
    normalization_run_id UUID NOT NULL REFERENCES normalization_runs(run_id) ON DELETE CASCADE,
    staging_id UUID NOT NULL REFERENCES staging_entities(staging_id) ON DELETE CASCADE,
    error_type VARCHAR(50) NOT NULL, -- MISSING_MAPPING, INVALID_CANONICAL_FIELD, TRANSFORMATION_FAILED, STANDARDIZATION_FAILED, PAYLOAD_ERROR, DUPLICATE_MAPPING
    source_field VARCHAR(100),
    source_value TEXT,
    error_message TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'OPEN', -- OPEN, RETRIED, RESOLVED, IGNORED
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(150)
);

CREATE INDEX IF NOT EXISTS idx_mapping_errors_tenant_status ON mapping_errors(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_mapping_errors_staging ON mapping_errors(staging_id);


-- =========================================================================
-- 7. STAGING ENTITIES UPDATES (ADD COLUMNS FOR PHASE 2)
-- =========================================================================
ALTER TABLE staging_entities 
ADD COLUMN IF NOT EXISTS normalization_run_id UUID REFERENCES normalization_runs(run_id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS mapped_payload_json JSONB,
ADD COLUMN IF NOT EXISTS standardized_payload_json JSONB,
ADD COLUMN IF NOT EXISTS normalization_status VARCHAR(50) DEFAULT 'PENDING',
ADD COLUMN IF NOT EXISTS normalized_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS normalization_error TEXT;

CREATE INDEX IF NOT EXISTS idx_staging_entities_norm_status ON staging_entities(normalization_status);
CREATE INDEX IF NOT EXISTS idx_staging_entities_norm_run ON staging_entities(normalization_run_id);

COMMIT;
