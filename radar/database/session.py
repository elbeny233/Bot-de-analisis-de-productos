from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def build_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    if url.drivername != "sqlite":
        raise ValueError("Solo se admite SQLite en esta fase")
    in_memory = url.database in {None, "", ":memory:"}
    if not in_memory:
        Path(url.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    options = {"poolclass": StaticPool} if in_memory else {}
    engine = create_engine(
        database_url, connect_args={"check_same_thread": False, "timeout": 15}, **options
    )

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def session_factory(engine: Engine):
    return sessionmaker(bind=engine, expire_on_commit=False)
