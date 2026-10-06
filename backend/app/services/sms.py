import httpx
from app.core.config import get_settings

def send_sms(phone_number: str, message: str) -> dict:
    settings = get_settings()
    if settings.sms_provider != "africas_talking":
        return {"status": "dry_run", "detail": "SMS provider is not configured"}
    response = httpx.post("https://api.africastalking.com/version1/messaging", data={"username": settings.africas_talking_username, "to": phone_number, "message": message, "from": settings.sms_sender_id}, headers={"apiKey": settings.africas_talking_api_key, "Accept": "application/json"}, timeout=20)
    response.raise_for_status()
    return response.json()
