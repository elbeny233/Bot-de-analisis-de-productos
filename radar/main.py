import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from radar.core.config import Settings, get_settings
from radar.database.session import build_engine


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logging.basicConfig(level=settings.log_level)
        app.state.engine = build_engine(settings.database_url)
        try:
            yield
        finally:
            app.state.engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/", response_class=HTMLResponse)
    def home():
        return """<!doctype html><html lang="es"><meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Radar Ofertas VIP</title>
        <body style="font-family:system-ui;max-width:720px;margin:4rem auto;padding:1rem">
        <h1>Radar Ofertas VIP</h1><p>Fundación · Fase 1</p>
        <p>La base del proyecto está instalada. El monitoreo, el panel administrativo
        y las publicaciones se incorporarán en las siguientes fases.</p>
        <p><a href="/health">Comprobar estado de la base de datos</a></p></body></html>"""

    @app.get("/health")
    def health():
        try:
            with app.state.engine.connect() as connection:
                revision = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                connection.execute(text("SELECT COUNT(*) FROM categories")).scalar_one()
            if revision != "0001":
                return JSONResponse(status_code=503, content={"status": "migration_required"})
        except SQLAlchemyError:
            return JSONResponse(status_code=503, content={"status": "database_not_ready"})
        return {
            "status": "ok",
            "phase": 1,
            "schema_revision": revision,
            "publications_enabled": False,
        }

    return app


app = create_app()
