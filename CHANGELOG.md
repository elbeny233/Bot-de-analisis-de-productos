# Cambios

## 0.2.0 — Fase 2

- Conector simulado y contrato normalizado con validación.
- APScheduler por fuente, ejecuciones persistentes, reintentos y pausas.
- Bloqueos de proceso y fuente, recuperación tras reinicio.
- Control local con contraseña, CSRF, revisión manual e intervalos.
- Migración 0002 conserva datos y agrega estado de monitoreo y marcas de simulación.
- Pruebas de monitoreo y guía de actualización sin borrar datos.

## Corrección de compatibilidad Windows

- Cierre explícito de conexiones SQLite al respaldar y validar respaldos.
- Corrige WinError 32 al eliminar el respaldo temporal en las pruebas.

## 0.1.0 — Fase 1

- Estructura modular Python/FastAPI y configuración mediante entorno.
- Modelos SQLAlchemy, migración Alembic, claves foráneas y restricciones.
- Inicialización repetible de 11 categorías y respaldo SQLite.
- Hash administrativo seguro, sin cuenta predeterminada ni login web todavía.
- Readiness HTTP, pruebas de fundación y documentación Windows/Linux.
- Sin monitoreo ni integración externa; no se publican ofertas ni se retiran miembros.
