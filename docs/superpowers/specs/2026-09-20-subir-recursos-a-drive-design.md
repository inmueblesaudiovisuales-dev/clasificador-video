# Subir carpetas de recursos a Drive — diseño

*(Spec del 2026-09-20. Punto 10 de la tanda de bugs del shooting del
2026-09-19 — [HANDOFF-2026-09-19-tanda-de-bugs-del-shooting.md](../HANDOFF-2026-09-19-tanda-de-bugs-del-shooting.md) —,
marcado ahí como feature nueva. Amplía
[2026-09-18-entrega-a-editor-externo-design.md](2026-09-18-entrega-a-editor-externo-design.md).)*

## 1. El problema

Bruno: "al subir a Drive no sube carpetas para recursos (música, etc.),
como se había hablado". Hoy "Subir a Drive" (`drive.py::subir_paquete`)
solo empaqueta el `.prproj` y los proxies. Si Bruno ya trae música,
fotos o gráficos elegidos en su carpeta local del proyecto, el editor no
los recibe — solo el video.

La spec del 2026-09-18 §6 ya resolvió el camino **contrario**: cuando el
editor agrega material, sube una carpeta `material nuevo/` con
subcarpetas por categoría, y "Traer de vuelta" la reparte a la
estructura local de Bruno usando `drive.mapa_de_categorias_de_material_nuevo()`:

```python
{
    "musica y audio": "01. ASSETS VIDEO/05. MUSICA Y AUDIO",
    "fotos": "03. ASSETS PHOTOS",
    "graficos y branding": "06. GRAFICOS Y BRANDING",
}
```

Este spec es el mismo mapa, en sentido inverso: lo que Bruno **ya
tiene** en esas tres carpetas locales, subirlo junto con el proyecto.

## 2. Diseño: mismo mapa, carpeta nueva "Recursos/"

`subir_paquete` sube el contenido de esas tres carpetas locales (si
existen y tienen archivos) a una carpeta nueva en Drive, **"Recursos/"**
— separada de `material nuevo/`, que sigue siendo exclusiva de lo que el
editor manda de vuelta. Mezclarlas confundiría "lo que yo mandé" con "lo
que él agregó".

```
(carpeta compartida en Drive)
├── Proxies/                    ← ya existe
├── Recursos/                   ← NUEVO
│   ├── musica y audio/
│   ├── fotos/
│   └── graficos y branding/
├── <nombre>.prproj
└── material nuevo/             ← ya existe, la llena el editor
```

Mismas tres categorías que `material nuevo/` — mismo `mapa_de_categorias_de_material_nuevo()`,
sin duplicar la lista. `04. TOUR 360` y `X. ARCHIVOS DRONE` quedan
fuera, igual que ya quedan fuera de `material nuevo/` (spec 2026-09-18 §6).

**Sin recursividad**: solo los archivos sueltos en cada carpeta, no
subcarpetas — mismo criterio que ya usa `traer_material_nuevo` al bajar
(ignora lo que sea carpeta dentro de cada categoría). Si Bruno organiza
su música en subcarpetas, esas subcarpetas no viajan; sería una
ampliación aparte si hiciera falta.

**Categoría vacía o carpeta que no existe → se omite**, ni siquiera se
crea la subcarpeta en Drive. Si NINGUNA de las tres tiene archivos (o no
hay raíz de proyecto todavía — cero bins con material), "Recursos/"
tampoco se crea. Nada de carpetas vacías esperando contenido que nunca
llega.

## 3. Dónde vive cada parte

- **`drive.py::subir_paquete`** gana un parámetro nuevo,
  `recursos: dict[str, list[Path]] | None`, con la misma forma que ya
  usa `traer_material_nuevo` del otro lado (nombre de categoría → rutas
  locales) — pero aquí las rutas son ARCHIVOS a subir, no un destino
  único. `drive.py` no conoce la estructura de carpetas de Bruno; arma
  la carpeta y sube lo que le pasan, igual que hace con `proxies`.
- **`main_window.py::_subir_a_drive`** arma ese diccionario ANTES de
  encolar el trabajo: por cada categoría de `mapa_de_categorias_de_material_nuevo()`,
  mira si `raiz_del_proyecto / <ruta de la categoría>` existe y lista
  los archivos sueltos que tiene. Mismo `_raiz_del_proyecto()` que ya
  usa `_traer_de_vuelta`.
- **La barra de progreso** (`progreso`, ya existe) cuenta también estos
  archivos en el total — mismo mecanismo que ya cuenta proxies, nada
  nuevo que inventar ahí.

## 4. Qué NO cambia

- **"Subir de nuevo"** sube los recursos otra vez, tal como ya hace con
  proxies y el `.prproj` — no hay control de duplicados hoy en ese
  camino, y agregar uno sería una mejora aparte que le tocaría por igual
  a proxies, no algo específico de este spec.
- **No hay botón nuevo.** Es parte del mismo "Subir a Drive" de
  siempre — Bruno no tiene que acordarse de nada extra.
- **La carpeta local de Bruno no se toca.** Es de lectura: subir no
  mueve ni borra nada de su estructura.

## 5. Cómo se comprueba

- `subir_paquete` con `recursos={"musica y audio": [archivo1, archivo2]}`
  crea "Recursos/musica y audio/" y sube ambos archivos.
- `recursos` con una categoría de lista vacía no crea esa subcarpeta.
- `recursos=None` o con todas las listas vacías no crea "Recursos/" en
  absoluto.
- `_subir_a_drive` arma el diccionario correcto a partir de una raíz de
  proyecto de prueba con algunas de las tres carpetas presentes y otras
  no — con doble de `drive.subir_paquete` para no tocar la red, mismo
  patrón que ya usan las pruebas de `test_main_window_entrega.py`.
