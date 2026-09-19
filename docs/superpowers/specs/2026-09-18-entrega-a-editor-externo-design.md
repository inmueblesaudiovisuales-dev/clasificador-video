# Entrega a un editor externo — diseño

*(Spec del 2026-09-18. Nace de que Bruno a veces necesita que alguien más
edite un proyecto suyo — sin que esa persona tenga Clipify — y de una
sesión larga de plática, sin construir nada, para encontrar la
metodología correcta antes de tocar código.)*

## 1. El problema

Bruno clasifica en Clipify, arma su proyecto de Premiere con el plugin
usando sus clips en 4K, y a veces necesita mandarle ese trabajo a un
editor externo para que corte — y que se lo regrese. El editor **nunca
tiene Clipify instalado**: solo recibe un link de una carpeta de Google
Drive y trabaja con Premiere normal.

Dos preguntas tuvieron que resolverse con pruebas reales, no a ojo,
porque la primera respuesta obvia resultó estar mal:

- **¿Con qué edita el editor, si no tiene los archivos originales en
  4K?** (§2)
- **¿Cómo viaja el proyecto de ida y vuelta sin que el editor necesite
  Clipify?** (§5)

## 2. El proxy cambia de forma: dimensión real, no 720p

**Esto reemplaza la decisión de `LADO_CORTO = 720` en `proxy_gen.py` —
en TODA la app, no solo para la entrega a un editor.** El proxy deja de
achicar el cuadro: sale siempre al mismo ancho × alto que el clip
original, con el mismo bitrate bajo de siempre (`6M` video, `128k`
audio). Un clip de 4K da un proxy de 4K; uno de otra resolución da un
proxy de esa resolución — nunca se fuerza un tamaño fijo.

### Por qué se abandonó el plan original (achicar a 720p)

La razón de encoger a 720p siempre fue la reproducción fluida dentro de
Clipify, y seguía pareciendo necesaria para este flujo — hasta que una
prueba real en la máquina de Bruno mostró un problema más grave que el
peso o la fluidez: **si el editor recorta o escala un clip mientras ve
un proxy de OTRA resolución que el original, ese ajuste queda calculado
sobre el tamaño equivocado.** Al reconectar después contra el archivo de
4K real, la imagen sale chica, aplastada y con las orillas cortadas —
comprobado con capturas reales, no en teoría (ver la prueba de la SSD
expulsada, 2026-09-18).

Se evaluó agregar un plugin nuevo para usar "Attach Proxy" (la función
de Premiere pensada para desacoplar el playback de las cuentas de
escala) — pero resultó innecesario: **si el proxy nunca cambia de
tamaño respecto al original, el problema no se presenta, sin tocar
ningún plugin.** El "Vincular medios" que Bruno ya usa hoy para
reconectar sigue funcionando exactamente igual — no hace falta
automatizar nada nuevo ahí.

### El peso, medido, no supuesto

La preocupación obvia — un proxy en 4K real debe pesar como el
original — resultó falsa. El peso de un video lo decide casi por
completo el bitrate, no la resolución. Medido con un clip real de la
Sony (`PIB0002`, 3 segundos, original de 3840×2160 a 98 Mbps):

| Versión | Resolución | Peso |
|---|---|---|
| Original (cámara) | 3840×2160 | 67 MB |
| Proxy nativo de la Sony | 720p | 16.9 MB |
| Proxy de Clipify, plan viejo (720p, 6M) | 720p | 2.4 MB |
| **Proxy nuevo (resolución real, 6M)** | 3840×2160 | **2.4 MB** |

El proxy nuevo pesa exactamente lo mismo que el de 720p — la resolución
no entró en la cuenta —, y Bruno lo probó escrubeando en su propio
Premiere: se ve bien y fluido.

### Consecuencia en el código

En `proxy_gen.py`, la constante `LADO_CORTO` y el filtro de escala
(`-vf scale=...`) del comando de ffmpeg desaparecen. El proxy sale del
mismo tamaño que entra — el comando ffmpeg pierde ese parámetro, el
resto (bitrate, mapeo de pistas, sufijo `S03`) sigue igual.

## 3. La carpeta de proxies se reconoce por cámara, no por nombre idéntico

**Esto amplía la spec `2026-08-25-carpeta-de-proxies-elegible-design.md`.**
Aquella decisión decía que la subcarpeta de proxies debía llamarse
**igual** que la carpeta del material (`02. VIDEO DRONE`, no `02. PROXY
DRONE`), para no arriesgar una lectura equivocada.

