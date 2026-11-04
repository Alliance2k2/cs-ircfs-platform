"""Explicitly opt-in temporary encrypted routing for private replies.

This is pseudonymized routing, not a claim of absolute anonymity. Keys stay outside
source control. The worker erases routing before the provider call; expired routes
are erased without dispatch. Default behavior retains the synchronous reply path.
"""
from datetime import datetime, timedelta, timezone
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import get_settings


def seal(phone):
    settings = get_settings()
    cipher = Fernet(settings.anonymous_reply_encryption_key.encode())
    return cipher.encrypt(phone.encode()).decode(), datetime.now(timezone.utc) + timedelta(seconds=settings.anonymous_reply_ttl_seconds)


def open_route(record):
    settings = get_settings()
    expires = record.private_recipient_expires_at
    if not settings.anonymous_reply_queue_enabled or not expires or expires <= datetime.now(timezone.utc):
        return None
    try:
        return Fernet(settings.anonymous_reply_encryption_key.encode()).decrypt(
            record.private_recipient.encode(), ttl=settings.anonymous_reply_ttl_seconds).decode()
    except (InvalidToken, ValueError, AttributeError, UnicodeError):
        return None
