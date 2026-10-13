# Resultados de validación

## Fase 3 — versión 0.3.0

Entorno: Linux, Python 3.12.14.

- Pytest: 92 pruebas pasadas, 0 fallidas, 0 omitidas.
- Ruff check y format --check: correctos.
- Alembic check: esquema y modelos coherentes; migración actual 0003.
- pip check: sin dependencias incompatibles.
- Migración desde Fase 2 con observaciones, oferta descartada y fuente pausada:
  conserva precios, estados, configuración y referencias; foreign_key_check sin errores.
- Estadísticas, medianas, descuentos, ventanas, confianza, anomalías y separación de
  ámbitos verificados con datos controlados. La fórmula y los límites están en ANALYTICS.md.
- HTTP real: /health phase=3/schema=0003; páginas de análisis, oportunidades y API
  accesibles con administrador y protegidas sin credenciales.
- Escenario HTTP explícitamente SIMULADO: mediana previa 100 MXN, nuevo precio 80 MXN,
  descuento 20%, puntuación 76/100; no recomendado para ofertas reales ni publicado.
- Reanálisis manual comprobado por HTTP; no duplica análisis ni candidatos.
- Pruebas incluyen escape HTML, búsquedas parametrizadas, fallo analítico que conserva
  precios, normalización de modelos/presentaciones/vendedores y compatibilidad de legado.
- Un aviso de deprecación Starlette/AnyIO en TestClient; sin fallo funcional.

Windows de Fase 3: pendiente de ejecución por el propietario.
Docker y fuentes externas: no ejecutados ni verificados. No se publican ofertas,
se gestionan cobros ni se revocan accesos. Las puntuaciones almacenadas son instantáneas;
se debe recalcular si los datos han perdido vigencia antes de actuar sobre ellas.

## Fase 2 — validación previa

47 pruebas pasadas en Linux. HTTP real: revisión automática y manual, tres productos,
seis precios simulados y reinicio conservando próxima revisión.
El propietario aportó captura de **47 passed** en Windows y del control local con
revisiones success, precios registrados y cero fallos. Confirmado el acceso administrativo.

## Fase 1 — validación previa

20 pruebas pasadas en Linux. Se corrigió el cierre SQLite tras WinError 32 detectado
por el propietario. Después aportó capturas de **20 passed**, /health status=ok y
la página inicial funcionando en Windows.
La entrega del código a GitHub está autorizada por el propietario.