El caso real de Bruno la contradice: su plantilla trae, hecha a mano,
`02. PROXY DRONE` como hermana de `02. VIDEO DRONE` — mismo número,
misma cámara, nombre distinto a propósito. Con la regla de agosto, la
app ignora esa carpeta ya preparada y crea `02. VIDEO DRONE` **dentro**
de la carpeta de proxies elegida, dejando la de Bruno vacía — el mismo
patrón de carpeta-vacía-y-huérfana que ya había costado una versión
rota.

**Regla nueva:** al buscar dónde escribir, si la carpeta elegida ya
tiene una subcarpeta cuyo **número coincide** con el de la carpeta de
material (`02.`) — aunque el resto del nombre no sea idéntico —, se usa
esa. Solo si no existe ninguna con ese número se crea una nueva,
llamada igual que el material (comportamiento de hoy, sin cambio).

## 4. Marcas de cámara en las carpetas de Premiere

**Esto amplía la spec `2026-09-18-marca-drone-en-carpetas-design.md`.**
Esa spec ya construyó `[DRONE]` sobre el nombre del *bin de importación*
(la tanda con la que Bruno arrastró el material), con una regla
estricta de todo-o-nada por cuarto. Se agrega:

- `[SONY]` — el nombre del bin contiene `sony`.
- `[POCKET]` — el nombre del bin contiene `pocket` (cubre "Osmo
  Pocket" completo).
- **Osmo Action no entra en este sistema.** No ocurre en la práctica de
  Bruno; un clip que no dice ninguna de las tres palabras simplemente no
  cuenta para la marca, ni suma ni resta.

### Marca combinada cuando un cuarto mezcla cámaras

A diferencia de `[DRONE]` sola (que se apaga por completo ante
cualquier mezcla), con tres cámaras posibles la regla cambia: **un
cuarto con más de una cámara se marca con las dos, combinadas**, en vez
de quedarse sin nada. Orden fijo, siempre el mismo sin importar en qué
orden se importó el material:

```
Sony, Pocket, Drone
```

Ejemplos: un cuarto solo de Sony → `[SONY]`. Sony + dron → `[SONY+DRONE]`.
Las tres → `[SONY+POCKET+DRONE]`.

Clips que no dicen ninguna de las tres palabras (p. ej. Osmo Action) se
ignoran para este cálculo — no apagan la marca de las cámaras que sí se
reconocen, ni las obligan a aparecer solas.

## 5. El flujo completo de entrega

Clipify **no construye el `.prproj`** — eso Bruno lo sigue haciendo él
mismo, dentro de Premiere, con el plugin que ya existe. El papel nuevo
de Clipify es exclusivamente subir y bajar archivos de Google Drive.

```
1. Bruno arma su proyecto en Clipify: clasifica, elige cuartos, genera
   proxies (ya con el tamaño real, §2).
2. Bruno abre Premiere y usa el plugin de Clipify para armar el .prproj,
   con sus clips en 4K -- exactamente como ya lo hace hoy.
3. De vuelta en Clipify, botón "Subir a Drive": empaqueta los proxies de
   los clips elegidos (no la carpeta completa) + el .prproj, los sube a
   la cuenta de Drive DE BRUNO, y da el link de esa carpeta.
4. Bruno le pasa el link al editor por donde sea (WhatsApp, correo). El
   editor -- que NUNCA tiene Clipify -- descarga, abre el .prproj en su
   propio Premiere, y Premiere le pide relink porque las rutas de su
   computadora no son las de Bruno: un clic, "buscar los demás
   automáticamente", y encuentra todo porque la estructura interna de
   carpetas es idéntica.
5. El editor corta usando los proxies -- que ya tienen el tamaño real
   del original, así que cualquier encuadre que toque queda bien
   calculado (§2) --. El original en 4K nunca viaja con él.
6. El editor sube de vuelta su .prproj editado, más cualquier recurso
   nuevo que haya usado, a la carpeta de "material nuevo" (§6).
7. Bruno, desde Clipify, le da a "Traer de vuelta": descarga el .prproj
   y lo reemplaza el suyo; reparte cada subcarpeta de "material nuevo"
   a su categoría real. Los proxies no se vuelven a bajar -- ya los
   tiene.
8. Bruno reconecta a mano contra sus originales en 4K -- el mismo
   "Vincular medios" de siempre, sin distorsión porque el tamaño nunca
   cambió (§2) -- y de ahí sigue con su After Effects y su exportación.
```

### Por qué Drive y con qué permiso

Es la cuenta de Google de **Bruno** la que autoriza a Clipify, una sola
vez — el editor nunca ve ni toca Clipify. El permiso que se pide debe
ser el acotado ("Clipify solo puede tocar los archivos que ella misma
sube"), que no exige el proceso de verificación larga de Google.

### Lo que se descartó en el camino

- **Sincronizar una carpeta en vivo (iCloud/Drive Desktop) con el
  proyecto abierto.** Riesgo real de corromper el `.prproj` a medio
  guardado si se sincroniza mientras está abierto. El diseño de "subir /
  bajar" por botón, en pasos discretos, evita esto — nunca hay dos
  personas con el mismo archivo abierto a la vez.
- **Adobe Team Projects.** Es la función oficial de Adobe para esto,
  pero no se pudo confirmar que siga disponible (Adobe la ha estado
  retirando). Se descarta como base del diseño; si en el futuro se
  confirma que sigue viva, sería una alternativa a evaluar aparte.
- **Leer el `.prproj` regresado para adivinar qué archivos nuevos
  agregó el editor.** El formato interno de un `.prproj` no está
  documentado por Adobe — mismo riesgo que ya enseñó el plugin UXP. Se
  prefiere la convención de carpeta (§6), que no depende de entender
  el archivo.
- **Attach Proxy vía un plugin nuevo.** Ver §2 — se volvió innecesario
  al resolver el problema de raíz con el tamaño del proxy.

## 6. La convención de "material nuevo"

Dentro de la misma carpeta de Drive, una carpeta `material nuevo/` con
subcarpetas que se llaman **igual que las categorías reales** del
proyecto de Bruno:

```
(carpeta compartida en Drive)
├── Proxies/                    ← lo que subió Clipify, no se toca
├── <nombre>.prproj             ← lo que regresa editado
└── material nuevo/
    ├── musica y audio/
    ├── fotos/
    └── graficos y branding/
```

Al "Traer de vuelta", cada subcarpeta se reparte a su categoría real
(`musica y audio` → `01. ASSETS VIDEO/05. MUSICA Y AUDIO`, etc.).

**`04. TOUR 360` y `X. ARCHIVOS DRONE` quedan fuera de esta lista a
propósito** — nunca reciben material de un editor externo, según
Bruno.

## 7. Qué NO cambia / NO entra

- **El plugin no arma el proyecto de forma remota ni automática.**
  Bruno lo sigue haciendo él mismo, a mano, dentro de Premiere.
- **No hay reconexión automática por software al final.** El paso 8
  (§5) es el mismo "Vincular medios" manual de siempre — se dejó de
  automatizar porque, con el proxy de tamaño real, ya no hace falta.
- **El editor no instala nada de Clipify.** Ni el plugin, ni la app.
- **Los proxies no se vuelven a bajar** al traer de vuelta el trabajo
  del editor — Bruno ya los tiene.
- **Osmo Action no entra en las marcas de cámara** (§4), ni Tour 360 /
  Archivos Drone en "material nuevo" (§6).

## 8. Cómo se comprueba

- `proxy_gen.py`: el comando de ffmpeg ya no incluye el filtro de
  escala; un proxy generado de un original de cualquier resolución sale
  exactamente a esa resolución.
- Reconocimiento de carpeta de proxies por número: una carpeta elegida
  con una subcarpeta de número coincidente pero nombre distinto se usa
  en vez de crear una nueva; sin coincidencia, se crea nueva con el
  nombre de siempre.
- Marcas de cámara: casos de `[SONY]`, `[POCKET]`, combinaciones en el
  orden fijo Sony/Pocket/Drone, y clips sin cámara reconocible que no
  alteran el resultado — extendiendo los mismos casos de prueba que ya
  tiene `[DRONE]`.
- Subir/bajar de Drive: se prueba con una cuenta de prueba, sin
  necesidad de un editor real — mockear las llamadas a la API de
  Drive.
- **Verificación visual real**, según `CLAUDE.md`: reconectar un proxy
  de tamaño real contra su original en un proyecto de Premiere real y
  confirmar a ojo que el encuadre no se mueve.

## 9. Estado

**Diseñado en conversación con Bruno el 2026-09-18, sin construir
nada.** Antes de implementar, falta una sesión aparte de **rediseño de
la interfaz de Clipify** para las funciones nuevas (el botón de subir a
Drive, el flujo de "traer de vuelta", cualquier pantalla de estado del
envío) — siguiendo el flujo normal del proyecto: diseño primero
(`docs/superpowers/mockups/`), luego plan de implementación
(`docs/superpowers/plans/`), luego construcción con TDD.
