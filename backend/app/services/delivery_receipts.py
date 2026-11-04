"""Monotonic application of recipient-free provider receipts."""
from datetime import datetime, timezone
from sqlalchemy import select
from app.db.models import DeliveryReceipt


def apply_receipts(db, kind, item):
    if not item.provider_id or item.status in ("queued", "dry_run", "cancelled"):
        return
    receipts = db.scalars(select(DeliveryReceipt).where(DeliveryReceipt.kind == kind,
        DeliveryReceipt.provider_id == item.provider_id, DeliveryReceipt.applied_at.is_(None)).order_by(DeliveryReceipt.id).with_for_update())
    for receipt in receipts:
        incoming = receipt.normalized_status
        if item.status != "delivered" and not (item.status == "failed" and incoming == "sent"):
            item.status = incoming
        receipt.applied_at = datetime.now(timezone.utc)
