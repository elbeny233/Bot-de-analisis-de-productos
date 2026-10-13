import hashlib
import hmac
import secrets
import time
from collections import deque
from datetime import timedelta
from html import escape
from threading import Lock
from urllib.parse import parse_qs

import anyio
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select

from radar.analytics.service import AnalyticsService
from radar.core.security import verify_password
from radar.dashboard.prices import register_price_routes
from radar.database.models import (
    AdminUser,
    EventLog,
    MonitorRun,
    PriceObservation,
    Product,
    Source,
    utc_now,
)

basic = HTTPBasic(auto_error=False)


def monitor_router() -> APIRouter:
    router = APIRouter()
    csrf_secret = secrets.token_bytes(32)
    failures = {}
    failures_lock = Lock()

    def admin(request: Request, credentials: HTTPBasicCredentials | None = Depends(basic)):
        if not request.app.state.database_ready:
            raise HTTPException(503, "Primero ejecuta init-db")
        address = request.client.host if request.client else "local"
        with failures_lock:
            now = time.monotonic()
            attempts = failures.setdefault(address, deque())
            while attempts and now - attempts[0] >= 60:
                attempts.popleft()
            if len(attempts) >= 5:
                raise HTTPException(429, "Demasiados intentos; espera un minuto")
        user = None
        if credentials and len(credentials.username) <= 100:
            with request.app.state.sessions() as session:
                user = session.scalar(
                    select(AdminUser).where(
                        AdminUser.username == credentials.username,
                        AdminUser.enabled.is_(True),
                        AdminUser.role == "admin",
                    )
                )
        if user is None or not verify_password(credentials.password, user.password_hash):
            with failures_lock:
                if len(failures) > 1024:
                    failures.clear()
                failures.setdefault(address, deque()).append(time.monotonic())
            raise HTTPException(
                401,
                "Credenciales requeridas",
                headers={"WWW-Authenticate": 'Basic realm="Radar local", charset="UTF-8"'},
            )
        return user.username

    def sign(username, payload):
        return hmac.new(csrf_secret, f"{username}:{payload}".encode(), hashlib.sha256).hexdigest()

    def csrf(username):
        payload = f"{int(time.time())}.{secrets.token_hex(16)}"
        return f"{payload}.{sign(username, payload)}"

    def valid_csrf(username, token):
        try:
            timestamp, nonce, signature = token.split(".")
            age = time.time() - int(timestamp)
            return (
                0 <= age <= 900
                and len(nonce) == 32
                and hmac.compare_digest(signature, sign(username, f"{timestamp}.{nonce}"))
            )
        except (ValueError, TypeError):
            return False

    @router.get("/monitor", response_class=HTMLResponse)
    def dashboard(request: Request, username: str = Depends(admin)):
        token = csrf(username)
        hidden = f'<input type="hidden" name="csrf" value="{token}">'
        with request.app.state.sessions() as session:
            sources = session.scalars(select(Source).order_by(Source.id)).all()
            runs = session.scalars(
                select(MonitorRun).order_by(MonitorRun.id.desc()).limit(30)
            ).all()
            events = session.scalars(select(EventLog).order_by(EventLog.id.desc()).limit(20)).all()
            prices = session.execute(
                select(
                    Product.id,
                    Product.name,
                    PriceObservation.price,
                    PriceObservation.currency,
                    PriceObservation.available,
                    PriceObservation.is_simulated,
                )
                .join(Product, PriceObservation.product_id == Product.id)
                .order_by(PriceObservation.id.desc())
                .limit(12)
            ).all()
        price_rows = "".join(
            f'<tr><td><a href="/analysis/{product_id}">{escape(name)}</a></td>'
            f"<td>{price} {escape(currency)}</td>"
            f"<td>{'Desconocida' if available is None else ('Sí' if available else 'No')}</td>"
            f"<td>{'SIMULADO' if simulated else 'No simulado'}</td></tr>"
            for product_id, name, price, currency, available, simulated in prices
        )
        rows = []
        for source in sources:
            state = (
                "Ejecutando"
                if source.running_token
                else ("Activa" if source.enabled else "Pausada")
            )
            forms = []
            for action, label in [
                ("run", "Revisar ahora"),
                ("pause", "Pausar"),
                ("resume", "Reactivar"),
                ("analyze", "Recalcular análisis"),
            ]:
                forms.append(
                    f'<form method="post" action="/monitor/{source.id}/{action}">'
                    f"{hidden}<button>{label}</button></form>"
                )
            forms.append(
                f'<form method="post" action="/monitor/{source.id}/interval">{hidden}'
                f'<label>Minutos <input type="number" name="minutes" min="1" '
                f'max="10080" value="{source.interval_minutes}" required></label>'
                "<button>Guardar intervalo</button></form>"
            )
            rows.append(
                f"<tr><td>{escape(source.name)}<br>#{source.id}</td><td>{state}</td>"
                f"<td>{source.interval_minutes}</td><td>{source.consecutive_failures}</td>"
                f"<td>{escape(str(source.next_run_at or 'Al iniciar'))}</td>"
                f"<td>{''.join(forms)}</td></tr>"
            )
        run_rows = "".join(
            f"<tr><td>{run.id}</td><td>{run.source_id}</td><td>{escape(run.status)}</td>"
            f"<td>{run.attempts}</td><td>{run.observations_count}</td>"
            f"<td>{escape(str(run.started_at))}</td><td>{escape(str(run.finished_at or '—'))}</td>"
            f"<td>{escape(run.error_code or '—')}</td></tr>"
            for run in runs
        )
        event_rows = "".join(
            f"<li>{escape(str(event.created_at))} · {escape(event.level)} · "
            f"{escape(event.event_code)}</li>"
            for event in events
        )
        return HTMLResponse(
            f"""<!doctype html><html lang="es"><meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Monitoreo · Radar Ofertas VIP</title><style>
        body{{font-family:system-ui;margin:2rem;line-height:1.5;background:#f6f8fb;color:#13233c}}
        table{{border-collapse:collapse;background:white;width:100%}}td,th{{padding:.6rem;
        border:1px solid #dde3eb;text-align:left}}.scroll{{overflow:auto}}form{{margin:.4rem 0}}
        button,input{{padding:.45rem}}.notice{{background:#fff2cc;padding:1rem}}
        </style><h1>Radar Ofertas VIP · Monitoreo</h1>
        <p class="notice">DEMOSTRACIÓN: datos simulados. No son ofertas reales.
        No se consulta ninguna tienda ni se publica en Telegram.</p>
        <p>Fechas en UTC. Actualiza la página para ver los cambios.</p>
        <h2>Fuentes</h2><div class="scroll"><table><tr><th>Fuente</th><th>Estado</th>
        <th>Intervalo</th><th>Fallos consecutivos</th><th>Próxima revisión UTC</th>
        <th>Controles</th></tr>{"".join(rows)}</table></div>
        <h2>Últimas 30 ejecuciones</h2><div class="scroll"><table><tr><th>ID</th><th>Fuente</th>
        <th>Resultado</th><th>Intentos</th><th>Precios guardados</th><th>Inicio UTC</th>
        <th>Fin UTC</th><th>Código de error</th></tr>{run_rows}</table></div>
        <h2>Últimos precios registrados</h2><div class="scroll"><table>
        <tr><th>Producto</th><th>Precio</th><th>Disponibilidad</th><th>Tipo de dato</th></tr>
        {price_rows}</table></div><h2>Últimos eventos</h2><ul>{event_rows}</ul>
        <p><a href="/analysis">Historial y análisis</a> · <a href="/offers">Oportunidades</a>
        · <a href="/">Inicio</a></p></html>""",
            headers={
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; "
                "form-action 'self'; frame-ancestors 'none'",
            },
        )

    @router.post("/monitor/{source_id}/{action}")
    async def control(
        source_id: int, action: str, request: Request, username: str = Depends(admin)
    ):
        if request.headers.get("content-type", "").split(";")[0] != (
            "application/x-www-form-urlencoded"
        ):
            raise HTTPException(415, "Formato de formulario requerido")
        raw = await request.body()
        if len(raw) > 4096:
            raise HTTPException(413, "Formulario demasiado grande")
        form = parse_qs(raw.decode("utf-8", errors="replace"))
        if not valid_csrf(username, form.get("csrf", [""])[0]):
            raise HTTPException(403, "Formulario vencido o inválido; actualiza la página")
        if action not in {"run", "pause", "resume", "interval", "analyze"}:
            raise HTTPException(404, "Acción desconocida")
        runtime = request.app.state.monitor
        if runtime is None and action != "analyze":
            raise HTTPException(503, "El programador está deshabilitado")
        with request.app.state.sessions.begin() as session:
            source = session.get(Source, source_id)
            if source is None:
                raise HTTPException(404, "Fuente desconocida")
            if action == "pause":
                source.enabled = False
            elif action == "resume":
                source.enabled = True
                source.consecutive_failures = 0
                source.next_run_at = utc_now()
            elif action == "interval":
                try:
                    minutes = int(form.get("minutes", [""])[0])
                except ValueError:
                    raise HTTPException(422, "Intervalo inválido") from None
                if not 1 <= minutes <= 10080:
                    raise HTTPException(422, "Intervalo permitido: 1 a 10080 minutos")
                source.interval_minutes = minutes
                source.next_run_at = utc_now() + timedelta(minutes=minutes)
            session.add(EventLog(level="INFO", event_code=f"admin_monitor_{action}"))
        if action == "run":
            status = await anyio.to_thread.run_sync(runtime.run_source, source_id)
            if status in {"paused", "already_running", "failed"}:
                raise HTTPException(409, f"Revisión no completada: {status}")
        if action == "analyze":
            analyzer = AnalyticsService(request.app.state.sessions, request.app.state.settings)
            await anyio.to_thread.run_sync(analyzer.analyze_source, source_id)
        if runtime is not None:
            runtime.refresh()
        return RedirectResponse("/monitor", status_code=303)

    register_price_routes(router, admin)
    return router
