# Proyectos guardables y reencontrar la media — diseño

*(Spec. Fecha: 2026-08-09. Sale de una pregunta de Bruno: «¿habría forma de
también guardar el proyecto? ¿Y que otra computadora pudiera abrir el proyecto
y revincular la media?»)*

## 1. El problema

Hoy la app guarda **todo** lo que hace falta —el nombre del proyecto, los
cuartos, cada clip con su bin, su cuarto, su pick, su in/out y su proxy, más
tamaños, duraciones y rotaciones— pero lo guarda en **un solo archivo
escondido**: `~/.clasificador_video/sesion.json`. Una sola sesión, invisible,
imposible de mover y atada a esa computadora.

O sea que el dato ya está. Lo que falta es dejar que ese archivo **tenga
nombre, viva donde Bruno quiera, y se pueda abrir en otra máquina**.

Y ahí aparece el problema de verdad: **el manifest y la sesión guardan rutas
absolutas** (`Clip.to_dict()` escribe `str(self.ruta)`). En otra computadora
no va a coincidir **ninguna**: el disco monta con otro nombre, la carpeta
cuelga de otro lado. Abrir sin reencontrar la media no serviría de nada.

## 2. Las decisiones que tomó Bruno

- **Una carpeta por bin**, no una sola por proyecto. Su material no siempre
  cuelga del mismo lado: la Sony viene de una tarjeta y el dron de otra, y
  pueden estar en discos distintos. Cada bin **ya recuerda** de qué carpeta
  salió (`Bin.origen`), así que la pieza existe.
- **La app abre con una pantalla de inicio** que lista los proyectos
  recientes, con «Proyecto nuevo» y «Abrir otro…». Textual: «eliges un
  proyecto pero te enseña los últimos, como Premiere».
- **Un proyecto nuevo pide nombre y lugar al crearse.** Nunca existe trabajo
  sin un archivo donde vivir.
- **Al abrir, si falta media, se pregunta de inmediato.** No es una excepción:
  es lo normal al abrir en otra computadora.

## 3. El archivo de proyecto

Un JSON con extensión propia, `.cvproj`, escrito con la misma escritura
atómica de `autosave.py` (temporal + `rename`) y con el mismo debounce de hoy:
**se guarda solo mientras trabajas**, no hay que acordarse.

Contiene lo que ya contiene la sesión, más una cosa nueva: **por cada bin, su
carpeta de origen, y por cada clip, su ruta relativa a esa carpeta**.

```json
"bins": [
  {"nombre": "Sony FX30", "origen": "/Volumes/CARD_A/01. VIDEO CAMARA",
   "clips": [0, 1, 2]}
],
"clips": [
  {"orden": 1, "ruta": "/Volumes/CARD_A/01. VIDEO CAMARA/C0001.MP4",
   "relativa": "C0001.MP4", "bin": "Sony FX30", ...}
]
```

**La ruta absoluta se conserva** además de la relativa. No es redundancia: en
la computadora de Bruno es la que hace que todo abra sin preguntar nada, y es
la que ya entiende el plugin de Premiere. La relativa es la que permite
reencontrar.

**Un clip suelto** (sin bin) no tiene raíz contra la cual ser relativo. Se
guarda solo con su ruta absoluta y, si no aparece, se reencuentra
individualmente o se queda faltando. Es un caso menor a propósito: los
sueltos son la cola de trabajo, no el material acomodado.

**`Clip.to_dict()` no se toca.** Es el contrato con el plugin de Premiere.
La ruta relativa y el bin viajan **al lado**, con el mismo criterio que ya se
usó para tamaños, duraciones, rotaciones y bins.

## 4. La pantalla de inicio

Lo primero que se ve al abrir. Reemplaza al arranque actual, que va directo a
la hoja.

- **Los proyectos recientes**, con nombre, fecha de última edición y la
  carpeta donde viven. Un clic abre.
- Un proyecto **que ya no está en su lugar se ve apagado** y dice por qué, en
  vez de tronar al abrirlo. Se puede quitar de la lista.
