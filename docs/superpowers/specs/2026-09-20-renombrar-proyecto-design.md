# Renombrar el proyecto — diseño

*(Spec. Fecha: 2026-09-20. Sale de que Bruno se equivocó poniéndole nombre a
un proyecto al crearlo, y ese nombre ya viaja hasta el nombre de las
secuencias que arma el plugin en Premiere.)*

## 1. Por qué

`project_name` hoy solo se pone una vez, al crear o abrir el proyecto
(`app.py::abrir_proyecto`, `app.py::_poblar_ventana`), y de ahí no se puede
tocar. Un error de dedo ahí se arrastra hasta Premiere: el plugin arma el
nombre de cada secuencia con `manifest.proyecto` (`uxp-plugin/js/secuencia.js`
línea 10 y línea 17) — «Shooting mal escrito 4K 9:16», «… 16:9 1080p», etc.

Bruno quiere corregirlo **antes de crear las secuencias** — no es el caso de
renombrar secuencias que ya existen en un proyecto de Premiere abierto, eso
queda fuera.

## 2. Interacción

Doble clic sobre `TitleBar.project_label` (`ui/title_bar.py:65`) abre
`QInputDialog.getText(self, "Renombrar proyecto", "Nombre:", text=self.project_name)`
— el mismo mecanismo que ya usa `RoomRailRow._pedir_nombre`
(`ui/room_rail.py:318`) para renombrar un cuarto. Se reusa el patrón a
propósito: es lo que Bruno ya conoce de la app.

Si el texto queda vacío después de `strip()`, o es igual al nombre actual, no
pasa nada — mismo criterio que `RoomRailRow.pedir_renombrar`
(`ui/room_rail.py:327-330`).

## 3. Qué toca al confirmar

`MainWindow.renombrar_proyecto(nuevo: str)`:

1. `self.project_name = nuevo`
2. `self.setWindowTitle(nuevo)`
3. `self.title_bar.set_project(nuevo, ...)` con el conteo de clips/bins que ya
   se le pasa hoy (`ui/main_window.py:1769`, mismo patrón)
4. `self._autosave()` — ya escribe `proyecto=self.project_name` en el
   documento (`ui/main_window.py:2279` vía `proyecto.a_dict`), no hace falta
   tocar `proyecto.py`
5. `Recientes(RECIENTES_PATH).registrar(self.session_path, nuevo)` — para que
   la pantalla de inicio no se quede mostrando el nombre viejo. `registrar`
   ya es un upsert por ruta (`recientes.py:99`), así que llamarlo de nuevo
   actualiza la entrada existente en vez de duplicarla.

No se toca ninguna carpeta ni archivo en disco: ni la carpeta del proyecto,
ni el `.cvproj`, ni las carpetas de proxies (que ya dependen de
`carpeta_de_proxies`/la carpeta del material, no del nombre del proyecto).

## 4. Fuera de alcance

- Renombrar secuencias que ya existen en un proyecto de Premiere abierto —
  Bruno confirmó que el caso que le importa es corregir el error antes de
  importar.
- Cualquier lógica de "sugerir" o "adivinar" un nombre — el diálogo abre con
  el nombre actual ya puesto, igual que renombrar un cuarto.
