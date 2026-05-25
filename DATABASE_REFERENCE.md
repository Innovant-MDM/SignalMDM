# SignalMDM: Database Schema & Referentials Manual

This document provides a highly detailed reference of the PostgreSQL database schemas, indexes, structural tenant-isolation strategies, and transactional audit layouts in SignalMDM.

---

## 1. Multi-Tenant Isolation Strategy

Logical isolation is enforced directly within the PostgreSQL storage tier.
1.  **Strict Scoping Column:** Every core table includes a mandatory column:
    ```sql
    tenant_id UUID NOT NULL
    ```
2.  **No Direct Deletes:** Foreign key definitions contain `ondelete="RESTRICT"`. This prevents organizational administrative data (e.g. Ingestion runs or Raw records) from being wiped out or orphaned:
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

Here we outline the structural details of key system tables.

### 2.1 Table: `tenant`
*   **Purpose:** The parent organization identity record. All system schemas reference this root.
*   **Columns:**
    *   `tenant_id` (`UUID`, Primary Key): Unique system identifier.
    *   `name` (`VARCHAR(255)`, Not Null): Legal company or entity name.
    *   `config_json` (`JSONB`, Nullable): Configuration variables (domain configurations, custom adaptors, mapping parameters).
*   **Indexes:**
    *   `pk_tenant` (B-Tree on `tenant_id`).
*   **Business Meaning:** Establishes organizational boundaries for data residency and billing configurations.

---

### 2.2 Table: `platform_admin`
*   **Purpose:** Stores identity records and authentication states for global administrators.
*   **Columns:**
    *   `admin_id` (`UUID`, Primary Key): Primary administrator key.
    *   `email` (`VARCHAR(255)`, Unique, Not Null): Login email address.
    *   `password_hash` (`VARCHAR(255)`, Not Null): password string, salted and hashed using bcrypt.
    *   `full_name` (`VARCHAR(255)`, Not Null): Name of the administrator.
    *   `status` (`VARCHAR(50)`, Default: `'active'`): Current state of the account (`active`, `locked`, `suspended`).
    *   `failed_login_attempts` (`INTEGER`, Default: `0`): Tracks sequential login failures.
    *   `locked_until` (`TIMESTAMP`, Nullable): Timestamp indicating when an account lockout expires.
*   **Indexes:**
    *   `uq_admin_email` (Unique B-Tree on `email`).
*   **Query Patterns:**
    *   ```sql
        SELECT * FROM platform_admin WHERE email = :email;
        ```
*   **Performance Considerations:** The email column is heavily indexed to guarantee sub-millisecond lookups on the initial login pipeline step.

---

### 2.3 Table: `raw_record`
*   **Purpose:** The immutable landing zone for ingested records. Files parsed by the data quality loader write directly here.
*   **Columns:**
    *   `raw_record_id` (`UUID`, Primary Key): Primary record key.
    *   `tenant_id` (`UUID`, Foreign Key, Not Null): Owning tenant ID.
    *   `run_id` (`UUID`, Foreign Key, Not Null): The ingestion run that generated this record.
    *   `raw_data` (`JSONB`, Not Null): The raw CSV or JSON data dictionary.
    *   `checksum_md5` (`VARCHAR(32)`, Not Null): MD5 hash of the row payload, preventing duplicate storage.
    *   `created_at` (`TIMESTAMP`, Default: `NOW()`): Creation timestamp.
*   **Indexes:**
    *   `idx_raw_checksum` (B-Tree on `tenant_id`, `checksum_md5`).
    *   `idx_raw_run` (B-Tree on `run_id`).
*   **Query Patterns:**
    *   ```sql
        SELECT * FROM raw_record WHERE tenant_id = :t_id AND checksum_md5 = :md5;
        ```
*   **Performance Considerations:** Features a composite index on `(tenant_id, checksum_md5)` to check for duplicates before bulk inserting batches of 50,000 records.

---

