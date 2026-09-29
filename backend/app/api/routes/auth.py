import hashlib
import hmac
import secrets
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import PlatformAccount
from app.schemas import AccountLogin, AccountRegister

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
sessions: dict[str, int] = {}

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

@router.post("/register", status_code=201)
def register(payload: AccountRegister, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if db.scalar(select(PlatformAccount).where(PlatformAccount.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    full_name = " ".join(part for part in (payload.first_name, payload.middle_name, payload.surname) if part)
    account = PlatformAccount(email=email, password_hash=hash_password(payload.password), full_name=full_name, role=payload.role, status="active")
    db.add(account); db.commit(); db.refresh(account)
    return {"id": account.id, "email": account.email, "status": account.status}

@router.post("/login")
def login(payload: AccountLogin, db: Session = Depends(get_db)):
    account = db.scalar(select(PlatformAccount).where(PlatformAccount.email == payload.email.strip().lower()))
    if not account or account.status != "active" or not verify_password(payload.password, account.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    token = secrets.token_urlsafe(32); sessions[token] = account.id
    return {"access_token": token, "token_type": "bearer", "account": {"id": account.id, "email": account.email, "role": account.role}}

@router.get("/me")
def me(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    token = authorization.removeprefix("Bearer ").strip() if authorization else ""
    account_id = sessions.get(token)
    account = db.get(PlatformAccount, account_id) if account_id else None
    if not account: raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in required")
    return {"id": account.id, "email": account.email, "role": account.role}

@router.post("/logout")
def logout(authorization: str | None = Header(default=None)):
    if authorization: sessions.pop(authorization.removeprefix("Bearer ").strip(), None)
    return {"ok": True}
