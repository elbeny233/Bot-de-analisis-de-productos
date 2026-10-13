# Arquitectura inicial

Flujo implementado: variables/.env → Settings → FastAPI → SQLAlchemy → SQLite.
La CLI aplica Alembic, inicializa categorías y crea respaldos o un administrador local.
Las rutas de esta fase no permiten consultar datos privados ni modificar el sistema.

| Módulo | Estado en Fase 1 |
|---|---|
| core | Configuración, validación, hash PBKDF2-SHA256 y registros de arranque |
| database | 13 tablas, motor, sesiones, integridad y categorías iniciales |
| main/cli | Página inicial, readiness, inicialización y respaldos |
| collectors/catalog/analytics | Espacios reservados; Fases 2–4 |
| scheduler/alerts/telegram | Espacios reservados; Fases 2 y 5 |
| subscriptions/dashboard | Espacios reservados; Fases 6–7 |

## Persistencia

Category, Store, Source, Product, PriceObservation, Offer, AdminUser, Member,
Membership, Payment, MonitorRun, Publication y EventLog.
La identidad de producto incluye fuente, identificador y variante obligatoria.
Cada observación conserva su moneda; la futura analítica deberá filtrar por moneda.
La disponibilidad desconocida es NULL. Precios monetarios usan Numeric(14,2).
SQLite conserva fechas sin zona; el contrato del proyecto es guardar y leer UTC.
El motor habilita claves foráneas en cada conexión y espera hasta 15 s ante bloqueos.
No se ejecuta `create_all` en producción: los cambios se versionan en Alembic.
La migración inicial es explícita e independiente de futuros cambios de modelos.

## Seguridad y límites

PBKDF2-SHA256: salt aleatorio de 16 bytes, 600000 iteraciones, comparación constante.
No hay credenciales predeterminadas; create-admin solicita la contraseña sin mostrarla.
El login web aún no existe. No exponer a Internet. Solo enlazar a 127.0.0.1.
No hay peticiones a URLs de productos en esta fase. Antes de incorporarlas se requiere
validación de destino, prevención de SSRF, permisos de fuente y límites de consulta.
No se almacena ni registra un token de Telegram. Las publicaciones están bloqueadas.
SQLite es adecuada para desarrollo local, no se promete concurrencia comercial.
