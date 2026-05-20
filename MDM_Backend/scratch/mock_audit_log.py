import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import text
from signalmdm.database import SessionLocal
from signalmdm.services.audit_service import log_action

with SessionLocal() as db:
    tenant_id = db.execute(text("SELECT tenant_id FROM tenant LIMIT 1")).scalar()
    log_action(
        db=db,
        tenant_id=tenant_id,
        entity_name="test_override_entity",
        operation_type="UPDATE",
        performed_by="alice",
        approved_by="bob_admin",
        approval_reason="Emergency manual override due to system failure in production.",
    )
    print("Mock audit log entry with approval created successfully.")
