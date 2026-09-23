# Proyecto en iCloud al crear un `.cvproj` (fase 1)

Fecha: 2026-09-23. Brainstorm con Bruno.

## Contexto y motivación

Bruno entrega proyectos a un editor externo subiéndolos a Google Drive
(`drive.py` + `entrega.py`). "Traer de vuelta" no le está funcionando bien y
bajar cosas de Drive es tedioso. Su alternativa: usar una carpeta de iCloud
que ya tiene armada a mano (`01. Proyectos 2026 IAV y PI/`, con una
subcarpeta por negocio, año y mes) para que el `.prproj`/`.aep` y los
proxies vivan ahí, sincronizados solos, sin subir ni bajar nada a mano.

Esto son dos proyectos separados (decisión tomada con Bruno al empezar el
brainstorm):

1. **Fase 1 (este documento):** que "Proyecto nuevo" arme la carpeta del
   proyecto en iCloud, con sus subcarpetas y los archivos de Premiere/AE ya
   creados a partir de un template.
2. **Fase 2 (fuera de alcance aquí):** reemplazar el mecanismo de
   "subir/traer de Drive" (estado de la entrega, colores de carpeta, "traer
   material nuevo") por algo que lea directo la carpeta de iCloud. Se
   brainstormea aparte, una vez que la fase 1 esté construida -- la
   necesita como base.

## Qué NO cambia en esta fase

- Los botones y el flujo de Drive (`drive.py`, `entrega.py`,
  `pantalla_config.py`) siguen exactamente como están. No se tocan en esta
  fase.
- Abrir un proyecto existente (`abrir_proyecto`) no cambia.

## El folio

El nombre de un proyecto de Clipify ya es el folio de Bruno
(`buscar_prproj.py` lo documenta). El formato, confirmado con Bruno:

```
<NEGOCIO>-<AA><MM>.<DD>-<LETRA>
```

- `NEGOCIO`: `IAV` (Inmuebles Audiovisuales) o `PI` (Proposal Inc). Siempre
  uno de los dos -- Bruno lo confirmó explícitamente, no hace falta
  preguntar cuál es si no calza.
- `AA`: año, dos dígitos (`26` → 2026).
- `MM`: mes, dos dígitos.
- `DD`: día, dos dígitos.
- `LETRA`: `A`, `B`, `C`... el número de proyecto de ESE día (el primero del
  día es `A`, el segundo `B`, etc).

Ejemplo real: `IAV-2609.10-A` → negocio IAV, 2026, septiembre, día 10,
primer proyecto del día.

Si el texto que escribe Bruno no calza con este patrón (letra de negocio
que no es IAV/PI, fecha imposible, formato raro), Clipify no adivina: se lo
dice y lo deja corregir el texto, sin crear nada.

## La carpeta raíz de iCloud es una preferencia, no un valor fijo

Igual que ya existe `carpeta_de_proyectos_premiere` en `preferencias.py`
para Drive, se agrega una preferencia nueva:

```python
def carpeta_raiz_icloud(ruta: Path | None = None) -> Path | None: ...
def guardar_carpeta_raiz_icloud(carpeta: Path, ruta: Path | None = None) -> None: ...
```

Se configura una vez desde Configuración (mismo patrón visual que ya existe
para la carpeta de proyectos de Premiere en `pantalla_config.py`). Sin
ella, "Proyecto nuevo" no puede armar la ruta y Clipify se lo dice --no cae
a ningún selector manual silencioso, porque sin esta carpeta no hay dónde
poner nada.

Dentro de esa raíz, la estructura que Bruno ya tiene armada a mano y que
Clipify recorre para llegar a la carpeta del folio:

```
<raíz>/
  01. IAV/
    2026/
      01. Enero/
      02. Febrero/
      ...
      09. Septiembre/
        <folio>/          ← esto es lo que Clipify crea
  02. PI/
    2026/
      ...
```

El nombre de la carpeta de negocio (`01. IAV`, `02. PI`) y de mes
(`09. Septiembre`) ya existen tal cual en el disco de Bruno -- se
confirmó mirando la carpeta real. Clipify no los crea: si faltaran (año
futuro que Bruno aún no arma, por ejemplo), es el mismo caso que "no se
pudo escribir", se lo dice y no continúa.

## Qué pasa al crear un proyecto nuevo

"Proyecto nuevo" deja de abrir el cuadro de "guardar como" de toda la
vida. En su lugar:

1. Pide el folio (texto).
2. Lo parsea. Si no calza con el patrón, avisa y deja corregir (paso 1).
3. Arma la ruta completa dentro de la carpeta raíz de iCloud (negocio →
   año → mes → folio) y **la enseña antes de crear nada**, para que Bruno
   la acepte o cancele. Nunca se adivina en silencio -- mismo criterio que
   ya aplica a la carpeta de proxies (`docs/.../2026-08-25-...`).
4. Si la carpeta del folio **ya existe** (Bruno la hizo a mano, o es un
   proyecto repetido), Clipify NO decide sola: avisa que ya existe y no
   crea ni copia nada -- Bruno decide qué hacer desde fuera de la app.
5. Si no existe, la crea con sus 8 subcarpetas, siempre las 8, en este
   orden:

   ```
   01. Proyecto premiere
   02. Proyecto AE
   03. Proxies
   04. Musica
   05. Logos y graficos
   06. Voz IA
   07. guiones
   08. Clipify
   ```

   (Los nombres exactos, con mayúsculas/tildes tal como los escribió
   Bruno, se preservan literal.)

6. Copia los templates vacíos:
   - `03. Templates/TemplatePremiere.prproj` → `01. Proyecto premiere/<folio>.prproj`
   - `03. Templates/TemplateAE.aep` → `02. Proyecto AE/<folio>.aep`

   La ruta de `03. Templates` es `<raíz>/03. Templates/`, hermana de
   `01. IAV`/`02. PI` (confirmado mirando el disco). Si algún template no
   está ahí, Clipify avisa con el nombre exacto que buscó y no crea nada a
   medias.

7. El `.cvproj` de Clipify (el que trae la clasificación de los clips) se
   guarda dentro de `08. Clipify/<folio>.cvproj`. Esto reemplaza al cuadro
   de "guardar como": ya no hace falta, porque el nombre y la ubicación ya
   se derivaron del folio.

No existe una pregunta de "Local o Colaborativo". Todo proyecto nuevo pasa
por este flujo -- Bruno ya guarda todos sus `.prproj` en esta carpeta de
iCloud hoy, con o sin editor externo de por medio. Ver la sección de
Proxies para dónde sí importa la diferencia.

## Proxies: la única diferencia real entre "para mí" y "para un editor"

`proxy_gen.proponer_carpeta(carpeta_del_bin)` decide qué carpeta proponerle
a Bruno la primera vez que genera un proxy de un rodaje, y hoy solo mira
qué hay junto al material. Se le agrega un candidato con prioridad más
alta: si el proyecto abierto tiene una carpeta de iCloud vinculada (la que
se creó en el paso anterior), se propone su `03. Proxies` en vez de la
carpeta junto al material.

Sigue siendo **una sola propuesta con confirmación** -- igual que hoy, no
un menú de opciones nuevo. Si Bruno no quiere que ese rodaje vaya a
iCloud, contesta la pregunta con otra carpeta (ya se puede desde el mismo
cuadro) y de ahí en adelante usa esa. Y como ya existe
"cambiar carpeta de proxies" en el menú del rodaje, cambiar de opinión más
adelante -- pasar de local a compartido o al revés -- no necesita nada
nuevo: ya se puede.

Esto es intencional y fue una simplificación que Bruno aprobó durante el
brainstorm: no hace falta un concepto de "modo" que Clipify recuerde por
proyecto. La única pregunta real es "¿en qué carpeta van los proxies de
este rodaje?", y esa pregunta -- y su respuesta -- ya existen.

### Cómo sabe `proponer_carpeta` de la carpeta de iCloud

`proponer_carpeta` no conoce nada del proyecto hoy, solo la carpeta del
material. Se le agrega un parámetro opcional:

```python
def proponer_carpeta(carpeta_del_bin: Path,
                      carpeta_de_icloud: Path | None = None) -> Path:
```

`main_window.py` se lo pasa desde el dato que guardó `crear_proyecto` en el
`.cvproj` (la ruta de la carpeta del folio en iCloud, si el proyecto se
creó con este flujo). Un proyecto viejo, de antes de esta fase, no tiene
ese dato -- sigue proponiendo como hoy.

## Qué se guarda en el `.cvproj`

Un campo nuevo, análogo a como `entrega` guarda su propio estado:

```json
"carpeta_de_icloud": "/Users/.../01. IAV/2026/09. Septiembre/IAV-2609.10-A"
```

`None`/ausente en proyectos viejos o creados fuera de este flujo. Sirve
para:
- proponer `03. Proxies` de ahí (sección anterior),
- ser la base de la fase 2 (saber dónde leer si el editor contestó, sin
  Drive).

## Errores y casos raros

- **Carpeta raíz de iCloud no configurada:** avisa y manda a Configuración,
  no crea nada.
- **La carpeta raíz no existe en disco** (iCloud no sincronizado, Mac
  offline, se movió): mismo aviso que "no se pudo escribir" hoy en
  `crear_proyecto` -- no revienta la app.
- **Folio no parseable:** avisa con el motivo (negocio no es IAV/PI, fecha
  inválida) y deja corregir el texto.
- **La carpeta del año/mes no existe** dentro del negocio: mismo trato que
  "no se pudo escribir" -- Bruno la arma a mano si hace falta (ya lo hace
  hoy para años nuevos).
- **La carpeta del folio ya existe:** avisa, no crea ni copia nada, Bruno
  decide fuera de la app.
- **Algún template no está en `03. Templates/`:** avisa con el nombre
  exacto que buscó, no crea nada a medias (ni las carpetas ni el otro
  archivo).

## Fuera de alcance (fase 2 o después)

- Tocar `drive.py`, `entrega.py`, o quitar los botones de Drive.
- Detectar si el editor externo contestó, leyendo la carpeta de iCloud.
- Migrar proyectos viejos para que tengan `carpeta_de_icloud`.
- Cualquier cambio a cómo se organiza el material original (sigue en el
  SSD de Bruno, sin tocarse).
