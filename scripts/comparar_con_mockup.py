#!/usr/bin/env python3
"""Arnés de comparación mockup ↔ app (Candado 2 del plan de rediseño).

Renderiza el mockup HTML y la ventana real de la app al mismo tamaño y
escribe un PNG con las dos, lado a lado, para poder juzgar la fidelidad
visual de un vistazo en vez de por opinión.

    .venv/bin/python scripts/comparar_con_mockup.py --salida /tmp/comp.png

El mockup se rinde con Chrome sin cabeza. QtWebEngine se probó y se
descartó el 2026-08-08: no carga el file:// del mockup (loadFinished llega
con ok=False y grab() devuelve una imagen de 0x0).

Ver docs/superpowers/plans/2026-08-08-f1-f2-tokens-y-esqueleto.md
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MOCKUP = RAIZ / "docs" / "superpowers" / "mockups" / "rediseno-2026-08-08" / "mockup.html"
ANCHO, ALTO = 1600, 1000

CHROME_CANDIDATOS = [
    os.environ.get("CHROME_BIN", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    shutil.which("google-chrome") or "",
    shutil.which("chromium") or "",
]


def buscar_chrome() -> str:
    for ruta in CHROME_CANDIDATOS:
        if ruta and Path(ruta).exists():
            return ruta
    raise SystemExit("No encontré Chrome ni Chromium. Instalá uno o exportá CHROME_BIN.")


def html_aislado(html: str, pantalla: int) -> str:
    """Devuelve el HTML del mockup con un <style> y un <script> inyectados
    en el <head> que dejan visible una sola pantalla, pegada a la esquina.

    Se trabaja sobre una COPIA: el mockup original nunca se modifica.
    """
    inyeccion = (
        "<style>"
        "body{padding:0!important;gap:0!important;background:#000!important}"
        ".caption{display:none!important}"
        ".window{display:none!important}"
        ".window.__solo{display:flex!important;border-radius:0!important;"
        "box-shadow:none!important}"
        "</style>"
        "<script>document.addEventListener('DOMContentLoaded',function(){"
        f"document.querySelectorAll('.window')[{pantalla}]"
        ".classList.add('__solo');});</script>"
    )
    return html.replace("</head>", inyeccion + "</head>", 1)


def geometria_lienzo(a: tuple[int, int], b: tuple[int, int], separacion: int) -> tuple[int, int]:
    return a[0] + separacion + b[0], max(a[1], b[1])


def parsear_recorte(texto: str) -> tuple[int, int, int, int]:
    """`X,Y,ANCHO,ALTO` en coordenadas de la mitad izquierda (el mockup)."""
    partes = texto.split(",")
    if len(partes) != 4:
        raise SystemExit(f"--recorte espera X,Y,ANCHO,ALTO y recibió {texto!r}")
    try:
        x, y, ancho, alto = (int(p) for p in partes)
    except ValueError:
        raise SystemExit(f"--recorte espera cuatro enteros y recibió {texto!r}") from None
    if ancho <= 0 or alto <= 0:
        raise SystemExit("--recorte necesita ancho y alto positivos")
    return x, y, ancho, alto


def regiones_de_recorte(
    recorte: tuple[int, int, int, int], ancho_mitad: int, separacion: int
) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    """La MISMA region en las dos mitades: la de la derecha va corrida por el
    ancho de la izquierda mas la separacion.

    Existe porque la vista general no alcanza: la regresion de las tarjetas de
    la F2 no se veia en la comparacion completa y era obvia al ampliar.
    """
    x, y, ancho, alto = recorte
    return (x, y, ancho, alto), (x + ancho_mitad + separacion, y, ancho, alto)


def ampliar_recorte(lienzo: Path, recorte: tuple[int, int, int, int], zoom: int,
                    separacion: int = 40) -> None:
    """Reescribe el lienzo con las dos regiones equivalentes, ampliadas."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QImage, QPainter

    completo = QImage(str(lienzo))
    izq, der = regiones_de_recorte(recorte, ANCHO, separacion)
    trozos = [
        completo.copy(*region).scaled(
            region[2] * zoom, region[3] * zoom,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            # sin suavizado: al ampliar interesa ver el pixel como es, no
            # una version interpolada que disimula las diferencias
            Qt.TransformationMode.FastTransformation,
        )
        for region in (izq, der)
    ]
    ancho, alto = geometria_lienzo(
        (trozos[0].width(), trozos[0].height()),
        (trozos[1].width(), trozos[1].height()),
        separacion,
    )
    salida = QImage(ancho, alto, QImage.Format_RGB32)
    salida.fill(QColor("black"))
    p = QPainter(salida)
    p.drawImage(0, 0, trozos[0])
    p.drawImage(trozos[0].width() + separacion, 0, trozos[1])
    p.end()
    salida.save(str(lienzo))


