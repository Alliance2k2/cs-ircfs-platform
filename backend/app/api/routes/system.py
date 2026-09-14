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
    settings = get_settings()
    return {
        "api_key_roles_present": bool(settings.api_key_roles.strip()),
        "api_keys_configured": bool(settings.configured_api_keys),
    }
