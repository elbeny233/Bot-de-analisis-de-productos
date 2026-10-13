from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from statistics import median

from sqlalchemy import select

from radar.database.models import PriceObservation, utc_now


def as_utc(value: datetime) -> datetime:
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def percentage_change(current: Decimal, baseline: Decimal) -> Decimal | None:
    if baseline <= 0:
        return None
    return ((current - baseline) / baseline * 100).quantize(Decimal("0.01"))


@dataclass(frozen=True)
class HistorySummary:
    currency: str
    is_simulated: bool
    count: int
    latest: Decimal | None
    minimum: Decimal | None
    maximum: Decimal | None
    average: Decimal | None
    median: Decimal | None
    period_start: datetime | None
    period_end: datetime | None
    changes: dict[str, Decimal | None]
    baseline_dates: dict[str, datetime | None]


def observations_for(session, product_id, currency, is_simulated, as_of=None):
    return session.scalars(
        select(PriceObservation)
        .where(
            PriceObservation.product_id == product_id,
            PriceObservation.currency == currency,
            PriceObservation.is_simulated.is_(is_simulated),
            PriceObservation.observed_at <= as_utc(as_of or utc_now()).replace(tzinfo=None),
        )
        .order_by(PriceObservation.observed_at, PriceObservation.id)
    ).all()


def summarize(session, product_id, currency="MXN", is_simulated=False, as_of=None):
    as_of = as_utc(as_of or utc_now())
    rows = observations_for(session, product_id, currency, is_simulated, as_of)
    changes = {key: None for key in ("24h", "7d", "30d")}
    dates = changes.copy()
    if not rows:
        return HistorySummary(
            currency, is_simulated, 0, None, None, None, None, None, None, None, changes, dates
        )
    values = [row.price for row in rows]
    for label, days in [("24h", 1), ("7d", 7), ("30d", 30)]:
        eligible = [row for row in rows if as_utc(row.observed_at) <= as_of - timedelta(days=days)]
        if eligible and eligible[-1].id != rows[-1].id:
            baseline = eligible[-1]
            changes[label] = percentage_change(rows[-1].price, baseline.price)
            dates[label] = as_utc(baseline.observed_at)
    return HistorySummary(
        currency,
        is_simulated,
        len(rows),
        rows[-1].price,
        min(values),
        max(values),
        (sum(values) / len(values)).quantize(Decimal("0.01")),
        Decimal(median(values)).quantize(Decimal("0.01")),
        as_utc(rows[0].observed_at),
        as_utc(rows[-1].observed_at),
        changes,
        dates,
    )
