from __future__ import annotations

from api.routes.mdm_phase2.canonical_models import router as canonical_models_router
from api.routes.mdm_phase2.field_mappings import router as field_mappings_router
from api.routes.mdm_phase2.mapping_errors import router as mapping_errors_router
from api.routes.mdm_phase2.normalization_runs import router as normalization_runs_router
from api.routes.mdm_phase2.standardization_rules import router as standardization_rules_router
from api.routes.mdm_phase2.transformation_rules import router as transformation_rules_router

__all__ = [
    "canonical_models_router",
    "field_mappings_router",
    "mapping_errors_router",
    "normalization_runs_router",
    "standardization_rules_router",
    "transformation_rules_router",
]
