from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service=get_settings().app_name)


@router.get("/api/v1/auth-status")
def auth_status() -> dict[str, bool]:
    """Report configuration presence without revealing credentials."""
    return {"api_keys_configured": bool(get_settings().configured_api_keys)}
