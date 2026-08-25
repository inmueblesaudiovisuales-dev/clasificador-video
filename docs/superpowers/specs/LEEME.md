# Los specs, y cuáles están construidos

Cada archivo `*-design.md` es una decisión de diseño acordada con Bruno: qué
se construye, qué NO, y **por qué se descartó lo que se descartó**. Esa última
parte es la que más vale — evita reabrir discusiones ya cerradas.

**Un spec no dice por sí mismo si su trabajo está hecho.** Esta tabla sí.

| Spec | ¿Construido? |
|---|---|
| `2026-08-05-clasificador-video-design.md` | ✅ |
| `2026-08-05-clasificador-video-uxp-design.md` | ✅ el plugin de Premiere |
| `2026-08-06-clasificador-video-app-externa-design.md` | ✅ |
| `2026-08-06-scrub-bar-interactiva-design.md` | ✅ |
| `2026-08-06-scrub-bar-regla-y-playhead-design.md` | ✅ |
| `2026-08-09-bins-por-camara-design.md` | ✅ |
| `2026-08-09-proyectos-y-revinculacion-design.md` | ✅ |
| **`2026-08-09-cuartos-rapidos-design.md`** | ❌ **NO** — aprobado por Bruno, sin plan ni código |
| `2026-08-15-agrupar-o-solo-etiquetar-design.md` | ✅ |
| `2026-08-15-modo-horizontal-design.md` | ✅ |
| `2026-08-18-bins-en-el-deshacer-design.md` | ✅ |
| `2026-08-20-cola-de-proxies-design.md` | ✅ |
| `2026-08-20-cuartos-mas-alla-del-nueve-design.md` | ✅ |
| `2026-08-20-orden-de-los-cuartos-design.md` | ✅ |
| `2026-08-20-las-flechas-siguen-lo-que-ves-design.md` | ✅ |
| `2026-08-20-abrir-sin-congelarse-design.md` | ✅ |
| `2026-08-22-proxies-adentro-design.md` | ✅ |
| **`2026-08-25-carpeta-de-proxies-elegible-design.md`** | ❌ **NO** — escrito, pendiente de revisión de Bruno |

**Pendientes: `cuartos-rapidos` y `carpeta-de-proxies-elegible`.**

`cuartos-rapidos`: crear muchos cuartos de un jalón,
con autocompletar y plantillas guardadas. Nace de que Bruno graba inmuebles y
los cuartos se repiten casa tras casa.

`carpeta-de-proxies-elegible` se escribió el 2026-08-25 y todavía tiene
una decisión abierta al final del documento.

Los specs sin archivo de plan al lado no están a medias: los chicos se
construyeron directo con TDD, sin pasar por un plan por fases.
