# Pruebas de Fase 2

Desde la raíz (PowerShell):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check radar tests migrations
.\.venv\Scripts\python.exe -m ruff format --check radar tests migrations
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m alembic check
```

Alembic check requiere init-db. Las pruebas crean SQLite temporal; no consultan tiendas,
Telegram ni modifican miembros. Cierre explícito de SQLite preserva compatibilidad Windows.

Cobertura de fundación: configuración, categorías repetibles, duplicados/variantes,
Decimal, moneda, disponibilidad desconocida, restricciones, contraseñas, respaldo,
migración y arranque HTTP. Cobertura de monitoreo: validación del contrato, demo,
historial persistente, reintentos progresivos, pausa tras fallos, fuente no disponible,
lotes duplicados/incompletos, independencia de fuentes, exclusión entre dos servicios,
bloqueo entre procesos, recuperación y reinicio del programador, dos pulsos programados,
intervalos por fuente, autenticación, CSRF, controles y límites de login.
La migración Fase 1 → Fase 2 se prueba con precios, configuración y administrador existentes.

Los tests de pulsos adelantan el job y la fecha de ejecución guardada; no esperan 30 minutos
ni sustituyen la función de obtención/persistencia. El servidor se valida también con
peticiones HTTP reales. Resultados y limitaciones en VALIDATION.md.
Pendientes: descuentos, clasificación analítica, fuentes reales, Telegram y membresías.
