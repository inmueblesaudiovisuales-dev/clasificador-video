# Entrega a un editor externo — diseño de interfaz

*(Spec del 2026-09-18. Sesión de brainstorming con maquetas en navegador,
sin tocar código. Completa a `2026-09-18-entrega-a-editor-externo-design.md`
—que ya cerró el QUÉ (proxy de tamaño real, marcas de cámara, la
convención de Drive)— con el CÓMO se ve: dónde viven los botones, qué
enseña cada diálogo antes de actuar, y cómo se entera Bruno del estado de
varios proyectos a la vez.)*

## 1. Dónde viven los botones

`Subir a Drive` vive en la barra superior, en el mismo renglón que
`Configuración` / `Proxies` / `Guía de edición` / `Exportar a Premiere` —no
en un menú aparte—, y **siempre está visible**, incluso antes de exportar a
Premiere. La barra ya es el lugar de "las acciones que no son de
clasificación" (`title_bar.py`), y la entrega a un editor es una más de
esas, no una categoría nueva.

El renglón cambia con el estado de entrega de ESE proyecto (una cápsula que
reemplaza su propio contenido, el resto de la barra no se mueve):

1. **Nunca se ha subido nada** — solo `Subir a Drive`.
2. **Subiendo** — el botón se apaga y muestra progreso (`Subiendo… 42%`).
3. **Ya subido, esperando al editor** — aparece una píldora de estado
   (`● Con el editor · hace 2 días`) más dos botones: `Subir de nuevo` (por
   si Bruno cambió proxies o cuartos después de la primera subida, sin
   perder el link ya compartido) y `Traer de vuelta`.
4. **Ya trajiste el material** — píldora (`✓ Trajiste el material · hace 3
   horas`) y el botón vuelve a ser `Subir a Drive`, para una ronda nueva.

## 2. El diálogo "Subir a Drive"

Aparece al apretar el botón. Antes que nada resuelve **dónde está el
`.prproj`** —Clipify no lo arma, así que no lo sabe de entrada— y lo hace
con el mismo criterio que ya usa la app para la carpeta de proxies:
**propone, nunca adivina en silencio.**

### Búsqueda automática por folio

El nombre del proyecto de Clipify **ya es el folio** de Bruno (`IAV-2609.10-A`,
`2607.09`, etc. — confirmado con sus proyectos reales). Clipify pide, una
sola vez en Configuración, la carpeta raíz donde Bruno guarda todos sus
`.prproj` (hoy: `.../01. Proyectos 2026 IAV y PI/01. IAV`, organizada por
año → mes). Al abrir el diálogo, busca recursivamente ahí un archivo
`.prproj` cuyo nombre **contenga** el folio, sin importar la subcarpeta ni
un sufijo de versión (` V2`, ` V3`…).

Tres resultados posibles, todos mostrando la ruta ANTES de que exista botón
para subir de verdad:

- **Una sola coincidencia** — la ruta ya aparece escrita, con `Cambiar…`
  por si está mal.
- **Varias coincidencias** (mismo folio, distintas versiones) — propone la
  de fecha de modificación más reciente, y lo dice explícitamente
  ("hay 2 versiones… se propone la más reciente"), para que Bruno sepa que
  existe otra antes de aceptar.
- **Ninguna coincidencia** — el campo se pone en rojo ("No se encontró…") y
  pide elegir a mano con `Elegir…`. El botón `Subir` se queda apagado hasta
  que hay una ruta válida.

### Qué más enseña antes de subir

Un resumen fijo, sin que haga falta desplegar nada:

- Cuántos clips se van a subir (los picks) sobre el total del proyecto.
- El peso estimado de esos proxies.
- A qué cuenta de Drive se sube (la de Bruno, ya autorizada).

## 3. El diálogo "Traer de vuelta"

Mismo principio: **enseña qué encontró en Drive antes de tocar disco.**
Compara la fecha de modificación del `.prproj` en Drive contra la que
tenía cuando Clipify lo subió, y lista el contenido de `material nuevo/`
con su destino real dentro del proyecto de Bruno (`musica y audio/` → `01.
ASSETS VIDEO/05. MUSICA Y AUDIO`, etc., según la convención ya cerrada en
§6 de la spec original).

Dos casos:

- **Hay cambios** — lista cada archivo/carpeta encontrada con su destino,
  y aclara que los proxies no se vuelven a bajar (ya los tiene Bruno). El
  botón dice `Traer de vuelta`.
