from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """Settings loaded from environment variables or a local .env file."""

    app_name: str = "CS-IRCFS Platform API"
    environment: str = "development"
    database_url: str = "sqlite:///./cs_ircfs.db"
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080,http://127.0.0.1:8080"
    require_api_key: bool = False
    api_key_roles: str = ""
    log_level: str = "INFO"
    sms_provider: str = "dry_run"
    africas_talking_username: str = ""
    africas_talking_api_key: str = ""
    sms_sender_id: str = ""  # only set once Africa's Talking approves the sender ID
    google_client_id: str = ""
    session_hours: int = 12
    # Local HTTP development sets COOKIE_SECURE=false; every deployed environment must use HTTPS.
    cookie_secure: bool = False
    # Field channels (architecture Section 4): USSD short code and SMS keyword number.
    ussd_service_code: str = "*801#"
    sms_shortcode: str = "8448"
    # Airtime incentive (architecture Section 8.1): reward every N weather/infrastructure reports.
    airtime_provider: str = "dry_run"
    incentive_amount_rwf: int = 100
    incentive_every_n_reports: int = 3
    # Which field reports count towards the reward (comma-separated: rainfall, infrastructure,
    # nutrition). Nutrition surveys are incentivised per the concept (Module 1) but are capped
    # at INCENTIVE_NUTRITION_PER_MONTH rewards per household per month to prevent abuse.
    incentive_report_types: str = "rainfall,infrastructure,nutrition"
    incentive_nutrition_per_month: int = 1
    # Irrigation Scheduling Assistant thresholds (7-day rainfall, mm). Calibrate these against
    # PADAB (Mwesa Valley) and APEFA (Ngeruka/Mareba) historical records — Section 9.2.
    dry_spell_threshold_mm: float = 10.0
    wet_spell_threshold_mm: float = 40.0
    # Staff alerts: comma-separated phone numbers that get an SMS when a case opens at or
    # above ALERT_MIN_PRIORITY ("critical" or "high"). Empty means no alerts.
    # Add the Open-Meteo 7-day rainfall forecast to irrigation advice (needs internet; free, no key).
    weather_forecast_enabled: bool = True
    # In-process weekly advice scheduler (WP2): off by default. scripts/send_weekly_advice.py
    # covers cron/Task Scheduler; this flag additionally runs the same idempotent send from
    # the API process at ADVICE_SCHEDULE_TIME on ADVICE_SCHEDULE_WEEKDAY (Africa/Kigali).
    advice_schedule_enabled: bool = False
    advice_schedule_weekday: str = "mon"  # mon..sun
    advice_schedule_time: str = "06:00"   # HH:MM, 24h, Africa/Kigali
    # Cooperative pilot and Data Champion training targets (WP5, Section 8). The
    # concept sets these two figures; change them here if the pilot plan changes.
    monitor_training_target: int = 200
    pilot_cooperative_target: int = 3
    # Recurring-bottleneck rule (WP7, Section 9.3): a category is auto-flagged on a
    # scheme when it reaches MIN_COUNT reports within WINDOW_DAYS, optionally also
    # holding at least MIN_SHARE of that scheme's reports (0 disables the share check),
    # and — when an AfDB baseline was imported — only above the historical baseline.
    # CATEGORY_MIN_COUNTS overrides per category, e.g. "technical:4,social:2".
    bottleneck_window_days: int = 90
    bottleneck_min_count: int = 3
    bottleneck_min_share: float = 0.0
    bottleneck_category_min_counts: str = ""
    alert_phone_numbers: str = ""
    alert_min_priority: str = "critical"
    # Gateway callbacks (USSD/SMS) are public URLs. Africa's Talking does not sign its
    # callbacks, so the callback URLs carry a shared secret: configure them in the
    # Africa's Talking dashboard as https://<host>/api/v1/ussd?token=<GATEWAY_CALLBACK_TOKEN>.
    # Required in production. GATEWAY_ALLOWED_IPS optionally adds a comma-separated
    # allow-list of the provider's callback addresses.
    gateway_callback_token: str = ""
    gateway_allowed_ips: str = ""

    # The project-root .env, found from this file so scripts work from any folder.
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[3] / ".env", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    def guard_runtime(self) -> None:
        """Refuse to start a deployment that is misconfigured as a local development server.

        Raises RuntimeError for every combination that must never reach production.
        """
        if self.environment != "production":
            return
        if not self.require_api_key:
            raise RuntimeError("ENVIRONMENT=production requires REQUIRE_API_KEY=true")
        if self.database_url.startswith("sqlite"):
            raise RuntimeError("ENVIRONMENT=production requires a PostgreSQL DATABASE_URL, not SQLite")
        if not self.cookie_secure:
            raise RuntimeError("ENVIRONMENT=production requires COOKIE_SECURE=true (sessions must only travel over HTTPS)")
        local = [origin for origin in self.allowed_origins if "localhost" in origin or "127.0.0.1" in origin]
        if local:
            raise RuntimeError(f"ENVIRONMENT=production must not allow local CORS origins: {', '.join(local)}")
        if len(self.gateway_callback_token.strip()) < 24:
            raise RuntimeError("ENVIRONMENT=production requires GATEWAY_CALLBACK_TOKEN (at least 24 characters)")

    @property
    def dev_auth_bypass(self) -> bool:
        """True when local development skips sign-in entirely."""
        return self.environment == "development" and not self.require_api_key

    @property
    def bottleneck_category_counts(self) -> dict[str, int]:
        """Per-category minimum counts, e.g. "technical:4,social:2"."""
        counts: dict[str, int] = {}
        for item in self.bottleneck_category_min_counts.split(","):
            category, separator, value = item.strip().partition(":")
            if separator and category.strip() and value.strip().isdigit():
                counts[category.strip()] = int(value)
        return counts

    @property
    def gateway_ips(self) -> set[str]:
        return {item.strip() for item in self.gateway_allowed_ips.split(",") if item.strip()}

    @property
    def incentive_types(self) -> set[str]:
        """The report types that count towards an airtime reward."""
        return {item.strip().lower() for item in self.incentive_report_types.split(",") if item.strip()}

    @property
    def allowed_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        if self.environment == "development" and "http://127.0.0.1:8080" not in origins:
            origins.append("http://127.0.0.1:8080")
        return origins

    @property
    def configured_api_keys(self) -> dict[str, str]:
        """Parse role pairs or a single administrator key without exposing secrets."""
        pairs: dict[str, str] = {}
        raw = self.api_key_roles.strip()
        if raw.startswith("API_KEY_ROLES="):
            raw = raw.removeprefix("API_KEY_ROLES=").strip()
        raw = raw.strip("\"'")
        for item in raw.split(","):
            item = item.strip().strip("\"'")
            if ":" in item:
                key, role = item.rsplit(":", 1)
            elif "," not in raw:
                key, role = item, "administrator"
            else:
                continue
            if key.strip() and role.strip():
                pairs[key.strip()] = role.strip()
        return pairs


@lru_cache
def get_settings() -> Settings:
    return Settings()
