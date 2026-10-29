"""Plausibility limits and gauge-aware rainfall aggregation."""
from datetime import datetime, timezone
from typing import Hashable, Iterable

MAX_READING_MM = 300.0
MAX_DAILY_GAUGE_MM = 300.0
MAX_WINDOW_GAUGE_MM = 2100.0


def cap_reading(mm: float | int | None) -> float | None:
    """Clamp a report reading so one malformed value cannot dominate advice."""
    if mm is None:
        return None
    value = float(mm)
    if value < 0:
        return 0.0
    return min(value, MAX_READING_MM)


def aggregate_gauges(rows: Iterable[tuple[Hashable, datetime | None, float | int | None]]) -> tuple[dict[Hashable, float], dict[Hashable, int]]:
    """Aggregate gauge readings with daily and seven-day-style window caps.

    Each gauge is identified by a caller-provided key (usually reporter/cell pair).
    Reports are capped per reading and once per UTC day, then the gauge window total
    is capped to the biological maximum represented by 300 mm per day for 7 days.
    """
    daily: dict[tuple[Hashable, object], float] = {}
    counts: dict[Hashable, int] = {}
    gauge_totals: dict[Hashable, float] = {}

    for key, created_at, mm in rows:
        value = cap_reading(mm)
        if value is None:
            continue
        created_at = created_at or datetime.now(timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        day = created_at.astimezone(timezone.utc).date()
        daily_key = (key, day)
        accepted = min(value, max(0.0, MAX_DAILY_GAUGE_MM - daily.get(daily_key, 0.0)))
        if accepted <= 0:
            continue
        daily[daily_key] = daily.get(daily_key, 0.0) + accepted
        counts[key] = counts.get(key, 0) + 1
        gauge_totals[key] = min(MAX_WINDOW_GAUGE_MM, gauge_totals.get(key, 0.0) + accepted)

    return gauge_totals, counts
