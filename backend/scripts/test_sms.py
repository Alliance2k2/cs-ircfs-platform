"""Send one test SMS through Africa's Talking using the settings in .env (the API key is never printed).

Usage:  python scripts/test_sms.py +250788123456 ["Optional message"]
With the sandbox username, the message appears in the Africa's Talking simulator, not on a real phone.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make the `app` package importable

from app.core.config import get_settings  # noqa: E402
from app.services.sms import api_base, is_valid_phone, normalise_phone, send_sms  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    settings = get_settings()
    phone = normalise_phone(sys.argv[1])
    if not is_valid_phone(phone):
        raise SystemExit(f"Not a valid phone number: {sys.argv[1]}")
    print("SMS provider:   ", settings.sms_provider)
    print("Username:       ", settings.africas_talking_username or "(empty)")
    print("API key set:    ", "yes" if settings.africas_talking_api_key.strip() else "NO")
    print("Sender ID:      ", settings.sms_sender_id or "(none - Africa's Talking default)")
    print("Endpoint:       ", api_base())
    if settings.sms_provider != "africas_talking":
        raise SystemExit("Set SMS_PROVIDER=africas_talking in .env first.")
    message = sys.argv[2] if len(sys.argv) > 2 else "CS-IRCFS: ubutumwa bw'igerageza. Murakoze! (test message)"
    result = send_sms(phone, message)
    print("Result:         ", result["status"], "-", result.get("detail") or result.get("provider_id"))


if __name__ == "__main__":
    main()
