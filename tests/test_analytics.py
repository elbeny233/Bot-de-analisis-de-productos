import re
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select, text

from radar.analytics.history import summarize
from radar.analytics.scoring import discount_percent, evaluate
from radar.analytics.service import AnalyticsService
from radar.catalog.normalization import classify_category, normalize_presentation, product_identity
from radar.collectors.base import CollectedProduct
from radar.core.config import Settings
from radar.core.security import hash_password
from radar.database.bootstrap import seed_categories, seed_demo_source
from radar.database.models import (
    AdminUser,
    Base,
    EventLog,
    Offer,
    PriceAnalysis,
    PriceObservation,
    Product,
    Source,
    utc_now,
)
from radar.database.session import build_engine, session_factory
from radar.main import create_app
from radar.scheduler.service import MonitorService

D = Decimal


def observation(price="80", day=0, id=1000, **values):
    return SimpleNamespace(
        id=id,
        product_id=1,
        price=D(price),
        currency="MXN",
        is_simulated=False,
        observed_at=NOW + timedelta(days=day),
        available=True,
        shipping_cost=D("0"),
        identity_confidence=D("1"),
        advertised_reference_price=None,
        **values,
    )


NOW = utc_now()


def prior_prices(prices=None):
    prices = prices or ["100"] * 5
    return [
        observation(price, day=-10 + index * 2, id=index + 1) for index, price in enumerate(prices)
    ]


def test_discount_math_and_zero_reference():
    assert discount_percent(D("80"), D("100")) == D("20.00")
    assert discount_percent(D("120"), D("100")) == D("-20.00")
    assert discount_percent(D("80"), D("0")) is None
    assert discount_percent(D("80"), None) is None


def test_confirmed_discount_score_and_review_gate():
    result = evaluate(observation(), prior_prices(), Settings(_env_file=None), now=NOW)
    assert result.reference_price == D("100")
    assert result.discount_percent == D("20")
    assert result.score == 76
    assert result.classification == "history_confirmed"
    assert result.review_candidate
    assert result.components["discount"] == 16


def test_score_maximum_100():
    result = evaluate(observation("50"), prior_prices(), Settings(_env_file=None), now=NOW)
    assert result.score == 100


def test_without_history_not_confirmed():
    result = evaluate(observation(), [], Settings(_env_file=None), now=NOW)
    assert result.reference_price is None
    assert result.discount_percent is None
    assert result.classification == "insufficient_information"
    assert result.score <= 49
    assert not result.review_candidate


def test_price_advertised_does_not_become_reference():
    current = observation()
    current.advertised_reference_price = D("1000")
    empty = evaluate(current, [], Settings(_env_file=None), now=NOW)
    assert empty.reference_price is None
    assert empty.advertised_discount_percent == D("92")
    assert empty.classification == "store_announced"
    confirmed = evaluate(current, prior_prices(), Settings(_env_file=None), now=NOW)
    assert confirmed.reference_price == D("100")
    assert confirmed.discount_percent == D("20")
    assert confirmed.score == 76


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("available", None, "availability_unknown"),
        ("available", False, "unavailable"),
        ("shipping_cost", None, "shipping_unknown"),
        ("identity_confidence", D("0.5"), "low_identity_confidence"),
        ("is_simulated", True, "simulated_data"),
    ],
)
def test_low_confidence_never_recommended_even_low_score_threshold(field, value, reason):
    current = observation()
    setattr(current, field, value)
    history = prior_prices()
    if field == "is_simulated":
        for row in history:
            row.is_simulated = True
    result = evaluate(current, history, Settings(analysis_min_score=0, _env_file=None), now=NOW)
    assert not result.review_candidate
    assert reason in result.reasons


def test_shipping_erases_savings():
    current = observation()
    current.shipping_cost = D("25")
    result = evaluate(current, prior_prices(), Settings(_env_file=None), now=NOW)
    assert result.discount_percent == D("20")
    assert result.effective_discount_percent == D("-5")
    assert result.score <= 49
    assert not result.review_candidate
    assert "shipping_erases_discount" in result.reasons


@pytest.mark.parametrize("price", ["0", "1", "600"])
def test_anomalies_are_not_auto_recommended(price):
    result = evaluate(observation(price), prior_prices(), Settings(_env_file=None), now=NOW)
    assert result.classification == "possible_price_error"
    assert result.score <= 39
    assert not result.review_candidate


