# Prompt para abrir la sesión que construye la guía de edición

*Cópialo entero y pégalo como primer mensaje de una conversación nueva, abierta
en este repo, en la rama `orden-sugerido-de-cuartos`.*

*Está escrito para correr **sin input de Bruno**: la sesión ejecuta las 21
tareas del plan, una por una, y solo se detiene si algo la deja sin poder
seguir. Lo que no se pueda verificar sin él queda anotado al final en vez de
convertirse en una pregunta a media construcción.*

---

```
Estás en el repo de Clipify, la app con la que Bruno clasifica el material de
sus rodajes inmobiliarios. Bruno es editor de video, no programador, y hoy no
va a estar mirando: esta sesión construye sola de principio a fin.

Antes de nada, las reglas de casa. Están en el CLAUDE.md del repo y tienen
prioridad sobre cualquier costumbre tuya, pero éstas son las que más se rompen:

- Todo en español mexicano, de tú. Nunca "vos" ni "vosotros". "Aquí", no "acá".
  "Computadora", no "ordenador". "Video", no "vídeo". Aplica a los commits, a
  los comentarios del código, a la documentación y sobre todo a los textos que
  Bruno ve dentro de la app.
- Los términos que la industria usa en inglés se quedan en inglés: pick,
  reject, render, proxy, frame, timecode.
- Trabaja directo sobre la rama `orden-sugerido-de-cuartos`. NO crees branches
  nuevas y NO abras PRs.
- Los commits terminan con:
  Co-Authored-By: <el modelo que de verdad hizo el trabajo> <noreply@anthropic.com>
- Los archivos temporales van al scratchpad de la sesión, NUNCA al repo.

QUÉ VAS A CONSTRUIR

La guía de edición se muda del plugin de Premiere a Clipify. Hoy Bruno le pide
a una pestaña de Premiere que le sugiera en qué orden acomodar los cuartos del
recorrido; de ahora en adelante eso se arma en Clipify —donde los cuartos nacen
y donde acaba de ver todo el material— y viaja congelada dentro del manifest.
El panel de Premiere queda de solo lectura: sin llave, sin red, sin esperas.

Lee estos tres, en este orden, ANTES de tocar nada:

  1. CLAUDE.md
  2. docs/superpowers/specs/2026-09-14-guia-de-edicion-en-clipify-design.md
  3. docs/superpowers/plans/2026-09-14-guia-de-edicion-en-clipify.md

El spec ya está aprobado por Bruno y el plan también. No los rediscutas, no
propongas alternativas y no abras un brainstorm: el diseño está cerrado. Si
encuentras que una tarea del plan no se puede hacer como está escrita,
actualiza el plan primero explicando por qué, y luego hazla.

CÓMO TRABAJAR

El plan trae 21 tareas en siete fases, y cada tarea trae sus pasos con casilla.
Hazlas EN ORDEN, sin saltarte ninguna:

- Escribe primero la prueba que falla, córrela y mira que falle por la razón
  correcta, escribe el código mínimo, córrela otra vez, y haz UN commit por
  tarea. Es TDD de verdad, no escribir el código y ponerle pruebas después.
- Antes de pasar de una fase a la siguiente, corre las dos suites completas:

      QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/ -q
      node uxp-plugin/pruebas/correr.js

  Las dos tienen que estar verdes. Si algo se rompió, arréglalo antes de
  avanzar: una fase que deja rota a la anterior no está terminada.
- No reportes nada como hecho sin haber visto la salida del comando que lo
  comprueba. Si una prueba falla, dilo con su salida; si algo lo dejaste
  pendiente, dilo.

LAS TRES TRAMPAS DE ESTE TRABAJO

Son las que ya mordieron antes en este repo. Están explicadas en el plan, pero
van aquí para que no se te pasen:

1. EL DOCUMENTO DEL PATRÓN NO LLEVA CUENTAS. Es la Tarea 1 y es la regla que
   más pidió Bruno y la más fácil de romper. Nada de "(15 videos)", nada de
   porcentajes, nada de "en la mayoría de los casos", nada de justificarse. Va
   escrito como se lo contarías a alguien que va a editar por él, más una lista
   de orden. Las cuentas SÍ se hacen —para decidir qué entra— pero se quedan
   fuera del documento. El plan trae un grep que las caza: córrelo.

2. NO LE CREAS A LA DOCUMENTACIÓN DE ADOBE sobre qué métodos existen en UXP. Ya
   falló tres veces el mismo día en este mismo plugin. Antes de llamar a
   cualquier cosa del objeto de Premiere —y en particular para renombrar un
   bin, que es lo que hace falta en la Tarea 17— imprime primero
   Object.getOwnPropertyNames(Object.getPrototypeOf(obj)) y usa lo que salga de
   verdad. Anota en el commit qué método resultó ser.

3. LA IGUALDAD ES EXACTA, siempre. Al comparar nombres de cuartos no hagas
   trim, ni minúsculas, ni quites acentos. "Recamara 1" contra "Recámara 1" son
   un cuarto que falta y otro inventado, no un empate — y normalizar ahí
   esconde justo el caso que la revisión existe para atrapar.

VERIFICACIÓN VISUAL: SI NO VISTE EL PIXEL, NO LO AFIRMES

Las Tareas 15 y 20 piden cuatro capturas y que las MIRES leyéndolas como
imagen, no solo generándolas. Un widget de PySide6 se captura con grab() y se
guarda como PNG; el panel del plugin es HTML, así que se sirve con
python3 -m http.server y se abre con una herramienta de navegador. Los archivos
de esa verificación van al scratchpad, nunca al repo.

LO QUE NO VAS A PODER COMPROBAR, Y QUÉ HACER

Tres cosas necesitan a Bruno o su computadora, y ninguna es razón para
detenerte:

- LA LLAVE DE LA API no la tienes, así que no puedes hacer una llamada de
  verdad al modelo. No hace falta: las pruebas de esa parte van con la llamada
  sustituida, y así están escritas en el plan. NO inventes una llave, NO la
  busques en el disco y NO metas ninguna al repo.
- PREMIERE no lo puedes abrir. La lógica del plugin se prueba con
  `node uxp-plugin/pruebas/correr.js`, que corre sin Premiere, y eso es lo que
  cubre el plan. Lo que de verdad necesita Premiere —crear bins, renombrarlos—
  queda para que Bruno lo pruebe.
- SI EL ORDEN QUE PROPONE LA GUÍA SE PARECE A CÓMO EDITA BRUNO. Eso solo lo
  sabe él.

Si te topas con algo que no está en esta lista y que te dejaría sin poder
seguir, haz TODO lo demás primero y deja eso anotado al final. No te detengas a
media construcción a esperar una respuesta que hoy no va a llegar.

CUANDO TERMINES

Deja el repo limpio: corre `git status --short` y revisa que cada archivo nuevo
esté en una carpeta que tenga sentido, que no haya nada suelto en la raíz y que
no quedaran restos del scratchpad.

Y escríbele a Bruno un reporte corto, en palabras normales y sin lenguaje
técnico —él no programa—, que diga:

- qué puede hacer ahora que antes no podía, en una o dos frases;
- las cuatro capturas, para que las vea;
- la salida de las dos suites;
- qué te faltó comprobar y qué necesitas de él para cerrarlo.

El detalle técnico va en los commits y en los docs, que es donde sirve. En el
mensaje final, no.
```
