# Fase 4 — evaluación de fuentes para CP 37278

Estado: evaluación pendiente de acceso de red. No hay conector real habilitado.
El CP solicitado es 37278. No se ha verificado ciudad, sucursal, cobertura, inventario
ni precio localizado; no se deducen esos datos a partir del código postal.

## Candidatas

| Tienda | Dominio oficial a evaluar | Evidencia obtenida |
|---|---|---|
| Walmart México | www.walmart.com.mx | Proxy del entorno rechaza acceso HTTPS con 403 |
| Bodega Aurrera | www.bodegaaurrera.com.mx | Error de proxy antes de recibir contenido |
| Soriana | www.soriana.com | Error de proxy antes de recibir contenido |
| Chedraui | www.chedraui.com.mx | Error de proxy antes de recibir contenido |

Estas respuestas NO son evidencia de prohibición de las tiendas, disponibilidad de
productos, CAPTCHA, compatibilidad de automatización ni existencia de API pública.
No se obtuvieron condiciones de uso, robots.txt ni catálogos.
Primera candidata de evaluación: Walmart México, sin afirmar todavía que sea viable.

## Revisión que falta

1. Leer las condiciones de acceso/uso previsto y robots.txt en el dominio oficial.
   robots.txt solo expresa reglas de rastreo; no sustituye autorización de uso.
2. Identificar una API pública documentada o catálogo gratuito autorizado, si existe.
   No descubrir/reutilizar endpoints privados ni credenciales de sesiones ajenas.
3. Confirmar cómo seleccionar el CP 37278 o sucursal mediante una vía permitida.
   No presentar precios genéricos como precios verificados para esa ubicación.
4. Elegir una muestra pequeña de productos, registrar presentación y vendedor y
   documentar moneda, disponibilidad, promociones y envío. Sin comprar ni publicar.
5. Determinar frecuencia y límites admitidos antes de programar consultas.
6. Si la primera candidata no tiene una vía compatible, evaluar las demás. No sortear
   CAPTCHA, bloqueos, autenticación ni límites de acceso.
7. Implementar y probar el conector solo después de establecer una vía válida.

## Aislamiento de ubicación (requisito previo al conector)

La identidad de fuente real deberá incluir tienda + contexto verificado de CP/sucursal.
Crear una fuente nueva para otra ubicación; no cambiar el CP de una fuente con historial.
No mezclar precios de vendedor, modelo, presentación, canal, moneda o ubicación distintos.
El CP no se añadirá a fuentes demo ni se afirmará aplicado sin respuesta de la tienda.
Los precios y disponibilidades desconocidos permanecen desconocidos.

## Configuración cloud

Se solicitaron dominios exactos de las cuatro candidatas para leer sus fuentes oficiales.
Los presets de gestores de paquetes se conservan. No se solicita acceso a todos los hosts.
Guardar el borrador no aplica automáticamente la política al proceso actual ni publica
el entorno. El propietario debe revisar y guardar el ajuste de red en configuración;
la operación afectada se reintentará después de ese cambio.

Fases 1–3: el propietario verificó en Windows 20, 47 y 92 pruebas pasadas respectivamente.
No se considera completada la Fase 4 con estos datos pendientes.
