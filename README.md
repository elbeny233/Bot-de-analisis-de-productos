# Radar Ofertas VIP

Plataforma de ofertas para México. Versión 0.1.0: **Fase 1 — Fundación**.

Implementado: configuración validada, FastAPI local, SQLite/SQLAlchemy, migración
Alembic, 11 categorías, modelos iniciales, hash de contraseñas y respaldo consistente.
No hay aún monitoreo, análisis de descuentos, tiendas conectadas, login web,
publicaciones Telegram ni gestión operativa de suscripciones. No contiene ofertas reales.

## Inicio rápido

Desde la raíz del proyecto con Python 3.12:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/python -m radar.cli init-db
.venv/bin/python -m uvicorn radar.main:app --host 127.0.0.1 --port 8000
```

Windows: [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md).
El endpoint `/health` responde 200 solo con base de datos migrada; 503 si falta.
La página raíz identifica explícitamente la fase actual, no es el panel administrativo.

## Documentación

- [Arquitectura](ARCHITECTURE.md)
- [Configuración](CONFIGURATION.md)
- [Pruebas](TESTING.md)
- [Operación y despliegue](DEPLOYMENT.md)
- [Cambios](CHANGELOG.md)

La siguiente fase es el programador y un conector simulado; no necesita credenciales.
Los módulos futuros solo reservan espacios de nombres y no se consideran implementados.
