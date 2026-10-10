"""The audit log: one append-only row per change a person makes. The caller commits."""
import json

from sqlalchemy.orm import Session

from app.core.security import Principal
from app.db.models import AuditEvent


def record(db: Session, principal: Principal, action: str, entity: str, entity_id: int | None = None, **detail) -> None:
    """Note who did what. ``detail`` holds the changed values (never passwords or message text)."""
    db.add(AuditEvent(
        actor_account_id=principal.account_id,
        actor_label=principal.name,
        action=action,
        entity=entity,
        entity_id=entity_id,
        detail=json.dumps({key: value for key, value in detail.items() if value is not None}, default=str) if detail else None,
    ))
