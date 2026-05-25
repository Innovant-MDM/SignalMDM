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
2.  **Restore the Schema:**
    The base schema dump is in `MDM_DataLayer/SignalMDM.sql`. Open a shell and run:
    ```bash
    psql -U postgres -d SignalMDM -f "d:\SignalMDM\MDM_DataLayer\SignalMDM.sql"
    ```
3.  **Seed Platform Administrators & RBAC Matrix:**
    You must execute the setup and RBAC scripts to enable administrative authentication:
    ```bash
    psql -U postgres -d SignalMDM -f "d:\SignalMDM\MDM_Backend\scripts\platform_admin_setup.sql"
    psql -U postgres -d SignalMDM -f "d:\SignalMDM\MDM_Backend\scripts\platform_rbac_migration.sql"
    ```
    *   **Seed Account Email:** `admin@signalmdm.com`
    *   **Seed Account Password:** `Admin@Signal123`
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

---

## 8. Known Limitations & Roadmap

### 8.1 Current Limitations
*   **Permissive CSP in Dev:** The Vite HMR model requires `'unsafe-inline'` and `'unsafe-eval'` policies inside Helmet, which are disabled only during standard client-build compilations.
*   **No Centralized Storage abstraction:** File chunks are stored directly in the local file system. Production setups require a custom S3/Cloud Storage object driver.
*   **Mock Dashboard Telemetry:** The main analytical charts on the layout interface populate simulated telemetry counts, with real data hook integration scheduled for Phase 2.

### 8.2 Roadmap
1.  **Phase 2 Entity Resolution:** Integration of probabilistic matching models, Jaro-Winkler/Levenshtein algorithms, and graph matching schemas.
2.  **Machine Learning Scoring Engine:** Integrate advanced scoring modules (`scoring.py`, `features.py`) to run anomaly detection models on raw inputs.
3.  **Real-Time Distributed Ingestion:** Deploy Apache Kafka event ingestion queues to stream live signal changes.