def test_many_samples_same_day_do_not_confirm_history():
    prior = [observation("100", id=i, day=0) for i in range(1, 100)]
    for row in prior:
        row.observed_at -= timedelta(minutes=row.id)
    result = evaluate(observation(), prior, Settings(_env_file=None), now=NOW)
    assert result.history_count == 99
    assert result.distinct_days == 1
    assert result.classification == "insufficient_information"
    assert not result.review_candidate


def test_currency_simulation_product_future_and_current_excluded():
    history = prior_prices()
    unrelated = []
    for field, value in [("currency", "USD"), ("is_simulated", True), ("product_id", 2)]:
        extra = observation("1", day=-5, id=200)
        setattr(extra, field, value)
        unrelated.append(extra)
    unrelated += [observation("1", day=1, id=300), observation()]
    result = evaluate(observation(), history + unrelated, Settings(_env_file=None), now=NOW)
    assert result.history_count == 5
    assert result.reference_price == D("100")


def test_window_excludes_old_prices_and_zero_reference_samples():
    result = evaluate(
        observation(),
        [observation("100", day=-40, id=1), observation("0", day=-2, id=2)],
        Settings(_env_file=None),
        now=NOW,
    )
    assert result.reference_price is None
    assert result.history_count == 0


def test_median_resists_single_high_advertised_or_observed_price():
    result = evaluate(
        observation(),
        prior_prices(["100", "100", "100", "100", "1000"]),
        Settings(_env_file=None),
        now=NOW,
    )
    assert result.reference_price == D("100")


@pytest.mark.parametrize(
    "now,reason",
    [
        (NOW + timedelta(days=2), "stale_observation"),
        (NOW - timedelta(hours=1), "future_observation"),
    ],
)
def test_freshness_gate(now, reason):
    result = evaluate(observation(), prior_prices(), Settings(_env_file=None), now=now)
    assert not result.review_candidate
    assert reason in result.reasons
    assert result.score <= 69


def test_configurable_weights_change_score():
    settings = Settings(
        analysis_weights=dict(
            discount=100, history=0, availability=0, freshness=0, costs=0, identity=0
        ),
        _env_file=None,
    )
    assert evaluate(observation(), prior_prices(), settings, now=NOW).score == 40


@pytest.mark.parametrize(
    "values",
    [
        {"analysis_weights": {"discount": 100}},
        {
            "analysis_weights": dict(
                discount=-1, history=61, availability=10, freshness=10, costs=10, identity=10
            )
        },
        {"analysis_min_history_days": 40, "analysis_reference_days": 30},
        {"analysis_min_observations": 0},
    ],
)
def test_invalid_analytics_configuration(values):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def item(**changes):
    base = dict(
        source_product_id="item",
        variant_key="1kg",
        name="Arroz",
        price="80",
        brand="Marca",
        model="modelo-A",
        presentation="1 kg",
        seller="Tienda",
    )
    return CollectedProduct(**(base | changes))


def test_presentation_normalization_and_variant_separation():
    assert normalize_presentation(" 1KG ") == "1 kg"
    assert product_identity(item())[0] == product_identity(item(presentation="1KG"))[0]
    assert product_identity(item())[0] != product_identity(item(presentation="500 g"))[0]
    assert product_identity(item())[0] != product_identity(item(model="modelo-B"))[0]
    assert product_identity(item())[0] != product_identity(item(seller="Otra tienda"))[0]


@pytest.mark.parametrize(
    "name,suggested,expected",
    [
        ("Arroz 1 kg", None, "alimentos"),
        ("AUDÍFONOS", None, "electronica"),
        ("Nintendo Switch", None, "videojuegos"),
        ("Laptop SSD", None, "computadoras"),
        ("Producto desconocido", None, None),
        ("Arroz y zapatos", None, None),
        ("Arroz", "categoria-personal", "categoria-personal"),
    ],
)
def test_product_classification(name, suggested, expected):
    known = {
        "alimentos",
        "electronica",
        "videojuegos",
        "computadoras",
        "ropa",
        "categoria-personal",
    }
    assert classify_category(name, suggested, known) == expected


@pytest.fixture
def database(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'analytics.db'}")
    Base.metadata.create_all(engine)
    sessions = session_factory(engine)
    with sessions() as session:
        seed_categories(session)
        seed_demo_source(session, 30)
        source_id = session.scalar(select(Source.id))
        product = Product(
            source_id=source_id,
            source_product_id="test",
            variant_key="500g",
            name="Producto de prueba",
        )
        session.add(product)
        session.commit()
        product_id = product.id
    yield sessions, source_id, product_id
    engine.dispose()


