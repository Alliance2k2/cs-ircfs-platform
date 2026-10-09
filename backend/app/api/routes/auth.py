"""Authentication for web dashboard staff (platform accounts).

Sign-in sets an httpOnly session cookie for browsers and also returns the bearer token
for API clients. Logout clears the cookie and deletes the stored session.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.ratelimit import limiter
from app.core.security import SESSION_COOKIE, account_for_token, hash_token, require_roles
from app.db.models import AuthSession, PlatformAccount, Sector, UserRole
from app.db.session import get_db
from app.schemas import AccountLogin, AccountRead, AccountRegister, AccountUpdate

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
admin = Depends(require_roles(UserRole.administrator))


class GoogleLogin(BaseModel):
    credential: str = Field(min_length=20)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
    return f"pbkdf2$210000${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        _, rounds, salt, digest = encoded.split("$")
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds)).hex()
        return hmac.compare_digest(candidate, digest)
    except (ValueError, TypeError):
        return False


PENDING = "pending"


def refuse_inactive(account: PlatformAccount) -> None:
    """Stop a pending or suspended account from signing in, saying which it is."""
    if account.status == PENDING:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your account is waiting for approval by a district administrator")
    if account.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is suspended")


def account_payload(account: PlatformAccount) -> dict:
    district_wide = account.role == UserRole.administrator or not account.sectors
    return {"id": account.id, "email": account.email, "full_name": account.full_name, "role": account.role, "status": account.status,
            "sector_ids": [] if district_wide else account.sector_ids, "area": "Bugesera District" if district_wide else ", ".join(s.name for s in account.sectors)}


def start_session(db: Session, account: PlatformAccount) -> dict:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=get_settings().session_hours)
    db.add(AuthSession(token_hash=hash_token(token), account_id=account.id, expires_at=expires_at))
    db.commit()
    return {"access_token": token, "token_type": "bearer", "expires_at": expires_at, "account": account_payload(account)}


def set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


def bearer(authorization: str | None) -> str:
    return authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else ""


def request_token(authorization: str | None, cookie: str | None) -> str:
    return bearer(authorization) or (cookie or "")


@router.get("/config")
def auth_config() -> dict:
    """Public sign-in settings for the login page (no secrets)."""
    return {"google_client_id": get_settings().google_client_id.strip() or None}


@router.post("/register", status_code=201)
def register(payload: AccountRegister, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if db.scalar(select(PlatformAccount).where(PlatformAccount.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    full_name = " ".join(part for part in (payload.first_name, payload.middle_name, payload.surname) if part)
    # Self-registration starts with the least-privileged web role and waits for approval:
    # monitors can read field records, so an open sign-up must not grant access by itself.
    # An administrator activates the account and promotes planners and officers from
    # Platform Management > Accounts.
    account = PlatformAccount(email=email, password_hash=hash_password(payload.password), full_name=full_name,
                              role=UserRole.citizen_science_monitor, status=PENDING)
    db.add(account)
    db.commit()
    db.refresh(account)
    return {"id": account.id, "email": account.email, "status": account.status, "role": account.role}


@router.post("/login")
@limiter.limit("10/minute")
def login(payload: AccountLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    account = db.scalar(select(PlatformAccount).where(PlatformAccount.email == payload.email.strip().lower()))
    if not account or not verify_password(payload.password, account.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    # The status is only revealed to someone who knows the password.
    refuse_inactive(account)
    session = start_session(db, account)
    set_session_cookie(response, session["access_token"])
    return session


@router.post("/google")
def google_login(payload: GoogleLogin, response: Response, db: Session = Depends(get_db)):
    client_id = get_settings().google_client_id.strip()
    if not client_id:
        raise HTTPException(503, "Google sign-in is not configured")
    try:
        # Imported lazily so the platform still starts when google-auth is not installed.
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token
        claims = id_token.verify_oauth2_token(payload.credential, google_requests.Request(), client_id)
    except ImportError as exc:
        raise HTTPException(503, "Google sign-in library is not installed on the server") from exc
    except Exception as exc:
        raise HTTPException(401, "Invalid Google sign-in") from exc
    email = str(claims.get("email", "")).strip().lower()
    if not email or not claims.get("email_verified"):
        raise HTTPException(401, "A verified Google email is required")
    account = db.scalar(select(PlatformAccount).where(PlatformAccount.email == email))
    if not account:
        account = PlatformAccount(email=email, password_hash=hash_password(secrets.token_urlsafe(32)), full_name=claims.get("name") or email.split("@")[0],
                                  role=UserRole.citizen_science_monitor, status=PENDING)
        db.add(account)
        db.commit()
        db.refresh(account)
    refuse_inactive(account)
    session = start_session(db, account)
    set_session_cookie(response, session["access_token"])
    return session


@router.get("/me")
def me(authorization: str | None = Header(default=None), session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE), db: Session = Depends(get_db)):
    account = account_for_token(db, request_token(authorization, session_cookie))
    if not account:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in required")
    if account.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is suspended")
    return account_payload(account)


@router.post("/logout")
def logout(response: Response, authorization: str | None = Header(default=None), session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE), db: Session = Depends(get_db)):
    token = request_token(authorization, session_cookie)
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == hash_token(token)))
        db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/accounts", response_model=list[AccountRead])
def list_accounts(db: Session = Depends(get_db), _: object = admin):
    return list(db.scalars(select(PlatformAccount).order_by(PlatformAccount.id.desc())))


@router.patch("/accounts/{account_id}", response_model=AccountRead)
def update_account(account_id: int, payload: AccountUpdate, db: Session = Depends(get_db), _: object = admin):
    account = db.get(PlatformAccount, account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    if payload.role is not None:
        account.role = payload.role
    if payload.status is not None:
        account.status = payload.status
        if payload.status != "active":
            db.execute(delete(AuthSession).where(AuthSession.account_id == account.id))
    if payload.sector_ids is not None:
        sectors = list(db.scalars(select(Sector).where(Sector.id.in_(payload.sector_ids)))) if payload.sector_ids else []
        if len(sectors) != len(set(payload.sector_ids)):
            raise HTTPException(422, "Unknown sector")
        account.sectors = sectors
    db.commit()
    db.refresh(account)
    return account
