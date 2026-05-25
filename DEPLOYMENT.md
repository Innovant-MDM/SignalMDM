# SignalMDM: Enterprise Production Deployment Manual

This document provides a highly detailed specification for configuring, deploying, scaling, and managing the SignalMDM platform in cloud environments.

---

## 1. Environments Specification

SignalMDM utilizes a standardized environment topology to guarantee smooth delivery paths:

| Profile | Purpose | Deployment Strategy | Isolation Type |
| :--- | :--- | :--- | :--- |
| **Development** | Sandbox / Local engineering | Local host execution / Single-node Docker | Logical |
| **QA** | Automated testing & validation | Docker Compose on virtualized host | Logical |
| **UAT** | Client acceptance & staging checks | Multi-node Kubernetes (EKS / GKE) | Shared Database, Dedicated Schema |
| **Production**| Public master systems | High Availability Kubernetes Cluster | Dedicated Database Instance |

---

## 2. Infrastructure Requirements

### 2.1 Compute Targets
*   **Web Frontend Pods:** 2x Replica nodes, 0.5 CPU Cores, 512MB RAM per pod.
*   **Backend API Pods:** 3x Replica nodes, 1.0 CPU Cores, 1.5GB RAM per pod.
*   **Celery Workers Pods:** 2x Replica nodes, 2.0 CPU Cores, 4.0GB RAM per pod (intensive Data Quality sanitization runs).

### 2.2 Storage & Network
*   **PostgreSQL Engine:** Managed instance (e.g. AWS RDS PostgreSQL 15) with multi-AZ replication. Minimum 4 vCPUs, 16GB RAM, 100GB provisioned IOPS SSD storage.
*   **Caching (Redis):** Elasticache Redis instance, minimum 2 Cores, 4GB RAM.
*   **Network:** Private subnet boundaries isolating Database and Caching layers, with access restricted to the Kubernetes cluster security group.

---

## 3. Container Configurations & Orchestration

### 3.1 Backend Dockerfile (`MDM_Backend/Dockerfile`)
```dockerfile
FROM python:3.12-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim as runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH
ENV APP_ENV=production

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
```

---

### 3.2 System Multi-Container Orchestration (`docker-compose.yml`)
For QA and staging environments:
```yaml
version: '3.8'

services:
  database:
    image: postgres:15-alpine
    container_name: mdm_database
    environment:
      POSTGRES_DB: SignalMDM
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: production_password
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: mdm_redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build:
      context: ./MDM_Backend
      dockerfile: Dockerfile
    container_name: mdm_api
    environment:
      - DATABASE_URL=postgresql://postgres:production_password@database:5432/SignalMDM
      - REDIS_URL=redis://redis:6379/0
      - APP_ENV=production
      - JWT_SECRET=production_jwt_secret
      - TOKEN_ENCRYPTION_KEY=a3f1b2c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2
    ports:
      - "8000:8000"
    depends_on:
      database:
        condition: service_healthy
      redis:
        condition: service_healthy

  worker:
    build:
      context: ./MDM_Backend
      dockerfile: Dockerfile
    container_name: mdm_worker
    command: celery -A signalmdm.workers.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://postgres:production_password@database:5432/SignalMDM
      - REDIS_URL=redis://redis:6379/0
      - APP_ENV=production
    depends_on:
      redis:
        condition: service_healthy

volumes:
  pgdata:
```

---

### 3.3 Kubernetes Deployment Resource Specs (`deployment.yaml`)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mdm-api-deployment
  namespace: mdm-production
  labels:
    app: mdm-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mdm-api
  template:
    metadata:
      labels:
        app: mdm-api
    spec:
      containers:
      - name: mdm-api-container
        image: mdm-registry.corp/signalmdm-backend:1.0.0
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: mdm-production-secrets
        resources:
          limits:
            cpu: "1.5"
            memory: 2Gi
          requests:
            cpu: "500m"
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

---

## 4. Disaster Recovery & Operational Runbooks

### 4.1 Automated Database Backup Script (`backup.sh`)
```bash
#!/bin/bash
set -e

BACKUP_DIR="/mnt/backups/postgres"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DATABASE_NAME="SignalMDM"
PGPASSWORD="production_password"
BACKUP_FILE="${BACKUP_DIR}/${DATABASE_NAME}_backup_${TIMESTAMP}.sql"

mkdir -p "$BACKUP_DIR"

echo "Starting automated database backup for database ${DATABASE_NAME}..."
PGPASSWORD="$PGPASSWORD" pg_dump -h localhost -U postgres -d "$DATABASE_NAME" -F p -f "$BACKUP_FILE"

echo "Compressing backup file..."
gzip "$BACKUP_FILE"

echo "Exporting compressed backup file to secure AWS S3 bucket..."
aws s3 cp "${BACKUP_FILE}.gz" "s3://corp-mdm-backups/database/${DATABASE_NAME}_backup_${TIMESTAMP}.sql.gz"

echo "Database backup and export completed successfully."
```

### 4.2 Rollback Procedure Runbook
If an active deployment fails liveness or integration checks:
1.  **Halt CI/CD pipeline progression:** Trigger pipeline cancellation.
2.  **Locate the last stable container tag:** E.g. `v1.0.0-RC1`.
3.  **Execute Kubernetes Rollback command:**
    ```bash
    kubectl rollout undo deployment/mdm-api-deployment -n mdm-production
    ```
4.  **Confirm rollback status:**
    ```bash
    kubectl rollout status deployment/mdm-api-deployment -n mdm-production
    ```
5.  **Verify Pod state and health endpoints:**
    ```bash
    kubectl get pods -n mdm-production
    curl -I http://mdm-production.corp/api/v1/health
    ```

---

## 5. Troubleshooting & Diagnostics

### 5.1 Issue: Redis Out of Memory (OOM)
*   **Symptom:** API requests hang or return `500 Internal Server Error`, Celery workers stop accepting raw ingestion tasks.
*   **Diagnostic:** Check Redis memory usage statistics:
    ```bash
    redis-cli -h localhost info memory
    ```
    If `used_memory_human` matches the allocated limits, Redis is out of memory.
*   **Resolution:**
    1.  Clear expired token revocation keys from the database:
        ```bash
        redis-cli keys "revoked:*" | xargs redis-cli del
        ```
    2.  Check the size of the Celery broker queues:
        ```bash
        redis-cli llen celery
        ```
    3.  If queues are persistently overloaded, scale background worker pods:
        ```bash
        kubectl scale deployment/mdm-worker-deployment --replicas=5 -n mdm-production
        ```