def render_mockup(salida: Path, pantalla: int) -> None:
    copia = Path(tempfile.mkdtemp()) / "mockup_solo.html"
    copia.write_text(html_aislado(MOCKUP.read_text(encoding="utf-8"), pantalla), encoding="utf-8")
    subprocess.run(
        [
            buscar_chrome(),
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--force-device-scale-factor=1",
            f"--window-size={ANCHO},{ALTO}",
            "--virtual-time-budget=3000",
            f"--screenshot={salida}",
            f"file://{copia}",
        ],
        capture_output=True,  # Chrome escupe ruido irrelevante en stderr
        check=False,          # su codigo de salida no es confiable
    )
    if not salida.exists():
        raise SystemExit(f"Chrome no escribió {salida}")


def render_app(salida: Path) -> None:
    from PySide6.QtWidgets import QApplication

    from clasificador_video.app import configure_gl_surface_format
    from clasificador_video.ui.theme import build_stylesheet

    # `scripts/` no es un paquete y al correr `python scripts/x.py` el
    # sys.path[0] es `scripts/`, no la raiz del repo: el import va plano.
    # (`clasificador_video` si resuelve, porque el proyecto esta instalado
    # en modo editable en el venv.)
    from _datos_de_ejemplo import construir_ventana_de_ejemplo

    configure_gl_surface_format()
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setStyleSheet(build_stylesheet())
    from _datos_de_ejemplo import pintar_frame_de_ejemplo

    ventana = construir_ventana_de_ejemplo()
    ventana.resize(ANCHO, ALTO)
    ventana.show()
    app.processEvents()
    # DESPUES del resize: `VideoStage._place_overlays` corre en cada resize
    # del video y hace `scrim.lower()`, asi que un frame agregado antes
    # terminaria por encima del scrim en vez de debajo de todo.
    pintar_frame_de_ejemplo(ventana)
    app.processEvents()
    ventana.grab().save(str(salida))


def normalizar(imagen, ancho: int = ANCHO, alto: int = ALTO):
    """Lleva la imagen al tamaño lógico de referencia.

    Sin esto la comparación no sirve: en una pantalla Retina, `grab()`
    devuelve la ventana a 2x (3200x2000) mientras Chrome captura a 1x
    (1600x1000), y las dos mitades quedan a escalas distintas.
    """
    from PySide6.QtCore import Qt

    if imagen.width() == ancho and imagen.height() == alto:
        return imagen
    return imagen.scaled(
        ancho, alto, Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def componer(izq: Path, der: Path, salida: Path, separacion: int = 40) -> None:
    from PySide6.QtGui import QColor, QImage, QPainter

    a, b = normalizar(QImage(str(izq))), normalizar(QImage(str(der)))
    ancho, alto = geometria_lienzo((a.width(), a.height()), (b.width(), b.height()), separacion)
    lienzo = QImage(ancho, alto, QImage.Format_RGB32)
    lienzo.fill(QColor("black"))
    p = QPainter(lienzo)
    p.drawImage(0, 0, a)
    p.drawImage(a.width() + separacion, 0, b)
    p.end()
    lienzo.save(str(salida))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", required=True, type=Path)
    ap.add_argument("--pantalla", type=int, default=0, help="0 = modo clip, 1 = modo hoja")
    ap.add_argument(
        "--recorte",
        help="X,Y,ANCHO,ALTO en coordenadas del mockup: amplía la MISMA región "
             "de las dos mitades. La vista general no alcanza para juzgar detalle.",
    )
    ap.add_argument("--zoom", type=int, default=3, help="factor del recorte (default 3)")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp())
    izq, der = tmp / "mockup.png", tmp / "app.png"
    render_mockup(izq, args.pantalla)  # subproceso externo, antes de crear la QApplication
    render_app(der)                    # la unica QApplication del proceso vive aca
    componer(izq, der, args.salida)    # reusa esa misma QApplication
    if args.recorte:
        ampliar_recorte(args.salida, parsear_recorte(args.recorte), args.zoom)
    print(f"comparación escrita en {args.salida}")
    print("  izquierda = mockup  |  derecha = app")


if __name__ == "__main__":
    main()
