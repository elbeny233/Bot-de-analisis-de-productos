from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from statistics import median

from radar.analytics.history import as_utc
from radar.database.models import utc_now

D = Decimal


def clip(value):
    return max(D(0), min(D(1), value))


def rounded(value):
    return value.quantize(D("0.01"), rounding=ROUND_HALF_UP)


def discount_percent(current, reference):
    if reference is None or reference <= 0:
        return None
    return rounded((reference - current) / reference * 100)


@dataclass(frozen=True)
class AnalysisResult:
    reference_price: Decimal | None
    discount_percent: Decimal | None
    effective_discount_percent: Decimal | None
    advertised_discount_percent: Decimal | None
    score: int
    classification: str
    history_count: int
    history_days: Decimal
    distinct_days: int
    review_candidate: bool
    reasons: list[str]
    components: dict[str, float]


def evaluate(current, prior, settings, now=None):
    now = as_utc(now or utc_now())
    consulted = as_utc(current.observed_at)
    window_start = consulted - timedelta(days=settings.analysis_reference_days)
    history = [
        row
        for row in prior
        if row.currency == current.currency
        and row.is_simulated == current.is_simulated
        and row.product_id == current.product_id
        and window_start <= as_utc(row.observed_at) <= consulted
        and row.price > 0
        and (as_utc(row.observed_at), row.id) < (consulted, current.id)
    ]
    history.sort(key=lambda row: (as_utc(row.observed_at), row.id))
    reference = rounded(D(median([row.price for row in history]))) if history else None
    # Calidad mide el intervalo ENTRE observaciones previas, no el hueco hasta el precio actual.
    span = (
        D(
            str(
                (as_utc(history[-1].observed_at) - as_utc(history[0].observed_at)).total_seconds()
                / 86400
            )
        )
        if len(history) > 1
        else D(0)
    )
    distinct_days = len({as_utc(row.observed_at).date() for row in history})
    enough = (
        len(history) >= settings.analysis_min_observations
        and span >= settings.analysis_min_history_days
        and distinct_days >= settings.analysis_min_distinct_days
    )
    discount = discount_percent(current.price, reference)
    effective = (
        discount_percent(current.price + current.shipping_cost, reference)
        if (current.shipping_cost is not None)
        else None
    )
    advertised = discount_percent(current.price, current.advertised_reference_price)
    age_hours = D(str((now - consulted).total_seconds() / 3600))
    fresh = 0 <= age_hours <= settings.analysis_max_age_hours
    identity = D(current.identity_confidence)
    known_identity = identity >= settings.analysis_min_identity_confidence
    reasons = []
    if not enough:
        reasons.append("insufficient_history")
    if not known_identity:
        reasons.append("low_identity_confidence")
    if current.available is not True:
        reasons.append("unavailable" if current.available is False else "availability_unknown")
    if not fresh:
        reasons.append("future_observation" if age_hours < 0 else "stale_observation")
    if current.shipping_cost is None:
        reasons.append("shipping_unknown")
    if current.is_simulated:
        reasons.append("simulated_data")
    anomaly = current.price == 0 or (
        reference is not None
        and (
            discount >= settings.analysis_anomaly_drop_percent
            or current.price >= reference * settings.analysis_anomaly_rise_multiplier
        )
    )
    if anomaly:
        reasons.append("price_anomaly")
    if effective is not None and effective <= 0 and discount is not None and discount > 0:
        reasons.append("shipping_erases_discount")
    if anomaly:
        classification = "possible_price_error"
    elif (
        enough
        and known_identity
        and discount is not None
        and (discount >= settings.analysis_min_discount_percent)
    ):
        classification = "history_confirmed"
    elif advertised is not None and advertised > 0:
        classification = "store_announced"
        reasons.append("announced_unconfirmed")
    elif not enough or not known_identity:
        classification = "insufficient_information"
    else:
        classification = "no_discount"
    quality = (
        clip(D(len(history)) / settings.analysis_min_observations)
        + clip(span / settings.analysis_min_history_days)
        + clip(D(distinct_days) / settings.analysis_min_distinct_days)
    ) / 3
    fractions = {
        "discount": clip((discount or D(0)) / settings.analysis_full_discount_percent),
        "history": quality,
        "availability": D(1) if current.available is True else D(0),
        "freshness": clip(1 - age_hours / settings.analysis_max_age_hours) if fresh else D(0),
        "costs": clip((effective or D(0)) / discount) if discount and discount > 0 else D(0),
        "identity": clip(identity),
    }
    components = {
        key: rounded(fractions[key] * weight) for key, weight in settings.analysis_weights.items()
    }
    score = int(sum(components.values()).quantize(D(1), rounding=ROUND_HALF_UP))
    if anomaly:
        score = min(score, 39)
    elif not enough or not known_identity or classification == "store_announced":
        score = min(score, 49)
    if not fresh or current.available is not True or current.shipping_cost is None:
        score = min(score, 69)
    if discount is None or discount <= 0 or (effective is not None and effective <= 0):
        score = min(score, 49)
    review_candidate = (
        classification == "history_confirmed"
        and fresh
        and enough
        and known_identity
        and current.available is True
        and effective is not None
        and effective >= settings.analysis_min_discount_percent
        and score >= settings.analysis_min_score
        and not current.is_simulated
    )
    return AnalysisResult(
        reference,
        discount,
        effective,
        advertised,
        max(0, min(score, 100)),
        classification,
        len(history),
        rounded(span),
        distinct_days,
        review_candidate,
        reasons,
        {key: float(value) for key, value in components.items()},
    )
