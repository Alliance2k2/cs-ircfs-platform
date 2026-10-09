"""Authentication and authorisation for the platform.

Browser sessions arrive as an httpOnly cookie; API clients send a Bearer token or an
X-API-Key. Both resolve to a :class:`Principal` representing the signed-in person.
"""
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AuthSession, PlatformAccount, UserRole
from app.db.session import get_db

SESSION_COOKIE = "cs_ircfs_session"


@dataclass(frozen=True)
class Principal:
    name: str
    role: UserRole
    account_id: int | None = None
    sector_ids: frozenset[int] | None = None  # None = whole district


def hash_token(token: str) -> str:
    """The only form of a session token ever stored."""
    return hashlib.sha256(token.encode()).hexdigest()


def account_for_token(db: Session, token: str) -> PlatformAccount | None:
    """Resolve a token to its account, or None if unknown or the session has expired.

    The account status is returned as-is so callers can answer 403 for a suspended
    account instead of the 401 used for an unknown or expired session.
    """
    if not token:
        return None
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(token)))
    if session is None:
        return None
    expires_at = session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    return db.get(PlatformAccount, session.account_id)


def get_current_principal(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
) -> Principal:
    """Authenticate a signed-in person (cookie or Bearer token) or a service (X-API-Key).

    Local development is intentionally open. In pilot/production set REQUIRE_API_KEY=true;
    people then sign in with their platform account, and integrations use API_KEY_ROLES.
    """
    settings = get_settings()
    if settings.environment == "development" and not settings.require_api_key:
        return Principal(name="local-development", role=UserRole.administrator)
    token = authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else ""
    token = token or (session_cookie or "")
    if token:
        account = account_for_token(db, token)
        if account is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Your session has expired. Please sign in again.")
        if account.status != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is suspended")
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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your role ({principal.role.value.replace('_', ' ')}) cannot use this feature",
            )
        return principal

    return verify
