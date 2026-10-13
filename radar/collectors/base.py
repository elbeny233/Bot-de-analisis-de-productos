from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, Field, HttpUrl, field_validator


class CollectedProduct(BaseModel):
    source_product_id: str = Field(min_length=1, max_length=200)
    variant_key: str = Field(min_length=1, max_length=300)
    name: str = Field(min_length=1, max_length=500)
    price: Decimal = Field(ge=0, max_digits=14, decimal_places=2, allow_inf_nan=False)
    currency: str = Field(default="MXN", pattern=r"^[A-Z]{3}$")
    brand: str | None = Field(default=None, max_length=150)
    model: str | None = Field(default=None, max_length=150)
    presentation: str | None = Field(default=None, max_length=200)
    category_slug: str | None = None
    seller: str | None = Field(default=None, max_length=200)
    url: HttpUrl | None = None
    available: bool | None = None
    shipping_cost: Decimal | None = Field(
        default=None, ge=0, decimal_places=2, max_digits=14, allow_inf_nan=False
    )
    conditions: str | None = Field(default=None, max_length=4000)
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("source_product_id", "variant_key", "name")
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El campo no puede estar vacío")
        return value

    @field_validator("observed_at")
    @classmethod
    def aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("La fecha de consulta debe incluir zona horaria")
        return value.astimezone(timezone.utc)


class TransientCollectorError(Exception):
    """Fallo temporal; permite reintentos limitados sin registrar datos sensibles."""


class SourceUnavailableError(Exception):
    """Fuente no disponible o no autorizada; no reintentar automáticamente."""


class Collector(Protocol):
    is_simulated: bool

    def collect(self) -> list[CollectedProduct]: ...
