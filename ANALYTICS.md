# Inteligencia de precios — Fase 3

## Separación y estadística

Cada consulta está limitada a un producto (fuente + identificador + variante normalizada),
una moneda y un tipo de dato: simulado o no simulado. No hay conversión monetaria implícita.
La identidad incorpora marca, modelo, presentación y vendedor, normalizados con Unicode,
mayúsculas/minúsculas y espacios; 1KG y 1 kg son equivalentes, 500g y 1kg son distintos.
No se convierte entre unidades diferentes ni se garantiza identificación universal.
Al cambiar modelo, presentación o vendedor se crea otra identidad. Un producto legado
se reutiliza solo si su variante normalizada y todos esos atributos son compatibles.

El historial muestra último precio, mínimo y máximo **del periodo observado**, promedio,
mediana, número de observaciones y fechas UTC de inicio/fin. Las variaciones 24h/7d/30d
son (último - base) / base × 100, usando la última observación en o antes del corte.
Se muestra la fecha de la base; puede ser anterior al corte si hubo huecos. Si no hay base,
la base es cero o no hubo nueva observación tras ella, se devuelve información insuficiente.
No se promete un mínimo histórico absoluto. Observaciones futuras no entran en estadísticas.

## Referencia de descuento

Mediana de precios positivos **anteriores** al precio evaluado, dentro de los últimos
30 días de esa consulta. Excluye el precio actual, monedas/tipos/productos distintos,
observaciones posteriores y valores cero. Los cortes incluyen orden de ID para consultas
con la misma fecha. No usa el precio tachado/anunciado como referencia.

- Descuento de producto = (referencia - precio) / referencia × 100.
- Descuento con envío = (referencia - precio - envío conocido) / referencia × 100.
- El precio anunciado se guarda por separado y solo calcula descuento anunciado.
- Si no existe referencia positiva, el descuento por historial es desconocido.

La comparación con envío es conservadora: la referencia es el precio de producto, sin
asumir costos históricos que no se conocen. Descuento negativo significa incremento.

## Puntuación de 0 a 100 — fórmula v1

Cada componente es peso × factor entre 0 y 1:

| Componente | Peso inicial | Factor |
|---|---:|---|
| Descuento | 40 | Descuento por historial / 50%, limitado a 0–1 |
| Historial | 20 | Media de cobertura de cantidad, duración y días distintos |
| Disponibilidad | 10 | 1 solo si disponible=True; 0 si desconocida o no disponible |
| Vigencia | 10 | 1 - edad/24h, limitado a 0–1; fecha futura o vencida vale 0 |
| Costos | 10 | Descuento con envío / descuento de producto; desconocido vale 0 |
| Identificación | 10 | Confianza estimada en los atributos de identidad |

Confianza: base 0.50 por ID/variante requeridos; +0.20 presentación no vacía;
+0.20 modelo no vacío; +0.10 marca no vacía. Es una heurística de completitud,
no una certificación del fabricante ni una garantía de correspondencia comercial.

Calidad de historial: media de min(n/5,1), min(duración/7 días,1),
min(días distintos/3,1). Duración es la distancia **entre primera y última observación
previas**, sin contar el hueco hasta el precio nuevo. Muchas muestras del mismo día
no sustituyen cobertura de varios días. Cada componente se redondea a dos decimales,
la suma al entero más cercano (ROUND_HALF_UP), y se aplican límites de confianza.

## Límites y clasificación

- Historial suficiente: ≥5 observaciones, ≥7 días de duración y ≥3 días distintos.
- Identificación suficiente: confianza ≥0.80.
- Historial o identificación insuficientes, o anuncio sin confirmar: máximo 49 puntos.
- Disponibilidad desconocida/no disponible, envío desconocido o consulta vieja: máximo 69.
- Precio cero, caída ≥80% o subida ≥5× la referencia: posible error, máximo 39.
- Sin ahorro conocido o ahorro eliminado por envío: máximo 49.

Clasificaciones: history_confirmed (descuento ≥10% e historial/identidad suficientes),
store_announced (anuncio sin confirmar), possible_price_error, insufficient_information,
no_discount. Las advertencias de vigencia/costos/disponibilidad se conservan por separado.

Apta para revisión de alta confianza: historial confirmado, consulta vigente, disponible,
identificación suficiente, envío conocido, ahorro efectivo ≥10%, puntuación ≥70 y
**datos no simulados**. Es una recomendación de revisión, no aprobación ni publicación.
Los pesos y umbrales se configuran; los seis pesos deben sumar 100.
Los datos simulados nunca reciben esta recomendación, aunque obtengan una puntuación alta.

Ejemplo de prueba: cinco precios previos de 100 MXN repartidos en ocho días, precio nuevo
80 MXN, envío 0, disponibilidad y metadatos completos → 20% de descuento, 76/100.
Si está marcado como SIMULADO, queda excluido de recomendaciones para ofertas reales.

## Persistencia y uso

PriceAnalysis guarda resultado, razones, componentes y fecha de análisis por observación.
Se analiza automáticamente después de guardar precios, en una transacción separada.
Un fallo analítico conserva la revisión y los precios, registra analysis_failed y permite
Recalcular análisis. Ese control evalúa la última observación de cada producto/moneda/tipo.
El reanálisis es idempotente: no duplica análisis ni ofertas y conserva estados de ofertas.
Si cambias pesos/umbrales, reinicia y usa Recalcular análisis.

La puntuación guardada es una instantánea en analyzed_at; puede perder vigencia. Antes de
actuar sobre ella hay que recalcular. Toda publicación futura deberá reevaluar también
la frescura y las restricciones; en Fase 3 no hay publicaciones externas.
Candidatos con descuento relevante, anuncio o anomalía crean Offer en estado pending.
No se aprueba, publica, descarta ni elimina automáticamente ninguna oferta.

## Qué verás al actualizar

Las primeras revisiones de la demo muestran Información insuficiente. Es correcto:
unos minutos de historial no permiten afirmar descuentos auténticos. La demo conserva
precios fijos; no inventa cambios ni un historial largo para mostrar ofertas ficticias.
La lista de oportunidades puede estar vacía. Los escenarios de descuentos y anomalías
se ejercitan con historiales sintéticos aislados en las pruebas, marcados cuando se muestran.
