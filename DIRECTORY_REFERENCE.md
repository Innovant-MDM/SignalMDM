# SignalMDM: Directory Reference & Module Catalog

This document provides a highly detailed structural reference mapping every directory and critical file in the SignalMDM enterprise repository.

---

## 1. Directory Structure Map

```
SignalMDM/
├── MDM_Backend/                  # Core FastAPI control-plane & async execution engine
│   ├── core/                     # Configuration schemas and cache connection setups
│   ├── scripts/                  # SQL seed and initial database migrations
│   ├── signalmdm/                # Python backend package
│   │   ├── middleware/           # Encryption filters, auth guards, rate limit checkers
│   │   ├── models/               # SQLAlchemy transactional definitions
│   │   ├── routers/              # FastAPI route controllers
│   │   ├── schemas/              # Pydantic v2 data transfer objects (DTO)
│   │   ├── services/             # Central transactional business handlers
│   │   └── workers/              # Celery worker process entries
│   ├── storage/                  # Local buffer for file ingestion operations
│   └── utils/                    # Data verification, paths, and sanitize libraries
│
├── MDM_DataLayer/                # DB restoration files and structure artifacts
│
└── MDM_Frontend/                 # React SPA user interface
    └── src/                      # Source workspace
        ├── components/           # Tables, layouts, indicators, dynamic boxes
        ├── context/              # React central context hooks (Auth, SnackBar, Tenant)
        ├── layouts/              # Dashboard structural shells
        ├── pages/                # Main React view panels
        ├── services/             # Axios API integration drivers
        └── utils/                # CryptoJS helpers and fingerprint engines
```

---

## 2. Directory Reference Details

### 2.1 Backend Directories

#### `MDM_Backend/core/`
*   **Purpose:** Application core setups, variables parsing, database credentials pooling.
*   **Responsibilities:** Loads Pydantic models from `.env`, creates and maintains single-instance Redis pools.
*   **Contained Modules:** `config.py`, `redis_client.py`.
*   **Dependencies:** `pydantic-settings`, `redis`.
*   **Used By:** Routers, Services, Middlewares.
*   **Examples:** Initializing Redis connection pools on application startup (`main.py`).

#### `MDM_Backend/signalmdm/middleware/`
*   **Purpose:** Intercepts incoming requests for authentication and sanitization.
*   **Responsibilities:** Rate limiting, JWT decryption, user fingerprinting, injection scanning.
*   **Contained Modules:** `auth.py`, `token_utils.py`, `rate_limit.py`.
*   **Dependencies:** `cryptography`, `jose`, `redis`, `fastapi`.
*   **Used By:** `main.py` routing lifecycle.

#### `MDM_Backend/signalmdm/models/`
*   **Purpose:** PostgreSQL database representation tables.
*   **Responsibilities:** Represents core data layers, joins, and integrity constraints.
*   **Contained Modules:** `tenant.py`, `platform_admin.py`, `platform_role.py`, `rbac.py`, `source_system.py`, `file_upload.py`, `upload_session.py`, `ingestion_run.py`, `raw_record.py`, `staging_entity.py`, `entity.py`, `audit.py`, `scoring.py`.
*   **Dependencies:** `sqlalchemy`.
*   **Used By:** Services, Routers.

#### `MDM_Backend/signalmdm/services/`
*   **Purpose:** Encapsulates the core transactional and logic rules of the system.
*   **Responsibilities:** Drives token workflows, processes source operations, maps raw databases.
*   **Contained Modules:** `auth_service.py`, `source_service.py`, `ingestion_service.py`, `raw_service.py`, `staging_service.py`, `audit_service.py`, `tenant_service.py`.
*   **Dependencies:** `sqlalchemy`, `bcrypt`, `pyotp`.
*   **Used By:** Routers, Workers.

#### `MDM_Backend/signalmdm/routers/`
*   **Purpose:** API Controllers exposing HTTP endpoints.
*   **Responsibilities:** Maps endpoints, resolves path parameters, delegates workflows to services.
*   **Contained Modules:** `auth_router.py`, `source_router.py`, `ingestion_router.py`, `raw_router.py`, `staging_router.py`, `upload_router.py`, `tenant_router.py`, `platform_rbac_router.py`.
*   **Dependencies:** `fastapi`, `sqlalchemy`.
*   **Used By:** Mounted in `main.py`.

---

### 2.2 Frontend Directories

#### `MDM_Frontend/src/context/`
*   **Purpose:** Global reactive state management contexts.
*   **Responsibilities:** Maintains logins, updates active tenants, triggers snackbar alerts.
*   **Contained Modules:** `AuthContext.tsx`, `PermissionsContext.tsx`, `TenantConfigContext.tsx`, `SnackbarContext.tsx`.
*   **Dependencies:** `react`, `js-cookie`.
*   **Used By:** Standard React Components.

#### `MDM_Frontend/src/pages/`
*   **Purpose:** Contains UI view components.
*   **Responsibilities:** Renders forms, mounts tables, handles UI bindings.
*   **Contained Modules:** `Login.tsx`, `SourceSystems.tsx`, `IngestionRuns.tsx`, `UploadData.tsx`, `RawLanding.tsx`, `StagingRecords.tsx`, `PlatformRBAC.tsx`.
*   **Dependencies:** `react`, `lucide-react`, `crypto-js`.
*   **Used By:** Mounted in `App.tsx` routes.

