# Reconectar todo el material de un jalón — diseño

*(Spec. Fecha: 2026-09-19. Sale de la plática con Bruno del mismo día,
después de arreglar el contador de miniaturas.)*

## 1. De dónde salió

Bruno mueve la carpeta del proyecto (o el disco entero cambia de lugar) y
al reconectar el archivo de Clipify se encuentra con que tiene que arreglar
el material **cuarto por cuarto**: el botón «Buscar…» ya existe por bin,
pero son tantos clics como cuartos tenga el rodaje. Lo pidió así:

> «Lo de reconectar todo me lo imagino como Premiere: en cuanto le doy un
> archivo, usa la misma estructura para encontrar los demás.»

## 2. Lo que ya existe y no se toca

- Cada bin guarda su `origen` (la carpeta de donde se importó) y cada clip
  su ruta **relativa a esa carpeta** (`proyecto.rutas_relativas`) — nunca
  se pierde aunque el archivo se mueva, mientras la relativa siga
  calzando.
- `revinculo.reencontrar_bin(carpeta, relativas, bytes, cuadros, medir)`
  ya busca y **confirma** (por tamaño y cuadros, nunca solo por nombre) el
  material de un bin bajo una carpeta dada. Esta función no cambia.
- El botón «Buscar…» de cada cuarto (`_on_buscar_media` en
  `main_window.py`) llama hoy a `QFileDialog.getExistingDirectory` y de
  ahí a `reconectar_bin(nombre, carpeta)`.
- El resultado se ve en la barra de avisos por bin (`aviso_de_media`), que
  ya sabe mostrar «reconectados», «no aparecieron», «se pelean por un
  archivo», etc. — **no se toca su forma**, solo va a reflejar más bins
  resueltos de una vez.

## 3. Las decisiones

1. **Sin botón nuevo.** El mismo «Buscar…» de cada cuarto es la única
   entrada. Bruno lo decidió así: menos que aprender, y el flujo ya existe.
2. **Pide un ARCHIVO, no una carpeta** — como Premiere. Bruno elige
   cualquier clip de ese cuarto en su ubicación nueva (no tiene que ser
   justo uno de los que faltan: cualquier clip de ese bin sirve para
   ubicar la carpeta).
3. **De ahí se derivan DOS cosas:**
   - la carpeta nueva de ESE bin (como hacía la carpeta elegida a mano
     hasta hoy), y
   - el **cambio de ruta**: qué parte del camino viejo se volvió qué parte
     del camino nuevo.
4. **El cambio se le aplica a los demás cuartos, y solo se usa si la
   carpeta resultante existe de verdad en el disco.** Ninguna carpeta
   inventada, ninguna adivinanza sin comprobar — la regla de siempre del
   proyecto: *la app propone, nunca adivina en silencio* aplicada aquí
   como *la app prueba, nunca engancha sin comprobar* (que ya hace
   `reencontrar_bin`: sin confirmar por tamaño/cuadros, no se engancha).
5. **Los proxies quedan fuera.** «Buscar proxies…» sigue pidiendo una
   carpeta, sin cambios.

## 4. Cómo se calcula el cambio de ruta

Con el archivo que Bruno eligió y la ruta relativa que ese clip ya tenía
guardada, se sube tantos niveles como carpetas tenga esa relativa para
llegar a la carpeta nueva del bin. Ejemplo: si la relativa guardada era
`C0001.MP4` (sin subcarpetas), la carpeta nueva es directamente la carpeta
que contiene al archivo elegido.

Con la carpeta **vieja** (`bins.origen_de(nombre)`, que nunca se
sobrescribe) y la carpeta **nueva** recién calculada, se comparan sus
partes **desde el final**: el tramo final que coincide en las dos rutas es
la parte que NO cambió (típicamente el nombre del propio cuarto, `Sony`,
`Dron`); el resto, desde el principio hasta ahí, es el tramo que sí
cambió.

```
vieja:  /Volumes/DiscoViejo/Rodaje X/Sony
nueva:  /Volumes/DiscoNuevo/Rodaje X copia/Sony
                                          └── coincide, no es el cambio
        └──────────────────┬─────────────┘
                       esto sí cambió
```

