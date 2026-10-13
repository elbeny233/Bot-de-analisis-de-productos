# Operación local y despliegue futuro

Esta versión prepara desarrollo local; no está lista para uso comercial o exposición pública.
No requiere hosting ni suscripciones de pago. No se publica en Internet.

## Inicio, parada y actualización

Arrancar con uvicorn en 127.0.0.1:8000. Parar con Ctrl+C y repetir para reiniciar.
Antes de actualizar: respaldar, parar el proceso y conservar .env/data/backups.
Después de obtener una versión revisada, reinstalar requirements-dev.lock y el paquete,
ejecutar init-db, pytest y /health. No usar git reset o eliminar datos para actualizar.

## Respaldo y recuperación (PowerShell)

```powershell
.\.venv\Scripts\python.exe -m radar.cli backup
```

La API de respaldo de SQLite permite copia consistente. El resultado se escribe en
backups/radar-fechaUTC.db; conservarlo fuera del equipo y protegerlo como dato privado.
Para restaurar, parar la aplicación, respaldar el estado actual y copiar el respaldo
seleccionado a data/radar.db; no sobrescribir la única copia. Reiniciar y consultar /health.
La restauración es una operación del propietario; no se ejecuta automáticamente.

## Docker futuro

Se proporcionan Dockerfile y compose.yaml para ejecutar la misma Fase 3 con volumen
persistente y puerto ligado a loopback. No se han validado con Docker en este entorno.
No publicar puertos públicamente sin autenticación, revisión de seguridad y HTTPS.

```powershell
docker compose up --build -d
docker compose logs -f
docker compose stop
```

No ejecutar `docker compose down -v`: elimina el volumen de datos.
Antes de operación comercial faltan el panel completo e integraciones
reales verificadas, revisión de dependencias, observabilidad y política de respaldo.

Usar un único worker. El proceso adquiere un bloqueo del SO por base de datos; no
eliminarlo para iniciar otra instancia. next_run_at se restaura; los procesos no sobreviven
a snapshots. Al pausar una fuente, su ejecución ya iniciada finaliza normalmente.

La operación validada usa migraciones ascendentes. No ejecutar downgrade en tu base de
trabajo: elimina datos analíticos y requiere un respaldo y una decisión del propietario.
No crear ofertas reales ni activar publicaciones a partir de datos simulados.