def save(session, product_id, price, days, **changes):
    values = dict(
        product_id=product_id,
        price=D(price),
        currency="MXN",
        is_simulated=False,
        observed_at=NOW + timedelta(days=days),
        available=True,
        shipping_cost=D("0"),
        identity_confidence=D("1"),
    )
    row = PriceObservation(**(values | changes))
    session.add(row)
    session.flush()
    return row


def test_history_statistics_periods_and_separated_scopes(database):
    sessions, _, product_id = database
    with sessions.begin() as session:
        save(session, product_id, "200", -31)
        save(session, product_id, "150", -8)
        save(session, product_id, "100", -2)
        save(session, product_id, "80", 0)
        save(session, product_id, "1", 0, currency="USD")
        save(session, product_id, "2", 0, is_simulated=True)
        save(session, product_id, "3", 1)
    with sessions() as session:
        summary = summarize(session, product_id, as_of=NOW)
        assert summary.count == 4
        assert summary.latest == D("80")
        assert summary.minimum == D("80")
        assert summary.maximum == D("200")
        assert summary.average == D("132.50")
        assert summary.median == D("125")
        assert summary.changes == {"24h": D("-20"), "7d": D("-46.67"), "30d": D("-60")}
        assert (summary.period_end - summary.period_start).days == 31
        assert summarize(session, product_id, "USD", False, NOW).count == 1
        assert summarize(session, product_id, "MXN", True, NOW).minimum == D("2")


def test_empty_history_and_missing_baseline(database):
    sessions, _, product_id = database
    with sessions() as session:
        assert summarize(session, product_id, as_of=NOW).count == 0
    with sessions.begin() as session:
        save(session, product_id, "80", 0)
    with sessions() as session:
        assert summarize(session, product_id, as_of=NOW).changes == {
            "24h": None,
            "7d": None,
            "30d": None,
        }


def test_analysis_idempotent_pending_offer_and_no_publication(database):
    sessions, _, product_id = database
    with sessions.begin() as session:
        for days in [-10, -8, -6, -4, -2]:
            save(session, product_id, "100", days)
        observation_id = save(session, product_id, "80", 0).id
    analyzer = AnalyticsService(sessions, Settings(_env_file=None))
    analyzer.analyze([observation_id])
    analyzer.analyze([observation_id])
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(PriceAnalysis)) == 1
        assert session.scalar(select(func.count()).select_from(Offer)) == 1
        offer = session.scalar(select(Offer))
        assert offer.status == "pending"
        assert offer.score == 76
        assert session.scalar(select(PriceAnalysis)).review_candidate
    with sessions.begin() as session:
        session.scalar(select(Offer)).status = "discarded"
    analyzer.analyze([observation_id])
    with sessions() as session:
        assert session.scalar(select(Offer)).status == "discarded"


def test_no_discount_does_not_create_offer(database):
    sessions, _, product_id = database
    with sessions.begin() as session:
        for days in [-10, -8, -6, -4, -2]:
            save(session, product_id, "100", days)
        observation_id = save(session, product_id, "100", 0).id
    AnalyticsService(sessions, Settings(_env_file=None)).analyze([observation_id])
    with sessions() as session:
        assert session.scalar(select(PriceAnalysis)).classification == "no_discount"
        assert session.scalar(select(func.count()).select_from(Offer)) == 0


def test_identity_change_never_mixes_model_history(database):
    sessions, source_id, _ = database
    collector = Mock(is_simulated=True)
    collector.collect.side_effect = [[item()], [item(model="modelo-B")], [item(model="modelo-B")]]
    runner = MonitorService(sessions, Settings(_env_file=None), collectors={"demo": collector})
    for _ in range(3):
        assert runner.run_source(source_id) == "success"
    with sessions() as session:
        # Más el producto inicial del fixture, que no tiene precios.
        assert session.scalar(select(func.count()).select_from(Product)) == 3
        models = session.execute(
            select(Product.model, func.count(PriceObservation.id))
            .join(PriceObservation)
            .group_by(Product.id)
        ).all()
        assert dict(models) == {"modelo-A": 1, "modelo-B": 2}


