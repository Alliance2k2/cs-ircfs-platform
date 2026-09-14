"""Verify the loopback production API using configured credentials."""
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.core.config import get_settings


def main() -> None:
    url = "http://127.0.0.1:8002/api/v1/analytics/dashboard-summary"
    try:
        urlopen(url, timeout=5)
    except HTTPError as error:
        print("Unauthenticated status:", error.code)
    key = next(iter(get_settings().configured_api_keys), None)
    if not key:
        raise RuntimeError("No API key configured")
    for path in ("analytics/dashboard-summary", "analytics/act-now", "users", "irrigation-schemes", "citizen-reports", "irrigation-reports", "feedback", "map-data"):
        request = Request(f"http://127.0.0.1:8002/api/v1/{path}", headers={"X-API-Key": key, "Origin": "http://127.0.0.1:8080"})
        try:
            with urlopen(request, timeout=5) as response:
                data = json.load(response)
                print(path, response.status, "records:", len(data) if isinstance(data, list) else "object")
                if path == "analytics/dashboard-summary":
                    print("Browser origin allowed:", response.headers.get("Access-Control-Allow-Origin"))
                    print("Dashboard summary:", data)
                if path == "irrigation-schemes":
                    print("Scheme choices:", [(item["name"], item["is_active"]) for item in data])
        except HTTPError as error:
            print(path, error.code)


if __name__ == "__main__":
    main()