---

## 3. Module Catalog: File-by-File Breakdown

### 3.1 Backend Module Details

#### `MDM_Backend/main.py`
*   **Purpose:** Main application launcher and middleware coordinator.
*   **Major Classes:** None.
*   **Major Functions:** `startup_event()`, `shutdown_event()`, `custom_validation_exception_handler()`.
*   **Dependencies:** `fastapi`, `uvicorn`, `redis_client`, `auth_middleware`.
*   **Used By:** System execution runtime.
*   **Business Role:** Binds the FastAPI routing layer, coordinates startup health checks, and mounts middlewares.

#### `MDM_Backend/signalmdm/middleware/auth.py`
*   **Purpose:** Enforces token verification and security guards.
*   **Major Classes:** `SecurityHeadersMiddleware`, `ResponseEnvelopeMiddleware`.
*   **Major Functions:** `require_auth()`, `require_admin()`, `is_super_admin()`.
*   **Dependencies:** `fastapi`, `token_utils`, `redis_client`, `sqlalchemy`.
*   **Used By:** Routers, Controllers.
*   **Business Role:** Validates encrypted JWT cookie assertions, checks device IDs, and maps role permissions.

#### `MDM_Backend/signalmdm/middleware/token_utils.py`
*   **Purpose:** Provides token cryptographic signature and envelope operations.
*   **Major Classes:** None.
*   **Major Functions:** `aes_encrypt()`, `aes_decrypt()`, `create_access_token()`, `decode_token()`.
*   **Dependencies:** `cryptography`, `jose`, `core.config`.
*   **Used By:** `auth.py`, `auth_service.py`.
*   **Business Role:** Restricts token payload viewing via AES-256 wrapping and validates JWT claims.

#### `MDM_Backend/signalmdm/middleware/rate_limit.py`
*   **Purpose:** Redis-backed request throttling middleware.
*   **Major Classes:** `RateLimitingMiddleware`.
*   **Major Functions:** `dispatch()`.
*   **Dependencies:** `fastapi`, `redis_client`, `core.config`.
*   **Used By:** Mounted in `main.py`.
*   **Business Role:** Implements sliding rate-limiting limits to prevent brute-force attacks.

#### `MDM_Backend/signalmdm/services/auth_service.py`
*   **Purpose:** Core identity controller for the platform.
*   **Major Classes:** `AuthService`.
*   **Major Functions:** `authenticate_admin()`, `verify_otp()`, `verify_2fa()`, `refresh_session()`.
*   **Dependencies:** `sqlalchemy`, `bcrypt`, `pyotp`, `redis_client`, `token_utils`.
*   **Used By:** `auth_router.py`.
*   **Business Role:** Processes hashes, generates temporary OTP secrets, and handles session caching.

#### `MDM_Backend/signalmdm/services/ingestion_service.py`
*   **Purpose:** Processes file loading workflows and state machines.
*   **Major Classes:** `IngestionService`.
*   **Major Functions:** `create_run()`, `transition_status()`, `process_run_sync()`.
*   **Dependencies:** `sqlalchemy`, `raw_service`, `staging_service`.
*   **Used By:** `ingestion_router.py`, workers.
*   **Business Role:** Orchestrates ingestion state boundaries, handling fail-open sync operations.

#### `MDM_Backend/signalmdm/utils/sanitize.py`
*   **Purpose:** Comprehensive Data Quality pipeline processor.
*   **Major Classes:** None.
*   **Major Functions:** `clean_payload()`, `scan_injection()`, `deduplicate_batch()`.
*   **Dependencies:** `re`, `json`, `hashlib`.
*   **Used By:** `raw_worker.py`, services.
*   **Business Role:** Audits incoming datasets to filter anomalies, detect injection attempts, and ensure clean ingestion.

---

### 3.2 Frontend Module Details

#### `MDM_Frontend/src/context/AuthContext.tsx`
*   **Purpose:** Manages global client login state.
*   **Major Classes:** `AuthProvider`.
*   **Major Functions:** `login()`, `logout()`, `verifyOtp()`.
*   **Dependencies:** `react`, `js-cookie`, `crypto-js`.
*   **Used By:** Header dashboards, protected views.
*   **Business Role:** Manages client-side login sessions and session storage caches.

#### `MDM_Frontend/src/pages/IngestionRuns.tsx`
*   **Purpose:** Displays ingestion workflows and system health stats.
*   **Major Classes:** None.
*   **Major Functions:** `IngestionRuns()`.
*   **Dependencies:** `react`, `lucide-react`, `TenantConfigContext`.
*   **Used By:** Shell routing.
*   **Business Role:** Provides administrators with real-time tracking of data loads.

#### `MDM_Frontend/src/pages/PlatformRBAC.tsx`
*   **Purpose:** Dynamic user roles configuration matrix.
*   **Major Classes:** None.
*   **Major Functions:** `PlatformRBAC()`.
*   **Dependencies:** `react`, `PermissionsContext`.
*   **Used By:** Shell routing.
*   **Business Role:** Allows super-admins to modify role scopes and system permissions.
