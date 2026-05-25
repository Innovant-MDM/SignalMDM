# SignalMDM: Enterprise Technical Reference Guide

This document provides a deep-dive technical reference on the frameworks, libraries, design architectures, and dependencies powering the SignalMDM enterprise application.

---

## 1. Core Technical Components

Here we detail the purpose, context, and integration flows of our core technology decisions.

### 1.1 FastAPI
*   **Purpose:** The primary asynchronous web API framework.
*   **Where Used:** Backend routing controller plane (`MDM_Backend/main.py` and routers).
*   **Files Utilizing:** `main.py`, `routers/auth_router.py`, `routers/ingestion_router.py`.
*   **Why It Is Used:** Standardizes API development by leveraging Pydantic models for request/response serialization. Native support for `async/await` ensures efficient concurrent request handling under high loads.
*   **Interaction Model:** Receives incoming JSON payloads, validates them using Pydantic, validates access scopes using dependency injection guards in `auth.py`, and delegates transaction handling to services.

---

### 1.2 Celery
*   **Purpose:** Asynchronous distributed task execution queue.
*   **Where Used:** Background processing of large ingestion runs (`MDM_Backend/signalmdm/workers`).
*   **Files Utilizing:** `celery_app.py`, `raw_worker.py`, `staging_worker.py`.
*   **Why It Is Used:** Decouples intensive data cleansing, deduplication, and staging operations from the HTTP request-response cycle, preventing timeouts and ensuring service stability.
*   **Interaction Model:** The FastAPI ingestion router queues jobs via `celery.send_task`. Celery workers consume tasks from Redis, execute SQL updates, and update the execution status in PostgreSQL.

---

### 1.3 React & TypeScript
*   **Purpose:** Client application engine.
*   **Where Used:** Frontend user interface layout (`MDM_Frontend/src`).
*   **Files Utilizing:** `main.tsx`, `App.tsx`, `pages/UploadData.tsx`, `context/AuthContext.tsx`.
*   **Why It Is Used:** TypeScript ensures type-safe component state management, preventing runtime UI exceptions. Vite provides extremely fast build compilation times.
*   **Interaction Model:** Standardizes API integration via Axios client configurations, manages sessions in global React Context wrappers, and enforces route protection using state properties.

---

### 1.4 PostgreSQL
*   **Purpose:** Authoritative enterprise relational database.
*   **Where Used:** Persistent data storage tier (`MDM_DataLayer/SignalMDM.sql`).
*   **Why It Is Used:** Excellent JSONB performance, transaction compliance, referential integrity safeguards (`ondelete="RESTRICT"`), and mature composite indexing options.
*   **Interaction Model:** Coordinates relational structures across tenants, administrators, ingestion runs, raw immutable records, and staging assets.

---

### 1.5 Redis
*   **Purpose:** Low-latency caching engine, rate limiter, and task message broker.
*   **Where Used:** Backend middleware and task queues.
*   **Files Utilizing:** `core/redis_client.py`, `middleware/rate_limit.py`, `services/auth_service.py`.
*   **Why It Is Used:** Delivers single-digit millisecond responses for token revocation checks, sliding-window rate limiting, and OTP caching.
*   **Interaction Model:** Stores revoked JWT signatures, salted/hashed OTP codes (with 10-minute TTLs), and tracks login attempts to prevent brute-force attacks.

---

## 2. Major Dependency Catalog

Below is a detailed inventory of the primary third-party dependencies used in SignalMDM.

| Dependency Name | Inspected Version | Purpose | Usage Files | Architectural Benefits | Alternatives |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FastAPI** | `0.136.1` | REST API orchestration and dependency injection. | `main.py`, `routers/*.py` | Asynchronous speed, automatic OpenAPI generation, clean type validation. | Django REST, Flask |
| **Uvicorn** | `0.42.0` | High-speed ASGI server execution. | Startup scripts | Ultra-low overhead, handles high-concurrency connections. | Hypercorn, Gunicorn |
| **SQLAlchemy** | `2.0.40` | Transaction-safe database ORM interface. | `database.py`, `models/*.py` | Unified query generation, connection pooling, complex mapping controls. | TortoiseORM, Peewee |
| **Pydantic** | `2.11.7` | Standard data parsing and serialization. | `schemas/*.py`, `core/config.py` | Fast data validation, clear runtime typing errors. | Marshmallow, Cerberus |
| **Celery** | `5.6.3` | Background asynchronous task distribution. | `workers/celery_app.py` | Proven task queues, automatic retries with exponential backoffs. | RQ (Redis Queue), Dramatiq |
| **Redis** | `6.2.0` | Cache memory storage and messaging client. | `core/redis_client.py` | Fast keyspace operations, sliding-window rate-limiting. | Memcached, RabbitMQ |
| **Python-Jose** | `3.5.0` | JWT token signature coding and decoding. | `middleware/token_utils.py` | Robust support for HS256 algorithm pinning, secure claim checks. | PyJWT |
| **Cryptography** | `46.0.5` | Standard AES-256-CBC token encryption wrapper. | `middleware/token_utils.py` | Strong client-server session envelope security. | PyCryptodome |
| **Bcrypt** | `5.0.0` | Adaptive hashing of sensitive values. | `services/auth_service.py` | High computational complexity prevents database dump cracking. | Argon2 |
| **PyOTP** | `2.9.0` | Encoded OTP code calculation algorithms. | `services/auth_service.py` | Seamless integration of standard MFA workflows. | Custom OTP logic |
| **Crypto-JS** | `4.2.0` | Client-side AES-256 encryption engine. | `utils/crypto.ts`, `context/AuthContext.tsx` | Secure client-side payload obfuscation before transit. | Web Crypto API |

---

## 3. Core Architectural Patterns

### 3.1 Encrypted Token Security Pattern
The platform implements an encrypted JWT payload pattern to protect credentials in transit:
```
[Client App (CryptoJS)]
      │
      ├─► 1. Encrypt JWT with AES-256-CBC using VITE_TOKEN_ENCRYPTION_KEY
      │
[Network Transit (Encrypted Ciphertext)]
      │
[Backend API Middleware (token_utils.py)]
      │
      ├─► 2. Decrypt envelope using TOKEN_ENCRYPTION_KEY
      ├─► 3. Validate signature against HS256 algorithm pin
      ├─► 4. Verify SHA-256 dynamic device fingerprint
      │
[FastAPI Router Context (Authenticated Session)]
```

### 3.2 Ingestion Engine State Machine
The async ingestion pipeline implements a transaction-safe state machine to track data processing:
```
           ┌───────────────────────┐
           │        CREATING       │
           └───────────┬───────────┘
                       │ (File received)
                       ▼
           ┌───────────────────────┐
           │        RUNNING        │
           └───────────┬───────────┘
                       │ (Loaded into Raw landing zone)
                       ▼
           ┌───────────────────────┐
           │       RAW_LOADED      │
           └───────────┬───────────┘
                       │ (Mapped to Staging layout)
                       ▼
           ┌───────────────────────┐
           │    STAGING_CREATED    │
           └───────────┬───────────┘
                       │ (Survivorship & alignment success)
                       ▼
           ┌───────────────────────┐
           │       COMPLETED       │
           └───────────────────────┘
```
If any stage fails (e.g. data quality anomalies or invalid CSV formats), the state transitions to `FAILED`, and the specific error is logged in the `IngestionRun` audit record.
