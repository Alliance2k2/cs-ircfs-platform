import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AuthSession, PlatformAccount, UserRole
from app.db.session import get_db


@dataclass(frozen=True)
class Principal:
    name: str
    role: UserRole
    account_id: int | None = None
    sector_ids: frozenset[int] | None = None  # None = whole district


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def account_for_token(db: Session, token: str) -> PlatformAccount | None:
    """Resolve a bearer token to an active account, or None if unknown or expired."""
    if not token:
        return None
    session = db.query(AuthSession).filter(AuthSession.token_hash == hash_token(token)).one_or_none()
    if session is None:
        return None
    expires_at = session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    account = db.get(PlatformAccount, session.account_id)
    return account if account and account.status == "active" else None


def get_current_principal(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Principal:
    """Authenticate a signed-in person (Bearer session) or a service (X-API-Key).

    Local development is intentionally open. In pilot/production set REQUIRE_API_KEY=true;
    people then sign in with their platform account, and integrations use API_KEY_ROLES.
    """
    settings = get_settings()
    if settings.environment == "development" and not settings.require_api_key:
        return Principal(name="local-development", role=UserRole.administrator)
    if authorization and authorization.lower().startswith("bearer "):
        account = account_for_token(db, authorization[7:].strip())
        if account is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Your session has expired. Please sign in again.")
        role = UserRole(account.role)
        sectors = frozenset(account.sector_ids) if role != UserRole.administrator and account.sector_ids else None
        return Principal(name=account.email, role=role, account_id=account.id, sector_ids=sectors)
    role_value = settings.configured_api_keys.get(x_api_key or "")
    if not role_value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in or provide a valid API key")
    try:
        return Principal(name="api-client", role=UserRole(role_value))
    except ValueError as error:
        raise HTTPException(status_code=500, detail="Invalid API key role configuration") from error


def require_roles(*allowed_roles: UserRole):
    def verify(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Your role ({principal.role.value.replace('_', ' ')}) cannot use this feature")
        return principal

    return verify
