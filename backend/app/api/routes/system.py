from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.metrics import snapshot
from app.db.models import AdvisoryMessage, InboundMessage
from app.db.session import get_db
from app.schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service=get_settings().app_name)


@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)) -> dict[str, str]:
    """Readiness probe: the process is ready only when it can query its database."""
    try:
        db.execute(text("SELECT 1")).scalar_one()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Database is unavailable") from exc
    return {"status": "ready", "database": "ok"}


@router.get("/metrics")
def operational_metrics(db: Session = Depends(get_db)) -> dict:
    """Operational JSON metrics for dashboards and simple alert probes."""
    outbound_statuses = dict(db.execute(
        select(AdvisoryMessage.status, func.count(AdvisoryMessage.id))
        .group_by(AdvisoryMessage.status)
    ).all())
    inbound_total = db.scalar(select(func.count()).select_from(InboundMessage)) or 0
    return {
        "database": "ok",
        "inbound_messages_total": inbound_total,
        "outbound_delivery_total": outbound_statuses,
        **snapshot(),
    }


@router.get("/api/v1/auth-status")
def auth_status() -> dict[str, bool]:
    """Report configuration presence without revealing credentials."""
    settings = get_settings()
    return {
        "api_key_roles_present": bool(settings.api_key_roles.strip()),
        "api_keys_configured": bool(settings.configured_api_keys),
    }
