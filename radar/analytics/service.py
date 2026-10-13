from sqlalchemy import select

from radar.analytics.history import observations_for
from radar.analytics.scoring import evaluate
from radar.database.models import EventLog, Offer, PriceAnalysis, PriceObservation, Product, utc_now


class AnalyticsService:
    def __init__(self, sessions, settings):
        self.sessions = sessions
        self.settings = settings

    def analyze(self, observation_ids):
        with self.sessions.begin() as session:
            for observation_id in observation_ids:
                current = session.get(PriceObservation, observation_id)
                if current is None:
                    continue
                prior = observations_for(
                    session,
                    current.product_id,
                    current.currency,
                    current.is_simulated,
                    current.observed_at,
                )
                result = evaluate(current, prior, self.settings)
                analysis = session.scalar(
                    select(PriceAnalysis).where(PriceAnalysis.observation_id == current.id)
                )
                if analysis is None:
                    analysis = PriceAnalysis(observation_id=current.id)
                    session.add(analysis)
                for field in (
                    "reference_price",
                    "discount_percent",
                    "effective_discount_percent",
                    "advertised_discount_percent",
                    "score",
                    "classification",
                    "history_count",
                    "history_days",
                    "distinct_days",
                    "review_candidate",
                    "reasons",
                    "components",
                ):
                    setattr(analysis, field, getattr(result, field))
                analysis.analyzed_at = utc_now()
                offer = session.scalar(select(Offer).where(Offer.observation_id == current.id))
                candidate = (
                    (
                        result.discount_percent is not None
                        and result.discount_percent >= self.settings.analysis_min_discount_percent
                    )
                    or (
                        result.advertised_discount_percent is not None
                        and result.advertised_discount_percent > 0
                    )
                    or result.classification == "possible_price_error"
                )
                if candidate or offer is not None:
                    if offer is None:
                        offer = Offer(observation_id=current.id, status="pending")
                        session.add(offer)
                    offer.score = result.score
                    offer.classification = result.classification
                    # Nunca aprobar, publicar ni borrar estados existentes automáticamente.
            session.add(EventLog(level="INFO", event_code="analysis_completed"))

    def analyze_source(self, source_id):
        with self.sessions() as session:
            rows = session.scalars(
                select(PriceObservation)
                .join(Product)
                .where(Product.source_id == source_id)
                .order_by(PriceObservation.observed_at.desc(), PriceObservation.id.desc())
            ).all()
            latest = {}
            for row in rows:
                latest.setdefault((row.product_id, row.currency, row.is_simulated), row.id)
        self.analyze(list(latest.values()))
        return len(latest)
