# SignalMDM: Systems & Architectural Specification

This document provides a comprehensive technical overview of the system architecture, logical layers, request pipelines, and background execution topologies of the SignalMDM platform.

---

## 1. System Topology & Logical Architecture

SignalMDM is designed around a decoupled, three-tier enterprise service architecture. The control plane, storage interfaces, task-queues, and caching subsystems operate independently, ensuring horizontal scale and structural high availability.

### 1.1 Architectural Component Topology
```mermaid
graph TD
    subgraph ClientLayer ["Client Layer (SPA)"]
        Browser["Web Browser (React SPA)"]
        CryptoJS["CryptoJS (Client Encrypter)"]
        Browser --> CryptoJS
    end

    subgraph ReverseProxy ["Reverse Proxy & Web Server"]
        Express["Express SPA Host (port: 3030)"]
        Helmet["Helmet Middleware (CSP/Headers)"]
        Express --> Helmet
    end

    subgraph ControlPlane ["Control Plane (API Server)"]
        FastAPI["FastAPI Engine (port: 8000)"]
        Uvicorn["Uvicorn Server Process"]
        RateLimit["Rate Limit Middleware"]
        DecryptMW["AES Decrypt Middleware"]
        AuthMW["Auth Guard Middleware"]
        FastAPI --> Uvicorn
        Uvicorn --> RateLimit
        RateLimit --> DecryptMW
        DecryptMW --> AuthMW
    end

    subgraph DataCache ["State & Cache Layer"]
        Redis["Redis Memory Cache (port: 6379)"]
        Blacklist["Token Revocation Hash"]
        OTPStore["OTP Token Hash"]
        Redis --> Blacklist
        Redis --> OTPStore
    end

    subgraph BackgroundWorkers ["Async Processing Tier"]
        Celery["Celery Task Manager"]
        RawWorker["Raw Extractor Worker"]
        StagingWorker["Staging Processor Worker"]
        Celery --> RawWorker
        RawWorker --> StagingWorker
    end

    subgraph StorageTier ["Data Storage Tier"]
        Postgres[("PostgreSQL Database (port: 5432)")]
        DiskStorage["Local File Store (/storage)"]
    end

    Browser -->|Encrypted Session / Static Web Request| Express
    Express -->|API Ingestion Request| Uvicorn
    AuthMW -->|Verify Revocation| Redis
    Celery -->|Queue Broker Tasks| Redis
    FastAPI -->|Async Job Delegation| Celery
    RawWorker -->|Load File Chunks| DiskStorage
    RawWorker -->|Insert Raw JSONB| Postgres
    StagingWorker -->|Transform and Align| Postgres
    FastAPI -->|Direct DB Operations / Sync Fallback| Postgres
```

---

## 2. Request Lifecycle & Authentication Flows

Every API request entering the SignalMDM boundary is intercepted, audited, decrypted, and evaluated before reaching the route business logic.

### 2.1 The Request Lifecycle Flow
```mermaid
sequenceDiagram
    autonumber
    participant Browser as Web Browser (React SPA)
    participant Express as Express SPA (Port 3030)
    participant RateLimit as Redis Rate Limiter
    participant Decrypt as AES Decryption Middleware
    participant Auth as Auth Middleware Guard
    participant Route as FastAPI Router Endpoint
    participant DB as PostgreSQL DB Engine

    Browser->>Express: HTTPS GET /api/v1/sources
    Note over Browser, Express: Payload contains VITE_TOKEN_ENCRYPTION_KEY encrypted JWT

    Express->>RateLimit: Request through rate limit check
    alt Rate limit exceeded (e.g. >20 req/min)
        RateLimit-->>Browser: HTTP 429 Too Many Requests
    else Limit OK
        RateLimit->>Decrypt: Forward payload
    end

    Decrypt->>Decrypt: Extract AES cipher in header/cookie
    alt Decryption fails (missing/malformed)
        Decrypt-->>Browser: HTTP 400 Bad Request
    else Decryption Successful (Plain JWT output)
        Decrypt->>Auth: Hand off decoded credentials
    end

    Auth->>Auth: Validate JWT Signature (HS256 Only)
    Auth->>Auth: Verify expiry time & device fingerprint (SHA256)
    alt Validation fails / Expired
        Auth-->>Browser: HTTP 401 Unauthorized
    else Validation Successful
        Auth->>Route: Mount user context in route dependecies
    end

    Route->>DB: Perform isolated database query (X-Tenant-ID scoping)
    DB-->>Route: Return query dataset
    Route-->>Browser: HTTP 200 OK (Cleaned JSON payload)
```

