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
   no revueltos con ellos. Es lo que se ve en `sample-media/`: el original está
   en `clips/` y el proxy `20260804_PIB0587S03.MP4` está afuera. Así que
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
   contra el par real que hay en el repo.

3. **El tamaño del clip lo sigue mandando el ORIGINAL.** `_clip_sizes` decide
   el ancho del video, la forma de la miniatura y el texto de la barra de
   estado (`2160×3840`). Si eso empieza a salir del proxy, el layout cambia de
   forma sin que nadie lo haya pedido y la barra de estado miente sobre la
   resolución del material. El proxy solo decide **qué archivo se abre**.

4. **Dos vistas del mismo dato se contradicen solas.** Van cinco veces en este
   proyecto. Aquí hay dos pares en riesgo: el badge del clip actual y el
   contador de la barra de estado (los dos dicen «1080p»), y la orientación del
   manifest contra la que ya muestra la barra de estado
   (`status_bar.py::set_clip_info` ya calcula `vertical`/`horizontal`). **Una
   sola función, y las dos vistas la llaman.**

5. **Importar ya es lento y bloquea.** Hoy corre un `ffprobe` por clip, en
   serie, dentro de `_load_clips_from_ingest`. Sondear además cada proxy puede
   duplicar esa espera. La Task 0 lo mide y la Task 2 elige entre dos caminos
   con un número, no con una corazonada.

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

## Task 0: Spike — ¿el proxy calza con el original? — **antes de todo**

**Files:** al scratchpad de la sesión, **no al repo**.

Hay un par real en el repo para medirlo, sin pedirle material a Bruno:

- original: `sample-media/clips/20260804_PIB0587.MP4`
- proxy: `sample-media/20260804_PIB0587S03.MP4`

**Qué hay que demostrar, con números escritos de vuelta en este documento:**

- [ ] `probe_clip()` de los dos, lado a lado. **Criterio de aceptación del
      proxy**: mismo `fps` (diferencia < 0.01), misma `duration_frames` (±1
      cuadro) y misma orientación. Anotar qué dio.
- [ ] Cuánto tarda **un** `ffprobe` sobre el proxy. **De aquí sale la decisión
      de la Task 2**: si sondear 128 proxies suma **menos de 2 s** al import,
      va en el mismo ciclo, en serie; si suma más, va al `QThreadPool` con
      guarda de generación, como las miniaturas.
- [ ] Abrir el proxy en mpv y medir **cuánto tarda en dar el primer cuadro** y
      cuánto cuesta un `seek` exacto, contra los mismos dos números del
      original. Es la razón de ser de la decisión 2 de Bruno: si no gana nada
      medible, se le dice y se reconsidera antes de construirlo.
- [ ] Sondear el proxy **rotado**: comprobar que `probe_clip()` le aplica la
      misma corrección de rotación que al original. Si el proxy viniera sin la
      matriz de rotación, el video se vería acostado — y eso lo decide este
      spike, no un test con doble.

**Si el proxy no valida contra el original**, se para y se le pregunta a Bruno
antes de seguir: sin eso, la mitad de esta fase no tiene sentido.

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
- [ ] El proxy está en la carpeta padre de la importada → lo encuentra (el caso
      real de `sample-media/`).
- [ ] El proxy está en una carpeta hermana (`Clip/` y `Sub/`, el caso Sony) →
      lo encuentra.
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

**El camino de sondeo lo decide el número de la Task 0.** Si va al thread pool,
va con la misma guarda de generación que las miniaturas
(`self._thumb_generation`), o una importación nueva recibe resultados de la
anterior — ese bug ya está resuelto una vez en este archivo, se copia el
patrón, no se reinventa.

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

## Task 5: El badge `Proxy 1080p` sobre el video

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
- [ ] Clip con proxy validado → el badge se ve y dice `PROXY 1080P` (mayúsculas
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
      el proyecto se arma con material de 1080p y nadie lo nota hasta exportar.

**Y una comprobación con material real, no con doble:** abrir el par de
`sample-media/` en la app y ver que el video se ve derecho, que el badge dice
`PROXY 1080P` y que `,`/`.` avanza un cuadro. Un doble de pruebas puede tapar el
bug que existe — ya pasó con `frame-step`.

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
