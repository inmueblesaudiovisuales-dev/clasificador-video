# Informe — Task 10: pantalla Revisar

## Alcance

Se agregó la pantalla separada de Revisar: rail de proyectos, hoja de clips,
filtros por estado, escalera con `↑`/`↓`, acceso a todo el rodaje y selector
superior Importar/Revisar/Armar y entregar. Armar queda intencionalmente como
un placeholder, sin funcionalidad de la fase 4.

## TDD

Primero se escribieron las pruebas UI de selección del rail, escalera,
disponibilidad de disco, rodaje completo, flecha sobre la tarjeta y el
switcher. La primera corrida fue RED por la importación esperada de
`pantalla_revisar`, que todavía no existía. Después de implementar lo mínimo,
la suite quedó verde:

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/ -q
```

Resultado: **36 passed in 0.67s**.

## Verificación visual

Se capturó `PantallaRevisar` offscreen y se inspeccionó el PNG. Se confirmó la
composición oscura y compacta: rail a la izquierda, switcher superior, filtros,
tarjetas y colores distintos para Descartada / Sin decidir / Elegida.

## Decisiones acotadas

- Un proyecto está disponible cuando existe al menos uno de sus clips. Esto
  permite progreso parcial con un SSD conectado de forma incompleta y queda
  comentado en el código para endurecerlo después si hiciera falta.
- Si no se deduce una carpeta común para el rodaje, el botón no hace nada. La
  interfaz para pedir la carpeta manualmente queda fuera de este Task y se deja
  comentario para evitar adivinar rutas.

## Fix round 1 — RED/GREEN

La revisión encontró cuatro huecos. Primero se añadieron pruebas para pedir una
carpeta inyectable cuando no hay una común, editar categoría, conservar color
de proyecto, navegar con `←`/`→` y pedir portadas solo para tarjetas visibles.
La corrida RED mostró cuatro fallas de API y navegación antes de implementar.

GREEN final:

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/ -q
```

Resultado: **41 passed in 1.52s**.

La portada usa el motor compartido `clasificador_video.thumbnails`, no widgets
de la UI normal: pide JPEG reducido (`economico=True`) y solo intenta cargar
tarjetas que intersectan el viewport. Se reutiliza su cache estable; no se
duplica criterio de extracción ni extensiones. También se capturó e inspeccionó
otra vez la pantalla offscreen, confirmando el selector de categoría oscuro,
el color estable del rail y el borde ámbar de la tarjeta actual.

## Fix round 2 — RED/GREEN

Se agregaron dos regresiones: una carpeta deducida pero inexistente (SSD
desconectado) debe abrir el selector manual antes de listar, y una categoría
nueva no se guarda letra por letra. La corrida RED tuvo las dos fallas
esperadas: `FileNotFoundError` al listar el SSD ausente y el prefijo `Ran`
persistido de inmediato.

Ahora se valida `is_dir()` antes de listar y el selector confirma la edición
con `editingFinished` (o una opción con `textActivated`), nunca con cambios de
cada tecla.

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests_portafolio/ -q
```

Resultado: **43 passed in 1.79s**.

## Fix round 3 — RED/GREEN

Se añadieron pruebas RED para persistir una decisión, reaplicar el filtro al
cambiar estado y distinguir 12 puntos de scrub para clips importados contra 3
para clips encontrados fuera de la secuencia. GREEN final: **46 passed in
1.80s** con `tests_portafolio/ -q`.

Revisar recibe la misma ruta `.cvportafolio` que Importar y guarda después de
decidir, cambiar categoría o sumar el rodaje. La portada visible sigue siendo
la única imagen que se carga ahora; `cantidad_miniaturas` deja explícita la
cantidad de puntos que el generador deberá producir al implementar scrub, sin
arrastrar widgets de la UI normal. Se capturó e inspeccionó otra vez la UI
offscreen.