### 2.2 Secure Encrypted Authentication Flow
The security pipeline utilizes client-side encryption to prevent JWT inspection or token interception, combined with multi-factor OTP validation and automated rate limiting.
```mermaid
graph TD
    A["User submits username/password (Login.tsx)"] --> B["API checks credentials (bcrypt)"]
    B -->|Success| C["Generate dynamic 6-digit OTP code"]
    C --> D["Write OTP salt and hash to Redis (10 min TTL)"]
    D --> E["Transmit OTP code to User Email (SMTP)"]
    E --> F["User submits OTP code"]
    F --> G["API verifies OTP in Redis"]
    G -->|Valid| H["Generate JSON Web Token (JWT)"]
    H --> I["Encrypt JWT with AES-256-CBC (VITE_TOKEN_ENCRYPTION_KEY)"]
    I --> J["Set secure HTTPOnly cookie (accessToken)"]
```

---

## 3. Data Ingestion & Async Processing Flow

The SignalMDM ingestion engine is an asynchronous state machine managed by Celery. It coordinates file landing-zone persistence, schema integrity validation, deduplication, and staging translation.

### 3.1 Upload Processing Flow
```mermaid
graph TD
    A["User initiates file upload (UploadData.tsx)"] -->|File stream| B["upload_router.py (POST /upload)"]
    B --> C["Sanitize path with os.path.basename()"]
    C --> D["Generate unique session upload run_id"]
    D --> E["Stream file chunks to local disk /storage/uploads/{run_id}"]
    E --> F["Generate final MD5 checksum of file"]
    F --> G["Write upload metadata to PostgreSQL (UploadSession)"]
    G --> H["Hand off execution to background task queue"]
```

### 3.2 Ingestion & Queue Processing Flow
Once a file is safely landed, the FastAPI control-plane dispatches tasks to the Celery broker (Redis), orchestrating an asynchronous processing pipeline.
```mermaid
sequenceDiagram
    autonumber
    participant Router as API Ingestion Router
    participant Queue as Redis Queue Broker
    participant Raw as Celery: Raw Ingest Worker
    participant Staging as Celery: Staging Ingest Worker
    participant DB as PostgreSQL Database

    Router->>DB: Set IngestionRun status = RUNNING
    Router->>Queue: Dispatch task: raw_worker.process_file(run_id)
    Router-->>Router: HTTP 202 Accepted (Returns run_id to Client)

    activate Raw
    Queue->>Raw: Consume raw ingestion job
    Raw->>DB: Load file metadata & open data stream
    Raw->>Raw: Execute Data Quality Pipeline (sanitize.py)<br/>- Dedup rows via MD5 hash<br/>- Regex scan columns for SQLi/XSS payloads<br/>- Filter oversized fields
    Raw->>DB: Bulk insert records into platform.raw_records table
    Raw->>DB: Update IngestionRun status = RAW_LOADED
    Raw->>Queue: Dispatch task: staging_worker.process_run(run_id)
    deactivate Raw

    activate Staging
    Queue->>Staging: Consume staging task
    Staging->>DB: Map 1-to-1 raw_records to staging_entities
    Staging->>DB: Verify target schemas & correlation IDs
    Staging->>DB: Apply matching/survivorship guidelines
    Staging->>DB: Update IngestionRun status = COMPLETED
    deactivate Staging
```

