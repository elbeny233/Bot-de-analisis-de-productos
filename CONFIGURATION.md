# Configuración

.env en la raíz y variables de entorno (tienen prioridad). Nunca versionar .env ni secretos.

| Variable | Inicial | Uso |
|---|---|---|
| RADAR_APP_NAME | Radar Ofertas VIP | Nombre de aplicación |
| RADAR_DATABASE_URL | sqlite:///./data/radar.db | Solo SQLite local |
| RADAR_MONITOR_INTERVAL_MINUTES | 30 | Intervalo al crear la fuente demo (1–10080) |
| RADAR_SCHEDULER_ENABLED | true | false impide iniciar el monitor |
| RADAR_MONITOR_MAX_ATTEMPTS | 3 | Intentos por revisión (1–5) |
| RADAR_MONITOR_RETRY_SECONDS | 1 | Espera inicial (0.1–30 s), duplicada, máximo 60 s |
| RADAR_MONITOR_PAUSE_AFTER_FAILURES | 3 | Revisiones fallidas hasta pausa (1–10) |
| RADAR_PUBLICATIONS_ENABLED | false | true se rechaza en esta fase |
| RADAR_LOG_LEVEL | INFO | DEBUG, INFO, WARNING, ERROR, CRITICAL |

El intervalo global solo se aplica a fuentes nuevas. Para una existente, modificarlo
mediante /monitor. Pausa e intervalos quedan guardados en SQLite. init-db no los restablece.
La demo recién creada se revisa al iniciar; después, cada 30 minutos por defecto.
Modificar .env requiere detener y reiniciar. No necesita ninguna credencial de servicios.

Crear administrador con la CLI y su contraseña interactiva; no ponerla en argumentos.
El navegador solicita usuario/contraseña al entrar en /monitor. Cerrar el navegador elimina
normalmente su autenticación Basic en memoria; el cierre de sesión completo será Fase 6.
Fechas del control local y de la base de datos en UTC, indicadas explícitamente.

## Analítica (Fase 3)

| Variable | Inicial |
|---|---|
| RADAR_ANALYSIS_REFERENCE_DAYS | 30 |
| RADAR_ANALYSIS_MIN_OBSERVATIONS | 5 |
| RADAR_ANALYSIS_MIN_HISTORY_DAYS | 7 |
| RADAR_ANALYSIS_MIN_DISTINCT_DAYS | 3 |
| RADAR_ANALYSIS_MAX_AGE_HOURS | 24 |
| RADAR_ANALYSIS_MIN_DISCOUNT_PERCENT | 10 |
| RADAR_ANALYSIS_FULL_DISCOUNT_PERCENT | 50 |
| RADAR_ANALYSIS_ANOMALY_DROP_PERCENT | 80 |
| RADAR_ANALYSIS_ANOMALY_RISE_MULTIPLIER | 5 |
| RADAR_ANALYSIS_MIN_SCORE | 70 |
| RADAR_ANALYSIS_MIN_IDENTITY_CONFIDENCE | 0.8 |

RADAR_ANALYSIS_WEIGHTS acepta JSON con discount, history, availability, freshness, costs
 e identity: pesos enteros no negativos, suma 100. Valores iniciales: 40,20,10,10,10,10.
Cambios en .env requieren reiniciar. Recalcular análisis aplica la configuración nueva
al último precio de cada ámbito; no cambia publicaciones ni estados de ofertas.
Fórmula y límites: ANALYTICS.md. Las publicaciones continúan bloqueadas.
