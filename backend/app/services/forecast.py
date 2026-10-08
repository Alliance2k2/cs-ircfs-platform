"""7-day rainfall forecast per sector from Open-Meteo (free, no API key).

Citizen rain gauges tell us what already fell; the forecast tells farmers what is coming,
so irrigation advice can look ahead. One request covers every sector. Results are cached,
and any failure returns no forecast: advice then falls back to the gauges alone.
"""
import logging
import time

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_SECONDS = 3 * 3600
RETRY_AFTER_FAILURE_SECONDS = 15 * 60
_cache: dict[tuple, tuple[float, dict]] = {}


def rainfall_forecast(points: dict[int, tuple[float, float]]) -> dict[int, float]:
    """Return {key: forecast rainfall in mm over the next 7 days} for {key: (latitude, longitude)}."""
    if not points or not get_settings().weather_forecast_enabled:
        return {}
    keys = sorted(points)
    cache_key = tuple((key, round(points[key][0], 3), round(points[key][1], 3)) for key in keys)
    cached = _cache.get(cache_key)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    try:
        response = httpx.get(FORECAST_URL, timeout=6, params={
            "latitude": ",".join(f"{points[key][0]:.4f}" for key in keys),
            "longitude": ",".join(f"{points[key][1]:.4f}" for key in keys),
            "daily": "precipitation_sum", "forecast_days": 7, "timezone": "Africa/Kigali",
        })
        response.raise_for_status()
        body = response.json()
        locations = body if isinstance(body, list) else [body]
        result = {key: round(sum(value or 0 for value in location["daily"]["precipitation_sum"]), 1) for key, location in zip(keys, locations)}
        _cache[cache_key] = (time.monotonic() + CACHE_SECONDS, result)
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
        logger.warning("Rainfall forecast unavailable: %s", error)
        result = {}
        _cache[cache_key] = (time.monotonic() + RETRY_AFTER_FAILURE_SECONDS, result)
    return result
