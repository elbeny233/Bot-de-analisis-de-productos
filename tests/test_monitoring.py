import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
from contextlib import closing
from datetime import timedelta
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select, text

from radar.collectors.base import CollectedProduct, SourceUnavailableError, TransientCollectorError
from radar.collectors.demo import DemoCollector
from radar.core.config import Settings
from radar.core.process_lock import MonitorAlreadyRunning, ProcessLock
from radar.core.security import hash_password
from radar.database.bootstrap import seed_categories, seed_demo_source
from radar.database.models import (
    AdminUser,
    Base,
    EventLog,
    MonitorRun,
    Offer,
    PriceObservation,
    Product,
    Source,
    utc_now,
)
from radar.database.session import build_engine, session_factory
from radar.main import create_app
from radar.scheduler.runtime import MonitorRuntime, as_utc
from radar.scheduler.service import MonitorService


@pytest.fixture
def database(tmp_path):
    url = f"sqlite:///{tmp_path / 'monitor.db'}"
    engine = build_engine(url)
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(text("INSERT INTO alembic_version VALUES ('0002')"))
    sessions = session_factory(engine)
    with sessions() as session:
        seed_categories(session)
        seed_demo_source(session, 30)
        source = session.scalar(select(Source))
        source.next_run_at = utc_now() + timedelta(hours=1)
        session.commit()
        source_id = source.id
    settings = Settings(database_url=url, _env_file=None)
    yield sessions, settings, source_id
    engine.dispose()


def service(database, collector=None, **options):
    sessions, settings, _ = database
    collectors = {"demo": collector} if collector is not None else None
    return MonitorService(sessions, settings, collectors=collectors, **options)


def wait_for_success(sessions, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with sessions() as session:
            if session.scalar(select(MonitorRun).where(MonitorRun.status == "success")):
                return
        time.sleep(0.02)
    pytest.fail("El programador no completó la revisión a tiempo")


def test_demo_normalized_and_marked():
    items = DemoCollector().collect()
    assert len(items) == 3
    assert all("SIMULADO" in item.name and item.url is None for item in items)
    assert any(item.available is None for item in items)
    assert {item.variant_key for item in items if item.source_product_id == "demo-arroz"} == {
        "1kg",
        "500g",
    }


@pytest.mark.parametrize(
    "values",
    [
        {"price": -1},
        {"price": "NaN"},
        {"currency": "mxn"},
        {"name": " "},
        {"variant_key": ""},
        {"url": "file:///etc/passwd"},
        {"source_product_id": ""},
        {"observed_at": "2026-01-01T00:00:00"},
        {"shipping_cost": -1},
    ],
)
def test_invalid_collected_data(values):
    base = dict(source_product_id="1", variant_key="500g", name="Demo", price="10.00")
    with pytest.raises(ValidationError):
        CollectedProduct(**(base | values))


def test_demo_persists_history_without_duplicate_products(database):
    sessions, _, source_id = database
    runner = service(database)
    assert runner.run_source(source_id) == "success"
    assert runner.run_source(source_id) == "success"
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(Product)) == 3
        assert session.scalar(select(func.count()).select_from(PriceObservation)) == 6
        assert session.scalar(select(func.count()).select_from(Offer)) == 0
        assert all(session.scalars(select(Product.is_simulated)))
        assert all(session.scalars(select(PriceObservation.is_simulated)))
        assert session.scalar(select(PriceObservation).where(PriceObservation.available.is_(None)))
        assert session.get(Source, source_id).running_token is None
        assert as_utc(session.get(Source, source_id).next_run_at) > utc_now()


def test_seed_preserves_existing_configuration(database):
    sessions, _, source_id = database
    with sessions() as session:
        source = session.get(Source, source_id)
        source.enabled = False
        source.interval_minutes = 99
        session.commit()
        seed_demo_source(session, 30)
        assert session.scalar(select(func.count()).select_from(Source)) == 1
        assert session.get(Source, source_id).interval_minutes == 99
        assert not session.get(Source, source_id).enabled


