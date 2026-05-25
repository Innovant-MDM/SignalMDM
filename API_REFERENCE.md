# SignalMDM: API Reference Manual

This document details all API endpoints exposed under the SignalMDM application control-plane `/api/v1` namespace.

---

## 1. Global API Parameters

### 1.1 Request Headers
Every authenticated endpoint requires the following headers:

| Header | Format | Description |
| :--- | :--- | :--- |
| `Authorization` | `Bearer <AES-256-encrypted-JWT>` | Base session token, encrypted using the global `TOKEN_ENCRYPTION_KEY`. |
| `X-Device-ID` | `UUIDv4` | Unique device identifier used to compile the SHA-256 fingerprint constraint. |
| `User-Agent` | `String` | Raw browser details matched against the fingerprint during verification. |
| `X-Tenant-ID` | `UUIDv4` | *(Optional)* Used by Platform SuperAdmins to override the current tenant query boundary. |

---

## 2. Endpoint Catalog

### 2.1 Authentication Control Layer (`/api/v1/auth`)

#### `POST /api/v1/auth/login`
*   **Purpose:** Initial phase authentication. Validates username and password, then triggers OTP code delivery.
*   **Authentication:** None.
*   **Implementation Location:** `MDM_Backend/signalmdm/routers/auth_router.py` (L45)
*   **Handler:** `login()`
*   **Service:** `AuthService.authenticate_admin()`
*   **Request Schema:**
    ```json
    {
      "email": "user@tenant.com",
      "password": "Password123"
    }
    ```
*   **Response Schema (200 OK):**
    ```json
    {
      "message": "OTP delivered. Validate verification session.",
      "admin_id": "a94037cf-e989-4823-b066-e83b708602c8",
      "mfa_required": true
    }
    ```
*   **Error Responses:**
    *   `401 Unauthorized`: "Invalid credentials."
    *   `429 Too Many Requests`: Rate limit triggered (Max 5 attempts/minute).
*   **Business Rules:** Returns identical "Invalid credentials" messages for both incorrect passwords and non-existent accounts to prevent user enumeration.

---

#### `POST /api/v1/auth/verify-otp`
*   **Purpose:** Validates the temporary 6-digit OTP code and issues the encrypted JWT access token.
*   **Authentication:** None.
*   **Implementation Location:** `MDM_Backend/signalmdm/routers/auth_router.py` (L82)
*   **Handler:** `verify_otp()`
*   **Service:** `AuthService.verify_otp()`
*   **Request Schema:**
    ```json
    {
      "admin_id": "a94037cf-e989-4823-b066-e83b708602c8",
      "otp_code": "123456"
    }
    ```
*   **Response Schema (200 OK):**
    ```json
    {
      "access_token": "U2FsdGVkX19xV...",
      "token_type": "bearer"
    }
    ```
*   **Error Responses:**
    *   `401 Unauthorized`: "OTP token expired or invalid."
    *   `403 Forbidden`: "Account locked. Maximum OTP validation attempts exceeded."
*   **Business Rules:** OTP validation limits attempts to 5 before locking out the admin ID.

---

#### `GET /api/v1/auth/me`
*   **Purpose:** Returns profile details for the currently active authenticated session.
*   **Authentication:** Required.
*   **Permissions:** Any valid active role.
*   **Implementation Location:** `MDM_Backend/signalmdm/routers/auth_router.py` (L120)
*   **Handler:** `get_me()`
*   **Response Schema (200 OK):**
    ```json
    {
      "admin_id": "a94037cf-e989-4823-b066-e83b708602c8",
      "email": "admin@signalmdm.com",
      "full_name": "Root Administrator",
      "role": "super_admin",
      "tenant_id": "platform"
    }
    ```

---

### 2.2 Source Systems Management (`/api/v1/sources`)

#### `POST /api/v1/sources`
*   **Purpose:** Registers a new external source system integration. (Deprecated alias: `POST /api/v1/sources/register`).
*   **Authentication:** Required.
*   **Permissions:** `admin`, `super_admin`, `data_architect`.
*   **Implementation Location:** `MDM_Backend/signalmdm/routers/source_router.py` (L29)
*   **Handler:** `register_source()`
*   **Service:** `SourceService.register_source()`
*   **Request Schema:**
    ```json
    {
      "code": "CRM-CORP",
      "name": "Corporate CRM Adapter",
      "description": "Consolidates corporate CRM contact profiles.",
      "config_json": {
        "sync_frequency": "hourly",
        "api_schema": {
          "mapping_id": "9cbae21f-1218-4825-9c9e-ca8cd0857030"
        }
      }
    }
    ```
