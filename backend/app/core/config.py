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
    sms_sender_id: str = "CS-IRCFS"
    google_client_id: str = ""
    session_hours: int = 12
    # Field channels (architecture Section 4): USSD short code and SMS keyword number.
    ussd_service_code: str = "*801#"
    sms_shortcode: str = "8448"
    # Airtime incentive (architecture Section 8.1): reward every N weather/infrastructure reports.
    airtime_provider: str = "dry_run"
    incentive_amount_rwf: int = 100
    incentive_every_n_reports: int = 3
    # Irrigation Scheduling Assistant thresholds (7-day rainfall, mm). Calibrate these against
    # PADAB (Mwesa Valley) and APEFA (Ngeruka/Mareba) historical records — Section 9.2.
    dry_spell_threshold_mm: float = 10.0
    wet_spell_threshold_mm: float = 40.0

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
