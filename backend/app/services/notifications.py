"""Closing-the-Loop SMS (architecture Module 3): tell the affected cell what action was taken."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Cell, User
from app.services.sms import deliver


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


def resolution_message(reference: str, subject: str, action_taken: str | None) -> str:
    action = (action_taken or "").strip() or "ikibazo cyakurikiranywe"
    return f"CS-IRCFS: {reference} ({subject}) cyakemuwe. Icyakozwe: {action[:300]}. Murakoze kudufasha gukurikirana."
