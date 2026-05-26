"""
signalmdm/models/__init__.py
-----------------------------
Import every model module so SQLAlchemy registers all mappers with Base
before `Base.metadata.create_all()` or Alembic autogenerate is called.

Phase 1 models (ingestion pipeline) are listed in the second block.

Usage::

    from db.models import *          # registers everything
    from db.models.tenant import Tenant
"""

# ---------------------------------------------------------------------------
# Core platform models (pre-existing)
# ---------------------------------------------------------------------------
from db.models.tenant        import Tenant
from db.models.entity        import Entity
from db.models.rbac          import AppUser, Role, Permission
from db.models.audit         import AuditLog
from db.models.signals       import SignalStreamBuffer, EntitySignal
from db.models.attributes    import EntityAttribute, EntityAttributeHistory
from db.models.relationships import EntityRelationship
from db.models.scoring       import (
    EntityRiskScore,
    EntityDrift,
    EntityGovernance,
    EntityAlert,
)
from db.models.features      import EntityFeatureStore, EntityDomainConfig

# ---------------------------------------------------------------------------
# Phase 1 — Ingestion pipeline models
# ---------------------------------------------------------------------------
from db.models.source_system  import SourceSystem
from db.models.ingestion_run  import IngestionRun
from db.models.file_upload    import FileUpload
from db.models.raw_record     import RawRecord
from db.models.staging_entity import StagingEntity

# ---------------------------------------------------------------------------
# Auth — Platform Admin + Platform RBAC
# ---------------------------------------------------------------------------
from db.models.platform_role  import PlatformRole, PlatformPermission, PlatformRolePermission
from db.models.platform_admin import PlatformAdmin
from db.models.upload_session import UploadSession, UploadSessionFile
from db.models.domain         import Domain

__all__ = [
    # Core
    "Tenant",
    "Entity",
    "AppUser",
    "Role",
    "Permission",
    "AuditLog",
    "SignalStreamBuffer",
    "EntitySignal",
    "EntityAttribute",
    "EntityAttributeHistory",
    "EntityRelationship",
    "EntityRiskScore",
    "EntityDrift",
    "EntityGovernance",
    "EntityAlert",
    "EntityFeatureStore",
    "EntityDomainConfig",
    # Phase 1
    "SourceSystem",
    "IngestionRun",
    "FileUpload",
    "RawRecord",
    "StagingEntity",
    # Auth
    "PlatformAdmin",
    "PlatformRole",
    "PlatformPermission",
    "PlatformRolePermission",
    # Upload sessions
    "UploadSession",
    "UploadSessionFile",
    # Domains
    "Domain",
]
