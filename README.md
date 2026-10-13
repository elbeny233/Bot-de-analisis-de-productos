# Radar Ofertas VIP

Versión 0.3.0 — **Fase 3: inteligencia de precios**.

Aplicación local gratuita para preparar la futura detección de ofertas de México.
**Todos los productos de demostración son SIMULADOS; no son ofertas reales.**
No consulta tiendas, no publica en Telegram y no gestiona cobros o accesos externos.

## Funciones implementadas

- FastAPI, SQLite/SQLAlchemy y migraciones Alembic; 11 categorías iniciales.
- Conector reemplazable de demostración: tres presentaciones/productos simulados.
- APScheduler con intervalo inicial de 30 minutos y configuración por fuente.
- Persistencia de productos, observaciones, ejecuciones y códigos de eventos.
- Exclusión de revisiones simultáneas, reintentos progresivos y pausa tras fallos.
- Recuperación de ejecuciones interrumpidas y programación guardada al reiniciar.
- Control local de monitoreo autenticado: revisión manual, pausa, reactivación e intervalos.
- Contraseñas con hash, protección CSRF y respaldos SQLite consistentes.
- Normalización conservadora y clasificación de categorías.
- Historial por producto/moneda/tipo con estadísticas y variaciones 24h/7d/30d.
- Referencia por mediana previa, puntuación configurable y advertencias de confianza.
- Pantallas autenticadas de historial, análisis y oportunidades pendientes.

El control local no sustituye el panel completo de la Fase 6.
No hay aún fuentes reales, Telegram ni gestión de membresías.

## Inicio (Linux, Python 3.12)

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/python -m radar.cli init-db
.venv/bin/python -m radar.cli create-admin --username propietario
.venv/bin/python -m uvicorn radar.main:app --host 127.0.0.1 --port 8000
```

Para Windows: [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md).
Para actualizar tu instalación anterior: [UPDATE_WINDOWS.md](UPDATE_WINDOWS.md).
Ejecutar desde la raíz; una sola instancia y un solo worker por base de datos.
La primera revisión se ejecuta al arrancar una fuente nueva. Las siguientes respetan su
intervalo. Una fuente pausada permanece pausada después de init-db y de reiniciar.

## Documentación

[Arquitectura](ARCHITECTURE.md) · [Fórmula y límites](ANALYTICS.md) · [Configuración](CONFIGURATION.md) ·
[Pruebas](TESTING.md) · [Operación](DEPLOYMENT.md) · [Resultados](VALIDATION.md) ·
[Cambios](CHANGELOG.md).

Al iniciar, los datos de demo pueden indicar Información insuficiente: no se inventa
un historial largo ni descuentos. Candidatos nuevos siempre quedan pendientes.
Siguiente fase: evaluación de fuentes reales gratuitas y compatibles con sus condiciones.
