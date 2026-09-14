from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from app.core.config import get_settings
from app.db.models import UserRole


@dataclass(frozen=True)
class Principal:
    name: str
    role: UserRole


def get_current_principal(x_api_key: str | None = Header(default=None)) -> Principal:
    """Authenticate API clients when protection is enabled in the environment.

    Local development is intentionally open. In pilot/production set REQUIRE_API_KEY=true
    and API_KEY_ROLES to comma-separated `secret:role` pairs.
    """
    settings = get_settings()
    if settings.environment == "development" and not settings.require_api_key:
        return Principal(name="local-development", role=UserRole.administrator)
    role_value = settings.configured_api_keys.get(x_api_key or "")
    if not role_value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Valid API key required")
    try:
        return Principal(name="api-client", role=UserRole(role_value))
    except ValueError as error:
        raise HTTPException(status_code=500, detail="Invalid API key role configuration") from error


def require_roles(*allowed_roles: UserRole):
    def verify(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role permission")
        return principal

    return verify
