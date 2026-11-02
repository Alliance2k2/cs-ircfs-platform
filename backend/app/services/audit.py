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


def personal_read(db, principal, entity, entity_id=None, rows=None):
    """Bounded access audit: no search terms, phone numbers, messages or coordinates."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.core.config import get_settings
    from app.core.privacy import sees_personal_data
    if not get_settings().audit_personal_reads or not sees_personal_data(principal):
        return
    recent = db.scalar(select(AuditEvent.id).where(AuditEvent.action == "personal.read",
        AuditEvent.actor_label == principal.name, AuditEvent.entity == entity, AuditEvent.entity_id == entity_id,
        AuditEvent.created_at >= datetime.now(timezone.utc) - timedelta(minutes=5)).limit(1))
    if recent is None:
        record(db, principal, "personal.read", entity, entity_id, rows=rows)
        db.commit()
