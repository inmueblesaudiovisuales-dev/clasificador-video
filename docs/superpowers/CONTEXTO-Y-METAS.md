# Contexto y metas del proyecto

*(Última actualización: sesión de limpieza de higiene de carpeta, agosto 2026.
Este documento describe intención y dirección — para decisiones técnicas ya
tomadas, ver `CLAUDE.md` en la raíz del repo. Para qué es la app y cómo
correrla, ver `README.md`.)*

## Estado actual

**En desarrollo activo — todavía faltan features, no es una herramienta
terminada.** La app (PySide6) y el plugin UXP funcionan de punta a punta
para el flujo básico: importar clips, clasificar por cuarto, marcar in/out y
pick/reject, exportar manifest, armar el proyecto en Premiere. Ese camino
está probado con material real (Sony FX30). Lo que sigue es una mezcla de
pulido de lo que ya existe y features nuevas que todavía no se construyeron.

## Hacia dónde va (metas de Bruno, en sus palabras)

### Video y reproducción
- **Layout para orientación vertical** — hoy la app está pensada para clips
  horizontales; falta un layout que funcione bien con material vertical
  (relevante porque parte del material real es vertical, ver
  `docs/superpowers/HALLAZGOS-2026-08-05-rotacion-vertical.md` para el
  contexto de por qué la rotación importa tanto en este proyecto).
- **Mejor performance de reproducción, menos latencia frame por frame** — la
  navegación cuadro a cuadro (marcar in/out con precisión) tiene que sentirse
  instantánea, no la siente así hoy.
- **Proxies** — poder trabajar con archivos proxy más livianos en vez del
  material original de la cámara, para mejorar el rendimiento general de
  reproducción/scrub. (Nota: existe `src/clasificador_video/proxy_match.py`
  y un `js/proxy.js` en el plugin UXP — revisar qué tan lejos llegó ese
  trabajo antes de asumir que se arranca de cero.)

### Diseño visual
- **Rediseño más pulido** — la dirección "Console" actual (`theme.py`) es un
  punto de partida, no el destino final. Ver
  `docs/superpowers/HANDOFF-2026-08-06-rediseno-visual-creativo.md` para el
  handoff de la sesión dedicada a esto.

### Alcance / distribución
- **Que otros editores puedan usarla, no solo Bruno** — hoy la app asume
  implícitamente un solo usuario en una sola máquina (rutas, configuración,
  sesión autosave todo local). Pasar a "otra gente la instala y la usa"
  implica pensar instalación/distribución, no solo la lógica de negocio.

### Escala
- **Estabilidad y performance con proyectos más grandes** — shootings con
  muchos más clips, clips más pesados. Lo que existe hoy está probado con
  volúmenes chicos/medianos de prueba.

## Qué NO es una meta (para no asumir de más)

No hay pedido de features de edición (efectos, transiciones, etc.) más allá
de lo que ya existe (in/out, pick/reject, categorización). El foco es
clasificar y preparar material para que Premiere arme el proyecto, no
reemplazar a Premiere como editor.
