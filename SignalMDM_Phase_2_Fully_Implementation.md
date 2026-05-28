# SignalMDM Phase 2 — Mapping & Standardization

## Master Implementation Specification

Version: 2.0  
Project: SignalMDM  
Module: Phase 2 — Mapping & Standardization  
Architecture Alignment: Must align with existing Phase 1 implementation  
Database: PostgreSQL  
Backend Stack: FastAPI + SQLAlchemy + Pydantic  
Frontend Stack: React + Vite  

---

# IMPORTANT IMPLEMENTATION DIRECTIVE

This Phase 2 implementation MUST be built by extending and aligning with the EXISTING Phase 1 architecture.

DO NOT redesign the architecture.
DO NOT introduce a separate standalone application.
DO NOT duplicate authentication, RBAC, middleware, ingestion, or staging logic.

Phase 2 MUST:

- Reuse existing Phase 1 services and conventions.
- Integrate into the current FastAPI backend.
- Integrate into the current React frontend.
- Reuse existing RBAC, middleware, request lifecycle, logging, auditing, and database session handling.
- Extend the existing `staging_entities` workflow.
- Continue using the same PostgreSQL database.
- Maintain compatibility with existing ingestion pipelines.
- Preserve existing API response standards.
- Preserve existing audit/event tracking patterns.
- Preserve existing Swagger/OpenAPI conventions.

The implementation MUST be modular so that:

- Phase 1 modules remain isolated and stable.
- Phase 2 modules are independently maintainable.
- Debugging can be done separately for Phase 1 and Phase 2.
- Future phases can be added without refactoring previous phases.

---

# Existing Project Structure (Phase 1)

```txt
MDM_Backend/
├── api/
├── core/
├── db/
│   ├── models/
│   ├── sessions/
├── middleware/
├── schemas/
├── services/
│   ├── audit/
│   ├── auth/
│   ├── ingestion/
│   ├── rawlanding/
│   ├── source/
│   ├── staging/
├── storage/
├── utils/
├── workers/

MDM_Frontend/
├── src/
│   ├── components/
│   ├── context/
│   ├── layouts/
│   ├── pages/
│   ├── services/
│   ├── styles/
│   ├── utils/
```

---

# Required Modular Structure for Phase 2

## Backend Structure

```txt
MDM_Backend/
├── api/
│   └── routes/
│       └── mdm_phase2/
│           ├── canonical_models.py
│           ├── field_mappings.py
│           ├── transformation_rules.py
│           ├── standardization_rules.py
│           ├── normalization_runs.py
│           └── mapping_errors.py
│
├── db/
│   ├── models/
│   │   └── mdm_phase2/
│   │       ├── canonical_field.py
│   │       ├── field_mapping.py
│   │       ├── transformation_rule.py
│   │       ├── standardization_rule.py
│   │       ├── normalization_run.py
│   │       └── mapping_error.py
│   │
│   └── migrations/
│       └── phase2/
│
├── schemas/
│   └── mdm_phase2/
│       ├── canonical_model_schema.py
│       ├── field_mapping_schema.py
│       ├── transformation_rule_schema.py
│       ├── standardization_rule_schema.py
│       ├── normalization_run_schema.py
│       └── mapping_error_schema.py
│
├── services/
│   └── mdm_phase2/
│       ├── canonical/
│       ├── mapping/
│       ├── transformation/
│       ├── standardization/
│       ├── normalization/
│       └── retry/
│
├── workers/
│   └── mdm_phase2/
│       └── normalization_worker.py
│
└── utils/
    └── mdm_phase2/
        ├── transformers.py
        ├── standardizers.py
        ├── validators.py
        └── mapping_helpers.py
```

---

## Frontend Structure

```txt
MDM_Frontend/src/
├── components/
│   └── mdm_phase2/
│       ├── canonical/
│       ├── mappings/
│       ├── normalization/
│       ├── errors/
│       └── shared/
│
├── pages/
│   └── mdm_phase2/
│       ├── CanonicalModelsPage.jsx
│       ├── FieldMappingsPage.jsx
│       ├── TransformationRulesPage.jsx
│       ├── StandardizationRulesPage.jsx
│       ├── NormalizationRunsPage.jsx
│       ├── NormalizedRecordsPage.jsx
│       └── MappingErrorsPage.jsx
│
├── services/
│   └── mdm_phase2/
│       ├── canonicalService.js
│       ├── mappingService.js
│       ├── normalizationService.js
│       └── ruleService.js
│
└── utils/
    └── mdm_phase2/
```

