# Validación de Fase 1

Entorno ejecutado: Linux, Python 3.12.14. Fecha: 2026-10-13.

- Pytest: 20 pruebas pasadas, 0 fallidas, 0 omitidas.
- Reinstalación desde requirements-dev.lock en un segundo venv limpio: correcta;
  mismas 20 pruebas pasadas.
- Ruff check y format --check: correctos.
- pip check: sin dependencias incompatibles.
- Alembic check: sin diferencias entre esquema migrado y modelos.
- HTTP real con Uvicorn: / y /health responden 200;
  health devuelve status=ok, phase=1, schema_revision=0001, publicaciones deshabilitadas.
- SQLite PRAGMA integrity_check: ok; 11 categorías persistentes.
- Tests de respaldo validan integridad y categorías en la copia.
- Un aviso de deprecación de Starlette/AnyIO en TestClient, sin fallo funcional.

No ejecutado: Windows, Docker, tiendas, Telegram, pagos, monitor ni login web.
Los últimos cinco no están implementados en la Fase 1.
Durante las pruebas no hubo publicaciones de ofertas, cobros ni revocaciones de miembros.
La entrega del código a GitHub es una operación separada autorizada por el propietario.
El archivo vacío original main se conserva.

Se guardaron install_script y start_skill en el borrador del entorno cloud.
El propietario debe revisar, guardar y publicar el entorno en su configuración.
Guardar el borrador no equivale a publicación ni validación de una tarea restaurada.

## Corrección posterior

El propietario ejecutó las pruebas en Windows: 19 pasaron y una falló con
WinError 32 al eliminar un respaldo cuya conexión seguía abierta. Se corrigió
el cierre explícito de conexiones en la CLI y las pruebas. La suite corregida
pasa 20 pruebas en Linux; pendiente de repetir en Windows por el propietario.