def test_transient_error_progressive_retry_then_success(database):
    sessions, _, source_id = database
    collector = Mock(is_simulated=True)
    collector.collect.side_effect = [
        TransientCollectorError("secret must not be logged"),
        TransientCollectorError(),
        DemoCollector().collect(),
    ]
    sleeper = Mock()
    assert service(database, collector, sleeper=sleeper).run_source(source_id) == "success"
    assert [call.args[0] for call in sleeper.call_args_list] == [1, 2]
    with sessions() as session:
        assert session.scalar(select(MonitorRun)).attempts == 3
        assert session.get(Source, source_id).consecutive_failures == 0


def test_repeated_connection_failure_pauses_and_does_not_leak(database, caplog):
    sessions, _, source_id = database
    collector = Mock(is_simulated=True)
    collector.collect.side_effect = TransientCollectorError("TOKEN-SHOULD-NOT-APPEAR")
    runner = service(database, collector, sleeper=Mock())
    for _ in range(3):
        assert runner.run_source(source_id) == "failed"
    assert collector.collect.call_count == 9
    assert runner.run_source(source_id) == "paused"
    with sessions() as session:
        assert not session.get(Source, source_id).enabled
        assert session.get(Source, source_id).consecutive_failures == 3
        assert session.scalar(select(func.count()).select_from(PriceObservation)) == 0
        assert session.scalar(select(EventLog).where(EventLog.event_code == "source_auto_paused"))
    assert "TOKEN-SHOULD-NOT-APPEAR" not in caplog.text


def test_unavailable_source_no_retry(database):
    sessions, _, source_id = database
    collector = Mock(is_simulated=True)
    collector.collect.side_effect = SourceUnavailableError()
    assert service(database, collector, sleeper=Mock()).run_source(source_id) == "failed"
    assert collector.collect.call_count == 1
    with sessions() as session:
        assert session.scalar(select(MonitorRun)).error_code == "source_unavailable"


@pytest.mark.parametrize("batch", [[], [{"name": "incomplete"}], DemoCollector().collect() * 2])
def test_invalid_batch_rolls_back_without_prices(database, batch):
    sessions, _, source_id = database
    collector = Mock(is_simulated=True)
    collector.collect.return_value = batch
    assert service(database, collector).run_source(source_id) == "failed"
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(Product)) == 0
        assert session.scalar(select(MonitorRun)).error_code == "invalid_data"


def test_failure_in_one_source_does_not_stop_another(database):
    sessions, _, source_id = database
    with sessions.begin() as session:
        source = session.get(Source, source_id)
        source.connector = "unknown"
        other = Source(name="otra demo", store_id=source.store_id, connector="demo", enabled=True)
        session.add(other)
        session.flush()
        other_id = other.id
    runner = service(database)
    assert runner.run_source(source_id) == "failed"
    assert runner.run_source(other_id) == "success"


def test_concurrent_manual_and_scheduled_run_claims_once(database):
    sessions, _, source_id = database
    started, release = threading.Event(), threading.Event()

    class BlockingDemo(DemoCollector):
        def collect(self):
            started.set()
            assert release.wait(5)
            return super().collect()

    runner = service(database, BlockingDemo())
    results = []
    thread = threading.Thread(target=lambda: results.append(runner.run_source(source_id)))
    thread.start()
    try:
        assert started.wait(5)
        assert service(database).run_source(source_id) == "already_running"
    finally:
        release.set()
        thread.join(5)
    assert results == ["success"]
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(MonitorRun)) == 1


