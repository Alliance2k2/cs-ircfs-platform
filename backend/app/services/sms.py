"""Outbound SMS and airtime through Africa's Talking, with a safe dry-run default."""
import logging
import re
from contextlib import contextmanager
from contextvars import ContextVar

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AdvisoryMessage

logger = logging.getLogger(__name__)
# E.164: a leading "+", a non-zero country code, 9-15 digits in total.
PHONE_PATTERN = re.compile(r"^\+[1-9]\d{8,14}$")
WITHHELD = "withheld"  # same value as app.core.privacy.WITHHELD

# Set while the phone simulator runs: nothing reaches a telecom provider, whatever the
# SMS_PROVIDER and AIRTIME_PROVIDER settings say (staff alerts and rewards included).
_simulating: ContextVar[bool] = ContextVar("simulating", default=False)


@contextmanager
def simulation():
    """Run a block with all SMS and airtime forced to dry-run."""
    token = _simulating.set(True)
    try:
        yield
    finally:
        _simulating.reset(token)


def live(provider: str) -> bool:
    """True only when the provider is configured and live sending is allowed here.

    Outside production a live provider is refused unless ALLOW_LIVE_MESSAGES=true, so a
    laptop that still holds live credentials cannot text real citizens by accident.
    """
    settings = get_settings()
    if provider != "africas_talking" or _simulating.get():
        return False
    return settings.environment == "production" or settings.allow_live_messages


def normalise_phone(value: str) -> str:
    """Return an E.164 Rwandan number:'788 123 456', '0788-123-456', '00250788123456'
    and '+250 788 123 456' all become '+250788123456'.

    One canonical form matters: the phone number is the identity key, so a second spelling
    would create a second field user, a second reward history and double airtime.
    """
    text = re.sub(r"[\s\-().]", "", value or "")
    if text.startswith("00"):
        text = "+" + text[2:]
    if text.startswith("+"):
        digits = re.sub(r"\D", "", text)
        return "+" + digits if digits else ""
    digits = re.sub(r"\D", "", text)
    if len(digits) == 10 and digits.startswith("07"):
        return "+250" + digits[1:]
    if len(digits) == 9 and digits.startswith("7"):
        return "+250" + digits
    if len(digits) == 12 and digits.startswith("250"):
        return "+" + digits
    if len(digits) >= 11:
        # An international number whose "+" was lost in form encoding.
        return "+" + digits
    return digits


def is_valid_phone(value: str) -> bool:
    return bool(PHONE_PATTERN.match(value or ""))


def api_base() -> str:
    """Sandbox credentials (username 'sandbox') only work against the sandbox host."""
    sandbox = get_settings().africas_talking_username.strip().lower() == "sandbox"
    return "https://api.sandbox.africastalking.com" if sandbox else "https://api.africastalking.com"


def send_sms(phone_number: str, message: str) -> dict:
    """Send one SMS. Never raises: provider errors come back as status 'failed'."""
    settings = get_settings()
    if not live(settings.sms_provider):
        return {"status": "dry_run", "detail": "SMS provider is not configured"}
    data = {"username": settings.africas_talking_username.strip(), "to": phone_number, "message": message}
    # Only send a sender ID once Africa's Talking has approved it; an unregistered one is rejected.
    if settings.sms_sender_id.strip():
        data["from"] = settings.sms_sender_id.strip()
    try:
        response = httpx.post(f"{api_base()}/version1/messaging", data=data,
                              headers={"apiKey": settings.africas_talking_api_key.strip(), "Accept": "application/json"}, timeout=20)
        response.raise_for_status()
        body = response.json()
        recipients = body.get("SMSMessageData", {}).get("Recipients", [])
        if not recipients:
            logger.warning("SMS not accepted: %s", body.get("SMSMessageData", {}).get("Message"))
            return {"status": "failed", "detail": body.get("SMSMessageData", {}).get("Message", "No recipient accepted")}
        recipient = recipients[0]
        # 100 Processed, 101 Sent, 102 Queued; anything else (e.g. 403 InvalidPhoneNumber) is a failure.
        if recipient.get("statusCode") not in (100, 101, 102):
            logger.warning("SMS rejected for recipient: %s", recipient.get("status"))
            return {"status": "failed", "detail": recipient.get("status", "Rejected")}
        return {"status": "sent", "provider_id": recipient.get("messageId"), "cost": recipient.get("cost")}
    except (httpx.HTTPError, ValueError) as error:
        logger.warning("SMS delivery failed: %s", error)
        return {"status": "failed", "detail": "SMS provider rejected or did not answer the request"}


def deliver(db: Session, phone_number: str, message: str, purpose: str, cell_id: int | None = None,
            anonymous: bool = False) -> AdvisoryMessage:
    """Send an SMS and log it in advisory_messages. The caller commits.

    ``anonymous`` logs the message without the recipient's number, for replies that
    would otherwise tie a phone to an anonymous grievance.
    """
    result = send_sms(phone_number, message)
    record = AdvisoryMessage(
        phone_number=WITHHELD if anonymous else phone_number, message=message, status=result["status"],
        provider_id=result.get("provider_id"), purpose=purpose, cell_id=cell_id,
    )
    db.add(record)
    return record


def send_airtime(phone_number: str, amount_rwf: int) -> dict:
    """Send an airtime top-up. Never raises: provider errors come back as status 'failed'."""
    settings = get_settings()
    if not live(settings.airtime_provider):
        return {"status": "dry_run", "detail": "Airtime provider is not configured"}
    try:
        response = httpx.post(
            f"{api_base()}/version1/airtime/send",
            data={"username": settings.africas_talking_username.strip(), "recipients": f'[{{"phoneNumber":"{phone_number}","amount":"RWF {amount_rwf}"}}]'},
            headers={"apiKey": settings.africas_talking_api_key.strip(), "Accept": "application/json"},
            timeout=20,
        )
        response.raise_for_status()
        body = response.json()
        responses = body.get("responses", [])
        if body.get("errorMessage", "None") != "None" or (responses and responses[0].get("status") not in ("Sent", "Success")):
            logger.warning("Airtime rejected: %s", body.get("errorMessage") or responses[0].get("errorMessage"))
            return {"status": "failed", "detail": body.get("errorMessage") or responses[0].get("errorMessage")}
        return {"status": "sent", "provider_id": responses[0].get("requestId") if responses else None}
    except (httpx.HTTPError, ValueError) as error:
        logger.warning("Airtime delivery failed: %s", error)
        return {"status": "failed", "detail": "Airtime provider rejected or did not answer the request"}