### 2.4 Table: `staging_entity`
*   **Purpose:** The staging zone where raw records are correlated, verified, and prepared for survivorship evaluation.
*   **Columns:**
    *   `staging_id` (`UUID`, Primary Key): Unique record identifier.
    *   `tenant_id` (`UUID`, Foreign Key, Not Null): Owning tenant ID.
    *   `raw_record_id` (`UUID`, Foreign Key, Unique, Not Null): References the raw record that generated this staging entity.
    *   `external_id` (`VARCHAR(255)`, Not Null): Target source identification key.
    *   `state` (`VARCHAR(50)`, Default: `'READY_FOR_MAPPING'`): Current validation status (`READY_FOR_MAPPING`, `VALIDATION_FAILED`, `MAPPED`).
    *   `validated_at` (`TIMESTAMP`, Nullable): Timestamp of the last validation run.
*   **Indexes:**
    *   `uq_staging_raw_record` (Unique index on `raw_record_id`).
    *   `idx_staging_external` (B-Tree on `tenant_id`, `external_id`).
*   **Business Meaning:** Represents cleaned transactional data mapped from external models into a unified schema, awaiting matching algorithms.

---

### 2.5 Table: `audit_log`
*   **Purpose:** Immutable append-only audit trail capturing all system mutations.
*   **Columns:**
    *   `audit_id` (`UUID`, Primary Key): Primary record key.
    *   `tenant_id` (`UUID`, Foreign Key, Not Null): References the target tenant.
    *   `action` (`VARCHAR(255)`, Not Null): Action performed (e.g. `'CREATE'`, `'UPDATE'`).
    *   `table_name` (`VARCHAR(100)`, Not Null): Table impacted by the change.
    *   `record_id` (`UUID`, Not Null): Primary key of the modified record.
    *   `old_value` (`JSONB`, Nullable): Snapshot of the data dictionary prior to modification.
    *   `new_value` (`JSONB`, Nullable): Snapshot of the data dictionary post-modification.
    *   `performed_by` (`VARCHAR(255)`, Not Null): Username or service identifier that initiated the change.
    *   `performed_at` (`TIMESTAMP`, Default: `NOW()`): Timestamp of the operation.
    *   `trace_id` (`UUID`, Not Null): Trace identifier linking HTTP requests to database changes.
*   **Indexes:**
    *   `idx_audit_trace` (B-Tree on `trace_id`).
    *   `idx_audit_performed` (B-Tree on `performed_at`).
*   **Business Meaning:** Ensures compliance with security regulations (such as SOC2 or HIPAA) by maintaining a complete, immutable history of master data changes.

---

### 2.6 Table: `domains`
*   **Purpose:** Stores registered data domains representing logical data classification categories (e.g. Customer, Finance, HR) per tenant.
*   **Columns:**
    *   `id` (`UUID`, Primary Key): Surrogate primary key.
    *   `tenant_id` (`UUID`, Foreign Key, Not Null): Owning tenant ID.
    *   `domain_name` (`VARCHAR(100)`, Not Null): Human-readable domain name (e.g. 'Customer').
    *   `description` (`TEXT`, Nullable): Optional description of the domain.
    *   `status` (`VARCHAR(50)`, Default: `'ACTIVE'`): Domain status (`ACTIVE`, `SUSPENDED`, `ARCHIVED`, `DEACTIVATED`).
    *   `created_at` (`TIMESTAMP`, Default: `NOW()`): Creation timestamp.
    *   `updated_at` (`TIMESTAMP`, Default: `NOW()`): Last update timestamp.
*   **Indexes:**
    *   `idx_domains_tenant` (B-Tree on `tenant_id`).
*   **Business Meaning:** Establishes the canonical registry of valid data domains for data cataloging and validation rules within a tenant.

---

## 3. Index Strategy Summary

*   **Foreign Key Indexing:** Every foreign key in the schema is backed by a B-Tree index to speed up join operations and avoid full table scans during cascades.
*   **Composite Indexing:** Multi-tenant scoping queries are optimized using composite indexes prefixed with the `tenant_id` column (e.g. `idx_raw_checksum` on `(tenant_id, checksum_md5)`).
*   **JSONB Indexing:** The `raw_data` and metadata `config_json` columns use generalized inverted index (GIN) models to support nested attribute filtering:
    ```sql
    CREATE INDEX idx_raw_data_gin ON raw_record USING gin (raw_data);
    ```
