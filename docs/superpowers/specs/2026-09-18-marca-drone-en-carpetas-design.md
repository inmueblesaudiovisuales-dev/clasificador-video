# La marca `[DRONE]` en las carpetas de Premiere — diseño

*(Spec. Fecha: 2026-09-18. Pedido de Bruno: «quiero que las tomas de drone
estén en una carpeta separada o algo indique que son de drone como
[DRONE]».)*

## 1. El problema

Hoy, en Premiere, la carpeta de un cuarto se llama nada más con su número y
su nombre: `03. Cocina`. Nada en el panel de proyecto dice de un vistazo que
un cuarto es del dron — hay que abrirlo y mirar el color de los clips
(`CAMARA`, azul Sony / amarillo DJI), que ya existe pero no se ve en la
lista de carpetas sin entrar a cada una.

## 2. Qué detecta «esto es del dron»

**Es una señal nueva y separada del color de cámara que ya existe.** El
color de cámara sigue decidiéndose exactamente igual que hoy, mirando el
nombre de los ARCHIVOS (`DJI` en el nombre del archivo → amarillo). Esta
marca no lo toca.

Lo que se revisa aquí es el **nombre del bin de importación** — la tanda con
la que Bruno arrastró el material, la misma que hoy se ve como encabezado en
la hoja de contactos. Por default ese nombre es el de la carpeta que
arrastró (`carpeta.name`), y Bruno puede renombrarlo desde el menú del bin.

**Regla:** si el nombre del bin contiene la palabra **`dron`**, sin
distinguir mayúsculas de minúsculas, ese bin cuenta como bin de dron.

`dron` y no `drone` a propósito: la cadena `dron` ya es parte de `drone`
(«**dron**e»), así que una sola comparación cubre las dos formas de
escribirlo sin necesitar una lista. Es el mismo criterio que ya usa
`camaras.py` para `DJI` — una palabra, buscada como substring, sin adivinar
más de la cuenta.

## 3. La regla del cuarto: todo o nada

Un cuarto (la carpeta `03. Cocina`, `05. Aérea final`, etc.) se marca
`[DRONE]` **solo si el 100% de sus clips vienen de un bin de dron.**

- Un solo clip que haya entrado por un bin que no dice `dron` —una tarjeta
  de la Sony que se coló— y el cuarto entero se queda sin marca. Bruno lo
  pidió así explícitamente, sobre la alternativa de «la mayoría manda» que
  ya usa `camaras.py` para el color: para esta marca quiere la regla más
  estricta.
- **Un clip suelto (sin bin) tampoco cuenta como dron.** No hay de dónde
  confirmarlo, y confirmar es el requisito — no basta con que no conste lo
  contrario.
- Un cuarto vacío, o que no aparece en el manifiesto que se está
  importando, no se evalúa: no hay clips de los que sacar una respuesta.

## 4. Cómo se ve

```
02. Clip
  ├── 01. Fachada
  ├── 02. [DRONE] Aérea fachada
  ├── 03. Cocina
  └── 04. [DRONE] Aérea final
```

El orden es **número, luego `[DRONE] `, luego el nombre que Bruno le puso al
cuarto** — tal como lo pidió.

Si el manifiesto no trae guía aceptada (y por lo tanto la carpeta no lleva
número, que es el comportamiento de hoy sin guía), la marca igual se pone,
al inicio del nombre: `[DRONE] Aérea fachada`. Es la misma posición relativa
— antes del nombre, nunca en medio ni al final —, nada más sin número que la
empuje.

## 5. Se actualiza sola, como el número

**Es exactamente el mismo problema que ya resolvió el número de la carpeta**
(`docs/superpowers/specs/2026-09-14-guia-de-edicion-en-clipify-design.md`):
Bruno reimporta el mismo cuarto en otra pasada, y esta vez la mezcla de
clips cambió — antes era 100% dron, ahora se coló uno de la Sony, o al
revés. La carpeta tiene que dejar de decir `[DRONE]` o empezar a decirlo,
sin crear una segunda carpeta para el mismo cuarto.