- **«Proyecto nuevo»** — pide nombre y lugar, y cae en la hoja vacía con el
  estado vacío que ya existe («Arrastra aquí tus carpetas o clips»).
- **«Abrir otro…»** — selector de archivo.

La lista de recientes vive en `~/.clasificador_video/recientes.json`, con la
misma tolerancia a archivo corrupto que `load_session`: lo que no se entiende
se trata como «no hay recientes», nunca como una excepción que impida abrir.

## 5. Reencontrar la media

Al abrir un proyecto, la app comprueba qué archivos existen. Es barato: son
`stat` por clip, imperceptible con 132.

**Si falta algo, se avisa por bin**, que es la unidad que Bruno reconoce:

> **Dron** — 23 clips no se encuentran.  `[Buscar…]`
> **Sony FX30** — 109 clips no se encuentran.  `[Buscar…]`

Señalas la carpeta de un bin y la app busca ahí dentro, **por la ruta relativa
que guardó**. Para cada candidato **confirma que es el archivo que era**
comparando el **tamaño en bytes** y la **duración en cuadros** contra lo que el
proyecto ya tenía guardado.

**Lo que no confirma, no se engancha, y se dice.** Esto no es celo: las cámaras
repiten los nombres —la Sony numera `C0001.MP4` en cada tarjeta que
formateas— y enganchar el archivo equivocado sería peor que no encontrarlo,
porque Bruno no se enteraría. El plugin de Premiere ya tiene una prueba para
ese caso exacto (dos tarjetas con el mismo nombre de archivo).

**El proxy se reencuentra igual**, con su propia carpeta si hace falta: vive
aparte del original (`sample-media/` los separa en `clips/` y `proxy/`, como
llegan de la cámara).

**Al reconectar, se reescriben las rutas absolutas** del proyecto y se guarda.
La próxima vez abre sin preguntar.

### Lo que cuesta, dicho de una vez

- **Las portadas se generan de nuevo** en la otra computadora. El cache va por
  ruta, tamaño y fecha (`cache_dir_for`), y en esa máquina no existe. Con 132
  clips son unos minutos trabajando solos, una sola vez.
- **La otra computadora necesita la app.** El paquete `.app` existe pero
  **nunca se ha abierto en otra Mac** — eso sigue sin comprobarse, y este
  diseño no lo cambia.

## 6. Migración de lo que ya existe

Bruno tiene material clasificado en la sesión escondida. **No se pierde**: al
arrancar por primera vez con esto, si existe `~/.clasificador_video/sesion.json`
con clips, se convierte en un proyecto de verdad y entra a la lista de
recientes. La sesión vieja se conserva en disco hasta que él guarde el proyecto
convertido — borrar lo viejo antes de que lo nuevo esté a salvo es cómo se
pierden cosas.

## 7. Qué NO entra

- **No copia ni mueve media.** El proyecto apunta a los archivos, no los
  guarda.
- **Nada en la nube, ni dos personas a la vez.** Un archivo, un usuario.
- **No se reencuentra clip por clip a mano.** Se reencuentra por bin; si un
  archivo no aparece dentro de la carpeta que señalaste, queda faltando.
- **El manifest a Premiere no cambia.**

## 8. Cómo se comprueba

- **Tests** de lo que es lógica pura: calcular la ruta relativa contra la raíz
  del bin; reencontrar contra una carpeta que tiene los archivos, otra que
  tiene la mitad, y otra que tiene un tocayo del tamaño equivocado; que el
  proyecto se guarde y se lea completo; recientes con un archivo corrupto,
  ausente, o apuntando a un proyecto borrado; y la migración de una sesión
  vieja.
- **El caso que más importa probar**: un archivo con el nombre correcto y el
  contenido equivocado **no se engancha**.
- **Verificación visual real**, según `CLAUDE.md`: `grab()` de la pantalla de
  inicio con recientes (uno de ellos apagado) y del aviso de media faltante
  con dos bins. Mirar los PNG.
- **Sin `exec()` ni modales nuevos** fuera de los selectores de archivo del
  sistema, que son los que ya usa la app.
