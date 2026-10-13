import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from radar.core.config import Settings, get_settings
from radar.dashboard.monitor import monitor_router
from radar.database.session import build_engine, session_factory
from radar.scheduler.runtime import MonitorRuntime

SCHEMA_REVISION = "0003"


def database_ready(engine):
    try:
        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            connection.execute(text("SELECT COUNT(*) FROM sources")).scalar_one()
            connection.execute(text("SELECT COUNT(*) FROM price_analyses")).scalar_one()
        return revision == SCHEMA_REVISION
    except SQLAlchemyError:
        return False


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logging.basicConfig(level=settings.log_level)
        logging.getLogger("apscheduler").setLevel(logging.WARNING)
        app.state.engine = build_engine(settings.database_url)
        app.state.sessions = session_factory(app.state.engine)
        app.state.settings = settings
        app.state.monitor = None
        app.state.database_ready = database_ready(app.state.engine)
        try:
            if settings.scheduler_enabled and app.state.database_ready:
                runtime = MonitorRuntime(app.state.sessions, settings)
                runtime.start()
                app.state.monitor = runtime
            yield
        finally:
            if app.state.monitor is not None:
                app.state.monitor.stop()
            app.state.engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version="0.3.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.include_router(monitor_router())

    @app.get("/", response_class=HTMLResponse)
    def home():
        return """<!doctype html><html lang="es"><meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Radar Ofertas VIP</title>
        <body style="font-family:system-ui;max-width:720px;margin:4rem auto;padding:1rem">
        <h1>Radar Ofertas VIP</h1><p>Inteligencia de precios · Fase 3</p>
        <p>DEMOSTRACIÓN: los productos y precios son simulados. No son ofertas reales.
        No se consulta ninguna tienda ni se publica en Telegram.</p>
        <p>Revisiones automáticas con intervalos configurables, registro de ejecuciones
        y recuperación después de reiniciar.</p>
        <p><a href="/monitor">Control local de monitoreo (requiere administrador)</a></p>
        <p><a href="/analysis">Historial y análisis (requiere administrador)</a></p>
        <p><a href="/health">Comprobar estado de la base de datos</a></p></body></html>"""

    @app.get("/health")
    def health():
        if not database_ready(app.state.engine):
            return JSONResponse(status_code=503, content={"status": "migration_required"})
        return {
            "status": "ok",
            "phase": 3,
            "schema_revision": SCHEMA_REVISION,
            "scheduler_running": (
                app.state.monitor is not None and app.state.monitor.scheduler.running
            ),
            "publications_enabled": False,
        }

    return app


app = create_app()
