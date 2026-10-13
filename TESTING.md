# Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check radar tests migrations
.\.venv\Scripts\python.exe -m ruff format --check radar tests migrations
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m alembic check
```

Pytest usa SQLite temporal y no hace consultas externas. Verifica configuración,
sembrado repetible, duplicados y variantes, Decimal, moneda, disponibilidad desconocida,
restricciones monetarias, claves foráneas, puntuación, fechas de membresía, hash y
credenciales, estado sin migrar, migraciones repetidas, reinicio de la aplicación y backup.
El reinicio probado es de FastAPI, **no de APScheduler**, pendiente de Fase 2.
No se prueban aún cálculo de descuentos, clasificación, conectores, Telegram,
vencimientos operativos ni publicaciones: no están implementados.
Alembic check requiere haber ejecutado init-db.

El resultado de la ejecución del entorno se conserva en VALIDATION.md.
