# Instalación en Windows 11 (PowerShell)

Instala Python 3.12 de python.org y Git. Descarga o copia **los archivos de esta versión**
a una carpeta local. En GitHub puedes usar Code → Download ZIP y extraer el archivo.
Abre PowerShell en la carpeta que contiene pyproject.toml y alembic.ini.

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m radar.cli init-db
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check radar tests migrations
.\.venv\Scripts\python.exe -m uvicorn radar.main:app --host 127.0.0.1 --port 8000
```

No requiere activar scripts ni modificar la política de ejecución de PowerShell.
Abre http://127.0.0.1:8000 en tu computadora. En otra terminal, desde la misma carpeta:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Resultado esperado: status=ok, phase=1, schema_revision=0001,
publications_enabled=False. Detén con Ctrl+C; reinicia con el comando uvicorn anterior.
Opcional, después de migrar (no habilita un login web):

```powershell
.\.venv\Scripts\python.exe -m radar.cli create-admin --username propietario
.\.venv\Scripts\python.exe -m radar.cli backup
```

No introduzcas secretos en GitHub. Windows requiere validación por el propietario:
el desarrollo y las pruebas de esta entrega se ejecutan en Linux con Python 3.12.
