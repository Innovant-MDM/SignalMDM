-- SignalMDM Phase 2 — Mapping & Standardization Canonical Field Seed Script
-- Run this AFTER executing db_phase2_migration.sql to seed all initial canonical models for existing tenants

DO $$
DECLARE
    t_rec RECORD;
BEGIN
    FOR t_rec IN SELECT tenant_id FROM tenant LOOP
        -- =====================================================================
        -- CUSTOMER CANONICAL FIELDS
        -- =====================================================================
        INSERT INTO canonical_fields (tenant_id, entity_type, canonical_field_name, data_type, is_required, validation_type, standardization_type, status)
        VALUES
            (t_rec.tenant_id, 'CUSTOMER', 'customer_name', 'TEXT', TRUE, 'TEXT', 'NAME', 'ACTIVE'),
            (t_rec.tenant_id, 'CUSTOMER', 'customer_legal_name', 'TEXT', FALSE, 'TEXT', 'NAME', 'ACTIVE'),
            (t_rec.tenant_id, 'CUSTOMER', 'primary_email', 'EMAIL', FALSE, 'EMAIL', 'EMAIL', 'ACTIVE'),
            (t_rec.tenant_id, 'CUSTOMER', 'primary_phone', 'PHONE', FALSE, 'PHONE', 'PHONE', 'ACTIVE'),
            (t_rec.tenant_id, 'CUSTOMER', 'website', 'TEXT', FALSE, 'URL', 'TEXT', 'ACTIVE'),
            (t_rec.tenant_id, 'CUSTOMER', 'gst_number', 'CODE', FALSE, 'GSTIN', 'CODE', 'ACTIVE'),
            (t_rec.tenant_id, 'CUSTOMER', 'country', 'TEXT', FALSE, 'COUNTRY', 'COUNTRY', 'ACTIVE'),
            (t_rec.tenant_id, 'CUSTOMER', 'state', 'TEXT', FALSE, 'STATE', 'STATE', 'ACTIVE'),
            (t_rec.tenant_id, 'CUSTOMER', 'city', 'TEXT', FALSE, 'CITY', 'CITY', 'ACTIVE'),
            (t_rec.tenant_id, 'CUSTOMER', 'postal_code', 'TEXT', FALSE, 'POSTAL_CODE', 'CODE', 'ACTIVE'),
            (t_rec.tenant_id, 'CUSTOMER', 'industry', 'TEXT', FALSE, 'TEXT', 'TEXT', 'ACTIVE'),
            (t_rec.tenant_id, 'CUSTOMER', 'status', 'TEXT', FALSE, 'TEXT', 'TEXT', 'ACTIVE')
        ON CONFLICT (tenant_id, entity_type, canonical_field_name) DO NOTHING;

        -- =====================================================================
        -- SUPPLIER CANONICAL FIELDS
        -- =====================================================================
        INSERT INTO canonical_fields (tenant_id, entity_type, canonical_field_name, data_type, is_required, validation_type, standardization_type, status)
        VALUES
            (t_rec.tenant_id, 'SUPPLIER', 'supplier_name', 'TEXT', TRUE, 'TEXT', 'NAME', 'ACTIVE'),
            (t_rec.tenant_id, 'SUPPLIER', 'supplier_legal_name', 'TEXT', FALSE, 'TEXT', 'NAME', 'ACTIVE'),
            (t_rec.tenant_id, 'SUPPLIER', 'primary_email', 'EMAIL', FALSE, 'EMAIL', 'EMAIL', 'ACTIVE'),
            (t_rec.tenant_id, 'SUPPLIER', 'primary_phone', 'PHONE', FALSE, 'PHONE', 'PHONE', 'ACTIVE'),
            (t_rec.tenant_id, 'SUPPLIER', 'gst_number', 'CODE', FALSE, 'GSTIN', 'CODE', 'ACTIVE'),
            (t_rec.tenant_id, 'SUPPLIER', 'country', 'TEXT', FALSE, 'COUNTRY', 'COUNTRY', 'ACTIVE'),
            (t_rec.tenant_id, 'SUPPLIER', 'state', 'TEXT', FALSE, 'STATE', 'STATE', 'ACTIVE'),
            (t_rec.tenant_id, 'SUPPLIER', 'city', 'TEXT', FALSE, 'CITY', 'CITY', 'ACTIVE'),
            (t_rec.tenant_id, 'SUPPLIER', 'supplier_category', 'TEXT', FALSE, 'TEXT', 'TEXT', 'ACTIVE'),
            (t_rec.tenant_id, 'SUPPLIER', 'status', 'TEXT', FALSE, 'TEXT', 'TEXT', 'ACTIVE')
        ON CONFLICT (tenant_id, entity_type, canonical_field_name) DO NOTHING;

        -- =====================================================================
        -- PRODUCT CANONICAL FIELDS
        -- =====================================================================
        INSERT INTO canonical_fields (tenant_id, entity_type, canonical_field_name, data_type, is_required, validation_type, standardization_type, status)
        VALUES
            (t_rec.tenant_id, 'PRODUCT', 'product_code', 'CODE', TRUE, 'SKU', 'CODE', 'ACTIVE'),
            (t_rec.tenant_id, 'PRODUCT', 'product_name', 'TEXT', TRUE, 'TEXT', 'NAME', 'ACTIVE'),
            (t_rec.tenant_id, 'PRODUCT', 'product_family', 'TEXT', FALSE, 'TEXT', 'TEXT', 'ACTIVE'),
            (t_rec.tenant_id, 'PRODUCT', 'product_category', 'TEXT', FALSE, 'TEXT', 'TEXT', 'ACTIVE'),
            (t_rec.tenant_id, 'PRODUCT', 'unit_of_measure', 'CODE', FALSE, 'TEXT', 'CODE', 'ACTIVE'),
            (t_rec.tenant_id, 'PRODUCT', 'status', 'TEXT', FALSE, 'TEXT', 'TEXT', 'ACTIVE')
        ON CONFLICT (tenant_id, entity_type, canonical_field_name) DO NOTHING;
    END LOOP;
END $$;
