"""Rutas a los recursos empacados de Premiere.

PyInstaller copia ``recursos/`` dentro de ``sys._MEIPASS``; al correr
desde el repositorio los recursos se buscan relativos a su raíz. Sin Qt.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

RELATIVA = Path("recursos") / "premiere"

TEMPLATE_COLOR_LUTS_NOMBRE = "TemplateColorLuts.prproj"
TEMPLATE_PROXY_ADJUNTO_NOMBRE = "TemplateProxyAdjunto.prproj"
SONY_CUBE_NOMBRE = "SONY-SLOG3.cube"
DJI_CUBE_NOMBRE = "DJI-DLOGM.cube"


def carpeta_premiere() -> Path:
    """La carpeta ``recursos/premiere`` del repo o de la app instalada."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / RELATIVA
    return Path(__file__).resolve().parents[2] / RELATIVA


def template_color_luts() -> Path:
    """Ruta a la plantilla de Premiere con los LUTs validados."""
    return carpeta_premiere() / TEMPLATE_COLOR_LUTS_NOMBRE


def template_proxy_adjunto() -> Path:
    """Ruta al cierre real de Premiere para un proxy ya adjunto."""
    return carpeta_premiere() / TEMPLATE_PROXY_ADJUNTO_NOMBRE


def marca_de_proxy() -> Path:
    """Renderiza el glifo existente de Clipify sobre PNG transparente.

    El archivo vive en el temporal del sistema para funcionar igual desde el
    repo y desde PyInstaller, donde los recursos empacados son de sólo lectura.
    """
    destino = Path(tempfile.gettempdir()) / "clipify-marca-proxy.png"
    if destino.is_file():
        return destino
    from PySide6.QtGui import QColor, QImage, QPainter
    from clasificador_video.ui.marca import _pintar_glifo
    from clasificador_video.ui import theme

    imagen = QImage(72, 72, QImage.Format.Format_ARGB32_Premultiplied)
    imagen.fill(0)
    pintor = QPainter(imagen)
    pintor.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    _pintar_glifo(pintor, 72, QColor(theme.TEXT))
    pintor.end()
    if not imagen.save(str(destino), "PNG"):
        raise RuntimeError("No se pudo crear la marca de proxy de Clipify")
    return destino


def cube_de_camara(camara: str) -> Path | None:
    """El LUT maestro de ``camara``, o ``None`` si no corresponde uno."""
    nombre = {"sony": SONY_CUBE_NOMBRE, "dji": DJI_CUBE_NOMBRE}.get(camara)
    return carpeta_premiere() / nombre if nombre else None
