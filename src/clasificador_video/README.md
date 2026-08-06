# Estado de este módulo — obsoleto como mecanismo de entrega, 2026-08-06

Este paquete (`rate.py`, `models.py`, `probe.py`, `xmeml.py`, y las pruebas
correspondientes en `tests/`) fue el primer intento de este proyecto: generar
un documento xmeml (Final Cut Pro 7 XML) con bins anidados, in/out por frame
y colores de etiqueta, para importarlo a Adobe Premiere Pro. Se construyó con
TDD, 39 pruebas, y funcionaba tal como estaba diseñado.

**Por qué quedó obsoleto:** se descubrió con clips reales que Premiere
**nunca abre el archivo de video al importar un xmeml** — arma el clip solo
con lo declarado en el XML. No existe ninguna etiqueta de rotación en ese
formato ni en el modelo de interpretación de material de Premiere, así que
un clip vertical (grabado con rotación de cámara, el caso normal de este
proyecto con la Sony FX30) siempre se ve acostado al importarlo por xmeml,
sin solución posible dentro de ese formato. Evidencia completa de la
investigación en `docs/superpowers/HALLAZGOS-2026-08-05-rotacion-vertical.md`
y `docs/superpowers/HANDOFF-2026-08-05-rotacion-vertical-sin-resolver.md`.

**La salida real:** un plugin UXP dentro de Premiere que usa
`project.importFiles()` — el mismo código que usa Premiere cuando arrastras
un archivo a mano — sí respeta la rotación. Ese plugin, construido y
verificado con material real, vive en `uxp-plugin/`. El spec vigente es
`docs/superpowers/specs/2026-08-05-clasificador-video-uxp-design.md`.

**Qué se queda y por qué no se borra:**

- `xmeml.py` es el que quedó específicamente obsoleto — genera un formato
  que ya no es el camino de entrega a Premiere. No se borra porque podría
  reciclarse si en algún momento se necesita generar xmeml por otra razón
  (otro NLE, otro flujo), pero **no se debe usar para este proyecto.**
- `probe.py` (lectura de fps/rotación/duración vía `ffprobe`) sigue siendo
  lógica válida y reusable — la app externa (PySide6, todavía sin construir)
  va a necesitar exactamente este mismo cálculo de fps y rotación para el
  manifest (§11 del spec) y para las miniaturas del filmstrip (§13 del
  spec). No es código muerto, es candidato directo a mover/adaptar cuando
  se construya esa app.
- `models.py` (`ClipSpec`) y `rate.py` son utilidades chicas, ligadas al
  diseño de xmeml pero simples de adaptar o descartar cuando se defina el
  modelo de datos real de la app externa.

**Resumen:** ningún archivo de este paquete se importa desde `uxp-plugin/`
ni desde ningún camino activo del proyecto hoy. No corre en producción. Se
queda en el repo como referencia, no como código vivo.
