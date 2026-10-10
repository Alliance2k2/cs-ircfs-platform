"""Administration helpers: who a case can be assigned to, and the audit log."""
import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import Principal, require_roles
from app.db.models import AuditEvent, PlatformAccount, UserRole
from app.db.session import get_db

router = APIRouter(prefix="/api/v1/admin", tags=["administration"])
planner = Depends(require_roles(UserRole.district_officer, UserRole.district_planner, UserRole.administrator))
admin = Depends(require_roles(UserRole.administrator))
ASSIGNABLE = (UserRole.district_officer, UserRole.district_planner, UserRole.administrator)


@router.get("/assignees")
def assignees(db: Session = Depends(get_db), _: Principal = planner) -> list[dict]:
    """Active district staff a case can be assigned to (names and roles only)."""
    accounts = db.scalars(select(PlatformAccount).where(PlatformAccount.status == "active", PlatformAccount.role.in_(ASSIGNABLE))
                          .order_by(PlatformAccount.full_name))
    return [{"id": account.id, "full_name": account.full_name, "role": account.role.value,
             "area": ", ".join(sector.name for sector in account.sectors) or "Bugesera District"} for account in accounts]


@router.get("/audit")
def audit_log(
    limit: int = Query(default=200, ge=1, le=1000),
    action: str | None = Query(default=None, max_length=60),
    entity: str | None = Query(default=None, max_length=40),
    db: Session = Depends(get_db),
    _: Principal = admin,
) -> list[dict]:
    """The latest changes made by staff, newest first."""
    query = select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)
    if action:
        query = query.where(AuditEvent.action.startswith(action))
    if entity:
        query = query.where(AuditEvent.entity == entity)
    rows = []
    for event in db.scalars(query):
        try:
            detail = json.loads(event.detail) if event.detail else {}
        except ValueError:
            detail = {"raw": event.detail}
        rows.append({"id": event.id, "actor": event.actor_label, "actor_account_id": event.actor_account_id, "action": event.action,
                     "entity": event.entity, "entity_id": event.entity_id, "detail": detail, "created_at": event.created_at})
    return rows
