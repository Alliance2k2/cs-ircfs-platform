"""Closing-the-Loop SMS (architecture Module 3): tell the affected cell what action was taken."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Cell, IncidentCase, Sector, User
from app.services.sms import deliver, is_valid_phone, normalise_phone

PRIORITY_RANK = {"medium": 1, "high": 2, "critical": 3}


def notify_cell(db: Session, cell_id: int | None, message: str, preview: bool) -> dict:
    """Preview or send one message to every active registered user in a cell. The caller commits."""
    if cell_id is None:
        raise HTTPException(status_code=422, detail="This record has no cell, so the affected community cannot be identified")
    cell = db.get(Cell, cell_id)
    phones = list(db.scalars(select(User.phone_number).where(User.cell_id == cell_id, User.is_active.is_(True))))
    if not preview:
        for phone in phones:
            deliver(db, phone, message, purpose="close_loop", cell_id=cell_id)
    return {"preview": preview, "cell": cell.name if cell else f"Cell #{cell_id}", "recipients": len(phones), "message": message,
            "sent": 0 if preview else len(phones)}


def alert_staff(db: Session, case: IncidentCase, summary: str, cell_id: int | None) -> int:
    """SMS the district staff in ALERT_PHONE_NUMBERS about a new case. Returns how many were sent. The caller commits."""
    settings = get_settings()
    if PRIORITY_RANK.get(case.priority, 0) < PRIORITY_RANK.get(settings.alert_min_priority.strip().lower(), 3):
        return 0
    phones = [phone for phone in (normalise_phone(item) for item in settings.alert_phone_numbers.split(",") if item.strip()) if is_valid_phone(phone)]
    if not phones:
        return 0
    place = db.execute(select(Cell.name, Sector.name).join(Sector, Cell.sector_id == Sector.id).where(Cell.id == cell_id)).first() if cell_id else None
    where = f"{place[1]} / {place[0]}" if place else "location not set"
    message = f"CS-IRCFS {case.priority.upper()}: {summary[:120]} ({where}). Case #{case.id}. Open the planner dashboard to act."
    for phone in dict.fromkeys(phones):
        deliver(db, phone, message, purpose="staff_alert", cell_id=cell_id)
    return len(set(phones))


def resolution_message(reference: str, subject: str, action_taken: str | None) -> str:
    action = (action_taken or "").strip() or "ikibazo cyakurikiranywe"
    return f"CS-IRCFS: {reference} ({subject}) cyakemuwe. Icyakozwe: {action[:300]}. Murakoze kudufasha gukurikirana."