---

## 4. Multi-Tenant Isolation Architecture

Logical multi-tenancy is enforced natively in the database schema.

### 4.1 Structural Database Relationship Design
Every entity, source system, mapping config, and transaction log is bound to the root organisation via the `tenant_id` foreign key.
```mermaid
erDiagram
    TENANT ||--o{ APP_USER : "has members"
    TENANT ||--o{ SOURCE_SYSTEM : "defines adapters"
    TENANT ||--o{ AUDIT_LOG : "generates history"
    TENANT ||--o{ INGESTION_RUN : "executes runs"
    TENANT ||--o{ RAW_RECORD : "ingests"
    TENANT ||--o{ STAGING_ENTITY : "holds staging"

    TENANT {
        uuid tenant_id PK
        string name
        jsonb config_json
    }
    APP_USER {
        uuid user_id PK
        uuid tenant_id FK
        string email
        string password_hash
    }
    SOURCE_SYSTEM {
        uuid source_id PK
        uuid tenant_id FK
        string code
        string name
    }
    INGESTION_RUN {
        uuid run_id PK
        uuid tenant_id FK
        string status
    }
    RAW_RECORD {
        uuid raw_record_id PK
        uuid tenant_id FK
        jsonb raw_data
        string checksum_md5
    }
    STAGING_ENTITY {
        uuid staging_id PK
        uuid tenant_id FK
        uuid raw_record_id FK
        string state
    }
```

### 4.2 Query-Level Tenant Scoping Pipeline
1.  **Direct Routing Scope:** 
    Standard tenants (`admin`, `data_architect`, `data_manager`) can only query records matching their session context `tenant_id` (extracted from the authenticated JWT payload). The database query layers automatically append `WHERE tenant_id = :session_tenant_id` to all SELECT, UPDATE, and DELETE operations.
2.  **SuperAdmin Scoping Overrides:**
    SuperAdmins belonging to the `"platform"` tenant can override the target tenant context:
    *   The browser app sends a specific header `X-Tenant-ID` containing the target UUID.
    *   The `auth.py` middleware parses this header, validates that the user is a `super_admin`, and mounts the requested `X-Tenant-ID` as the active `tenant_id` parameter inside the request database session context.
3.  **Referential Integrity Safeguard:**
    All database tables declare:
    ```python
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenant.tenant_id", ondelete="RESTRICT"), nullable=False)
    ```
    This constraint prevents accidental deletions or cascades from wiping out organizational master data.

---

## 5. Deployment Topology

SignalMDM is deployed as a resilient micro-services cluster managed by Kubernetes.

```mermaid
graph TD
    subgraph Internet ["Public Network"]
        Client["Web Browser"]
    end

    subgraph DMZ ["Kubernetes Cluster Boundary"]
        Ingress["Nginx Ingress Controller (TLS Termination)"]
        WebPod["Frontend Service Pod (Express)"]
    end

    subgraph PrivateSubnet ["Isolated Backend Services"]
        APIPod["Backend API Service Pods (FastAPI)"]
        WorkerPod["Celery Task Processing Pods"]
        RedisCluster[("Redis Replication Set (Rate Limiting/Queue)")]
    end

    subgraph DataStorage ["Secure Databases Layer"]
        PostgresReplica[("PostgreSQL Master/Replica Set")]
    end

    Client -->|HTTPS / Port 443| Ingress
    Ingress -->|Static Bundle / SPA Assets| WebPod
    Ingress -->|Forward API Traffic /api/v1| APIPod
    APIPod -->|Broker Jobs| RedisCluster
    WorkerPod -->|Consume Queued Jobs| RedisCluster
    APIPod -->|Query / Mutate| PostgresReplica
    WorkerPod -->|Query / Mutate| PostgresReplica
```
