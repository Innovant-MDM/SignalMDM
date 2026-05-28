# SignalMDM: Enterprise Multi-Tenant Master Data Management Platform

[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)]()
[![Platform Version](https://img.shields.io/badge/Version-1.0.0--RC1-blue.svg)]()

A state-of-the-art, secure, multi-tenant Master Data Management (MDM) platform designed for large-scale enterprise data consolidation, quality assurance, mapping, and auditable data lineage tracking.

---

## 1. Project Overview

### 1.1 Business Purpose
In modern enterprises, data is fragmented across multiple transactional systems, CRM applications, and cloud data warehouses. This fragmentation leads to operational inefficiencies, duplicate records, reporting errors, and compliance risks.

**SignalMDM** acts as the single source of truth (Golden Record engine) for the enterprise. It ingests records from disparate external source systems, cleanses and normalizes the payload, runs survivorship and mapping rules, and exposes unified data entities. By providing robust logical tenant isolation, administrative audit logs, and granular access control, SignalMDM ensures enterprise data remains consistent, compliant, and highly available.

### 1.2 System Objectives
*   **Single Source of Truth:** Unify multiple representations of the same real-world entity into a single "Golden Record".
*   **Strict Multi-Tenancy:** Ensure structural, logical, and transactional isolation between corporate tenants under a single deployment.
*   **Security & Compliance First:** Protect sensitive data with client-side encrypted session tokens, device fingerprint verification, sliding-window rate limiting, and immutable database audit logs.
*   **Scalable Async Ingestion:** Leverage a robust Celery+Redis task distribution pipeline to load and process millions of records with automated retry capabilities and seamless fallback synchronization.
*   **Enterprise Observability:** Track every modification, data drift anomaly, API transaction, and quality exception through intuitive administration dashboard panels.

---

## 2. Technology Stack

SignalMDM is engineered using a premium, decoupled architecture separating the API control-plane, background execution threads, caching/throttling layers, and a modern SPA frontend.

### 2.1 Backend Core
*   **FastAPI (v0.136.1):** A high-performance web framework for building APIs, leveraging standard Python type hints.
*   **Uvicorn (v0.42.0):** An ultra-fast ASGI web server implementation for launching FastAPI in local and production environments.
*   **SQLAlchemy ORM (v2.0.40):** Unified Object Relational Mapper offering transaction control and dynamic query execution.
*   **Pydantic (v2.11.7) & Pydantic-Settings (v2.10.1):** Strict, runtime typing validation models and secure configuration management.
*   **Celery (v5.6.3):** Distributed asynchronous task execution framework.
*   **Redis (v6.2.0):** High-throughput, low-latency in-memory cache, Celery broker, and sliding rate limiter.

### 2.2 Security & Authentication
*   **PyJWT (python-jose v3.5.0):** JSON Web Token signing, validation, and claim decoding.
*   **Cryptography (v46.0.5):** AES-256-CBC encryption and decryption of token payloads.
*   **Bcrypt (v5.0.0):** Adaptive hashing for passwords and verification tokens.
*   **PyOTP (v2.9.0):** Time-based and counter-based One-Time Password generation for Multi-Factor Authentication.

### 2.3 Frontend Application
*   **React (v18.3.1):** A declarative UI component rendering library.
*   **TypeScript (v5.5.3):** Type safety across components, models, and custom React hook integrations.
*   **Vite (v5.4.1):** Ultra-fast compilation, bundling, and hot-module replacement tool.
*   **React Router (v6.22.3):** Dynamic declarative route engine with path matching and guard middleware.
*   **Crypto-JS (v4.2.0):** Client-side payload encryption conforming to AES standards.

### 2.4 Database & Data Layers
*   **PostgreSQL (v15+):** Advanced open-source object-relational database with strong JSONB support.
*   **Psycopg2-binary (v2.9.11):** High-performance PostgreSQL adapter for Python applications.

---

## 3. Major Implemented Features

*   **Logic Isolation Engine:** Soft multi-tenancy utilizing foreign key constraints scoped to `tenant_id` tables using a strict `ondelete="RESTRICT"` policy.
*   **Encrypted Token Pipeline:** Frontend-encrypted JWT tokens using AES-256-CBC. Decrypted at the backend middleware and validated against SHA-256 device/browser agent fingerprints.
*   **Brute-Force Lockout & OTP:** Redis-backed OTP generation delivering secure codes, supported by multi-failed attempt account locks.
*   **Multi-Stage Ingestion Pipeline:** Comprehensive state machine (CREATING → RUNNING → RAW_LOADED → STAGING_CREATED → COMPLETED) processing uploads asynchronously via Celery worker chains.
*   **Data Quality Pipeline:** High-performance, bulk sanitization layer checking empty values, size boundaries, wildcards, deduping via MD5 hashing, and performing deep regex SQLi/XSS scanning.
*   **SuperAdmin Overrides:** Allows members of the `"platform"` tenant to pass `X-Tenant-ID` headers to view and edit distinct tenant scopes dynamically.
*   **Immutable Append-Only Audit:** Persistent history log preserving JSONB old/new snapshots and correlating transactions via trace IDs.
*   **Sliding-Window Rate Limiter:** Throttles high-risk endpoints (`/auth/login`) backed by Redis.

---

## 4. Repository Structure

```
SignalMDM/
├── MDM_Backend/                  # FastAPI Backend API Server
│   ├── core/                     # Centralized settings & Redis connection pool
│   ├── scripts/                  # SQL migration & platform seeding scripts
│   ├── signalmdm/                # Core Application Package
│   │   ├── models/               # SQLAlchemy ORM schemas
│   │   ├── schemas/              # Pydantic v2 schemas
│   │   ├── services/             # Core business logic handlers
│   │   ├── routers/              # API route controllers
│   │   ├── middleware/           # Decryption, Auth guards, & Rate-limiting
│   │   └── workers/              # Celery background tasks
│   ├── storage/                  # Ingested file buffer storage
│   ├── utils/                    # Hash generators and path sanitizers
│   ├── main.py                   # FastAPI Application Entrypoint
│   └── signalmdm_security_tester.py # Dynamic pentest suite
│
├── MDM_DataLayer/                # Database Artifacts
│   └── SignalMDM.sql             # Full PostgreSQL schema binary dump
│
├── MDM_Frontend/                 # React SPA Client App
│   ├── src/                      # Source Code
│   │   ├── components/           # Reusable UI controls and tables
│   │   ├── context/              # Contexts (Auth, Tenant, Theme)
│   │   ├── layouts/              # Shells (Dashboard sidebars)
│   │   ├── pages/                # Views (Ingestion, Tenants, RBAC)
│   │   ├── services/             # API client services
│   │   └── utils/                # Crypto wrappers and helpers
│   ├── serverClient.js           # Production Express Server with Helmet CSP
│   └── vite.config.ts            # Vite asset bundler config
└── README.md                     # Home documentation page
```

---

## 5. Quick Start & Local Development

This section covers full local configuration of SignalMDM on a development machine.

### 5.1 Environment Prerequisites
Ensure the following tools are installed locally:
*   **Python:** v3.10+ (Recommended: v3.12)
*   **Node.js:** v18+ (Recommended: v20 LTS)
*   **PostgreSQL:** v15+ (Local port `5432` with username `postgres`)
*   **Redis:** v7+ (Or **Memurai** for Windows installations)

---

### 5.2 Step 1: Database Setup
1.  **Create the Database:**
    Connect to PostgreSQL using pgAdmin or psql and run:
    ```sql
    CREATE DATABASE "SignalMDM" WITH ENCODING = 'UTF8';
    ```
2.  **Initialize Schema and Seed Data:**
    You can initialize the database using either of the following two options:

    *   **Option A (Using the SQL Files):**
        Open a shell and execute the base schema dump followed by the administration and RBAC setup scripts:
        ```bash
        # Restore base tables
        psql -U postgres -d SignalMDM -f "d:\SignalMDM\MDM_DataLayer\SignalMDM.sql"
        # Seed platform administrators & roles
        psql -U postgres -d SignalMDM -f "d:\SignalMDM\MDM_Backend\scripts\platform_admin_setup.sql"
        psql -U postgres -d SignalMDM -f "d:\SignalMDM\MDM_Backend\scripts\platform_rbac_migration.sql"
        ```
    *   **Option B (Copy & Paste Unified Script):**
        Open the [DATABASE_REFERENCE.md](file:///d:/SignalMDM/DATABASE_REFERENCE.md) file and copy-paste the unified **PostgreSQL DDL Script** (Section 4) followed by the **Seed Data & Sample User Script** (Section 5) directly into your database query editor.

3.  **Seeded SuperAdmin Credentials:**
    *   **Seed Account Email:** `jofrey.joseph@flame.edu.in`
    *   **Seed Account Username:** `Jofrey`
    *   **Seed Account Password:** `Admin@123`
    *   **Assigned Seed Role:** `super_admin`

---

### 5.3 Step 2: Caching & Task Broker (Redis)
Start the Redis server on your local system:
*   **Windows (Memurai):**
    ```powershell
    net start Memurai
    ```
*   **Linux/macOS:**
    ```bash
    redis-server
    ```
Confirm Redis is listening:
```bash
redis-cli ping
# Expected response: PONG
```

---

### 5.4 Step 3: Backend Configuration (`MDM_Backend/`)
1.  **Initialize Virtual Environment:**
    ```bash
    cd d:\SignalMDM\MDM_Backend
    python -m venv venv
    ```
    *   *Activate (Windows PowerShell):* `.\venv\Scripts\Activate.ps1`
    *   *Activate (Linux/macOS):* `source venv/bin/activate`
2.  **Install Python Dependencies:**
    ```bash
    pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic pydantic-settings python-dotenv celery redis python-multipart "python-jose[cryptography]" cryptography bcrypt pyotp email-validator
    ```
3.  **Create local `.env` file:**
    Verify and configure `MDM_Backend/.env`:
    ```env
    DATABASE_URL=postgresql://postgres:2025@localhost:5432/SignalMDM
    REDIS_URL=redis://localhost:6379/0
    JWT_SECRET=supersecretkey
    JWT_ALGORITHM=HS256
    JWT_EXPIRE_MINUTES=1440
    TOKEN_ENCRYPTION_KEY=a3f1b2c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2
    APP_ENV=development
    UPLOAD_DIR=storage/uploads
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=your_email@gmail.com
    SMTP_PASSWORD=your_app_password
    SMTP_FROM=no-reply@signalmdm.com
    SMTP_USE_TLS=True
    ```
4.  **Create Upload Buffer:**
    ```bash
    mkdir -p storage/uploads
    ```
5.  **Verify Routing Integrity:**
    ```bash
    python -c "import main; print('OK:', len(main.app.routes), 'routes compiled')"
    # Expected: OK: 17 routes compiled
    ```

---

### 5.5 Step 4: Run Backend Applications
Start two separate command-line shells to run the API and task queue workers:

*   **Terminal A: FastAPI Web Server**
    ```bash
    cd d:\SignalMDM\MDM_Backend
    # Ensure venv is active
    python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```
    API Docs are visible at: `http://localhost:8000/docs`

*   **Terminal B: Celery Worker Task Processor**
    ```bash
    cd d:\SignalMDM\MDM_Backend
    # Ensure venv is active
    # Solo pool is mandatory for Windows environments
    python -m celery -A signalmdm.workers.celery_app worker --loglevel=info --pool=solo
    ```

---

### 5.6 Step 5: Frontend Configuration (`MDM_Frontend/`)
1.  **Install Node Modules:**
    ```bash
    cd d:\SignalMDM\MDM_Frontend
    npm install
    ```
2.  **Verify Frontend Settings (`.env.local`):**
    Create `MDM_Frontend/.env.local`:
    ```env
    VITE_API_BASE_URL=http://localhost:8000/api/v1
    VITE_TOKEN_ENCRYPTION_KEY=a3f1b2c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2
    ```
3.  **Run Development Mode (Hot-Reloading):**
    ```bash
    npm run dev
    ```
    Frontend is available at `http://localhost:5173`.

4.  **Compile & Run Production Mode (Strict CSP Testing):**
    To validate headers and Helmet CSP compliance, compile and run the production build using the Express server wrapper:
    ```bash
    npm run build
    npm run serve
    ```
    This serves compiled static assets with strict Content-Security-Policies on `http://localhost:3030`.

---

## 6. Testing

Dynamic security verification and API scanning can be validated using the built-in pentester tool:
1.  Ensure the FastAPI server is running on `http://localhost:8000`.
2.  Open a shell inside `MDM_Backend/` and execute:
    ```bash
    python signalmdm_security_tester.py
    ```
This triggers **115 active test scenarios** checking JWT parameters, brute force lockouts, SQL injection, XSS reflection, and traversal attacks.

---

## 7. Links to System Documentation

For detailed guides, please refer to the specialized documentation files:
*   [ARCHITECTURE.md](ARCHITECTURE.md): System architecture, Logical layouts, Request lifecycles, and complete Mermaid flows.
*   [DIRECTORY_REFERENCE.md](DIRECTORY_REFERENCE.md): File-by-file explanations of classes, methods, and functions.
*   [API_REFERENCE.md](API_REFERENCE.md): Endpoint list, authorization parameters, validation checks, and payloads.
*   [DATABASE_REFERENCE.md](DATABASE_REFERENCE.md): PostgreSQL schema catalogs, multi-tenant restrictions, and audit structures.
*   [DEPLOYMENT.md](DEPLOYMENT.md): Kubernetes deployment matrices, Dockerfiles, and incident runbooks.
*   [TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md): Deep-dive reference guides for third-party libraries.
*   [frontEnd_instructions_phase2.md](frontEnd_instructions_phase2.md): Frontend team developer guide detailing service paths, layout registrations, and UI screen integration instructions.

---

## 8. Known Limitations & Roadmap

### 8.1 Current Limitations
*   **Permissive CSP in Dev:** The Vite HMR model requires `'unsafe-inline'` and `'unsafe-eval'` policies inside Helmet, which are disabled only during standard client-build compilations.
*   **No Centralized Storage abstraction:** File chunks are stored directly in the local file system. Production setups require a custom S3/Cloud Storage object driver.
*   **Mock Dashboard Telemetry:** The main analytical charts on the layout interface populate simulated telemetry counts, with real data hook integration scheduled for Phase 3.

### 8.2 Roadmap
1.  **Phase 3 Entity Resolution:** Integration of probabilistic matching models, Jaro-Winkler/Levenshtein algorithms, and graph matching schemas.
2.  **Machine Learning Scoring Engine:** Integrate advanced scoring modules (`scoring.py`, `features.py`) to run anomaly detection models on raw inputs.
3.  **Real-Time Distributed Ingestion:** Deploy Apache Kafka event ingestion queues to stream live signal changes.

---

## 9. Phase 2: Mapping & Standardization

Phase 2 introduces the core multi-tenant mapping, transformation, standardization, and asynchronous normalization run architecture.

### 9.1 Database Preparation
Four SQL migration and seed scripts are provided at the root of the workspace to initialize Phase 2. Run them in the following order:
1.  **Schema Migration**: Adds Canonical Fields, Rules, Field Mappings, Normalization Runs, Mapping Errors, and updates `staging_entities`.
    ```bash
    psql -U postgres -d SignalMDM -f "d:\SignalMDM\db_phase2_migration.sql"
    ```
2.  **Canonical Models Seed**: Seeds standard multi-tenant target fields.
    ```bash
    psql -U postgres -d SignalMDM -f "d:\SignalMDM\db_phase2_seed.sql"
    ```
3.  **Rules Catalog Seed**: Seeds standard data cleanup, transformation, and translation rules.
    ```bash
    psql -U postgres -d SignalMDM -f "d:\SignalMDM\db_phase2_seed_rules.sql"
    ```
4.  **RBAC Permissions Seed**: Seeds 13 screen-level permissions and connects them to default platform roles. (Note: These are also auto-seeded on backend startup).
    ```bash
    psql -U postgres -d SignalMDM -f "d:\SignalMDM\db_phase2_rbac_seed.sql"
    ```

### 9.2 File Structure Guide

#### Backend (MDM_Backend)
*   **Database Models**: `db/models/mdm_phase2/`
    *   [canonical_field.py](file:///d:/SignalMDM/MDM_Backend/db/models/mdm_phase2/canonical_field.py) — Defines `CanonicalField`
    *   [transformation_rule.py](file:///d:/SignalMDM/MDM_Backend/db/models/mdm_phase2/transformation_rule.py) — Defines `TransformationRule`
    *   [standardization_rule.py](file:///d:/SignalMDM/MDM_Backend/db/models/mdm_phase2/standardization_rule.py) — Defines `StandardizationRule`
    *   [field_mapping.py](file:///d:/SignalMDM/MDM_Backend/db/models/mdm_phase2/field_mapping.py) — Defines `FieldMapping`
    *   [normalization_run.py](file:///d:/SignalMDM/MDM_Backend/db/models/mdm_phase2/normalization_run.py) — Defines `NormalizationRun`
    *   [mapping_error.py](file:///d:/SignalMDM/MDM_Backend/db/models/mdm_phase2/mapping_error.py) — Defines `MappingError`
*   **Validation Schemas**: `schemas/mdm_phase2/` (Pydantic models)
*   **Business Logic Layer**: `services/mdm_phase2/`
    *   `canonical_service.py`, `rule_service.py`, `mapping_service.py`, `normalization_service.py`, `retry_service.py`
*   **API Routers**: `api/routes/mdm_phase2/` (registered in `main.py`)
*   **Processing Utilities**: `utils/mdm_phase2/`
    *   `transformers.py` (Trim, Upper, Regex, Date Formats)
    *   `standardizers.py` (Domain translates)
    *   `validators.py` (Pydantic / Type validations)
*   **Celery Background Task**: `workers/mdm_phase2/normalization_worker.py` (runs asynchronous validation rules)

#### Frontend (MDM_Frontend)
*   **API Client Services**: `src/services/mdm_phase2/`
    *   [canonicalService.ts](file:///d:/SignalMDM/MDM_Frontend/src/services/mdm_phase2/canonicalService.ts) (Canonical Fields)
    *   [mappingService.ts](file:///d:/SignalMDM/MDM_Frontend/src/services/mdm_phase2/mappingService.ts) (Mappings)
    *   [ruleService.ts](file:///d:/SignalMDM/MDM_Frontend/src/services/mdm_phase2/ruleService.ts) (Rules)
    *   [normalizationService.ts](file:///d:/SignalMDM/MDM_Frontend/src/services/mdm_phase2/normalizationService.ts) (Runs, Errors, Retries)
*   **Skeleton Pages**: `src/pages/mdm_phase2/` (includes comments pointing to service API files)
    *   `CanonicalModelsPage.tsx`, `FieldMappingsPage.tsx`, `TransformationRulesPage.tsx`, `StandardizationRulesPage.tsx`, `NormalizationRunsPage.tsx`, `NormalizedRecordsPage.tsx`, `MappingErrorsPage.tsx`
*   **External CSS Files**: `src/styles/mdm_phase2/`
    *   `CanonicalModelsPage.css`, `FieldMappingsPage.css`, `TransformationRulesPage.css`, `StandardizationRulesPage.css`, `NormalizationRunsPage.css`, `NormalizedRecordsPage.css`, `MappingErrorsPage.css`