def test_compatible_legacy_product_reuses_history(database):
    sessions, source_id, product_id = database
    with sessions.begin() as session:
        legacy = session.get(Product, product_id)
        legacy.source_product_id = "item"
        legacy.variant_key = "1KG"
        legacy.brand = "Marca"
        legacy.model = "modelo-A"
        legacy.presentation = "1 kg"
        legacy.seller = "Tienda"
        save(session, product_id, "100", -1, is_simulated=True)
    collector = Mock(is_simulated=True)
    collector.collect.return_value = [item()]
    runner = MonitorService(sessions, Settings(_env_file=None), collectors={"demo": collector})
    assert runner.run_source(source_id) == "success"
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(Product)) == 1
        assert session.scalar(select(func.count()).select_from(PriceObservation)) == 2
        assert "~" in session.get(Product, product_id).variant_key


def test_analytics_failure_preserves_successful_collection(database, monkeypatch):
    sessions, source_id, _ = database
    monkeypatch.setattr(AnalyticsService, "analyze", Mock(side_effect=RuntimeError("failure")))
    assert MonitorService(sessions, Settings(_env_file=None)).run_source(source_id) == "success"
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(PriceObservation)) == 3
        assert session.scalar(select(EventLog).where(EventLog.event_code == "analysis_failed"))


@pytest.fixture
def web_client(database):
    sessions, source_id, product_id = database
    with sessions.kw["bind"].begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(text("INSERT INTO alembic_version VALUES ('0003')"))
    with sessions.begin() as session:
        session.add(AdminUser(username="owner", password_hash=hash_password("analytics-password")))
        for days in [-10, -8, -6, -4, -2]:
            save(session, product_id, "100", days)
        current_id = save(session, product_id, "80", 0).id
    settings = Settings(
        database_url=str(sessions.kw["bind"].url), scheduler_enabled=False, _env_file=None
    )
    AnalyticsService(sessions, settings).analyze([current_id])
    with TestClient(create_app(settings)) as client:
        yield client, sessions, source_id, product_id, ("owner", "analytics-password")


def test_analytics_pages_and_history_api(web_client):
    client, _, _, product_id, auth = web_client
    for route in ["/analysis", "/offers", f"/products/{product_id}/history"]:
        assert client.get(route).status_code == 401
    assert client.get("/analysis", auth=auth).status_code == 200
    response = client.get(f"/analysis/{product_id}", auth=auth)
    assert response.status_code == 200
    assert "20.00%" in response.text
    assert "76/100" in response.text
    assert "Mínimo del periodo observado" in response.text
    assert "Descuento confirmado por historial observado" in response.text
    assert client.get("/offers", auth=auth).status_code == 200
    summary = client.get(f"/products/{product_id}/history", auth=auth).json()
    assert summary["count"] == 6
    assert summary["latest"] == "80.00"
    assert summary["median"] == "100.00"
    assert summary["changes"]["7d"] == "-20.00"
    assert (
        client.get(f"/products/{product_id}/history?currency=USD", auth=auth).json()["count"] == 0
    )
    assert client.get("/analysis/999999", auth=auth).status_code == 404
    assert client.get(f"/products/{product_id}/history?currency=bad", auth=auth).status_code == 422


def test_html_escaping_search_and_manual_reanalysis(web_client):
    client, sessions, source_id, product_id, auth = web_client
    with sessions.begin() as session:
        session.get(Product, product_id).name = '<img src=x onerror="bad">'
        session.scalar(
            select(PriceObservation).order_by(PriceObservation.id.desc())
        ).conditions = "<script>bad</script>"
    html = client.get(f"/analysis/{product_id}", auth=auth).text
    assert "<img src=x" not in html
    assert "<script>bad" not in html
    assert "&lt;img" in html
    assert "&lt;script&gt;" in html
    response = client.get("/analysis", params={"q": "' OR 1=1 --"}, auth=auth)
    assert response.status_code == 200
    assert "&lt;img" not in response.text
    page = client.get("/monitor", auth=auth)
    token = re.search(r'name="csrf" value="([^"]+)"', page.text)[1]
    response = client.post(
        f"/monitor/{source_id}/analyze", auth=auth, data={"csrf": token}, follow_redirects=False
    )
    assert response.status_code == 303
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(Offer)) == 1
        assert session.scalar(select(func.count()).select_from(PriceAnalysis)) == 1


def test_stale_history_without_new_observations_has_no_recent_change(database):
    sessions, _, product_id = database
    with sessions.begin() as session:
        save(session, product_id, "100", -5)
    with sessions() as session:
        assert summarize(session, product_id, as_of=NOW).changes["24h"] is None


def test_blank_metadata_does_not_increase_identity_confidence():
    collected = item(brand=" ", model=" ", presentation=" ")
    assert product_identity(collected)[1] == D("0.50")