def test_process_lock_blocks_second_process_and_releases(tmp_path):
    path = tmp_path / "monitor.lock"
    code = (
        "from pathlib import Path; from radar.core.process_lock import ProcessLock; "
        "import sys; lock=ProcessLock(Path(sys.argv[1])); lock.acquire(); lock.release()"
    )
    with ProcessLock(path):
        result = subprocess.run([sys.executable, "-c", code, str(path)], capture_output=True)
        assert result.returncode != 0
        assert b"MonitorAlreadyRunning" in result.stderr
    subprocess.run([sys.executable, "-c", code, str(path)], check=True, capture_output=True)


def test_restart_recovers_interrupted_run_and_keeps_schedule(database):
    sessions, settings, source_id = database
    with sessions.begin() as session:
        source = session.get(Source, source_id)
        source.running_token = "old-process"
        source.next_run_at = utc_now() - timedelta(minutes=1)
        session.add(MonitorRun(source_id=source_id, status="running", started_at=utc_now()))
    runtime = MonitorRuntime(sessions, settings)
    runtime.start()
    try:
        wait_for_success(sessions)
        with sessions() as session:
            interrupted = session.scalar(
                select(MonitorRun).where(MonitorRun.status == "interrupted")
            )
            assert interrupted.error_code == "process_restarted"
            due = as_utc(session.get(Source, source_id).next_run_at)
        duplicate = MonitorRuntime(sessions, settings)
        with pytest.raises(MonitorAlreadyRunning):
            duplicate.start()
    finally:
        runtime.stop()
    restarted = MonitorRuntime(sessions, settings)
    restarted.start()
    try:
        assert restarted.scheduler.get_job(f"source-{source_id}").next_run_time == due
        with sessions() as session:
            assert session.scalar(select(func.count()).select_from(MonitorRun)) == 2
    finally:
        restarted.stop()


def test_per_source_interval_and_pause_refresh(database):
    sessions, settings, source_id = database
    with sessions.begin() as session:
        source = session.get(Source, source_id)
        source.interval_minutes = 7
        second = Source(
            store_id=source.store_id,
            name="intervalo distinto",
            connector="demo",
            enabled=True,
            interval_minutes=11,
            next_run_at=source.next_run_at,
        )
        session.add(second)
        session.flush()
        second_id = second.id
    runtime = MonitorRuntime(sessions, settings)
    runtime.start()
    try:
        assert (
            runtime.scheduler.get_job(f"source-{source_id}").trigger.interval.total_seconds() == 420
        )
        assert (
            runtime.scheduler.get_job(f"source-{second_id}").trigger.interval.total_seconds() == 660
        )
        with sessions.begin() as session:
            session.get(Source, source_id).enabled = False
            session.get(Source, second_id).interval_minutes = 13
        runtime.refresh()
        assert runtime.scheduler.get_job(f"source-{source_id}") is None
        assert (
            runtime.scheduler.get_job(f"source-{second_id}").trigger.interval.total_seconds() == 780
        )
    finally:
        runtime.stop()


def credentials(sessions):
    password = "windows-test-password"
    with sessions.begin() as session:
        session.add(AdminUser(username="owner", password_hash=hash_password(password)))
    return "owner", password


def test_monitor_auth_manual_run_csrf_and_controls(database):
    sessions, settings, source_id = database
    auth = credentials(sessions)
    with TestClient(create_app(settings)) as client:
        assert client.get("/monitor").status_code == 401
        assert client.get("/monitor", auth=("owner", "wrong")).status_code == 401
        response = client.get("/monitor", auth=auth)
        assert response.status_code == 200
        assert "datos simulados" in response.text
        token = re.search(r'name="csrf" value="([^"]+)"', response.text)[1]
        assert (
            client.post(
                f"/monitor/{source_id}/run", auth=auth, data={"csrf": "invalid"}
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/monitor/{source_id}/run", auth=auth, data={"csrf": token}, follow_redirects=False
            ).status_code
            == 303
        )
        assert (
            client.post(
                f"/monitor/{source_id}/interval", auth=auth, data={"csrf": token, "minutes": "0"}
            ).status_code
            == 422
        )
        assert (
            client.post(
                f"/monitor/{source_id}/interval",
                auth=auth,
                data={"csrf": token, "minutes": "9"},
                follow_redirects=False,
            ).status_code
            == 303
        )
        assert (
            client.post(
                f"/monitor/{source_id}/pause",
                auth=auth,
                data={"csrf": token},
                follow_redirects=False,
            ).status_code
            == 303
        )
        assert (
            client.post(f"/monitor/{source_id}/run", auth=auth, data={"csrf": token}).status_code
            == 409
        )
        assert (
            client.post(
                f"/monitor/{source_id}/resume",
                auth=auth,
                data={"csrf": token},
                follow_redirects=False,
            ).status_code
            == 303
        )
        with sessions() as session:
            assert session.get(Source, source_id).enabled
            assert session.get(Source, source_id).interval_minutes == 9
        assert client.get("/health").json()["scheduler_running"]


