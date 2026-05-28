-- SignalMDM Phase 2 — Mapping & Standardization Reusable Rules Seed Script
-- Run this AFTER executing db_phase2_migration.sql to seed standard rules for all existing tenants

DO $$
DECLARE
    t_rec RECORD;
BEGIN
    FOR t_rec IN SELECT tenant_id FROM tenant LOOP
        -- =====================================================================
        -- TRANSFORMATION RULES SEED
        -- =====================================================================
        INSERT INTO transformation_rules (tenant_id, rule_name, rule_code, transformation_type, config_json, status)
        VALUES
            (t_rec.tenant_id, 'Trim Whitespace', 'TRIM', 'TRIM', '{}'::jsonb, 'ACTIVE'),
            (t_rec.tenant_id, 'Convert to Uppercase', 'UPPERCASE', 'UPPERCASE', '{}'::jsonb, 'ACTIVE'),
            (t_rec.tenant_id, 'Convert to Lowercase', 'LOWERCASE', 'LOWERCASE', '{}'::jsonb, 'ACTIVE'),
            (t_rec.tenant_id, 'Convert to Title Case', 'TITLE_CASE', 'TITLE_CASE', '{}'::jsonb, 'ACTIVE'),
            (t_rec.tenant_id, 'Remove Special Characters', 'REMOVE_SPECIAL_CHARS', 'REMOVE_SPECIAL_CHARS', '{}'::jsonb, 'ACTIVE'),
            (t_rec.tenant_id, 'Normalize Indian Phone Numbers', 'NORMALIZE_IN_PHONE', 'NORMALIZE_PHONE', '{"default_country": "IN"}'::jsonb, 'ACTIVE'),
            (t_rec.tenant_id, 'Normalize US Phone Numbers', 'NORMALIZE_US_PHONE', 'NORMALIZE_PHONE', '{"default_country": "US"}'::jsonb, 'ACTIVE'),
            (t_rec.tenant_id, 'Normalize Standard Dates', 'NORMALIZE_DATE', 'NORMALIZE_DATE', '{"output_format": "YYYY-MM-DD"}'::jsonb, 'ACTIVE')
        ON CONFLICT (tenant_id, rule_code) DO NOTHING;

        -- =====================================================================
        -- STANDARDIZATION RULES SEED
        -- =====================================================================
        INSERT INTO standardization_rules (tenant_id, rule_name, rule_code, standardization_type, mappings_json, status)
        VALUES
            (t_rec.tenant_id, 'Standardize Country Codes', 'COUNTRY_CODE_STD', 'COUNTRY', '{"US": "United States", "USA": "United States", "IN": "India", "IND": "India", "UK": "United Kingdom", "GB": "United Kingdom"}'::jsonb, 'ACTIVE'),
            (t_rec.tenant_id, 'Standardize Indian States', 'IN_STATE_STD', 'STATE', '{"DL": "Delhi", "MH": "Maharashtra", "KA": "Karnataka", "TN": "Tamil Nadu", "UP": "Uttar Pradesh", "HR": "Haryana"}'::jsonb, 'ACTIVE'),
            (t_rec.tenant_id, 'Standardize Product Status', 'PRODUCT_STATUS_STD', 'CODE', '{"A": "ACTIVE", "ACT": "ACTIVE", "I": "INACTIVE", "INACT": "INACTIVE", "D": "DRAFT", "DRF": "DRAFT"}'::jsonb, 'ACTIVE')
        ON CONFLICT (tenant_id, rule_code) DO NOTHING;
    END LOOP;
END $$;
