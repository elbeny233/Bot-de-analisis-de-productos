import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from radar.core.config import Settings
from radar.core.security import hash_password, verify_password
from radar.database.bootstrap import seed_categories
from radar.database.models import (
    Base,
    Category,
    Member,
    Membership,
    Offer,
    PriceObservation,
    Product,
    Source,
    Store,
)
from radar.database.session import build_engine, session_factory
from radar.main import create_app


@pytest.fixture
def session():
    engine = build_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with session_factory(engine)() as session:
        yield session
    engine.dispose()


def product(session, variant="500g"):
    store = session.scalar(select(Store))
    if store is None:
        store = Store(name="Tienda simulada")
        session.add(store)
        session.flush()
    source = session.scalar(select(Source))
    if source is None:
        source = Source(store_id=store.id, name="demo", connector="demo")
        session.add(source)
        session.flush()
    item = Product(
        source_id=source.id,
        source_product_id="item-1",
        variant_key=variant,
        name="Producto simulado",
        presentation=variant,
    )
    session.add(item)
    session.flush()
    return item


def test_defaults(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RADAR_PUBLICATIONS_ENABLED", raising=False)
    monkeypatch.delenv("RADAR_MONITOR_INTERVAL_MINUTES", raising=False)
    settings = Settings(_env_file=None)
    assert settings.monitor_interval_minutes == 30
    assert settings.publications_enabled is False


@pytest.mark.parametrize(
    "values",
    [
        {"monitor_interval_minutes": 0},
        {"database_url": "postgresql://host/db"},
        {"publications_enabled": True},
        {"log_level": "invalid"},
    ],
)
def test_invalid_configuration(values):
    with pytest.raises((ValueError, ValidationError)):
        Settings(_env_file=None, **values)


def test_environment_override(monkeypatch):
    monkeypatch.setenv("RADAR_MONITOR_INTERVAL_MINUTES", "45")
    assert Settings(_env_file=None).monitor_interval_minutes == 45


def test_categories_are_idempotent(session):
    seed_categories(session)
    seed_categories(session)
    assert session.scalar(select(func.count()).select_from(Category)) == 11
    assert session.scalar(select(Category).where(Category.slug == "electronica"))


def test_duplicate_products_rejected(session):
    product(session)
    session.commit()
    with pytest.raises(IntegrityError):
        product(session)


def test_presentations_kept_separate(session):
    first = product(session, "500g")
    second = product(session, "1kg")
    assert first.id != second.id
    session.commit()


def test_observation_decimal_and_unknown_availability(session):
    item = product(session)
    price = PriceObservation(product_id=item.id, price=Decimal("129.90"))
    session.add(price)
    session.commit()
    session.refresh(price)
    assert price.price == Decimal("129.90")
    assert price.available is None
    assert price.currency == "MXN"


def test_currency_observations_are_separate(session):
    item = product(session)
    for currency in ["MXN", "USD"]:
        session.add(PriceObservation(product_id=item.id, price=Decimal("100"), currency=currency))
    session.commit()
    assert set(session.scalars(select(PriceObservation.currency))) == {"MXN", "USD"}


@pytest.mark.parametrize(
    "values",
    [
        {"price": Decimal("-1")},
        {"price": Decimal("1"), "shipping_cost": Decimal("-1")},
        {"price": Decimal("1"), "currency": "INVALID"},
    ],
)
def test_invalid_prices_rejected(session, values):
    item = product(session)
    session.add(PriceObservation(product_id=item.id, **values))
    with pytest.raises(IntegrityError):
        session.commit()


def test_foreign_keys_enforced(session):
    session.add(PriceObservation(product_id=999, price=Decimal("10")))
    with pytest.raises(IntegrityError):
        session.commit()


def test_offer_score_constraint(session):
    item = product(session)
    observation = PriceObservation(product_id=item.id, price=Decimal("10"))
    session.add(observation)
    session.flush()
    session.add(Offer(observation_id=observation.id, score=101))
    with pytest.raises(IntegrityError):
        session.commit()


def test_membership_dates_constraint(session):
    member = Member(telegram_user_id="123")
    session.add(member)
    session.flush()
    now = datetime.now(timezone.utc)
    session.add(Membership(member_id=member.id, starts_at=now, expires_at=now - timedelta(days=1)))
    with pytest.raises(IntegrityError):
        session.commit()


def test_password_hash_and_credentials():
    password = "a-long-test-password"
    encoded = hash_password(password)
    assert password not in encoded
    assert encoded != hash_password(password)
    assert verify_password(password, encoded)
    assert not verify_password("wrong", encoded)
    assert not verify_password(password, "malformed")
    assert not verify_password(password, "pbkdf2_sha256$999999999$x$x")
    with pytest.raises(ValueError):
        hash_password("short")


def test_missing_database_returns_unready(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'missing.db'}", _env_file=None)
    with TestClient(create_app(settings)) as client:
        assert client.get("/health").status_code == 503
        assert "Fase 1" in client.get("/").text
        assert client.get("/docs").status_code == 404


def test_migration_restart_and_backup(tmp_path):
    database = tmp_path / "radar.db"
    env = {**os.environ, "RADAR_DATABASE_URL": f"sqlite:///{database}"}
    for _ in range(2):
        subprocess.run(
            [sys.executable, "-m", "radar.cli", "init-db"], check=True, env=env, capture_output=True
        )
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 11
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0001"
    settings = Settings(database_url=f"sqlite:///{database}", _env_file=None)
    for _ in range(2):
        with TestClient(create_app(settings)) as client:
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json()["publications_enabled"] is False
    result = subprocess.run(
        [sys.executable, "-m", "radar.cli", "backup"],
        check=True,
        env=env,
        capture_output=True,
        text=True,
    )
    backup = result.stdout.strip().split(": ", 1)[1]
    try:
        with closing(sqlite3.connect(backup)) as connection:
            assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert connection.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 11
    finally:
        from pathlib import Path

        Path(backup).unlink()
