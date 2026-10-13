# Actualizar Fase 1 a Fase 2 sin perder tus datos

No borres la carpeta original, .venv, data, backups ni .env.

1. Detén el servidor en su PowerShell con Ctrl+C.
2. En la carpeta ORIGINAL crea un respaldo:

```powershell
.\.venv\Scripts\python.exe -m radar.cli backup
```

3. Descarga el ZIP actualizado de GitHub y extráelo en OTRA carpeta.
4. Desde la carpeta nueva copia las carpetas completas **radar**, **migrations** y **tests**
   a la carpeta original. Acepta reemplazar archivos. No las anides: debe existir
   radar/main.py, no radar/radar/main.py.
5. Copia también **pyproject.toml**, **requirements-dev.lock**, **alembic.ini**,
   **README.md**, **ARCHITECTURE.md**, **CONFIGURATION.md**, **TESTING.md**,
   **INSTALL_WINDOWS.md**, **UPDATE_WINDOWS.md**, **DEPLOYMENT.md**,
   **VALIDATION.md**, **CHANGELOG.md** y **.env.example** desde la nueva a la original.
   .env.example es solo una plantilla; conserva tu .env.
6. En PowerShell de la carpeta ORIGINAL ejecuta, uno por uno:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
.\.venv\Scripts\python.exe -m radar.cli init-db
.\.venv\Scripts\python.exe -m pytest -q
```

init-db aplica 0002 y conserva los datos anteriores. Si algo falla, no continúes ni
restaures sobrescribiendo datos: guarda el mensaje y consulta el diagnóstico.

7. Crea tu administrador si aún no existe:

```powershell
.\.venv\Scripts\python.exe -m radar.cli create-admin --username propietario
```

La contraseña debe tener al menos 12 caracteres. No se ve al escribirla; confírmala.
8. Arranca:

```powershell
.\.venv\Scripts\python.exe -m uvicorn radar.main:app --host 127.0.0.1 --port 8000
```

9. Abre http://127.0.0.1:8000, entra al control de monitoreo y autentícate.
   Espera la primera revisión o pulsa Revisar ahora. Debe aparecer success y tres
   precios simulados. Cambiar intervalo, pausar y reactivar son acciones locales.
   Una fuente pausada no se ejecuta; reactívala explícitamente cuando corresponda.
