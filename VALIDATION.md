# Resultados de validación

## Fase 2 — versión 0.2.0

Entorno ejecutado: Linux, Python 3.12.14.

- Pytest: 47 pruebas pasadas, 0 fallidas, 0 omitidas.
- Ruff check y format --check: correctos.
- pip check: sin dependencias incompatibles.
- Alembic check: sin diferencias entre esquema y modelos.
- Migración 0001 → 0002: conserva precios, configuración de fuente y administrador.
- Servidor Uvicorn real: / y /health 200; phase=2 y scheduler_running=true.
- Control local real: sin credenciales 401; con administrador de prueba 200.
- Revisión automática y manual real por HTTP: dos ejecuciones success,
  tres productos y seis observaciones simuladas; no se crean ofertas ni publicaciones.
- Reinicio real del proceso: conserva próxima revisión, sin duplicar ejecuciones.
- Pruebas incluyen concurrencia, dos pulsos programados, bloqueo entre procesos,
  recuperación de ejecución interrumpida, pausas, errores y reintentos progresivos.
- La prueba de lotes duplicados detectó un fallo de validación; se corrigió antes de entregar.
- Se mantiene un aviso de deprecación de Starlette/AnyIO en TestClient, sin fallo funcional.

Windows de Fase 2: pendiente de validación por el propietario. tzdata se incluye
para que el programador tenga datos de zonas horarias también en Windows.
Docker: archivos preparados, no ejecutado en este entorno.
Fuentes reales, analítica de descuentos, Telegram, pagos y control de membresías:
no implementados ni verificados en esta fase. El control local no es el panel completo.
No se consulta ninguna tienda, se publican ofertas o se revocan accesos durante pruebas.

## Fase 1 — validación previa

20 pruebas pasadas en Linux y servidor/base de datos verificados.
El propietario detectó WinError 32 en Windows en el cierre de una conexión SQLite.
Se corrigió el cierre de conexiones. Posteriormente, el propietario aportó capturas con
20 passed y /health status=ok, además de la página inicial funcionando en Windows.
La entrega de código a GitHub está autorizada por el propietario.