---

# Phase 2 Objective

Phase 2 introduces:

- Canonical data modeling
- Field mapping
- Data transformation
- Data standardization
- Normalization processing
- Mapping error handling
- Retry processing
- Normalized canonical payload generation

The goal is to transform Phase 1 records:

```txt
READY_FOR_MAPPING
        ↓
Mapping + Transformation + Standardization
        ↓
READY_FOR_DQ
```

Phase 2 output becomes the input for Phase 3 Data Quality.

---

# Existing Phase 1 Dependency

Phase 2 MUST consume existing records from:

```txt
staging_entities
```

Records MUST already exist with:

```txt
staging_status = 'READY_FOR_MAPPING'
```

Phase 2 MUST NOT recreate ingestion.

Phase 2 ONLY handles:

- Mapping
- Transformation
- Standardization
- Normalization
- Canonical payload generation

---

# Required Database Objects

The PostgreSQL migration scripts MUST be generated separately.

DO NOT inline all SQL into application code.

The developer MUST:

1. Create dedicated migration scripts.
2. Create seed scripts separately.
3. Keep migrations versioned.
4. Ensure rollback compatibility.
5. Maintain compatibility with existing Phase 1 tables.

---

# Required New Tables

## 1. canonical_fields

Stores canonical field definitions.

### Purpose

Defines normalized enterprise fields for each entity type.

### Examples

- customer_name
- primary_email
- primary_phone
- country

---

## 2. field_mappings

Stores source-to-canonical mappings.

### Purpose

Maps incoming source fields into canonical fields.

### Example

```txt
customerName -> customer_name
emailId -> primary_email
mobileNo -> primary_phone
```

---

## 3. transformation_rules

Stores reusable transformation logic.

### Examples

- TRIM
- LOWERCASE
- REGEX_REPLACE
- REMOVE_SPECIAL_CHARS
- NORMALIZE_PHONE

---

## 4. standardization_rules

Stores standardization conversion logic.

### Examples

- COUNTRY_STANDARDIZATION
- STATE_STANDARDIZATION
- CUSTOMER_STATUS_STANDARDIZATION

---

## 5. normalization_runs

Tracks normalization execution.

### Purpose

Tracks batch execution status.

### Example Statuses

- CREATED
- RUNNING
- COMPLETED
- FAILED
- PARTIAL_SUCCESS

---

## 6. mapping_errors

Stores failed normalization records.

### Purpose

Tracks:

- failed mappings
- transformation errors
- retry attempts
- payload issues

---

# Required Updates to Existing Table

## staging_entities

The following columns MUST be added:

```sql
normalization_run_id UUID
mapped_payload_json JSONB
standardized_payload_json JSONB
normalization_status VARCHAR(50)
normalized_at TIMESTAMP
normalization_error TEXT
```

---

# Required Indexes

The migration script MUST include indexes for:

- canonical_fields
- field_mappings
- normalization_runs
- mapping_errors
- staging_entities phase2 statuses

Indexes MUST optimize:

- normalization queries
- source lookups
- retry operations
- status filtering
- tenant isolation

---

# Required Enums

## Entity Types

```txt
CUSTOMER
SUPPLIER
PRODUCT
ACCOUNT
ASSET
LOCATION
CONTACT
```

---

## Canonical Field Status

```txt
ACTIVE
INACTIVE
ARCHIVED
```

---

## Mapping Status

```txt
DRAFT
ACTIVE
INACTIVE
```

---

## Transformation Types

```txt
TRIM
UPPERCASE
LOWERCASE
TITLE_CASE
REMOVE_SPECIAL_CHARS
REGEX_REPLACE
NORMALIZE_PHONE
NORMALIZE_DATE
NORMALIZE_COUNTRY
```

---

## Standardization Types

```txt
NAME
EMAIL
PHONE
ADDRESS
COUNTRY
STATE
CITY
DATE
CODE
TEXT
```

---

## Normalization Run Status

```txt
CREATED
RUNNING
COMPLETED
FAILED
PARTIAL_SUCCESS
CANCELLED
```

---

## Staging Status

```txt
READY_FOR_MAPPING
MAPPING_IN_PROGRESS
NORMALIZED
NORMALIZATION_FAILED
READY_FOR_DQ
```

---

## Mapping Error Type

