# Arquitectura — Fases 1–3

Settings → FastAPI → MonitorRuntime/APScheduler → MonitorService → Collector.
Los datos normalizados de Collector se validan antes de una transacción de persistencia.
SQLAlchemy → SQLite almacena productos, precios, fuentes, próxima revisión y ejecuciones.
La obtención de datos se separa del análisis: después de persistir se ejecuta
AnalyticsService en otra transacción. Una falla de análisis no revierte los precios.

## Módulos

| Módulo | Implementado |
|---|---|
| core | Configuración, hash PBKDF2-SHA256, bloqueo del SO |
| collectors | Contrato normalizado, errores tipificados, demo sin red |
| database | 14 modelos, motor, migraciones 0001/0002/0003, inicialización repetible |
| scheduler | Reintentos, persistencia, recuperación, programación por fuente |
| dashboard | Control local de monitoreo; el panel completo es Fase 6 |
| main/cli | Readiness, inicialización, administrador, respaldos |
| catalog/analytics | Normalización, categorías, estadísticas y puntuación |
| alerts/telegram/subscriptions | Reservados para fases posteriores |

## Concurrencia y recuperación

Un archivo junto a la base de datos (`radar.db.monitor.lock`) se bloquea mediante flock
(Linux) o msvcrt (Windows). El SO libera el bloqueo al morir el proceso; el archivo puede
permanecer y no debe borrarse para forzar otra instancia. Una segunda instancia falla.
Usar exactamente un worker de Uvicorn y no usar --reload en operación continua.
Cada fuente reclama running_token con UPDATE condicional. Las ejecuciones programadas
y manuales comparten este mecanismo. APScheduler usa max_instances=1 y coalesce=True.

next_run_at se guarda en SQLite y los jobs se reconstruyen al arrancar. Revisiones vencidas
se agrupan en un único pulso; no se reproducen todos los intervalos perdidos. Tras obtener
el bloqueo, los runs que estaban running pasan a interrupted con fecha y código de reinicio.
La configuración y las pausas existentes no se sobrescriben al sembrar la fuente demo.
El programador sincroniza configuración cada cinco segundos; los controles sincronizan
inmediatamente. Una revisión en curso finaliza al pausar su fuente.

## Fallos

Por revisión: hasta tres intentos; errores temporales esperan 1 y 2 segundos (configurable).
Errores de datos, conectores desconocidos o fuentes no disponibles no se reintentan.
Tras tres revisiones fallidas consecutivas la fuente se deshabilita, con evento persistente.
Un éxito reinicia el contador. Un fallo de una fuente no detiene otras.
Si la base de datos impide registrar el resultado, queda un error de runtime en consola;
la revisión se recupera como interrupted después de resolver el problema y reiniciar.
Los futuros conectores de red deberán definir timeout y respetar límites y condiciones:
esta versión no incorpora ningún conector externo, navegador ni evasión de controles.

## Identidad y demostración

Identidad: source_id + source_product_id + variant_key. No se mezclan 500g y 1kg.
Cada observación conserva moneda, UTC, envío, condiciones y disponibilidad nullable.
Cada lote se valida completo y se rechazan identificadores repetidos antes de guardar.
Productos y observaciones incluyen is_simulated. La demo usa nombres SIMULADO y no URLs.
La analítica separa monedas/tipos y excluye simulaciones de recomendaciones de alta confianza.
SQLite devuelve datetimes sin zona: el contrato de almacenamiento y lectura es UTC.

## Seguridad local

Control /monitor con HTTP Basic y administradores habilitados de rol admin.
No hay cuenta predeterminada. PBKDF2-SHA256: salt 16 bytes y 600000 iteraciones.
Las acciones requieren token CSRF firmado, vinculado al usuario y válido 15 minutos.
Se escapa HTML y se limitan intentos de autenticación. Los eventos almacenan códigos,
no excepciones ni secretos. HTTP Basic se permite aquí solo en loopback; no exponer
el panel a Internet. Antes de despliegue público se requiere HTTPS y revisión de seguridad.

## Análisis y consultas

PriceObservation agrega advertised_reference_price (nunca referencia histórica) e
identity_confidence. PriceAnalysis guarda un resultado único por observación, motivos,
componentes y fecha. El índice compuesto delimita historial por producto/moneda/tipo/fecha.
Offer almacena candidatos pendientes; no existe aprobación/publicación automática.
Los GET /analysis, /analysis/{id}, /offers y /products/{id}/history requieren administrador.
Nombres y condiciones se escapan en HTML; búsquedas usan parámetros SQLAlchemy.
La fórmula versionada y los límites están en ANALYTICS.md. Las puntuaciones guardadas son
instantáneas; hay que recalcular antes de actuar cuando la información haya envejecido.
