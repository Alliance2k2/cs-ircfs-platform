"""Authentication and platform-account schemas.

These describe web dashboard staff (``platform_accounts``). Field users are described
separately in :mod:`app.schemas.field_users`.
"""
from datetime import datetime

from pydantic import BaseModel, Field

from app.db.models import UserRole


class AccountRegister(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=200)
    first_name: str = Field(min_length=1, max_length=80)
    middle_name: str | None = Field(default=None, max_length=80)
    surname: str = Field(min_length=1, max_length=80)


class AccountLogin(BaseModel):
    email: str
    password: str


class AccountRead(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    status: str
    created_at: datetime
    sector_ids: list[int] = []  # empty = whole district
    model_config = {"from_attributes": True}


class AccountUpdate(BaseModel):
    role: UserRole | None = None
    status: str | None = Field(default=None, pattern="^(active|pending|suspended)$")
    sector_ids: list[int] | None = None  # [] = whole district
