"""
signalmdm/enums.py
------------------
Centralised string-valued enums used across ORM models, Pydantic schemas,
and application logic.

Rules:
  • All values are UPPER_SNAKE_CASE strings so they read cleanly in the DB.
  • Never remove or rename a value — add a deprecation comment instead.
"""

from __future__ import annotations

from enum import Enum


# ---------------------------------------------------------------------------
# General / shared
# ---------------------------------------------------------------------------

class StatusEnum(str, Enum):
    ACTIVE      = "ACTIVE"
    SUSPENDED   = "SUSPENDED"
    ARCHIVED    = "ARCHIVED"
    DEACTIVATED = "DEACTIVATED"


class OperationTypeEnum(str, Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    MERGE  = "MERGE"
    UPLOAD = "UPLOAD"
    CANCEL = "CANCEL"
    PROCESS_RAW = "PROCESS_RAW"
    PROCESS_ERROR = "PROCESS_ERROR"


# ---------------------------------------------------------------------------
# Entity domain
# ---------------------------------------------------------------------------

class EntityTypeEnum(str, Enum):
    CUSTOMER  = "CUSTOMER"
    PRODUCT   = "PRODUCT"
    SUPPLIER  = "SUPPLIER"
    EMPLOYEE  = "EMPLOYEE"
    LOCATION  = "LOCATION"
    ACCOUNT   = "ACCOUNT"
    ASSET     = "ASSET"
    OTHER     = "OTHER"


class LifecycleStageEnum(str, Enum):
    ONBOARDING  = "ONBOARDING"
    ACTIVE      = "ACTIVE"
    DORMANT     = "DORMANT"
    OFFBOARDED  = "OFFBOARDED"
    SUSPENDED   = "SUSPENDED"


# ---------------------------------------------------------------------------
# Signal / stream
# ---------------------------------------------------------------------------

class ProcessingStatusEnum(str, Enum):
    PENDING    = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED  = "PROCESSED"
    FAILED     = "FAILED"


class SeverityEnum(str, Enum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


class SignalCategoryEnum(str, Enum):
    BEHAVIOURAL  = "BEHAVIOURAL"
    TRANSACTIONAL = "TRANSACTIONAL"
    DEMOGRAPHIC  = "DEMOGRAPHIC"
    OPERATIONAL  = "OPERATIONAL"
    OTHER        = "OTHER"


# ---------------------------------------------------------------------------
# Phase 1 — Ingestion pipeline
# ---------------------------------------------------------------------------

class IngestionStateEnum(str, Enum):
    """
    State machine for an ingestion run.

    Valid transitions:
        CREATED → RUNNING → RAW_LOADED → STAGING_CREATED → COMPLETED
        RUNNING → RUNNING (additional file), RAW_LOADED → RUNNING (additional file)
        Any state → FAILED
    """
    CREATED          = "CREATED"
    RUNNING          = "RUNNING"
    RAW_LOADED       = "RAW_LOADED"
    STAGING_CREATED  = "STAGING_CREATED"
    COMPLETED        = "COMPLETED"
    FAILED           = "FAILED"


class SourceTypeEnum(str, Enum):
    CRM        = "CRM"
    ERP        = "ERP"
    DATABASE   = "DATABASE"
    FILE       = "FILE"
    API        = "API"
    STREAMING  = "STREAMING"
    OTHER      = "OTHER"


class ConnectionTypeEnum(str, Enum):
    CSV       = "CSV"
    JSON      = "JSON"
    REST_API  = "REST_API"
    JDBC      = "JDBC"
    SFTP      = "SFTP"
    S3        = "S3"
    OTHER     = "OTHER"


class StagingStateEnum(str, Enum):
    READY_FOR_MAPPING = "READY_FOR_MAPPING"
    MAPPED            = "MAPPED"           # Phase 2
    REJECTED          = "REJECTED"