```txt
MISSING_MAPPING
INVALID_CANONICAL_FIELD
TRANSFORMATION_FAILED
STANDARDIZATION_FAILED
PAYLOAD_ERROR
DUPLICATE_MAPPING
```

---

## Mapping Error Status

```txt
OPEN
RETRIED
RESOLVED
IGNORED
```

---

# Required Seed Data

The developer MUST provide:

- Seed SQL separately
- Seed JSON separately
- Migration files separately

The main implementation MUST NOT hardcode seed logic.

---

# Initial Canonical Models

## CUSTOMER

Fields:

- customer_name
- customer_legal_name
- primary_email
- primary_phone
- website
- gst_number
- country
- state
- city
- postal_code
- industry
- status

---

## SUPPLIER

Fields:

- supplier_name
- supplier_legal_name
- primary_email
- primary_phone
- gst_number
- country
- state
- city
- supplier_category
- status

---

## PRODUCT

Fields:

- product_code
- product_name
- product_family
- product_category
- unit_of_measure
- status

---

# Example Seed JSON

```json
[
  {
    "entity_type": "CUSTOMER",
    "canonical_field_name": "customer_name",
    "data_type": "TEXT",
    "is_required": true,
    "validation_type": "TEXT",
    "standardization_type": "NAME"
  },
  {
    "entity_type": "CUSTOMER",
    "canonical_field_name": "primary_email",
    "data_type": "EMAIL",
    "is_required": false,
    "validation_type": "EMAIL",
    "standardization_type": "EMAIL"
  }
]
```

---

# Required API Standards

ALL APIs MUST follow existing Phase 1 standards.

DO NOT introduce new response structures.

---

# Standard Success Response

```json
{
  "status": "success",
  "message": "Operation completed successfully",
  "data": {},
  "meta": {
    "request_id": "REQ-...",
    "timestamp": "2026-05-25T10:00:00Z"
  }
}
```

---

# Standard Error Response

```json
{
  "status": "error",
  "message": "Validation failed",
  "errors": [
    {
      "field": "canonical_field_name",
      "message": "Field name must be snake_case"
    }
  ],
  "meta": {
    "request_id": "REQ-...",
    "timestamp": "2026-05-25T10:00:00Z"
  }
}
```

---

# Required APIs

## Canonical Models

```txt
GET    /api/mdm/canonical-models
POST   /api/mdm/canonical-models
PUT    /api/mdm/canonical-models/{id}
PATCH  /api/mdm/canonical-models/{id}/status
```

---

## Field Mappings

```txt
GET     /api/mdm/field-mappings
POST    /api/mdm/field-mappings
PUT     /api/mdm/field-mappings/{id}
DELETE  /api/mdm/field-mappings/{id}
```

---

## Transformation Rules

```txt
GET   /api/mdm/transformation-rules
POST  /api/mdm/transformation-rules
```

---

## Standardization Rules

```txt
GET   /api/mdm/standardization-rules
POST  /api/mdm/standardization-rules
```

---

## Normalization Runs

```txt
POST  /api/mdm/normalization-runs
GET   /api/mdm/normalization-runs
GET   /api/mdm/normalization-runs/{id}/status
```

---

## Normalized Records

```txt
GET /api/mdm/normalized-records
GET /api/mdm/normalized-records/{staging_entity_id}
```

---

## Mapping Errors

```txt
GET  /api/mdm/mapping-errors
POST /api/mdm/mapping-errors/{id}/retry
```

---

# Core Backend Service Logic

## create_canonical_field

Must:

- validate entity_type
- validate snake_case field names
- validate uniqueness
- validate enums
- insert canonical field
- write audit event

---

## create_field_mapping

Must:

- validate source system
- validate canonical field existence
- validate duplicate mappings
- validate transformation rules
- insert mapping
- write audit event

---

## run_normalization

Must:

- create normalization run
- fetch eligible staging_entities
- set status RUNNING
- enqueue normalization worker

---

## process_record

Must:

1. Read raw payload.
2. Apply field mappings.
3. Apply transformation chain.
4. Apply standardization.
5. Generate canonical payload.
6. Update staging record.
7. Update statuses.

---

## handle_mapping_error

Must:

- create mapping_errors row
- update normalization status
- update staging status
- persist error details

---

## retry_mapping_error

Must:

- validate correction exists
- reprocess staging record
- update retry status

---

# Normalization Engine Flow