*   **Response Schema (201 Created):**
    ```json
    {
      "source_id": "7b093dcf-18e4-4d81-8b01-a67b9393e9a1",
      "code": "CRM-CORP",
      "status": "active"
    }
    ```
*   **Validation Rules:** Code must be uppercase, alphanumeric, and between 3-10 characters.

---

### 2.3 File Upload & Ingestion (`/api/v1/upload` & `/api/v1/ingestion`)

#### `POST /api/v1/upload`
*   **Purpose:** Uploads raw multi-part CSV/JSON files for processing.
*   **Authentication:** Required.
*   **Permissions:** `admin`, `data_architect`, `data_manager`.
*   **Implementation Location:** `MDM_Backend/signalmdm/routers/upload_router.py` (L28)
*   **Handler:** `upload_file()`
*   **Response Schema (200 OK):**
    ```json
    {
      "session_id": "f5b61c92-34ab-4673-89bd-2b00567ef890",
      "filename": "contacts_2026.csv",
      "size_bytes": 1048576,
      "checksum_md5": "9e107d9d372bb6826bd81d3542a419d6"
    }
    ```
*   **Business Rules:** Filenames are automatically sanitized using `os.path.basename()` to prevent path traversal attacks.

---

#### `POST /api/v1/ingestion/run`
*   **Purpose:** Triggers the asynchronous parsing and staging task chain.
*   **Authentication:** Required.
*   **Permissions:** `admin`, `data_architect`, `data_manager`.
*   **Implementation Location:** `MDM_Backend/signalmdm/routers/ingestion_router.py` (L45)
*   **Handler:** `trigger_ingestion()`
*   **Service:** `IngestionService.create_run()`
*   **Request Schema:**
    ```json
    {
      "source_id": "7b093dcf-18e4-4d81-8b01-a67b9393e9a1",
      "session_id": "f5b61c92-34ab-4673-89bd-2b00567ef890"
    }
    ```
*   **Response Schema (202 Accepted):**
    ```json
    {
      "run_id": "3cbae21f-1218-4825-9c9e-ca8cd0857030",
      "status": "RUNNING",
      "message": "Async ingestion task successfully queued."
    }
    ```
*   **Business Rules:** Automatically falls back to synchronous processing if the Celery worker queue is unavailable, returning a `200 OK` once processing completes.

---

### 2.4 Platform Role-Based Access Control (`/api/v1/platform-rbac`)

#### `GET /api/v1/platform-rbac/my-permissions`
*   **Purpose:** Fetches the current user's navigation permission matrix.
*   **Authentication:** Required.
*   **Permissions:** Any valid session.
*   **Implementation Location:** `MDM_Backend/signalmdm/routers/platform_rbac_router.py` (L25)
*   **Response Schema (200 OK):**
    ```json
    {
      "permissions": [
        {
          "permission_id": "9cbae21f-1218-4825-9c9e-ca8cd0857030",
          "screen_key": "ingestion_runs",
          "feature_key": "trigger_run",
          "label": "Trigger Ingestion In UI",
          "description": "Grants rights to dispatch ingestion run tasks."
        }
      ]
    }
    ```
*   **Business Rules:** Results are cached in the browser's `sessionStorage` with automatic validation against background API checks on layout mount.

---

### 2.5 Domain Management (`/api/v1/domains`)

#### `POST /api/v1/domains`
*   **Purpose:** Registers a new logical data domain classification.
*   **Authentication:** Required.
*   **Permissions:** `admin`, `super_admin`, `data_architect`, `data_manager`.
*   **Implementation Location:** `MDM_Backend/signalmdm/routers/domain_router.py` (L28)
*   **Handler:** `create_domain()`
*   **Service:** `domain_service.create_domain()`
*   **Request Schema:**
    ```json
    {
      "domain_name": "Customer",
      "description": "Customer demographics and contact profiles.",
      "status": "ACTIVE"
    }
    ```
