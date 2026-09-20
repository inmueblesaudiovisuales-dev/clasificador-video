# Configuración desde la pantalla de inicio

2026-09-20. Bruno lo pidió directo: "en la pantalla de inicio quiero tener
acceso a configuración". Se brainstormeó en el chat (no hubo mockup ni
sesión con el visual companion) y quedó aprobado ahí mismo.

## El problema

`PantallaInicio` (`src/clasificador_video/ui/pantalla_inicio.py`) es una
ventana propia, sin la barra de título de `MainWindow` — ahí es donde vive
hoy el único botón de "Configuración" (`title_bar.py` →
`config_requested` → `main_window._abrir_configuracion`). Para llegar a
configuración hay que abrir un proyecto primero, aunque nada de lo que
`PantallaConfig` contiene es de un proyecto en particular: la llave de la
API, la conexión a Google Drive, la carpeta de Premiere, modo económico y
rápido, y borrar miniaturas son todas cosas de la app, guardadas en rutas
fijas (`~/.clasificador_video/`, `default_cache_root()`). El mensaje de
aviso que ya existe en `Coordinador._al_refrescar` ("Conecta Google Drive
desde Configuración...") ya asumía que se podía llegar ahí sin haber
abierto nada — un hueco que hoy no se puede cerrar.

## La decisión

Un ícono chico de engrane, arriba a la derecha de `PantallaInicio`, junto
al título "Tus proyectos". Al hacerle clic abre la misma `PantallaConfig`
que ya existe, como ventana hija no modal sobre `PantallaInicio` — mismo
patrón que usa `MainWindow._abrir_configuracion` (no modal porque el
`exec()` viejo colgaba la suite bajo `offscreen`, murió con la F3).

Se descartó ponerlo con palabra junto a "Proyecto nuevo" / "Abrir otro…":
esos dos ya son con texto y ese renglón es la fila de acciones del
día a día; configuración no lo es. Y el botón con texto que hay en la
barra de título fue una decisión deliberada (un glifo solo, ahí, se veía
como un punto perdido entre otros botones con texto) — pero esa razón no
aplica aquí: el ícono va solo, sin nada al lado que le compita, así que un
engrane chico se lee bien. Ya hay precedente de un glifo unicode como
texto de botón en este mismo archivo (`refrescar_button = QPushButton("⟳")`),
así que no hace falta un dibujo custom con `QPainter`.

## Qué se construye

- `PantallaInicio` gana una señal nueva, `configuracion_pedida`, y un botón
  `self.boton_configuracion` (`QPushButton("⚙")`, `objectName
  "inicioConfigBoton"`, tooltip "Configuración") en la misma fila que
  `self.titulo`, empujado a la derecha con un stretch. Sigue la misma regla
  de la clase: no abre nada por su cuenta, solo emite.
- QSS nuevo para `#inicioConfigBoton`: transparente, sin borde, `TEXT_3` en
  reposo y `TEXT` al pasar el mouse — mismo patrón que ya existe para los
  botones de `#guiaChip`.
- `Coordinador` (`src/clasificador_video/app.py`) gana su propia
  `_pantalla_config: PantallaConfig | None` y un método
  `_abrir_configuracion`, conectado a `self.inicio.configuracion_pedida`.
  Es una copia fiel del método que ya tiene `MainWindow`, con las mismas
  señales (`llave_guardada`, `llave_borrada`, `modo_economico_cambiado`,
  `modo_rapido_cambiado`, `carpeta_premiere_guardada`, `drive_conectado`,
  `miniaturas_borrar_pedido`, `cerrada`) — todas ya son operaciones
  globales (`llave.guardar/borrar`, `preferencias.*`,
  `default_cache_root()`), así que no hace falta inventar nada nuevo,
  solo cablearlas sin pasar por una ventana de proyecto.
  - Lo único que `MainWindow._cambiar_modo_economico` /
    `_cambiar_modo_rapido` hacen que `Coordinador` no puede (además de
    guardar la preferencia): tocar el pool de hilos de una ventana ya
    abierta. Desde el inicio no hay ventana que tocar, así que ahí el
    método de `Coordinador` solo llama a `preferencias.guardar_modo_*`. La
    próxima ventana que se abra ya lee la preferencia guardada al
    construirse.
  - `drive_conectado` deja el cliente en `Coordinador._drive_cliente_config`
    (atributo nuevo, solo para esto) en vez de en una ventana — sirve nada
    más para que la sesión de `PantallaConfig` no vuelva a pedir OAuth si
    se cierra y se reabre desde el mismo `Coordinador`.
- Posicionamiento: igual que en `MainWindow`,
  `setGeometry(self.inicio.rect().adjusted(...))` centrado sobre
  `PantallaInicio`.

## Qué NO cambia

- `PantallaConfig` (`pantalla_config.py`) no se toca: es la misma clase,
  los mismos campos, para los dos caminos.
- El botón de la barra de título de `MainWindow` sigue como está — sigue
  siendo texto, sigue a la izquierda de todo.
- No hay atajo de teclado nuevo.

## Pruebas

- `tests/ui/test_pantalla_inicio.py`: el botón existe, tiene el tooltip
  correcto, y un clic emite `configuracion_pedida`.
- `tests/test_app.py`: `Coordinador` abre `PantallaConfig` al recibir la
  señal, y guardar la llave / cambiar modo económico y rápido / la carpeta
  de Premiere pasan por las mismas funciones que ya usa `MainWindow` (se
  verifica con mocks de `llave` y `preferencias`, sin ventana abierta).
