"""Outbound SMS and airtime through Africa's Talking, with a safe dry-run default."""
import logging
import re

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AdvisoryMessage

logger = logging.getLogger(__name__)
PHONE_PATTERN = re.compile(r"^\+?\d{9,15}$")


def normalise_phone(value: str) -> str:
    """Return an E.164-style Rwandan number: '0788 123 456' -> '+250788123456'."""
    phone = re.sub(r"[\s\-()]", "", value or "")
    if phone.startswith("07") and len(phone) == 10:
        phone = "+250" + phone[1:]
    elif phone.startswith("250"):
        phone = "+" + phone
    return phone


def is_valid_phone(value: str) -> bool:
    return bool(PHONE_PATTERN.match(value or ""))


def send_sms(phone_number: str, message: str) -> dict:
    """Send one SMS. Never raises: provider errors come back as status 'failed'."""
    settings = get_settings()
    if settings.sms_provider != "africas_talking":
        return {"status": "dry_run", "detail": "SMS provider is not configured"}
    try:
        response = httpx.post(
            "https://api.africastalking.com/version1/messaging",
            data={"username": settings.africas_talking_username, "to": phone_number, "message": message, "from": settings.sms_sender_id},
            headers={"apiKey": settings.africas_talking_api_key, "Accept": "application/json"},
            timeout=20,
        )
        response.raise_for_status()
        body = response.json()
        recipients = body.get("SMSMessageData", {}).get("Recipients", [])
        provider_id = recipients[0].get("messageId") if recipients else None
        return {"status": "sent", "provider_id": provider_id, "provider_response": body}
    except (httpx.HTTPError, ValueError) as error:
        logger.warning("SMS delivery failed: %s", error)
        return {"status": "failed", "detail": "SMS provider rejected or did not answer the request"}


def deliver(db: Session, phone_number: str, message: str, purpose: str, cell_id: int | None = None) -> AdvisoryMessage:
    """Send an SMS and log it in advisory_messages. The caller commits."""
    result = send_sms(phone_number, message)
    record = AdvisoryMessage(
        phone_number=phone_number, message=message, status=result["status"],
        provider_id=result.get("provider_id"), purpose=purpose, cell_id=cell_id,
    )
    db.add(record)
    return record


def send_airtime(phone_number: str, amount_rwf: int) -> dict:
    """Send an airtime top-up. Never raises: provider errors come back as status 'failed'."""
    settings = get_settings()
    if settings.airtime_provider != "africas_talking":
        return {"status": "dry_run", "detail": "Airtime provider is not configured"}
    try:
        response = httpx.post(
            "https://api.africastalking.com/version1/airtime/send",
            data={"username": settings.africas_talking_username, "recipients": f'[{{"phoneNumber":"{phone_number}","amount":"RWF {amount_rwf}"}}]'},
            headers={"apiKey": settings.africas_talking_api_key, "Accept": "application/json"},
            timeout=20,
        )
        response.raise_for_status()
        body = response.json()
        responses = body.get("responses", [])
        return {"status": "sent", "provider_id": responses[0].get("requestId") if responses else None}
    except (httpx.HTTPError, ValueError) as error:
        logger.warning("Airtime delivery failed: %s", error)
        return {"status": "failed", "detail": "Airtime provider rejected or did not answer the request"}
