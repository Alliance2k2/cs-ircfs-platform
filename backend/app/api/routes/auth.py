import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import account_for_token, hash_token, require_roles
from app.db.models import AuthSession, PlatformAccount, UserRole
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


def account_payload(account: PlatformAccount) -> dict:
    return {"id": account.id, "email": account.email, "full_name": account.full_name, "role": account.role, "status": account.status}


def start_session(db: Session, account: PlatformAccount) -> dict:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=get_settings().session_hours)
    db.add(AuthSession(token_hash=hash_token(token), account_id=account.id, expires_at=expires_at))
    db.commit()
    return {"access_token": token, "token_type": "bearer", "expires_at": expires_at, "account": account_payload(account)}


def bearer(authorization: str | None) -> str:
    return authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else ""


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
    # Self-registration always starts with the least-privileged web role. An administrator
    # promotes planners and officers from Platform Management > Accounts.
    account = PlatformAccount(email=email, password_hash=hash_password(payload.password), full_name=full_name,
                              role=UserRole.citizen_science_monitor, status="active")
    db.add(account); db.commit(); db.refresh(account)
    return {"id": account.id, "email": account.email, "status": account.status, "role": account.role}


@router.post("/login")
def login(payload: AccountLogin, db: Session = Depends(get_db)):
    account = db.scalar(select(PlatformAccount).where(PlatformAccount.email == payload.email.strip().lower()))
    if not account or account.status != "active" or not verify_password(payload.password, account.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return start_session(db, account)


@router.post("/google")
def google_login(payload: GoogleLogin, db: Session = Depends(get_db)):
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
                                  role=UserRole.citizen_science_monitor, status="active")
        db.add(account); db.commit(); db.refresh(account)
    if account.status != "active":
        raise HTTPException(403, "This account is not active")
    return start_session(db, account)


@router.get("/me")
def me(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    account = account_for_token(db, bearer(authorization))
    if not account:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in required")
    return account_payload(account)


@router.post("/logout")
def logout(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    token = bearer(authorization)
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == hash_token(token)))
        db.commit()
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
    db.commit(); db.refresh(account)
    return account
