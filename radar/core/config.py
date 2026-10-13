from decimal import Decimal
from functools import lru_cache

from pydantic import Field, field_validator, model_validator
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
    analysis_reference_days: int = Field(default=30, ge=7, le=365)
    analysis_min_observations: int = Field(default=5, ge=2, le=1000)
    analysis_min_history_days: int = Field(default=7, ge=1, le=365)
    analysis_min_distinct_days: int = Field(default=3, ge=2, le=365)
    analysis_max_age_hours: Decimal = Field(default=Decimal("24"), gt=0, le=168)
    analysis_min_discount_percent: Decimal = Field(default=Decimal("10"), gt=0, le=100)
    analysis_full_discount_percent: Decimal = Field(default=Decimal("50"), gt=0, le=100)
    analysis_anomaly_drop_percent: Decimal = Field(default=Decimal("80"), gt=0, le=100)
    analysis_anomaly_rise_multiplier: Decimal = Field(default=Decimal("5"), gt=1, le=100)
    analysis_min_score: int = Field(default=70, ge=0, le=100)
    analysis_min_identity_confidence: Decimal = Field(default=Decimal("0.8"), ge=0, le=1)
    analysis_weights: dict[str, int] = Field(
        default_factory=lambda: {
            "discount": 40,
            "history": 20,
            "availability": 10,
            "freshness": 10,
            "costs": 10,
            "identity": 10,
        }
    )
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

    @field_validator("analysis_weights")
    @classmethod
    def validate_weights(cls, value):
        expected = {"discount", "history", "availability", "freshness", "costs", "identity"}
        if (
            set(value) != expected
            or any(weight < 0 for weight in value.values())
            or sum(value.values()) != 100
        ):
            raise ValueError("Los seis pesos deben ser no negativos y sumar 100")
        return value

    @model_validator(mode="after")
    def validate_history_window(self):
        if self.analysis_min_history_days > self.analysis_reference_days:
            raise ValueError("El historial mínimo no puede superar la ventana de referencia")
        if self.analysis_min_distinct_days > self.analysis_reference_days + 1:
            raise ValueError("Los días distintos deben caber en la ventana de referencia")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
