# Actualizar a Fase 3 sin perder datos (desde Fase 1 o 2)

Conserva la carpeta original, .venv, data, backups y .env; no los reemplaces con el ZIP.

1. En el PowerShell donde está el servidor pulsa Ctrl+C y espera el cierre.
2. En PowerShell de la carpeta ORIGINAL respalda:

```powershell
.\.venv\Scripts\python.exe -m radar.cli backup
```

3. Descarga el ZIP actualizado desde GitHub y extráelo en OTRA carpeta.
4. Copia desde la nueva las carpetas completas **radar**, **migrations** y **tests** a la
   original, reemplazando los archivos. No las anides: debe existir radar/main.py.
5. Copia también los archivos **pyproject.toml**, **requirements-dev.lock**, **alembic.ini**,
   **.env.example** y los documentos **README.md**, **ARCHITECTURE.md**, **ANALYTICS.md**,
   **CONFIGURATION.md**, **INSTALL_WINDOWS.md**, **UPDATE_WINDOWS.md**, **TESTING.md**,
   **DEPLOYMENT.md**, **VALIDATION.md** y **CHANGELOG.md**. Conserva tu .env.
6. En PowerShell de la carpeta ORIGINAL ejecuta uno por uno:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
.\.venv\Scripts\python.exe -m radar.cli init-db
.\.venv\Scripts\python.exe -m pytest -q
```

Detente si hay errores. La migración 0003 agrega análisis y metadatos, conservando datos,
pausas, intervalos y administradores. No ejecuta downgrade ni borra observaciones.
7. Usa tu usuario **propietario** y tu contraseña existentes. Si es instalación nueva,
   crea el administrador siguiendo INSTALL_WINDOWS.md; no necesitas recrearlo al actualizar.
8. Inicia:

```powershell
.\.venv\Scripts\python.exe -m uvicorn radar.main:app --host 127.0.0.1 --port 8000
```

9. Abre http://127.0.0.1:8000/monitor. Pulsa **Revisar ahora** (si la fuente está activa)
   o **Recalcular análisis**. Abre **Historial y análisis**, selecciona un producto y
   comprueba cantidad, periodo, mínimo, máximo, promedio, mediana y puntuación.
10. En /health se espera phase=3 y schema_revision=0003. Los datos siguen siendo SIMULADOS.

Información insuficiente y una lista de oportunidades vacía son normales al inicio:
la demo tiene precios fijos y un historial corto. No fabrica ofertas para llenar la pantalla.
Las variantes o modelos distintos se separan; los productos legados compatibles conservan
su historial. Una separación conservadora puede crear otro producto si faltan metadatos.