- **No hay cambios** (el `.prproj` en Drive tiene la misma fecha que
  cuando se subió, y `material nuevo/` está vacía) — no bloquea, solo
  avisa ("No parece que el editor haya subido nada todavía. ¿Seguro que
  quieres continuar?") y el botón cambia a `Traer de todas formas`. La
  decisión final siempre es de Bruno, igual que reconectar un proxy
  perdido.

## 4. Multi-proyecto: el estado se ve en la lista de inicio

Bruno puede tener varios proyectos con un editor externo a la vez, y la
`PantallaInicio` (`pantalla_inicio.py`) ya es el lugar donde ve todos sus
proyectos de un vistazo — es ahí donde debe verse quién tiene algo
pendiente, no solo dentro de cada proyecto.

Cada fila (`_FilaReciente`) que tiene un estado de entrega activo suma una
píldora a la derecha:

- **`● Con el editor`** (ámbar) — ya se subió, no se sabe si el editor
  contestó. Trae al lado un botón circular `⟳` que consulta Drive por ESE
  proyecto puntual.
- **`✓ El editor ya contestó`** (verde) — Clipify ya confirmó que hay algo
  nuevo en Drive (vía el `⟳` o al abrir el diálogo de "Traer de vuelta"
  dentro del proyecto). Sin `⟳`: ya se sabe, lo que sigue es abrir el
  proyecto.
- **Sin píldora** — nada pendiente (nunca se subió, o ya se trajo de
  vuelta). La fila se ve exactamente igual que hoy.

**La consulta a Drive es siempre a petición de Bruno, nunca automática al
abrir la app** —lo pidió explícitamente, para no depender de la conexión
cada vez que abre Clipify—. Eso significa que `● Con el editor` puede
quedarse ahí varios días aunque el editor ya haya contestado, hasta que
Bruno aprieta `⟳` o entra al proyecto y usa "Traer de vuelta". Es una
lectura que puede estar desactualizada por diseño, no un bug.

Esto es lo que hace que la función escale con varios proyectos activos:
Bruno no necesita abrir cada uno para saber cuál tiene algo esperando —lee
la lista una vez y decide dónde entrar—, y ningún proyecto sin entrega
activa cambia su fila ni un pixel.

## 5. Proxies viejos en 720p (hueco que dejó la spec original)

La spec original (§2) no dice qué pasa con los proxies que ya existen de
antes del cambio, generados en 720p. Decisión de esta sesión: **no se
toca nada de forma especial.** Un proxy viejo en 720p sigue sirviendo para
ver y clasificar en Clipify exactamente igual que hoy — el problema del
encuadre torcido (§2 de la spec original) solo aparece cuando ESE proxy
viaja a un editor externo que reencuadra sobre él. Regenerarlo es una
decisión manual de Bruno (borrar el proxy viejo y dejar que la app lo
vuelva a generar), no algo que la app fuerce ni ofrezca de forma especial.

## 6. Qué NO cambia

- El resto de `title_bar.py`, `pantalla_inicio.py` y el flujo de
  clasificación/hoja/clip quedan intactos — esto se **suma**, no
  reemplaza nada del diseño ya construido (rediseño 2026-08-08).
- No hay reconexión ni polling automático de Drive en segundo plano.
- No se vuelve a bajar el proxy al traer de vuelta (ya cerrado en la spec
  original, §5 y §7).
- El plugin de Premiere no se toca por esta sesión — la entrega a Drive es
  pura interfaz de Clipify.

## 7. Cómo se comprueba

- **Búsqueda por folio**: con una carpeta raíz de prueba y varios
  `.prproj` (un folio único, un folio con dos versiones, ningún folio
  coincidente) — que el diálogo proponga la ruta correcta en cada caso, o
  el fallback manual cuando no hay coincidencia.
- **Diálogo "Traer de vuelta"**: con un `.prproj` de Drive más nuevo que
  el subido → caso "hay cambios"; con la misma fecha → caso "no hay
  cambios", sin bloquear.
- **Píldoras de la lista de inicio**: un proyecto sin entrega activa no
  cambia su fila; uno con `subido_en` pero sin confirmación muestra
  `Con el editor`; uno confirmado por `⟳` o por el diálogo interno muestra
  `El editor ya contestó`.
- **Verificación visual real** (`CLAUDE.md`): construir la barra superior,
  el diálogo de subir, el de traer y la lista de inicio con los datos de
  prueba de arriba, capturar con `grab()` y mirar el PNG antes de decir
  que se ve bien.

## 8. Maquetas de esta sesión

Guardadas en
`.superpowers/brainstorm/4495-1789793393/content/` (no se copian al
repo — son de trabajo, la fuente de verdad queda en este documento):

- `titlebar-estados.html` — los 4 estados del botón/píldora en la barra.
- `dialogo-subir-v2.html` — el diálogo de subir con búsqueda por folio.
- `lista-proyectos.html` — la lista de inicio con las píldoras.
- `dialogo-traer.html` — el diálogo de traer de vuelta.

## 9. Estado

**Diseñado con Bruno el 2026-09-18, con maquetas revisadas en navegador,
sin tocar código.** Sigue el plan de implementación
(`docs/superpowers/plans/`), luego construcción con TDD, según el flujo
normal del proyecto.
