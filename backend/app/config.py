from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://injury_risk:dev_password@localhost:5432/injury_risk_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # App
    secret_key: str = "dev-secret-key-change-in-production"
    debug: bool = True
    environment: Literal["development", "staging", "production"] = "development"

    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:8000"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    # Risk Score Thresholds
    risk_threshold_green_max: int = 35
    risk_threshold_yellow_max: int = 60
    # Above yellow_max is red


@lru_cache
def get_settings() -> Settings:
    return Settings()