Por eso, **la marca se trata igual que el número**: es parte de lo que el
plugin reconoce como «suyo» al decidir si una carpeta que ya existe es la
misma que está buscando, y se agrega o se quita sola al reimportar —
comparando el nombre SIN el número y SIN la marca. Es la misma idea que ya
usan las marcas de estado en el nombre de los clips (`★`/`✓`/`✕`): se quita
lo que el plugin puso, nunca lo que Bruno haya escrito él mismo en el
nombre del cuarto.

**Nunca se duplica ni se acumula.** Dos pasadas seguidas con la misma mezcla
de clips dejan la carpeta exactamente igual — ni un `[DRONE] [DRONE]`, ni
una carpeta nueva al lado de la vieja.

## 6. Cómo viaja el dato

De qué bin salió cada clip ya se sabe hoy del lado de la app (es lo mismo
que usa para el color de cámara, `_camaras_por_clip`, nada más que mirando
el NOMBRE DEL BIN en vez del nombre del archivo). Ese dato — «este clip
vino de un bin que decía dron» — viaja en el manifiesto junto con cada
clip, igual que ya viaja `camara`. El plugin del lado de Premiere es quien
decide, cuarto por cuarto, si TODOS sus clips traen ese dato en verdadero,
y arma el nombre de la carpeta con eso.

**La app no decide qué cuartos son de dron.** Solo dice, de cada clip, de
qué bin salió. Juntar eso por cuarto y ponerle la marca a la carpeta es
trabajo del plugin — mismo reparto de tareas que ya existe para el número
de la carpeta (la app manda el orden de la guía, el plugin arma el nombre).

## 7. Qué NO cambia / qué NO entra

- **El color de cámara del clip.** Sigue exactamente igual, con su propia
  detección por nombre de archivo. Esta marca es una señal aparte y no la
  reemplaza ni la corrige.
- **Ninguna carpeta separada para el dron.** Bruno mencionó dos ideas al
  pedir esto —carpeta aparte o marca en el nombre— y se quedó con la
  marca: los clips del dron se clasifican en su cuarto de siempre (`Aérea
  fachada`, `Aérea final`...), y es la carpeta de ESE cuarto la que se
  marca. No hay un cajón nuevo que junte todo lo del dron sin importar el
  cuarto.
- **No hay forma manual de forzar o quitar la marca de un cuarto.** Sale
  sola de la regla del §3. Si algún día hace falta corregirla a mano, es
  una función nueva y aparte — hoy no se pidió.
- **El nombre del bin de importación no se valida ni se sugiere.** Si Bruno
  arrastra una carpeta que no dice «dron», sus clips simplemente no cuentan
  para la marca; no hay aviso ni corrección automática. Puede renombrar el
  bin desde su menú si le atinó mal, como ya puede hacer con la cámara.

## 8. Cómo se comprueba

**Lógica pura, con tests (`node uxp-plugin/pruebas/correr.js` y
`pytest`):**

- Del lado de la app: qué bins cuentan como dron por su nombre —
  `Dron`, `DRONE FINAL`, `dron_card_2`, y un nombre que NO trae la palabra
  (`Sony A`, `Tarjeta 2`) que no cuenta. Y que ese dato viaja por clip en el
  manifiesto igual que `camara`.
- Del lado del plugin: un cuarto con todos sus clips de bins de dron sale
  marcado; uno con un solo clip de otro bin, no; un cuarto con algún clip
  suelto (sin bin), no; la marca se agrega y se quita sola entre dos
  pasadas con distinta mezcla; dos pasadas iguales no acumulan ni
  duplican; un cuarto sin número (sin guía aceptada) también se marca, en
  la misma posición relativa.

**Verificación visual real**, según `CLAUDE.md`: importar un manifiesto de
prueba con un cuarto 100% dron y otro mezclado, contra un proyecto de
Premiere real, y mirar el panel de proyecto con los ojos.
