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