Para cada OTRO bin con material perdido, se toma su carpeta vieja
(`origen_de` de ese bin) y se comprueba si empieza con el tramo que
cambió. Si sí, se arma la carpeta candidata reemplazando ese tramo por el
nuevo (`/Volumes/DiscoViejo/Rodaje X/Dron` →
`/Volumes/DiscoNuevo/Rodaje X copia/Dron`). Si esa carpeta candidata
**existe en el disco**, se corre `reencontrar_bin` sobre ella exactamente
igual que si Bruno la hubiera elegido a mano. Si no existe, o la carpeta
vieja de ese bin no empezaba con el tramo que cambió, ese bin se deja tal
cual — sigue pidiendo que lo busquen, como hoy.

Este cálculo es una función sin Qt y sin tocar disco más que un
`.exists()`, así que se prueba entera con pruebas normales de Python, sin
ventana.

## 5. Qué archivo eligió Bruno, y a qué clip corresponde

El archivo elegido se compara por **nombre** (igual que ya hace
`buscar_bajo`, sin mayúsculas) contra las rutas relativas de **todos los
clips de ese bin**, no solo los que faltan — así Bruno no tiene que
adivinar cuál de los que faltan es el que tiene enfrente, cualquier clip
del cuarto le sirve para ubicar la carpeta.

- **Ningún clip de ese bin tiene ese nombre** → se le dice que ese archivo
  no es de ese cuarto, y no se hace nada.
- **Más de un clip del bin tiene ese nombre** (pasa si formateó la tarjeta
  a medio rodaje y repitió `C0001.MP4`) → no se adivina cuál es: se le
  pide que seleccione la carpeta a mano para ese cuarto, con el mismo
  mensaje que ya usa el proyecto para «esto no se puede comprobar solo».
- **Exactamente un clip calza por nombre** → se sigue con el cálculo del
  §4.

## 6. Lo que Bruno ve

Nada nuevo que aprender: aprieta «Buscar…» en el cuarto que le avisa,
ahora el diálogo pide un archivo en vez de una carpeta, y listo. Si de
paso se resolvieron otros cuartos, sus renglones en la misma barra de
avisos cambian solos a «reconectados» — es la misma barra que ya existe,
diciendo la verdad de más bins a la vez.

## 7. Lo que NO entra

- **Proxies.** Buscan por carpeta, como hoy (§3.5).
- **Un botón «Reconectar todo» separado.** Se evaluó y Bruno prefirió
  reusar el botón que ya existe (§3.1).
- **Adivinar cuando la carpeta candidata no existe.** Nunca se inventa ni
  se ofrece una carpeta sin comprobar que está ahí (§3.4).
- **Cambiar `bins.origen_de`.** Sigue siendo la carpeta ORIGINAL de
  importación, nunca la última reconectada — es justo lo que permite
  comparar vieja-contra-nueva la próxima vez que se mueva algo.

## 8. Cómo se comprueba

**Con pruebas de Python**, en `tests/test_revinculo.py` (la función nueva
vive en `revinculo.py`, sin Qt):

- Que la carpeta nueva de un bin se calcule bien con una relativa sin
  subcarpetas y con una relativa anidada.
- Que el «tramo que cambió» se calcule bien cuando el tramo común es de
  un solo nivel (`Sony`) y cuando no hay ningún tramo común (carpetas sin
  relación → no se puede adivinar nada, se dice que no hay patrón).
- Que aplicar el cambio a la carpeta vieja de OTRO bin devuelva la
  candidata correcta, y `None` cuando esa carpeta vieja no empieza con el
  tramo que cambió.
- Que un archivo que calza con dos clips del mismo bin no elija ninguno.
- Que un archivo que no es de ningún clip del bin no haga nada.

**Con pruebas de la ventana**, en `tests/ui/test_main_window_revinculo.py`:

- Que elegir un archivo (no una carpeta) para el cuarto A reconecte
  también al cuarto B cuando su carpeta candidata existe con el material
  de verdad.
- Que el cuarto B se quede sin tocar cuando su carpeta candidata no
  existe en disco.
- Que «Buscar proxies…» siga pidiendo una carpeta sin cambios.

**Verificación visual real**: captura del diálogo de archivo abriéndose
desde «Buscar…», y de la barra de avisos con dos cuartos reconectados
después de un solo archivo elegido.
