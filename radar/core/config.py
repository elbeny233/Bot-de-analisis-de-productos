from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RADAR_", env_file=".env", extra="ignore")

    app_name: str = "Radar Ofertas VIP"
    database_url: str = "sqlite:///./data/radar.db"
    monitor_interval_minutes: int = Field(default=30, ge=1, le=10080)
    scheduler_enabled: bool = True
    monitor_max_attempts: int = Field(default=3, ge=1, le=5)
    monitor_retry_seconds: float = Field(default=1, ge=0.1, le=30)
    monitor_pause_after_failures: int = Field(default=3, ge=1, le=10)
    publications_enabled: bool = False
    log_level: str = "INFO"

    @field_validator("database_url")
    @classmethod
    def validate_database(cls, value: str) -> str:
        url = make_url(value)
        if url.drivername != "sqlite" or not url.database:
            raise ValueError(
                "El desarrollo local admite únicamente SQLite con una base de datos definida"
            )
        return value

    @field_validator("publications_enabled")
    @classmethod
    def disable_publications(cls, value: bool) -> bool:
        if value:
            raise ValueError("Las publicaciones externas no están habilitadas en esta fase")
        return value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        value = value.upper()
        if value not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("Nivel de registro inválido")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
