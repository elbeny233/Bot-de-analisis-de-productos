import logging
import time
from datetime import timedelta
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import select, update

from radar.analytics.service import AnalyticsService
from radar.catalog.normalization import (
    classify_category,
    compatible_legacy,
    normalize_presentation,
    product_identity,
)
from radar.collectors.base import (
    CollectedProduct,
    SourceUnavailableError,
    TransientCollectorError,
)
from radar.collectors.demo import DemoCollector
from radar.database.models import (
    Category,
    EventLog,
    MonitorRun,
    PriceObservation,
    Product,
    Source,
    utc_now,
)

logger = logging.getLogger(__name__)


class MonitorService:
    def __init__(self, sessions, settings, collectors=None, sleeper=time.sleep):
        self.sessions = sessions
        self.settings = settings
        self.collectors = {"demo": DemoCollector()} if collectors is None else collectors
        self.sleeper = sleeper

    def recover(self):
        """Solo llamar después de adquirir el bloqueo exclusivo del proceso."""
        with self.sessions.begin() as session:
            running = session.scalars(select(MonitorRun).where(MonitorRun.status == "running"))
            for run in running:
                run.status = "interrupted"
                run.finished_at = utc_now()
                run.error_code = "process_restarted"
                session.add(EventLog(level="WARNING", event_code="monitor_interrupted"))
            session.execute(update(Source).values(running_token=None))

    def run_source(self, source_id: int) -> str:
        token = uuid4().hex
        with self.sessions.begin() as session:
            source = session.get(Source, source_id)
            if source is None:
                return "not_found"
            if not source.enabled:
                return "paused"
            claimed = session.execute(
                update(Source)
                .where(
                    Source.id == source_id, Source.enabled.is_(True), Source.running_token.is_(None)
                )
                .values(running_token=token)
            )
            if claimed.rowcount != 1:
                return "already_running"
            connector_name = source.connector
            interval = source.interval_minutes
            run = MonitorRun(source_id=source_id, status="running", started_at=utc_now())
            session.add(run)
            session.flush()
            run_id = run.id
        attempts = 0
        error_code = None
        result = None
        collector = self.collectors.get(connector_name)
        for attempts in range(1, self.settings.monitor_max_attempts + 1):
            try:
                if collector is None:
                    raise SourceUnavailableError()
                raw = collector.collect()
                if not isinstance(raw, list) or not 1 <= len(raw) <= 1000:
                    raise ValueError("Invalid collector batch")
                validated = [CollectedProduct.model_validate(item) for item in raw]
                keys = [(item.source_product_id, product_identity(item)[0]) for item in validated]
                if len(keys) != len(set(keys)):
                    raise ValueError("Duplicate observation in batch")
                result = validated
                break
            except TransientCollectorError:
                error_code = "connection_error"
                if attempts < self.settings.monitor_max_attempts:
                    self.sleeper(min(self.settings.monitor_retry_seconds * 2 ** (attempts - 1), 60))
            except SourceUnavailableError:
                error_code = "source_unavailable"
                break
            except (ValueError, ValidationError):
                error_code = "invalid_data"
                break
            except Exception:
                error_code = "collector_internal_error"
                break
        try:
            if result is not None:
                ids = self._persist(
                    source_id, run_id, token, attempts, result, collector.is_simulated
                )
                self._analyze(ids)
                return "success"
        except Exception:
            # Nunca registrar respuestas, URLs, excepciones o credenciales del conector.
            error_code = "persistence_error"
        with self.sessions.begin() as session:
            source = session.get(Source, source_id)
            run = session.get(MonitorRun, run_id)
            run.status = "failed"
            run.attempts = attempts
            run.finished_at = utc_now()
            run.error_code = error_code
            source.consecutive_failures += 1
            if source.consecutive_failures >= self.settings.monitor_pause_after_failures:
                source.enabled = False
                session.add(EventLog(level="WARNING", event_code="source_auto_paused"))
            source.next_run_at = utc_now() + timedelta(minutes=interval)
            if source.running_token == token:
                source.running_token = None
            session.add(EventLog(level="ERROR", event_code=f"monitor_{error_code}"))
        logger.warning("monitor_failed source_id=%s code=%s", source_id, error_code)
        return "failed"

    def _persist(self, source_id, run_id, token, attempts, items, is_simulated):
        observation_ids = []
        with self.sessions.begin() as session:
            source = session.get(Source, source_id)
            if source.running_token != token:
                raise RuntimeError("Lost run ownership")
            categories = dict(session.execute(select(Category.slug, Category.id)).all())
            for item in items:
                identity_key, confidence = product_identity(item)
                product = session.scalar(
                    select(Product).where(
                        Product.source_id == source_id,
                        Product.source_product_id == item.source_product_id,
                        Product.variant_key == identity_key,
                    )
                )
                if product is None:
                    legacy = session.scalars(
                        select(Product).where(
                            Product.source_id == source_id,
                            Product.source_product_id == item.source_product_id,
                        )
                    ).all()
                    matching = [
                        candidate
                        for candidate in legacy
                        if normalize_presentation(candidate.variant_key)
                        == normalize_presentation(item.variant_key)
                        and compatible_legacy(candidate, item)
                    ]
                    if len(matching) == 1:
                        product = matching[0]
                        product.variant_key = identity_key
                if product is None:
                    product = Product(
                        source_id=source_id,
                        source_product_id=item.source_product_id,
                        variant_key=identity_key,
                        name=item.name,
                    )
                    session.add(product)
                for key in ("name", "brand", "model", "presentation", "seller"):
                    setattr(product, key, getattr(item, key))
                product.url = str(item.url) if item.url else None
                category = classify_category(item.name, item.category_slug, set(categories))
                product.category_id = categories.get(category)
                product.is_simulated = is_simulated
                session.flush()
                observation = PriceObservation(
                    product_id=product.id,
                    price=item.price,
                    currency=item.currency,
                    available=item.available,
                    shipping_cost=item.shipping_cost,
                    advertised_reference_price=item.advertised_reference_price,
                    identity_confidence=confidence,
                    conditions=item.conditions,
                    observed_at=item.observed_at,
                    is_simulated=is_simulated,
                )
                session.add(observation)
                session.flush()
                observation_ids.append(observation.id)
            run = session.get(MonitorRun, run_id)
            run.status = "success"
            run.finished_at = utc_now()
            run.attempts = attempts
            run.observations_count = len(items)
            source.running_token = None
            source.consecutive_failures = 0
            source.next_run_at = utc_now() + timedelta(minutes=source.interval_minutes)
            session.add(EventLog(level="INFO", event_code="monitor_success"))
        logger.info("monitor_success source_id=%s observations=%s", source_id, len(items))

        return observation_ids

    def _analyze(self, observation_ids):
        try:
            AnalyticsService(self.sessions, self.settings).analyze(observation_ids)
        except Exception:
            logger.warning("analysis_failed: los precios se conservaron; recalcular desde el panel")
            try:
                with self.sessions.begin() as session:
                    session.add(EventLog(level="ERROR", event_code="analysis_failed"))
            except Exception:
                logger.error("analysis_event_unavailable")
