# Configuración

Se lee .env en la carpeta actual y variables de entorno, que tienen prioridad.
Ejecutar siempre desde la raíz del proyecto. .env está ignorado por Git.

| Variable | Valor inicial | Validación |
|---|---|---|
| RADAR_APP_NAME | Radar Ofertas VIP | Texto |
| RADAR_DATABASE_URL | sqlite:///./data/radar.db | Solo SQLite en esta fase |
| RADAR_MONITOR_INTERVAL_MINUTES | 30 | Entero 1–10080; aún no ejecuta monitoreo |
| RADAR_PUBLICATIONS_ENABLED | false | true se rechaza hasta implementar publicaciones |
| RADAR_LOG_LEVEL | INFO | DEBUG, INFO, WARNING, ERROR, CRITICAL |

No se necesitan secretos, cuentas, API de pago ni servicios externos.
Los 11 temas iniciales se guardan en categories, sin IDs Telegram.
init-db es repetible y no sobrescribe categorías existentes ni usuarios.
Los IDs, credenciales Telegram y configuración del panel se incorporarán en sus fases.