```txt
READY_FOR_MAPPING
        ↓
MAPPING_IN_PROGRESS
        ↓
NORMALIZED
        ↓
READY_FOR_DQ
```

If processing fails:

```txt
NORMALIZATION_FAILED
```

---

# Validation Rules

## Canonical Models

Must validate:

- required field name
- snake_case only
- uniqueness per tenant/entity
- valid enum values
- valid standardization types

---

## Field Mappings

Must validate:

- source system exists
- canonical field exists
- no duplicate active mappings
- active transformation rules

---

## Transformation Rules

Must validate:

- unique rule_code
- valid transformation type
- regex validity
- JSON structure

---

## Standardization Rules

Must validate:

- unique rule_code
- valid JSON
- no duplicate key mappings

---

## Normalization Run

Must validate:

- ingestion run exists
- source system matches
- READY_FOR_MAPPING records exist
- active mappings exist

---

# Frontend Requirements

## Required Screens

### Canonical Models

Features:

- list fields
- filters
- pagination
- create/edit
- import/export
- inline edit

---

### Field Mappings

Features:

- source system filtering
- entity filtering
- mapping preview
- transformation selection
- before/after preview

---

### Transformation Rules

Features:

- reusable rule management
- JSON config editor
- validation preview

---

### Standardization Rules

Features:

- regex rules
- key-value standardization
- replacement management

---

### Normalization Runs

Features:

- trigger run
- monitor execution
- timeline
- status tracking
- failure summaries

---

### Normalized Records

Features:

- raw payload view
- mapped payload view
- standardized payload view
- canonical payload view
- before/after comparison

---

### Mapping Errors

Features:

- failed records
- retry actions
- payload snapshot
- correction workflows

---

# Required Frontend Components

## CanonicalModelTable

Must support:

- server-side pagination
- filtering
- sorting
- loading states
- import/export

---

## FieldMappingGrid

Must support:

- inline editing
- mapping previews
- transformation chips
- status badges

---

## MappingPreviewWidget

Must show:

- source value
- transformed value
- standardized value

---

## RuleConfigEditor

Must support:

- JSON validation
- reusable templates
- structured editing

---

## PayloadComparisonView

Must show:

- raw payload
- mapped payload
- standardized payload
- copy support
- expand/collapse JSON

---

# Required Frontend Routes

```txt
/signalmdm/mapping/canonical-models
/signalmdm/mapping/field-mappings
/signalmdm/mapping/transformation-rules
/signalmdm/mapping/standardization-rules
/signalmdm/mapping/normalization-runs
/signalmdm/mapping/normalized-records
/signalmdm/mapping/mapping-errors
```

---

# RBAC Requirements

## Admin

Can:

- manage canonical fields
- manage mappings
- manage rules
- trigger normalization
- retry failures
- access audit logs

---

## Data Engineer

Can:

- manage mappings
- manage rules
- trigger normalization
- retry failures
- view records

---

## Data Steward

Can:

- view records
- review mapping errors
- limited retry access

---

## Viewer

Can:

- read-only access

---

# Required Error Handling

## Duplicate Canonical Field

```txt
409 - Canonical field already exists
```

---

## Invalid Field Name

```txt
422 - Field name must be snake_case
```

---

## Invalid Enum

```txt
400 - Invalid enum value
```

---

## Duplicate Mapping

```txt
409 - Mapping already exists
```

---

## Unauthorized

```txt
401 - Authentication required
```

---

## Forbidden

```txt
403 - Insufficient permission
```

---

## Server Error

```txt
500 - Internal server error
```

---

# Testing Requirements

## Unit Tests

Must test:

- transformers
- standardizers
- validators
- normalization services

---

## API Tests

Must test:

- canonical APIs
- mapping APIs
- normalization APIs
- retry APIs

---

## Frontend Tests

Must test:

- forms
- grids
- JSON viewers
- monitoring screens
- retry UI

---

## Integration Tests

Must validate:

```txt
READY_FOR_MAPPING
        ↓
Normalization
        ↓
READY_FOR_DQ
```

---

## Security Tests

Must validate:

- RBAC
- tenant isolation
- unauthorized access prevention

---

## Regression Tests

Must confirm:

- Phase 1 ingestion still works
- Phase 1 staging still works
- Existing APIs remain stable
- Existing frontend pages remain stable

---

# Required Acceptance Criteria

## TC-01

Create CUSTOMER canonical field.

Expected:

Field appears successfully.

---

## TC-02

Create duplicate canonical field.

