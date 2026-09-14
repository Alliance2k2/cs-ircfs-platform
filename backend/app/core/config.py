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
        """Parse `key:role,key:role` without ever exposing keys in API responses."""
        pairs: dict[str, str] = {}
        for item in self.api_key_roles.split(","):
            if ":" in item:
                key, role = item.strip().split(":", 1)
                if key and role:
                    pairs[key] = role
        return pairs


@lru_cache
def get_settings() -> Settings:
    return Settings()
