# Windows 11 — instalación nueva

Instala Python 3.12.10 de python.org. No necesitas Git ni Docker.
Descarga el proyecto desde GitHub (Code → Download ZIP), extrae y abre PowerShell
**en la carpeta que contiene pyproject.toml**, usando Alt+D y escribiendo powershell.
Si ya tienes Fase 1 o 2, sigue [UPDATE_WINDOWS.md](UPDATE_WINDOWS.md).

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m radar.cli init-db
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m radar.cli create-admin --username propietario
.\.venv\Scripts\python.exe -m uvicorn radar.main:app --host 127.0.0.1 --port 8000
```

Ejecuta uno por uno y detente si hay ERROR. create-admin pide una contraseña de
mínimo 12 caracteres y confirmación; al escribirla no se muestran caracteres (normal).
Si ya existe el administrador, no vuelvas a crearlo: usa sus credenciales.

Abre http://127.0.0.1:8000 y entra al control de monitoreo. Introduce propietario y
la contraseña elegida. Verás datos SIMULADOS, próximas revisiones, estados y registros.
Pulsa Revisar ahora y comprueba una ejecución success con tres precios guardados.
La disponibilidad desconocida se conserva. No son ofertas reales ni se envían mensajes.

En /health se espera status=ok, phase=3, schema_revision=0003,
scheduler_running=true y publications_enabled=false. Deja PowerShell abierto.
Detener: Ctrl+C. Reiniciar: repetir el comando uvicorn. Si otra instancia está abierta,
detenerla antes: no usar múltiples workers ni borrar el archivo .monitor.lock.

Pruebas de Fase 3 ejecutadas en Linux; Windows requiere validación del propietario.
Las Fases 1 y 2 ya se verificaron por el propietario en Windows (20 y 47 pruebas pasadas).

Entra en Historial y análisis y selecciona un producto. Inicialmente verás Información
insuficiente, porque no existe aún un historial distribuido durante varios días.
Esto no es un fallo. Oportunidades puede estar vacía: los precios de demo son fijos.