def test_login_rate_limit(database):
    sessions, settings, _ = database
    credentials(sessions)
    with TestClient(create_app(settings)) as client:
        for _ in range(5):
            assert client.get("/monitor", auth=("owner", "wrong")).status_code == 401
        assert client.get("/monitor", auth=("owner", "wrong")).status_code == 429


def test_upgrade_phase1_preserves_prices_and_admin(tmp_path):
    database = tmp_path / "phase1.db"
    env = {**os.environ, "RADAR_DATABASE_URL": f"sqlite:///{database}"}
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "0001"],
        check=True,
        env=env,
        capture_output=True,
    )
    with closing(sqlite3.connect(database)) as connection:
        with connection:
            connection.execute("INSERT INTO stores(id,name) VALUES(1,'Existente')")
            connection.execute(
                "INSERT INTO sources(id,store_id,name,connector,enabled,interval_minutes,"
                "consecutive_failures) VALUES(1,1,'Preexistente','unknown',0,45,2)"
            )
            connection.execute(
                "INSERT INTO products(id,source_id,source_product_id,variant_key,name,created_at) "
                "VALUES(1,1,'prod','1kg','Existente','2026-01-01 00:00:00')"
            )
            connection.execute(
                "INSERT INTO price_observations(product_id,price,currency,observed_at) "
                "VALUES(1,123.45,'MXN','2026-01-01 00:00:00')"
            )
            connection.execute(
                "INSERT INTO admin_users(username,password_hash,role,enabled) "
                "VALUES('existing','keep-hash','admin',1)"
            )
    subprocess.run(
        [sys.executable, "-m", "radar.cli", "init-db"], check=True, env=env, capture_output=True
    )
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT price,is_simulated FROM price_observations"
        ).fetchone() == (123.45, 0)
        assert (
            connection.execute("SELECT password_hash FROM admin_users").fetchone()[0] == "keep-hash"
        )
        assert connection.execute(
            "SELECT interval_minutes,enabled,consecutive_failures FROM sources WHERE id=1"
        ).fetchone() == (45, 0, 2)
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0002"


def test_runtime_executes_second_scheduled_pulse(database):
    sessions, settings, source_id = database
    runtime = MonitorRuntime(sessions, settings)
    runtime.start()
    try:
        # Adelantar solo el job en la prueba evita esperar 30 minutos.
        # Se conserva la función de revisión real y la persistencia de APScheduler.
        job_id = f"source-{source_id}"
        runtime.scheduler.modify_job(job_id, next_run_time=utc_now())
        wait_for_success(sessions)
        with sessions.begin() as session:
            session.get(Source, source_id).next_run_at = utc_now() - timedelta(seconds=1)
        runtime.refresh()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with sessions() as session:
                count = session.scalar(
                    select(func.count())
                    .select_from(MonitorRun)
                    .where(MonitorRun.status == "success")
                )
            if count == 2:
                break
            time.sleep(0.02)
        assert count == 2
        with sessions() as session:
            assert session.scalar(select(func.count()).select_from(PriceObservation)) == 6
    finally:
        runtime.stop()
