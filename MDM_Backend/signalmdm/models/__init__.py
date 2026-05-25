"""
signalmdm/models/__init__.py
-----------------------------
Import every model module so SQLAlchemy registers all mappers with Base
before `Base.metadata.create_all()` or Alembic autogenerate is called.

Phase 1 models (ingestion pipeline) are listed in the second block.

Usage::

    from signalmdm.models import *          # registers everything
    from signalmdm.models.tenant import Tenant
"""

# ---------------------------------------------------------------------------
# Core platform models (pre-existing)
# ---------------------------------------------------------------------------
from signalmdm.models.tenant        import Tenant
from signalmdm.models.entity        import Entity
from signalmdm.models.rbac          import AppUser, Role, Permission
from signalmdm.models.audit         import AuditLog
from signalmdm.models.signals       import SignalStreamBuffer, EntitySignal
from signalmdm.models.attributes    import EntityAttribute, EntityAttributeHistory
from signalmdm.models.relationships import EntityRelationship
from signalmdm.models.scoring       import (
    EntityRiskScore,
    EntityDrift,
    EntityGovernance,
    EntityAlert,
)
from signalmdm.models.features      import EntityFeatureStore, EntityDomainConfig

# ---------------------------------------------------------------------------
# Phase 1 — Ingestion pipeline models
# ---------------------------------------------------------------------------
from signalmdm.models.source_system  import SourceSystem
from signalmdm.models.ingestion_run  import IngestionRun
from signalmdm.models.file_upload    import FileUpload
from signalmdm.models.raw_record     import RawRecord
from signalmdm.models.staging_entity import StagingEntity

# ---------------------------------------------------------------------------
# Auth — Platform Admin + Platform RBAC
# ---------------------------------------------------------------------------
from signalmdm.models.platform_role  import PlatformRole, PlatformPermission, PlatformRolePermission
from signalmdm.models.platform_admin import PlatformAdmin
from signalmdm.models.upload_session import UploadSession, UploadSessionFile
from signalmdm.models.domain         import Domain

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
