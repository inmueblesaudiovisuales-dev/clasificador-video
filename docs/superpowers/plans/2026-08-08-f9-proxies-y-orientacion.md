# F9 del rediseño — Proxies y orientación — Implementation Plan

> **Para quien lo ejecute:** las tareas van con checkbox (`- [ ]`) y el test se
> escribe **antes** que la implementación, como en los cinco planes anteriores.

**Goal:** que la app deje de inventar dos datos que ya tiene el material. La
orientación del manifest sale del video y no de una constante, y el proxy pasa
de ser código muerto a ser **lo que se reproduce y lo que se le entrega a
Premiere**.

**Punto de partida:** **704 tests en verde**, F0–F8 hechas, árbol limpio. Si al
empezar no da 704, averigua qué pasó antes de escribir código.

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
```

**Referencias:**
- Punto de control vigente: `docs/superpowers/ANALISIS-2026-08-08-post-f8.md`
- Comportamiento acordado: `docs/superpowers/mockups/rediseno-2026-08-08/DECISIONES.md`
  («Proxies», en la tabla de metas futuras)
- Candados anti-deriva: `docs/superpowers/plans/2026-08-08-rediseno-ui-fidelidad-al-mockup.md`

---

## Lo que Bruno decidió hoy (2026-08-08)

Se le preguntó antes de escribir este plan, porque las dos respuestas cambian
el trabajo:

1. **Los proxies viven en una carpeta aparte**, al lado de la de originales —
   no revueltos con ellos. Es lo que Bruno armó en `sample-media/` el mismo
   día que respondió: `clips/20260804_PIB0587.MP4` y
   `proxy/20260804_PIB0587S03.MP4`, **dos carpetas hermanas**. Así que
   emparejar **no puede** mirar solo la carpeta importada.
2. **La app reproduce el proxy**, no solo lo anuncia. Es la meta escrita en
   `CONTEXTO-Y-METAS.md` («poder trabajar con archivos proxy más livianos… para
   mejorar el rendimiento de reproducción/scrub»). Esto agranda la fase: deja
   de ser solo datos y toca el reproductor.

---

## Advertencias antes de empezar

1. **La trampa de esta fase es construir el indicador antes que el dato.** Si
   el badge y el contador se hacen primero, quedan dos avisos que mienten y
   nadie lo nota, porque el arnés los dibuja igual. **Las tareas 1 a 3 van
   antes que la 5 y la 6, y no se negocia.** Es la misma regla que hizo
   descartar la precarga en la F6: si el dato no llega, no se construye el
   indicador.

2. **Un proxy que no calza cuadro a cuadro no es un proxy.** Si el archivo
   `S03` tiene otro fps u otra cantidad de cuadros que el original, el in/out
   que marques cae en el lugar equivocado — y peor, Premiere lo engancha igual.
   Un proxy que no valida se descarta **en los tres lados**: no se reproduce, no
   entra al manifest y no cuenta en el contador. Por eso la Task 0 es un spike
   contra el par real de Bruno — ya corrido: **valida exacto**, ver más abajo.

3. **El tamaño del clip lo sigue mandando el ORIGINAL.** `_clip_sizes` decide
   el ancho del video, la forma de la miniatura y el texto de la barra de
   estado (`2160×3840`). Si eso empieza a salir del proxy, el layout cambia de
   forma sin que nadie lo haya pedido y la barra de estado miente sobre la
   resolución del material. El proxy solo decide **qué archivo se abre**.

4. **Dos vistas del mismo dato se contradicen solas.** Van cinco veces en este
   proyecto. Aquí hay dos pares en riesgo: el badge del clip actual y el
   contador de la barra de estado (los dos dicen la resolución), y la
   orientación del manifest contra la que ya muestra la barra de estado
   (`status_bar.py::set_clip_info` ya calcula `vertical`/`horizontal`). **Una
   sola función, y las dos vistas la llaman.**

5. **Importar ya es lento y bloquea.** Hoy corre un `ffprobe` por clip, en
   serie, dentro de `_load_clips_from_ingest`. Sondear además cada proxy suma
   **3.42 s** en 128 clips (medido en la Task 0), así que ese sondeo **no** va
   en el mismo ciclo: va al thread pool.

6. **Estas dos cosas ya existen y no hay que rehacerlas:**

   | Qué | Dónde |
   |---|---|
   | `match_proxies()` — empareja por «mismo stem + `S03`» | `proxy_match.py`, con sus tests |
   | `probe_clip()` — ya devuelve `width`/`height`/`fps`/`rotation`/`duration_frames`, ya corregidos por rotación | `probe.py` |
   | `Clip.ruta_proxy` y su serialización en el manifest | `manifest.py`, y `app.py` ya lo restaura de la sesión |
   | El plugin de Premiere ya engancha el proxy si viene | `uxp-plugin/js/proxy.js` |

   O sea: **el contrato con Premiere no se toca en esta fase.** La llave
   `ruta_proxy` ya está en el JSON y hoy siempre sale `null`. Lo único que
   cambia es que empiece a traer una ruta.

7. **Lo que existe pero no alcanza:** `match_proxies()` recibe dos listas ya
   armadas. Nadie las arma. Falta el paso de **buscar** los candidatos, y ahí
   está la decisión 1 de Bruno.

---

## Task 0: Spike — ¿el proxy calza con el original? — ✅ HECHO (2026-08-08)

**Files:** al scratchpad de la sesión, **no al repo**.

Se midió contra el par real que Bruno tiene en `sample-media/` (que **no se
versiona**: está en `.gitignore`, así que estos números no se pueden reproducir
sin su material):

- original: `sample-media/clips/20260804_PIB0587.MP4` — 3840×2160 HEVC 10-bit,
  268 Mbps, rot 90°, 120 cuadros
- proxy: `sample-media/proxy/20260804_PIB0587S03.MP4` — **1280×720**, mismos
  120 cuadros

### A) El proxy valida ✅

| | original | proxy |
|---|---|---|
| fps | 59.94005994 | 59.94005994 |
| cuadros | 120 | 120 |
| rotación | 90° | 90° |
| orientación (ya corregida) | vertical | vertical |

Delta de fps **0.000000**, delta de cuadros **0**. Calza cuadro a cuadro y el
proxy trae su propia matriz de rotación, así que `probe_clip()` lo endereza
igual que al original — no se va a ver acostado.

**Pero el proxy es 720p, no 1080p.** La cámara escribe `S03` a 1280×720. El
badge del mockup dice `Proxy 1080p` porque era un dibujo; la app va a decir
**`PROXY 720P`**, que es la verdad. La Task 4 ya deriva la etiqueta del lado
corto, así que no hay nada que cambiar — pero el texto del mockup **no** es el
que se copia.

### B) El sondeo extra va al thread pool ❌ el criterio de «en serie»

`ffprobe` del proxy: **26.7 ms** de promedio (el del original, 22.1 ms). Con
128 clips eso suma **3.42 s** al import, por arriba del tope de 2 s que fijaba
este plan. **Decisión: el sondeo de proxies va al `QThreadPool`**, con la misma
guarda de generación que las miniaturas.

### C) Reproducir el proxy es lo mejor que va a pasarle a esta app

Con `hwdec=videotoolbox`, destinos dentro de la duración real del clip:

| | original | proxy | gana |
|---|---|---|---|
| primer cuadro al abrir | 204.5 ms | **8.9 ms** | 23× |
| seek exacto (promedio) | 367.6 ms | **19.0 ms** | 19× |
| un cuadro atrás (`,`) | 529.9 ms | **22.3 ms** | 24× |

**Medio segundo por cada `,`** es exactamente la queja de
`CONTEXTO-Y-METAS.md` («la navegación cuadro a cuadro tiene que sentirse
instantánea, no la siente así hoy»). No era un problema de la app: era el
material. La decisión 2 de Bruno queda justificada con número.

Dos advertencias sobre estos números:

- **`frame-step` (`.`) no se pudo medir acá**: el harness espera a que cambie
  `estimated-frame-number` y se topa con el final del clip, así que los
  promedios salen contaminados por el timeout. Lo que sí se ve es que el paso
  hacia adelante es barato en los dos (8.4 ms y 0.5 ms en el mejor caso): el
  caro es el de atrás, que es un seek.
- **El clip de prueba dura 2 s.** En un clip de 30 s un seek largo sobre el
  original va a costar más, no menos. O sea que la ganancia medida es un
  **piso**.

### Lo que este spike cambió del resto del plan

1. La Task 2 va con thread pool, no en serie.
2. El badge dirá `PROXY 720P` con el material de Bruno.
3. El criterio de validación queda como estaba: mismo fps (< 0.01), mismos
   cuadros (±1), misma orientación. El par real lo cumple exacto.

---

## Task 1: Buscar los archivos proxy (lógica pura, sin Qt)

**Files:**
- Modificar: `src/clasificador_video/proxy_match.py`
- Test: `tests/test_proxy_match.py`

**Qué se agrega:** `buscar_proxies(carpeta_importada: Path) -> list[Path]`.

La regla, que sale de la decisión 1 de Bruno:

- Se busca desde **la carpeta padre** de la importada, no desde la importada —
  el proxy está afuera.
- Recursivo, **con tope de profundidad 2** desde el padre. Sin tope, importar
  algo de la raíz de una tarjeta recorre el volumen entero.
- Solo cuentan archivos con extensión de video (reusar `VIDEO_EXTENSIONS` de
  `ingest.py`) **cuyo stem termine en `S03`**.

**Tests (antes):**
- [ ] El proxy está en una **carpeta hermana** de la importada → lo encuentra.
      Es el caso real de `sample-media/` (`clips/` y `proxy/`) y también el de
      la tarjeta Sony (`Clip/` y `Sub/`).
- [ ] El proxy está suelto en la carpeta **padre** → lo encuentra.
- [ ] El proxy está revuelto con los originales → lo encuentra igual (que la
      decisión 1 no se convierta en una limitación).
- [ ] Un archivo tres niveles abajo **no** se busca: el tope de profundidad
      existe y hay un test que lo fija.
- [ ] Una carpeta sin ningún `S03` devuelve lista vacía, sin reventar.
- [ ] Una carpeta padre inaccesible (permisos) devuelve vacío, no una
      excepción: importar de un volumen ajeno no puede tumbar la app.

**Y una guarda en el ingest:**
- [ ] `tests/test_ingest.py`: un archivo `…S03.MP4` dentro de la carpeta
      importada **no entra como clip**. Hoy entraría, y Bruno vería 256 clips
      en vez de 128 si importa la carpeta equivocada.

---

## Task 2: Conectar el emparejamiento a la importación

**Files:**
- Modificar: `src/clasificador_video/ui/main_window.py` (`_load_clips_from_ingest`)
- Test: `tests/ui/test_main_window.py`

**Qué pasa:** por cada carpeta importada se buscan los candidatos, se llama a
`match_proxies()`, y el resultado que **valide** (criterio de la Task 0) se
guarda en `Clip.ruta_proxy`.

**El sondeo va al `QThreadPool`**, no en serie: la Task 0 midió 26.7 ms por
`ffprobe`, o sea 3.42 s de más en una importación de 128 clips. Va con la misma
guarda de generación que las miniaturas (`self._thumb_generation`), o una
importación nueva recibe resultados de la anterior — ese bug ya está resuelto
una vez en este archivo, se copia el patrón, no se reinventa.

Consecuencia de que sea asíncrono: **el badge y el contador aparecen unos
segundos después de importar**, y hay que probar explícitamente que un clip
abierto ANTES de que su proxy valide se abre con el original y no se rompe.

**Tests (antes):**
- [ ] Con un proxy que valida, `clips[i].ruta_proxy` queda apuntando al `S03`.
- [ ] Con un proxy que **no** valida (fps distinto), `ruta_proxy` queda en
      `None`. Y el mismo test con cantidad de cuadros distinta.
- [ ] Un clip sin proxy sigue con `None` y no rompe nada — es el caso normal
      del dron, dice el docstring de `proxy_match.py`.
- [ ] `_clip_sizes` **sigue saliendo del original** aunque haya proxy
      (advertencia 3). Este test es el guardián del layout.
- [ ] La sesión guardada trae `ruta_proxy` y al restaurarla vuelve. `app.py` ya
      lo hace: el test es para que nadie lo rompa.

---

## Task 3: La orientación del manifest sale del material

**Files:**
- Modificar: `src/clasificador_video/ui/main_window.py` (busca el
  `TODO F9` al lado de `orientacion="horizontal"`)
- Test: `tests/ui/test_main_window.py`

**Dónde vive la función:** una sola, pura, que reciba los tamaños y devuelva
`"vertical"`/`"horizontal"`. La barra de estado ya calcula lo mismo para **un**
clip (`status_bar.py::set_clip_info`): que las dos llamen a la misma función
(advertencia 4).

**Tests (antes):**
- [ ] Mayoría vertical → `"vertical"`. Mayoría horizontal → `"horizontal"`.
- [ ] **Empate → `"vertical"`**, y el test lo dice con esas palabras. No es
      arbitrario: el material de Bruno es mayoría vertical y una secuencia
      vertical con material horizontal adentro se arregla en Premiere; al
      revés, se recorta.
- [ ] **Sin ningún tamaño conocido** (sesión restaurada de disco, donde no se
      volvió a correr `ffprobe`) → `"horizontal"`, el default de hoy, y no
      revienta. Este es el caso que se olvida.
- [ ] Un clip cuadrado no cuenta como vertical.

---

## Task 4: La etiqueta de resolución del proxy, en un solo lugar

**Files:**
- Modificar: `src/clasificador_video/proxy_match.py`
- Test: `tests/test_proxy_match.py`

`etiqueta_de_resolucion(ancho, alto) -> str`: devuelve `"1080p"` a partir del
**lado corto**, para que un proxy vertical de 1080×1920 también diga `1080p` y
no `1920p`.

- [ ] `1920×1080` → `"1080p"`; `1080×1920` → `"1080p"`; `1280×720` → `"720p"`.
- [ ] La usan **las dos** vistas (badge y contador). Un test lo comprueba
      llamando a las dos y comparando el texto, no leyendo el código.

---

## Task 5: El badge de proxy sobre el video

**Files:**
- Modificar: `src/clasificador_video/ui/video_stage.py` (`_BadgeRow`, que ya
  tiene el hueco anotado en su docstring)
- Test: `tests/ui/test_video_stage.py`

Va al final de la fila de badges, como en el mockup (línea 434 de
`mockup.html`: `<span class="badge">Proxy 1080p</span>`). Es el badge **sin
color**: los otros tres usan color porque son estado del clip; este es
información del reproductor. Sin token nuevo si `theme.py` ya tiene el gris de
badge — y si hace falta uno, **va en `theme.py`**, que el candado 1 ya saltó una
vez por esto.

**Tests (antes):**
- [ ] Clip con proxy validado de 1280×720 → el badge se ve y dice `PROXY 720P`
      (la resolución sale del archivo, no del texto del mockup; mayúsculas
      escritas a mano: `text-transform` no existe en QSS, ya pasó con `▶ AUTO`).
- [ ] Clip sin proxy → el badge está escondido, no vacío.
- [ ] El badge declara `background-color: transparent` — la regla global
      `QWidget { background-color }` alcanza a las QLabel y ya costó dos bugs.
- [ ] Cambiar de clip con proxy a uno sin proxy y volver: aparece y desaparece
      sin dejar hueco en la fila.

---

## Task 6: El contador de la barra de estado

**Files:**
- Modificar: `src/clasificador_video/ui/status_bar.py`, y quien lo alimente en
  `main_window.py`
- Test: `tests/ui/test_status_bar.py`

Texto: `proxies 1080p · 118/128`. Va **antes de la ruta del volumen**, del lado
derecho: es información de referencia, del mismo tipo que la ruta. El mockup no
lo dibuja (solo lo pide `DECISIONES.md`), así que esta ubicación es una
decisión de este plan y queda escrita aquí.

**Tests (antes):**
- [ ] Con 118 de 128 validados dice `proxies 1080p · 118/128`.
- [ ] **Con cero proxies el contador no se ve** — un `· 0/128` es ruido en cada
      sesión de dron.
- [ ] Si los proxies conocidos tienen resoluciones distintas, **se cae la
      palabra**: `proxies · 118/128`. Mejor callar que mentir.
- [ ] Sin clips importados, vacío.

---

## Task 7: Reproducir el proxy

**Files:**
- Modificar: `src/clasificador_video/ui/main_window.py` (`_abrir_clip_actual`)
- Test: `tests/ui/test_main_window.py`

Una sola función decide qué archivo se abre: proxy si validó, original si no.
**No hay interruptor**: `DECISIONES.md` no lo pide y el badge ya dice qué estás
viendo.

**Tests (antes):**
- [ ] Con proxy validado, `open_clip` recibe la ruta del **proxy**.
- [ ] Sin proxy, recibe la del original. Con proxy no validado, también.
- [ ] El `in`/`out` marcado sobre el proxy queda en el mismo número de cuadro
      que sobre el original — el criterio de la Task 0 es lo que lo garantiza,
      y este test lo fija.
- [ ] El manifest exporta **`ruta` del original y `ruta_proxy` del proxy**, en
      ese orden y sin cruzarse. Es el test que protege a Premiere: si se cruzan,
      el proyecto se arma con el material de 720p y nadie lo nota hasta exportar.

**Y una comprobación con material real, no con doble:** importar
`sample-media/clips/` en la app y ver que el video se ve **derecho** (el proxy
trae rot 90°, igual que el original), que el badge dice **`PROXY 720P`**, y que
`,` se siente instantáneo — es el gesto donde la Task 0 midió 530 ms contra
22 ms. Un doble de pruebas puede tapar el bug que existe: ya pasó con
`frame-step`.

**Fuera de alcance, a propósito:** las miniaturas se siguen generando del
original. Generarlas del proxy sería más rápido, pero es otra decisión y no
está en `DECISIONES.md`. Se anota en el punto de control, no se hace aquí.

---

## Task 8: Cierre de fase

- [ ] Suite completa en verde (sin `--ignore`), y el número anotado.
- [ ] Los detectores de la §8 del handoff: señales sin conectar, tokens
      huérfanos, widgets huérfanos tras 60 teclas (procesando `DeferredDelete`
      antes de contar), y textos de la app contra atajos registrados.
- [ ] **cProfile** de la importación y de la tecla de cuarto. Encontró algo las
      tres veces que se corrió; esta fase agrega trabajo al import, que es
      justo donde no se ha perfilado nunca.
- [ ] Los **dos anchos** (1600 y 1150 px): el badge nuevo alarga la fila de
      badges, y a 1150 px la fila de badges es más angosta.
- [ ] El arnés en las **dos pantallas**, mirando la imagen:

```bash
.venv/bin/python scripts/comparar_con_mockup.py --salida /tmp/comp.png
.venv/bin/python scripts/comparar_con_mockup.py --salida /tmp/hoja.png --pantalla 1
.venv/bin/python scripts/comparar_con_mockup.py --salida /tmp/rec.png --recorte 200,800,420,160 --zoom 3
```

- [ ] **`scripts/_datos_de_ejemplo.py` tiene que ejercitar lo nuevo**: sin un
      clip con proxy en los datos, el arnés compara el badge del mockup contra
      un hueco y no dice nada. Ya pasó tres veces.
- [ ] Sacar el renglón de la orientación hardcodeada de la lista de ejecución
      —era el único vivo— y verificar con `grep`, no de memoria.
- [ ] Actualizar `CONTEXTO-Y-METAS.md`: la meta «Proxies» deja de ser futura.
