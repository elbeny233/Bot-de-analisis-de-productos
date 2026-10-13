from dataclasses import asdict
from decimal import Decimal
from html import escape

from fastapi import Depends, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from radar.analytics.history import summarize
from radar.database.models import Offer, PriceAnalysis, PriceObservation, Product

CLASSIFICATIONS = {
    "history_confirmed": "Descuento confirmado por historial observado",
    "store_announced": "Descuento anunciado por tienda; sin confirmar",
    "possible_price_error": "Posible error de precio; requiere revisión",
    "insufficient_information": "Información insuficiente",
    "no_discount": "Sin descuento relevante",
}
REASONS = {
    "insufficient_history": "Historial insuficiente",
    "low_identity_confidence": "Identificación del producto de baja confianza",
    "unavailable": "No disponible",
    "availability_unknown": "Disponibilidad desconocida",
    "stale_observation": "Consulta desactualizada",
    "future_observation": "Fecha de consulta en el futuro",
    "shipping_unknown": "Envío desconocido",
    "simulated_data": "DATOS SIMULADOS",
    "price_anomaly": "Precio anómalo; no asumir que es válido",
    "shipping_erases_discount": "El envío elimina el ahorro",
    "announced_unconfirmed": "El precio anunciado no confirma un descuento real",
}
HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; "
    "frame-ancestors 'none'",
}


def page(title, content):
    return HTMLResponse(
        f"""<!doctype html><html lang="es"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{escape(title)} · Radar Ofertas VIP</title><style>
    body{{font-family:system-ui;max-width:1200px;margin:2rem auto;padding:1rem;line-height:1.5}}
    table{{border-collapse:collapse;width:100%}}th,td{{padding:.6rem;border:1px solid #ddd}}
    .scroll{{overflow:auto}}.notice{{background:#fff2cc;padding:1rem}}
    </style><h1>{escape(title)}</h1><p class="notice">DEMOSTRACIÓN: los datos de la fuente demo
    son simulados, no ofertas reales. No se publica en Telegram. Los mínimos y medianas
    corresponden únicamente al periodo observado.</p>{content}
    <p><a href="/analysis">Productos</a> · <a href="/offers">Oportunidades</a> ·
    <a href="/monitor">Monitoreo</a></p></html>""",
        headers=HEADERS,
    )


def availability(value):
    return "Desconocida" if value is None else ("Sí" if value else "No")


def value(number):
    return "—" if number is None else str(number)


