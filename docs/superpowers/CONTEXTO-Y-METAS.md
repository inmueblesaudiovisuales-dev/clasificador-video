# Contexto y metas del proyecto

*(Última actualización: 2026-08-09, después de cerrar el rediseño de la UI y
de la primera tanda de uso real con material de la FX30 y del dron. Este
documento describe **intención y dirección** — para decisiones técnicas ya
tomadas, ver `CLAUDE.md` en la raíz; para qué es la app y cómo correrla, ver
`README.md`; para el estado del código y cómo seguir, ver el handoff.)*

## Estado actual

**El rediseño está terminado y la app se usa con material real.** Un shooting
completo se clasifica sin tocar el mouse: llega reproduciendo, se marca con el
teclado, se cruza a la hoja de contactos, se pinta por lotes y se exporta a
Premiere, que arma el proyecto solo.

Lo que cambió el criterio en esta última etapa: **Bruno la usó con 109 clips
suyos**, y de ahí salieron más bugs reales que de cualquier revisión. Dos de
ellos llevaban meses escondidos —las portadas no se generaban nunca, y el
borde que marca el clip actual no llegaba al píxel— y ninguno lo detectó la
suite.

**Ya no es una herramienta a medias, pero tampoco está repartida**: corre en la
máquina de Bruno. El primer paquete `.app` existe y arranca sin Homebrew, pero
falta probarlo en otra computadora.

## Hacia dónde va (metas de Bruno, en sus palabras)

### Lo que está en marcha ahora mismo

- **Importación tipo Premiere: bins, drag and drop, y acciones por bin.**
  Es el pedido más reciente y el más grande que queda:

  > «No me encanta la importación. Es difícil importar archivos individuales,
  > solo se pueden carpetas. No se distinguen entre carpetas o cámaras. Me
  > gustaría que fuera tan fácil como drag and drop en bins, como en Premiere.
  > Y de esa forma los videos que estén en ciertos bins ya sé que son de Sony,
  > otros ya sé que son de un dron. Poder hacer clic derecho en esos bins y
  > enlazar los proxies. También meter los LUTs a esos videos.»

  El fondo del pedido es correcto y va más allá de la comodidad: **el proxy y
  el LUT son propiedades de la CÁMARA, no del clip suelto**. Un LUT de S-Log de
  la FX30 no va sobre material del dron. Hoy no existe ninguna forma de decir
  «estos 23 son del dron».

  Y media pieza ya existe sin interfaz: `ingest.py` ya guarda las carpetas
  importadas por separado, con nombre editable (`IngestFolder.display_name`,
  `rename_folder`). El rediseño de la UI quitó el panel que las mostraba.

- **Proxies del dron.** Medido: el `.LRF` que escribe el DJI **no sirve como
  proxy** aunque se le cambie la extensión —el contenido está corrido entre 1 y
  5 cuadros, y cambia de clip a clip—, así que hay que generarlos desde el
  original. Cuesta ~10 s por cada 6 s de video con el codificador del chip.

- **LUT hacia Premiere.** La API de UXP sí permite ponerle un efecto al *master
  clip* (`ClipProjectItem.getComponentChain`), así que es alcanzable sin armar
  la secuencia. Falta confirmar dentro de Premiere que el parámetro del LUT de
  entrada de Lumetri acepta una ruta de archivo.

### Distribución

- **Que la use la gente con la que Bruno trabaja.** Sin venderla: por USB o
  carpeta compartida, que es el camino que **no** necesita la firma de pago de
  Apple. El paquete ya se arma (`empaque/clasificador.spec`) y arranca sin
  Homebrew; falta abrirlo en otra Mac.

### Video y reproducción

- ~~**Layout para orientación vertical**~~ — hecho. Es el caso de diseño
  principal: el material de Bruno es mayoría vertical, incluido el del dron.
- ~~**Mejor performance de reproducción, cuadro por cuadro**~~ — hecho en la
  F9, y no como se esperaba: **no era la app, era el material**. Un cuadro
  atrás sobre HEVC 4K cuesta 530 ms y sobre el proxy 22 ms.
- ~~**Proxies**~~ — hechos, y **a mano** por decisión explícita de Bruno:
  eliges el proxy de un clip y del par sale el patrón para los demás, como el
  *Attach Proxies* de Premiere.

### Diseño visual

- ~~**Rediseño más pulido**~~ — hecho, en once fases contra un mockup, con
  cuatro candados anti-deriva. Ver el handoff.

### Escala

- **Estabilidad con proyectos más grandes.** Hoy medido y cómodo con 128
  clips. Lo que se degrada primero al crecer es la generación de miniaturas —
  ahora que salen del proxy, cinco veces más barata.

## Qué NO es una meta (para no asumir de más)

- **Ninguna función de edición.** La app clasifica y prepara; Premiere edita.
- **No reemplazar el panel de proyecto de Premiere.** El pedido de los bins es
  para saber de qué cámara viene cada clip y actuar por cámara — no para
  reconstruir una jerarquía de carpetas con arrastre y anidamiento.
- **Ningún paso de configuración antes de trabajar.** La app abre con el rail
  vacío y los cuartos se crean sobre la marcha.
