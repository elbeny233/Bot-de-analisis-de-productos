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

## Seguimiento: enlace oficial proporcionado por el propietario

La página https://www.walmart.com.mx/ayuda/articulo/terminos-y-condiciones/0ce968556dd14c0e98097b3675d39b08
respondió HTTP 200. La página de ayuda no contiene los términos completos; enlaza a:
https://www.walmartmexico.com/content/dam/walmart-mexico/documents/terminos_y_condiciones/Terminos_y_Condiciones_de_Walmart.pdf

La descarga de ese PDF y la página de propiedad intelectual del mismo dominio quedaron
bloqueadas por el proxy del entorno. Se añadió www.walmartmexico.com al borrador,
preservando los dominios previamente configurados. Pendiente de aplicación de red.
https://www.walmart.com.mx/robots.txt respondió HTTP 418 con contenido HTML; no se obtuvo
un archivo de reglas válido. No se reintenta con identidades falsas ni mecanismos de evasión.
El HTTP 200 de la ayuda no establece permiso para extracción, acceso a productos o precios
localizados en CP 37278. No se implementó ni habilitó un conector real por este resultado.

## Resultado de la revisión documental

Se descargó la copia desde el enlace oficial del PDF, ya que el adjunto excede el límite
de transferencia de 32 MiB. Archivo oficial: 40658186 bytes, SHA-256
93ad68de53b469b91ccc467cafa113b9fe4951e2a8c2d003021bc28f60d2c03b.
No se pudo comparar byte a byte con el adjunto. El PDF es una página muy alta; la extracción
de texto pierde caracteres en el tramo final. La cláusula siguiente se confirmó visualmente
al renderizar la sección 07, sin depender únicamente de búsquedas de palabras u OCR.

### Walmart y Bodega Aurrera: no activar extracción sin autorización aplicable

PDF oficial, sección 07, Disposiciones generales → Sobre usos indebidos de los Sitios Web:

> Utilizar herramientas automatizadas para obtener información de los Sitios.

El documento incluye Walmart y Bodega Aurrera entre los negocios cubiertos y se refiere
al uso de los sitios de compras en línea del Grupo Walmart. Es una restricción del PDF
de compras, independiente de las condiciones del sitio corporativo.
Su última actualización visible es 01 de septiembre de 2026. Se verificará de nuevo
antes de cualquier integración, dado que la página de ayuda anuncia cambios próximos.
No se consultaron productos ni se verificaron precios/cobertura para CP 37278.

### Soriana: extracción y uso comercial restringidos

https://www.soriana.com/static-pages/terminos-y-condiciones.html respondió HTTP 200.
En el apartado de USO INDEBIDO incluye:

> La utilización de tecnología para realizar la extracción, obtención o recopilación, directa o indirecta, de cualquier información incluida en el SITIO.

También incluye el uso comercial del sitio o sus contenidos. robots.txt respondió 200,
pero que una ruta no esté excluida no anula esas condiciones. No activar un extractor
para Radar Ofertas VIP sin una autorización aplicable o fuente con licencia distinta.

### Chedraui: posible vía mediante autorización previa por escrito

https://www.chedraui.com.mx/terminos-y-condiciones/plataformas-digitales respondió HTTP 200.
Sección 2, De la licencia: limita copiar información a uso personal no comercial y
condiciona otros usos a autorización previa por escrito. Esto no confirma que Chedraui
ofrezca una API o un feed gratuitos ni que concederá permiso: hay que consultarlo.
robots.txt respondió 200, con múltiples rutas excluidas que habría que respetar además
si se autoriza el acceso. No se consultaron productos, precios o cobertura localizada.

## Siguiente acción concreta

Solicitar una autorización o una fuente de datos autorizada antes de implementar el
conector comercial. Chedraui es candidata para preguntar por esa vía escrita, no una
fuente ya aprobada. Borrador listo en REQUEST_DATA_ACCESS.md; no se envió a nadie.
Puede usarse también para Walmart o Soriana adaptando el destinatario.
No se contratarán servicios, creará cuentas ni enviarán mensajes sin instrucciones.
No se propone como alternativa recopilar manualmente el mismo contenido restringido
para republicarlo comercialmente. Un archivo/API de precios facilitado con autorización
adecuada sí permitiría continuar el desarrollo y la verificación de datos reales.
Fase 4 sigue pendiente de una vía compatible; Fases 1–3 no se modificaron.