*   **Response Schema (201 Created):**
    ```json
    {
      "status": "ok",
      "message": "Domain created successfully.",
      "data": {
        "id": "e0dbe21f-1218-4825-9c9e-ca8cd0857030",
        "tenant_id": "platform",
        "domain_name": "Customer",
        "description": "Customer demographics and contact profiles.",
        "status": "ACTIVE",
        "created_at": "2026-05-25T12:00:00Z",
        "updated_at": "2026-05-25T12:00:00Z"
      }
    }
    ```
*   **Validation Rules:** `domain_name` must be unique per tenant and between 1-100 characters.

---

#### `GET /api/v1/domains`
*   **Purpose:** Lists all domains scoped to the authenticated tenant.
*   **Authentication:** Required.
*   **Permissions:** Any valid session.
*   **Implementation Location:** `MDM_Backend/signalmdm/routers/domain_router.py` (L63)
*   **Handler:** `list_domains()`
*   **Response Schema (200 OK):**
    ```json
    {
      "status": "ok",
      "message": "1 domain(s) found.",
      "data": [
        {
          "id": "e0dbe21f-1218-4825-9c9e-ca8cd0857030",
          "tenant_id": "platform",
          "domain_name": "Customer",
          "description": "Customer demographics and contact profiles.",
          "status": "ACTIVE",
          "created_at": "2026-05-25T12:00:00Z",
          "updated_at": "2026-05-25T12:00:00Z"
        }
      ]
    }
    ```

---

#### `GET /api/v1/domains/{domain_id}`
*   **Purpose:** Fetches a single domain by ID, scoped to the tenant.
*   **Authentication:** Required.
*   **Permissions:** Any valid session.
*   **Implementation Location:** `MDM_Backend/signalmdm/routers/domain_router.py` (L86)
*   **Handler:** `get_domain()`
*   **Response Schema (200 OK):**
    ```json
    {
      "status": "ok",
      "data": {
        "id": "e0dbe21f-1218-4825-9c9e-ca8cd0857030",
        "tenant_id": "platform",
        "domain_name": "Customer",
        "description": "Customer demographics and contact profiles.",
        "status": "ACTIVE",
        "created_at": "2026-05-25T12:00:00Z",
        "updated_at": "2026-05-25T12:00:00Z"
      }
    }
    ```

---

#### `PATCH /api/v1/domains/{domain_id}`
*   **Purpose:** Updates an existing domain.
*   **Authentication:** Required.
*   **Permissions:** `admin`, `super_admin`, `data_architect`, `data_manager`.
*   **Implementation Location:** `MDM_Backend/signalmdm/routers/domain_router.py` (L100)
*   **Handler:** `update_domain()`
*   **Request Schema:**
    ```json
    {
      "description": "Updated description",
      "status": "SUSPENDED"
    }
    ```
*   **Response Schema (200 OK):**
    ```json
    {
      "status": "ok",
      "message": "Domain updated successfully.",
      "data": {
        "id": "e0dbe21f-1218-4825-9c9e-ca8cd0857030",
        "tenant_id": "platform",
        "domain_name": "Customer",
        "description": "Updated description",
        "status": "SUSPENDED",
        "created_at": "2026-05-25T12:00:00Z",
        "updated_at": "2026-05-25T12:15:00Z"
      }
    }
    ```

---

#### `DELETE /api/v1/domains/{domain_id}`
*   **Purpose:** Soft-deactivates a domain (status set to `DEACTIVATED`).
*   **Authentication:** Required.
*   **Permissions:** `admin`, `super_admin` (Admin role restriction enforced).
*   **Implementation Location:** `MDM_Backend/signalmdm/routers/domain_router.py` (L124)
*   **Handler:** `delete_domain()`
*   **Response Schema (200 OK):**
    ```json
    {
      "status": "ok",
      "message": "Domain deactivated.",
      "data": {
        "id": "e0dbe21f-1218-4825-9c9e-ca8cd0857030",
        "tenant_id": "platform",
        "domain_name": "Customer",
        "status": "DEACTIVATED",
        "created_at": "2026-05-25T12:00:00Z",
        "updated_at": "2026-05-25T12:20:00Z"
      }
    }
    ```