def register_price_routes(router, admin):
    @router.get("/analysis", response_class=HTMLResponse)
    def catalogue(
        request: Request, q: str = Query(default="", max_length=100), username: str = Depends(admin)
    ):
        with request.app.state.sessions() as session:
            query = select(Product)
            if q:
                query = query.where(Product.name.ilike(f"%{q}%"))
            products = session.scalars(query.order_by(Product.id.desc()).limit(100)).all()
        links = "".join(
            f'<li><a href="/analysis/{item.id}">{escape(item.name)}</a> '
            f"· {'SIMULADO' if item.is_simulated else 'No simulado'}</li>"
            for item in products
        )
        return page(
            "Historial y análisis",
            '<form method="get"><label>Buscar producto '
            f'<input name="q" maxlength="100" value="{escape(q, quote=True)}"></label>'
            "<button>Buscar</button></form><p>Hasta 100 productos.</p><ul>" + links + "</ul>",
        )

    @router.get("/analysis/{product_id}", response_class=HTMLResponse)
    def detail(product_id: int, request: Request, username: str = Depends(admin)):
        with request.app.state.sessions() as session:
            product = session.get(Product, product_id)
            if product is None:
                raise HTTPException(404, "Producto desconocido")
            scopes = session.execute(
                select(PriceObservation.currency, PriceObservation.is_simulated)
                .where(PriceObservation.product_id == product_id)
                .distinct()
            ).all()
            sections = []
            for currency, simulated in scopes:
                summary = summarize(session, product_id, currency, simulated)
                recent = session.scalars(
                    select(PriceObservation)
                    .where(
                        PriceObservation.product_id == product_id,
                        PriceObservation.currency == currency,
                        PriceObservation.is_simulated.is_(simulated),
                    )
                    .order_by(PriceObservation.observed_at.desc(), PriceObservation.id.desc())
                    .limit(30)
                ).all()
                analysis = (
                    session.scalar(
                        select(PriceAnalysis).where(PriceAnalysis.observation_id == recent[0].id)
                    )
                    if recent
                    else None
                )
                changes = " · ".join(
                    f"{label}: {value(number)}% (base UTC: "
                    f"{escape(str(summary.baseline_dates[label] or 'sin datos'))})"
                    for label, number in summary.changes.items()
                )
                description = "Aún sin análisis: ejecuta Revisar ahora o Recalcular análisis."
                if analysis:
                    reasons = "; ".join(REASONS.get(code, code) for code in analysis.reasons) or "—"
                    classification = escape(
                        CLASSIFICATIONS.get(analysis.classification, analysis.classification)
                    )
                    labels = {
                        "discount": "Descuento",
                        "history": "Historial",
                        "availability": "Disponibilidad",
                        "freshness": "Vigencia",
                        "costs": "Costos",
                        "identity": "Identificación",
                    }
                    components = " · ".join(
                        f"{labels.get(key, key)}: {number:g} puntos"
                        for key, number in analysis.components.items()
                    )
                    description = (
                        f"<strong>{classification}</strong>"
                        f"<p>Puntuación: {analysis.score}/100 · Referencia (mediana previa): "
                        f"{value(analysis.reference_price)} {escape(currency)} "
                        "· Descuento de producto: "
                        f"{value(analysis.discount_percent)}% · Incluyendo envío conocido: "
                        f"{value(analysis.effective_discount_percent)}%</p>"
                        f"<p>Descuento anunciado (no usado como referencia): "
                        f"{value(analysis.advertised_discount_percent)}%</p>"
                        f"<p>Historial previo: {analysis.history_count} observaciones, "
                        f"{analysis.history_days} días entre la primera y la última, "
                        f"{analysis.distinct_days} días distintos.</p>"
                        f"<p>Motivos: {escape(reasons)}.</p>"
                        "<p>Apta al analizar para revisión de alta confianza: "
                        f"{'Sí' if analysis.review_candidate else 'No'}. "
                        "No implica publicación.</p>"
                        f"<p>Análisis UTC: {escape(str(analysis.analyzed_at))}. "
                        "Recalcula si la información perdió vigencia.</p>"
                        f"<p>Puntos antes de límites de confianza: {escape(components)}</p>"
                    )
                price_rows = "".join(
                    f"<tr><td>{escape(str(row.observed_at))}</td><td>{row.price}</td>"
                    f"<td>{value(row.shipping_cost)}</td>"
                    "<td>"
                    f"{availability(row.available)}"
                    "</td>"
                    f"<td>{escape(row.conditions or '—')}</td></tr>"
                    for row in recent
                )
                sections.append(f"""<h2>{escape(currency)} ·
                {"SIMULADO" if simulated else "No simulado"}</h2>
                <p>Periodo observado UTC: {escape(str(summary.period_start))} a
                {escape(str(summary.period_end))}. Observaciones: {summary.count}.</p>
                <p>Último: {value(summary.latest)} · Mínimo del periodo observado:
                {value(summary.minimum)}
                · Máximo: {value(summary.maximum)} · Promedio: {value(summary.average)}
                · Mediana: {value(summary.median)}</p><p>Variación: {changes}</p>
                <h3>Último análisis</h3>{description}<h3>Últimos 30 precios</h3>
                <div class="scroll"><table><tr><th>Consulta UTC</th><th>Precio</th><th>Envío</th>
                <th>Disponible</th><th>Condiciones</th></tr>{price_rows}</table></div>""")
        return page(product.name, "".join(sections) or "<p>Sin observaciones todavía.</p>")

    @router.get("/products/{product_id}/history")
    def history_api(
        product_id: int,
        request: Request,
        currency: str = Query(default="MXN", pattern="^[A-Z]{3}$"),
        simulated: bool = False,
        username: str = Depends(admin),
    ):
        with request.app.state.sessions() as session:
            if session.get(Product, product_id) is None:
                raise HTTPException(404, "Producto desconocido")
            summary = summarize(session, product_id, currency, simulated)
        return jsonable_encoder(asdict(summary), custom_encoder={Decimal: str})

    @router.get("/offers", response_class=HTMLResponse)
    def offers(request: Request, username: str = Depends(admin)):
        with request.app.state.sessions() as session:
            entries = session.execute(
                select(Offer, PriceObservation, Product)
                .join(PriceObservation, Offer.observation_id == PriceObservation.id)
                .join(Product, PriceObservation.product_id == Product.id)
                .order_by(Offer.id.desc())
                .limit(100)
            ).all()
        rows = "".join(
            f'<tr><td><a href="/analysis/{product.id}">{escape(product.name)}</a></td>'
            f"<td>{observation.price} {escape(observation.currency)}</td><td>{offer.score}/100</td>"
            f"<td>{escape(CLASSIFICATIONS.get(offer.classification, offer.classification))}</td>"
            f"<td>{escape(offer.status)}</td>"
            f"<td>{'SIMULADO' if observation.is_simulated else 'No simulado'}</td></tr>"
            for offer, observation, product in entries
        )
        return page(
            "Oportunidades pendientes de revisión",
            """<p>Hasta 100 registros.
        Todo candidato nuevo queda pendiente. No hay aprobación ni publicación automática.</p>
        <div class="scroll"><table><tr><th>Producto</th><th>Precio</th><th>Puntuación</th>
        <th>Clasificación</th><th>Estado</th><th>Tipo de dato</th></tr>"""
            + rows
            + "</table></div>",
        )
