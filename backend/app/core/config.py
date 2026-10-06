from functools import lru_cache

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

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

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