Expected:

409 conflict returned.

---

## TC-03

Create invalid canonical field.

Expected:

Validation failure.

---

## TC-04

Create source mapping.

Expected:

Mapping saved successfully.

---

## TC-05

Duplicate mapping.

Expected:

Duplicate error returned.

---

## TC-06

Transformation preview.

Expected:

Correct before/after output.

---

## TC-07

Run normalization.

Expected:

Successful processing.

---

## TC-08

Missing mapping.

Expected:

Mapping error captured.

---

## TC-09

Successful normalization.

Expected:

READY_FOR_DQ status.

---

## TC-10

Retry failed mapping.

Expected:

Record reprocessed.

---

# Required Development Sequence

1. Review existing Phase 1 implementation.
2. Confirm READY_FOR_MAPPING records exist.
3. Create Phase 2 modular folder structure.
4. Create PostgreSQL migration scripts.
5. Create seed scripts.
6. Add Phase 2 columns to staging_entities.
7. Create SQLAlchemy models.
8. Create Pydantic schemas.
9. Implement repositories.
10. Implement validators.
11. Implement canonical APIs.
12. Implement mapping APIs.
13. Implement rule APIs.
14. Implement normalization engine.
15. Implement retry engine.
16. Implement frontend skeleton pages.
17. Implement frontend screens.
18. Implement frontend comparison views.
19. Implement retry workflows.
20. Execute integration testing.
21. Freeze API contracts before Phase 3.

---

# Critical Engineering Requirements

## DO NOT Hardcode

DO NOT:

- hardcode mappings
- hardcode dropdowns
- hardcode enums in frontend only
- hardcode transformations

Everything MUST be metadata-driven.

---

# Architecture Requirements

## Separation of Responsibilities

Phase 1:

- ingestion
- raw landing
- staging

Phase 2:

- mapping
- transformation
- standardization
- normalization

Phase 3:

- data quality
- validation
- survivorship

DO NOT mix responsibilities.

---

# Audit Requirements

The system MUST create audit events for:

- create canonical field
- update canonical field
- create mapping
- update mapping
- deactivate mapping
- create rules
- retry failed record
- normalization execution

---

# Swagger/OpenAPI Requirements

All APIs MUST:

- appear in Swagger
- include request models
- include response models
- include RBAC documentation
- include error responses

---

# Definition of Done

Phase 2 is considered complete ONLY when:

- database migrations execute successfully
- seed scripts execute successfully
- canonical APIs function correctly
- mapping APIs function correctly
- normalization engine functions correctly
- READY_FOR_MAPPING records become READY_FOR_DQ
- mapping errors are captured
- retry APIs function correctly
- frontend screens are connected to real APIs
- RBAC is enforced
- audit logs are generated
- Swagger documentation is complete
- QA tests pass
- regression tests pass

---

# Known Risks

## Canonical Inconsistency

Mitigation:

Enforce centralized canonical model management.

---

## Hardcoded Mappings

Mitigation:

Keep mappings metadata-driven.

---

## Phase Boundary Violations

Mitigation:

Strictly separate Phase 2 from Phase 3 responsibilities.

---

## JSONB Overuse

Mitigation:

Use typed columns for core metadata.

---

## Missing Retry Mechanism

Mitigation:

Implement retry APIs from the start.

---

## Phase 1 Regression

Mitigation:

Run full regression before sign-off.

---

# Final Required Outcome

At the end of Phase 2:

- Source records from Phase 1 MUST become normalized canonical records.
- Mapping MUST be configurable.
- Transformation MUST be reusable.
- Standardization MUST be reusable.
- Errors MUST be auditable.
- Retry workflows MUST exist.
- Records MUST become READY_FOR_DQ.
- Phase 3 MUST be able to consume Phase 2 output without additional restructuring.

---

# Final Developer Instruction

The developer implementing this Phase 2 module MUST:

1. Study the existing Phase 1 architecture before implementation.
2. Follow existing coding patterns.
3. Reuse existing middleware, RBAC, auth, audit, and response systems.
4. Maintain compatibility with current FastAPI services.
5. Maintain compatibility with current React frontend structure.
6. Keep Phase 2 fully modular.
7. Provide migration SQL separately.
8. Provide seed SQL separately.
9. Avoid architectural rewrites.
10. Ensure Phase 1 continues functioning without regression.

This implementation MUST behave as a natural extension of the existing SignalMDM platform — not as an isolated subsystem.

